# Module 6: In-App Chat

## Overview

Chat in GoAlong is **booking-gated** — a passenger can only message a driver after making a confirmed booking. Each chat thread is tied to a specific booking. This prevents spam, protects driver privacy, and keeps conversations contextual.

| Rule                                          | Reason                                      |
|-----------------------------------------------|---------------------------------------------|
| Chat unlocks only after confirmed booking     | No unsolicited messages                     |
| One thread per booking                        | Conversations stay ride-specific             |
| Driver phone/email never exposed              | Privacy protection                          |
| Chat persisted even after ride completes      | Dispute resolution, accountability           |
| No voice calls, no video, no file sharing     | MVP — text only                             |

---

## Architecture

```
┌──────────────┐                 ┌──────────────────────────┐              ┌──────────────┐
│  Passenger   │                 │      FastAPI Server      │              │    Driver     │
│  (Flutter)   │                 │                          │              │  (Flutter)    │
└──────┬───────┘                 │  ┌────────────────────┐  │              └──────┬────────┘
       │                         │  │  WebSocket Manager │  │                     │
       │  ws://host/api/v1/      │  │                    │  │                     │
       │  chat/ws/{booking_id}   │  │  In-memory map:    │  │  ws://host/api/v1/  │
       │  ?token=jwt             │  │  booking_id →      │  │  chat/ws/{booking_id}
       │─────────────────────────►  │    [connection1,    │  ◄─────────────────────│
       │                         │  │     connection2]    │  │                     │
       │                         │  └─────────┬──────────┘  │                     │
       │                         │            │             │                     │
       │     {"msg": "Hello"}    │            │             │                     │
       │─────────────────────────►────────────┤             │                     │
       │                         │            │ Save to     │                     │
       │                         │            │ MongoDB     │                     │
       │                         │            │             │                     │
       │                         │            │ Forward     │                     │
       │                         │            ├─────────────────────────────────────►
       │                         │            │             │  {"msg": "Hello"}   │
       │                         │            │             │                     │
       │                         │  If driver offline:      │                     │
       │                         │  Send FCM push ──────────────────────────────────►
       │                         │                          │                     │
```

---

## Technology Choices

| Component        | Choice                     | Why                                            |
|------------------|----------------------------|------------------------------------------------|
| WebSocket Server | FastAPI built-in WebSocket  | No extra dependency, native async support      |
| Message Storage  | MongoDB (Atlas)             | Append-heavy, no joins, schema-flexible        |
| Offline Delivery | FCM push notification       | Standard solution for mobile                   |
| Connection Auth  | JWT token as query param    | WebSocket doesn't support headers in browsers  |

### Why NOT Firebase Realtime DB / Firestore for chat?
- Adds another service dependency
- Supabase + MongoDB + Firebase is too many data stores
- FastAPI WebSocket gives full control over auth, message format, and persistence
- For a booking-gated 1:1 chat, self-hosted WebSocket is simple enough

---

## MongoDB Schema

### Collection: `chat_messages`

```json
{
  "_id": "ObjectId (auto)",
  "booking_id": "uuid-string",
  "sender_id": "uuid-string",
  "receiver_id": "uuid-string",
  "message": "string (max 1000 chars)",
  "sent_at": "ISODate",
  "read": false
}
```

### Indexes
```javascript
// Create in MongoDB Atlas (or via Motor on startup)
db.chat_messages.createIndex({ "booking_id": 1, "sent_at": 1 })
db.chat_messages.createIndex({ "receiver_id": 1, "read": 1 })
```

### Things To Note:
- **No separate `conversations` collection needed.** Each booking IS a conversation. `booking_id` is the conversation ID.
- **`read` is a simple boolean.** When receiver opens the chat, mark all unread messages for that booking as read. No read receipts in Phase 1.
- **Message max length = 1000 characters.** Prevents abuse. Validate on both Flutter and backend.
- **No media messages.** Text only for Phase 1. MongoDB schema can accommodate media URLs later.

---

## MongoDB Connection (Motor)

```python
# db/mongo.py

from motor.motor_asyncio import AsyncIOMotorClient
from app.config import settings

class MongoDB:
    client: AsyncIOMotorClient = None
    db = None

    async def connect(self):
        self.client = AsyncIOMotorClient(settings.MONGO_URI)
        self.db = self.client["goalong"]
        # Create indexes on startup
        await self.db.chat_messages.create_index(
            [("booking_id", 1), ("sent_at", 1)]
        )
        await self.db.chat_messages.create_index(
            [("receiver_id", 1), ("read", 1)]
        )

    async def close(self):
        if self.client:
            self.client.close()

mongo = MongoDB()
```

### In `main.py`:
```python
from app.db.mongo import mongo

@app.on_event("startup")
async def startup():
    await mongo.connect()

@app.on_event("shutdown")
async def shutdown():
    await mongo.close()
```

---

## WebSocket Implementation

```python
# services/chat_service.py

from fastapi import WebSocket, WebSocketDisconnect
from datetime import datetime, timezone
from uuid import UUID
from app.db.mongo import mongo
from app.services.notification_service import notification_service

class ConnectionManager:
    """
    Manages active WebSocket connections grouped by booking_id.
    Each booking can have at most 2 connections (passenger + driver).
    """

    def __init__(self):
        # { booking_id: { user_id: WebSocket } }
        self.active_connections: dict[str, dict[str, WebSocket]] = {}

    async def connect(self, booking_id: str, user_id: str, websocket: WebSocket):
        await websocket.accept()
        if booking_id not in self.active_connections:
            self.active_connections[booking_id] = {}
        self.active_connections[booking_id][user_id] = websocket

    def disconnect(self, booking_id: str, user_id: str):
        if booking_id in self.active_connections:
            self.active_connections[booking_id].pop(user_id, None)
            if not self.active_connections[booking_id]:
                del self.active_connections[booking_id]

    async def send_to_user(self, booking_id: str, user_id: str, message: dict):
        """Send message to a specific user if they're connected."""
        connections = self.active_connections.get(booking_id, {})
        ws = connections.get(user_id)
        if ws:
            await ws.send_json(message)
            return True
        return False

    def is_online(self, booking_id: str, user_id: str) -> bool:
        return user_id in self.active_connections.get(booking_id, {})


manager = ConnectionManager()


async def save_message(
    booking_id: str,
    sender_id: str,
    receiver_id: str,
    message: str,
) -> dict:
    """Save message to MongoDB and return the saved document."""
    doc = {
        "booking_id": booking_id,
        "sender_id": sender_id,
        "receiver_id": receiver_id,
        "message": message,
        "sent_at": datetime.now(timezone.utc),
        "read": False,
    }
    result = await mongo.db.chat_messages.insert_one(doc)
    doc["_id"] = str(result.inserted_id)
    return doc


async def get_chat_history(booking_id: str, limit: int = 50, before=None) -> list:
    """
    Fetch chat history for a booking.
    Returns messages in chronological order (oldest first).
    Supports cursor-based pagination via 'before' timestamp.
    """
    query = {"booking_id": booking_id}
    if before:
        query["sent_at"] = {"$lt": before}

    cursor = (
        mongo.db.chat_messages
        .find(query)
        .sort("sent_at", -1)    # Newest first for pagination
        .limit(limit)
    )
    messages = await cursor.to_list(length=limit)
    messages.reverse()          # Return oldest first for display

    # Convert ObjectId to string
    for msg in messages:
        msg["_id"] = str(msg["_id"])

    return messages


async def mark_as_read(booking_id: str, reader_id: str):
    """Mark all messages to this user in this booking as read."""
    await mongo.db.chat_messages.update_many(
        {
            "booking_id": booking_id,
            "receiver_id": reader_id,
            "read": False,
        },
        {"$set": {"read": True}},
    )


async def get_unread_count(user_id: str) -> int:
    """Get total unread message count across all bookings for a user."""
    count = await mongo.db.chat_messages.count_documents({
        "receiver_id": user_id,
        "read": False,
    })
    return count
```

---

## WebSocket Router

```python
# routers/chat.py

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException, Query
from app.services.chat_service import manager, save_message, get_chat_history, mark_as_read, get_unread_count
from app.services.notification_service import notification_service
from app.middleware.auth import verify_jwt_token
from app.models.booking import Booking
from app.models.driver import Driver
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

router = APIRouter(prefix="/api/v1/chat", tags=["chat"])


async def _validate_chat_access(db: AsyncSession, booking_id: str, user_id: str):
    """
    Verify that the user is either the passenger or the driver for this booking.
    This is the booking-gate enforcement.
    """
    booking = await db.execute(
        select(Booking).where(Booking.id == booking_id)
    )
    booking = booking.scalar_one_or_none()

    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")

    if booking.status != "confirmed":
        raise HTTPException(status_code=403, detail="Chat is only available for confirmed bookings")

    # Check if user is the passenger
    if str(booking.passenger_id) == user_id:
        # Get driver's user_id as the other party
        ride = await db.get(Ride, booking.ride_id)
        driver = await db.execute(
            select(Driver).where(Driver.id == ride.driver_id)
        )
        driver = driver.scalar_one()
        return str(booking.passenger_id), str(driver.user_id)

    # Check if user is the driver
    ride = await db.get(Ride, booking.ride_id)
    driver = await db.execute(
        select(Driver).where(Driver.id == ride.driver_id)
    )
    driver = driver.scalar_one()
    if str(driver.user_id) == user_id:
        return str(driver.user_id), str(booking.passenger_id)

    raise HTTPException(status_code=403, detail="You are not part of this booking")


@router.websocket("/ws/{booking_id}")
async def websocket_chat(
    websocket: WebSocket,
    booking_id: str,
    token: str = Query(...),       # JWT passed as query parameter
    db: AsyncSession = Depends(get_db),
):
    """
    WebSocket endpoint for real-time chat.

    Connection URL: ws://host/api/v1/chat/ws/{booking_id}?token=<jwt>
    """

    # 1. Authenticate
    try:
        user = await verify_jwt_token(token, db)
    except Exception:
        await websocket.close(code=4001, reason="Authentication failed")
        return

    user_id = str(user.id)

    # 2. Validate booking access
    try:
        sender_id, receiver_id = await _validate_chat_access(db, booking_id, user_id)
    except HTTPException as e:
        await websocket.close(code=4003, reason=e.detail)
        return

    # 3. Connect
    await manager.connect(booking_id, user_id, websocket)

    # 4. Mark existing messages as read (user just opened the chat)
    await mark_as_read(booking_id, user_id)

    try:
        while True:
            # 5. Receive message
            data = await websocket.receive_json()
            message_text = data.get("message", "").strip()

            if not message_text or len(message_text) > 1000:
                continue  # Silently ignore empty or too-long messages

            # 6. Save to MongoDB
            saved_msg = await save_message(
                booking_id=booking_id,
                sender_id=sender_id,
                receiver_id=receiver_id,
                message=message_text,
            )

            # 7. Prepare response payload
            payload = {
                "id": saved_msg["_id"],
                "booking_id": booking_id,
                "sender_id": sender_id,
                "message": message_text,
                "sent_at": saved_msg["sent_at"].isoformat(),
            }

            # 8. Forward to receiver (if online)
            delivered = await manager.send_to_user(
                booking_id, receiver_id, payload
            )

            # 9. If receiver is offline, send FCM push
            if not delivered:
                await notification_service.send_push(
                    user_id=receiver_id,
                    title="New Message",
                    body=f"{user.name or 'Someone'}: {message_text[:100]}",
                    data={
                        "type": "chat_message",
                        "booking_id": booking_id,
                    },
                )

            # 10. Echo back to sender (confirmation)
            await websocket.send_json({**payload, "status": "sent"})

    except WebSocketDisconnect:
        manager.disconnect(booking_id, user_id)


# REST endpoints for chat history

@router.get("/{booking_id}/history")
async def chat_history(
    booking_id: str,
    limit: int = 50,
    current_user=Depends(get_current_user),
    db=Depends(get_db),
):
    """Fetch chat history for a booking. Used when opening chat screen."""

    # Validate access
    await _validate_chat_access(db, booking_id, str(current_user.id))

    messages = await get_chat_history(booking_id, limit=limit)

    # Mark as read
    await mark_as_read(booking_id, str(current_user.id))

    return {"data": messages}


@router.get("/unread-count")
async def unread_message_count(
    current_user=Depends(get_current_user),
):
    """Get total unread message count for the current user. Used for badge display."""
    count = await get_unread_count(str(current_user.id))
    return {"data": {"unread_count": count}}


@router.put("/{booking_id}/read")
async def mark_messages_read(
    booking_id: str,
    current_user=Depends(get_current_user),
    db=Depends(get_db),
):
    """Explicitly mark all messages in a booking chat as read for the current user."""
    await _validate_chat_access(db, booking_id, str(current_user.id))
    modified = await mark_as_read(booking_id, str(current_user.id))
    return {"data": {"marked_read": modified}}
```

---

## Flutter WebSocket Client

```dart
// services/websocket_service.dart

import 'dart:convert';
import 'package:web_socket_channel/web_socket_channel.dart';
import 'package:supabase_flutter/supabase_flutter.dart';

class ChatService {
  WebSocketChannel? _channel;
  final String _baseWsUrl;

  ChatService(this._baseWsUrl); // e.g., "wss://your-app.run.app"

  /// Connect to a chat room for a specific booking
  void connect({
    required String bookingId,
    required Function(Map<String, dynamic>) onMessage,
    required Function() onDisconnect,
  }) {
    final token = Supabase.instance.client.auth.currentSession?.accessToken;
    if (token == null) throw Exception('Not authenticated');

    final uri = Uri.parse(
      '$_baseWsUrl/api/v1/chat/ws/$bookingId?token=$token'
    );

    _channel = WebSocketChannel.connect(uri);

    _channel!.stream.listen(
      (data) {
        final message = jsonDecode(data as String);
        onMessage(message);
      },
      onDone: onDisconnect,
      onError: (error) {
        print('WebSocket error: $error');
        onDisconnect();
      },
    );
  }

  /// Send a text message
  void sendMessage(String text) {
    if (_channel == null) return;
    _channel!.sink.add(jsonEncode({'message': text}));
  }

  /// Disconnect
  void disconnect() {
    _channel?.sink.close();
    _channel = null;
  }
}
```

### Flutter Chat Screen (Simplified)

```dart
// screens/chat/chat_screen.dart

class ChatScreen extends ConsumerStatefulWidget {
  final String bookingId;
  const ChatScreen({required this.bookingId});

  @override
  ConsumerState<ChatScreen> createState() => _ChatScreenState();
}

class _ChatScreenState extends ConsumerState<ChatScreen> {
  final _controller = TextEditingController();
  final _messages = <Map<String, dynamic>>[];
  late ChatService _chatService;

  @override
  void initState() {
    super.initState();
    _loadHistory();
    _connectWebSocket();
  }

  Future<void> _loadHistory() async {
    final response = await ref.read(apiClientProvider).dio.get(
      '/chat/${widget.bookingId}/history',
    );
    setState(() {
      _messages.addAll(
        List<Map<String, dynamic>>.from(response.data['data']),
      );
    });
  }

  void _connectWebSocket() {
    _chatService = ChatService('wss://your-app.run.app');
    _chatService.connect(
      bookingId: widget.bookingId,
      onMessage: (msg) {
        setState(() => _messages.add(msg));
        // Auto-scroll to bottom
      },
      onDisconnect: () {
        // Show "reconnecting..." banner, attempt reconnect after delay
      },
    );
  }

  void _sendMessage() {
    final text = _controller.text.trim();
    if (text.isEmpty) return;
    _chatService.sendMessage(text);
    _controller.clear();
  }

  @override
  void dispose() {
    _chatService.disconnect();
    _controller.dispose();
    super.dispose();
  }

  // ... build method with ListView for messages + TextField + send button
}
```

---

## Chat List Screen

Passengers and drivers need a "Messages" tab showing all their active chat threads.

```python
# routers/chat.py

@router.get("/my-chats")
async def my_chats(
    current_user=Depends(get_current_user),
    db=Depends(get_db),
):
    """
    Get list of active chats for the current user.
    Returns bookings with their last message and unread count.
    """
    user_id = str(current_user.id)

    # Get all confirmed bookings where user is passenger or driver
    # ... query bookings joined with rides and drivers ...

    # For each booking, get the last message from MongoDB
    chats = []
    for booking in bookings:
        last_msg = await mongo.db.chat_messages.find_one(
            {"booking_id": str(booking.id)},
            sort=[("sent_at", -1)],
        )
        unread = await mongo.db.chat_messages.count_documents({
            "booking_id": str(booking.id),
            "receiver_id": user_id,
            "read": False,
        })
        chats.append({
            "booking_id": str(booking.id),
            "other_user_name": "...",   # Passenger or driver name
            "ride_destination": "...",
            "last_message": last_msg["message"] if last_msg else None,
            "last_message_time": last_msg["sent_at"].isoformat() if last_msg else None,
            "unread_count": unread,
        })

    # Sort by last_message_time descending
    chats.sort(key=lambda x: x["last_message_time"] or "", reverse=True)

    return {"data": chats}
```

---

## WebSocket on Cloud Run — Important Notes

Cloud Run supports WebSocket connections, but with constraints:

| Constraint                    | Detail                                            |
|-------------------------------|---------------------------------------------------|
| **Max connection duration**   | 3600 seconds (1 hour) by default                  |
| **Idle timeout**              | Connection closed if no data for 10 minutes        |
| **Scaling**                   | Multiple instances = connections on different servers |

### Handling These Constraints:

**1. Idle Timeout — Send Ping/Pong**
```python
# In the WebSocket loop, add periodic ping
import asyncio

async def websocket_chat(websocket, ...):
    # ... connection setup ...

    async def ping_loop():
        while True:
            await asyncio.sleep(30)  # Every 30 seconds
            try:
                await websocket.send_json({"type": "ping"})
            except:
                break

    ping_task = asyncio.create_task(ping_loop())

    try:
        while True:
            data = await websocket.receive_json()
            if data.get("type") == "pong":
                continue  # Heartbeat response, ignore
            # ... handle message ...
    finally:
        ping_task.cancel()
```

**2. Multi-Instance — Sticky Sessions or Accept Limitation**

For MVP (1-3 instances), the chance of passenger and driver being on different instances is manageable. The system already handles offline delivery via FCM.

**For MVP:** Accept that real-time delivery might occasionally miss if users are on different instances. FCM push ensures message is not lost. When the user opens the chat, history is loaded from MongoDB.

**Phase 2 upgrade:** Use Redis Pub/Sub to broadcast messages across instances.

**3. Reconnection on Client**

Flutter should auto-reconnect when WebSocket drops:
```dart
void _connectWithRetry() {
  _chatService.connect(
    bookingId: widget.bookingId,
    onMessage: (msg) => setState(() => _messages.add(msg)),
    onDisconnect: () {
      // Wait 3 seconds and reconnect
      Future.delayed(const Duration(seconds: 3), () {
        if (mounted) _connectWithRetry();
      });
    },
  );
}
```

---

## Things To Note

1. **WebSocket auth uses query param, not header.** This is standard — WebSocket protocol doesn't support custom headers in browsers. The `?token=jwt` approach is used by Slack, Discord, and most real-time apps.

2. **Messages are persisted BEFORE forwarding.** If the forward fails (recipient offline, connection dropped), the message is safe in MongoDB. It's loaded when the user opens chat history.

3. **FCM push for offline users is essential.** Without it, offline users wouldn't know they have a message until they open the app and check. The push notification triggers them to open the chat.

4. **Chat is disabled after ride completion or booking cancellation.** If `booking.status != 'confirmed'`, the WebSocket connection is rejected. Keep this simple — once a ride is done, chat is read-only (load history, but no new messages).

5. **No typing indicators in Phase 1.** Adds complexity with no real value for a ride-sharing chat. Users send practical messages like "I'm at the pickup point" — they don't need to see typing bubbles.

6. **Rate limiting on messages.** In the WebSocket loop, add a simple rate limit: max 1 message per second per user. Prevents spam flooding.

7. **MongoDB Atlas free tier (M0) is 512 MB.** At ~200 bytes per message, that's ~2.5 million messages. More than enough for MVP.
