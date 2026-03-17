from fastapi import WebSocket, WebSocketDisconnect, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from datetime import datetime, timezone
from uuid import UUID
from typing import Any

from app.models.booking import Booking
from app.models.ride import Ride


# ─── Connection Manager ───────────────────────
class ConnectionManager:
    """
    In-memory registry of active WebSocket connections.
    Key: booking_id → {user_id: WebSocket}

    NOTE: Per-instance only. Cloud Run multi-instance = use Redis Pub/Sub in Phase 2.
    FCM push is the fallback for offline users.
    """

    def __init__(self):
        # { booking_id_str: { user_id_str: WebSocket } }
        self.active: dict[str, dict[str, WebSocket]] = {}

    async def connect(
        self,
        booking_id: UUID,
        user_id: UUID,
        websocket: WebSocket,
    ) -> None:
        await websocket.accept()
        bid = str(booking_id)
        uid = str(user_id)
        if bid not in self.active:
            self.active[bid] = {}
        self.active[bid][uid] = websocket

    def disconnect(self, booking_id: UUID, user_id: UUID) -> None:
        bid = str(booking_id)
        uid = str(user_id)
        if bid in self.active:
            self.active[bid].pop(uid, None)
            if not self.active[bid]:
                del self.active[bid]

    async def send_to_user(
        self,
        booking_id: UUID,
        target_user_id: UUID,
        message: dict,
    ) -> bool:
        """Send message to user if online. Returns True if delivered."""
        bid = str(booking_id)
        uid = str(target_user_id)
        ws = self.active.get(bid, {}).get(uid)
        if ws:
            await ws.send_json(message)
            return True
        return False

    def is_online(self, booking_id: UUID, user_id: UUID) -> bool:
        bid = str(booking_id)
        uid = str(user_id)
        return uid in self.active.get(bid, {})


# ─── Singleton Manager ────────────────────────
manager = ConnectionManager()


# ─── Verify Booking Participant ───────────────
async def verify_participant(
    db: AsyncSession,
    booking_id: UUID,
    user_id: UUID,
) -> Booking:
    """Ensure user is passenger or driver for this booking."""
    result = await db.execute(
        select(Booking).where(Booking.id == booking_id)
    )
    booking = result.scalar_one_or_none()

    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")

    if booking.status != "confirmed":
        raise HTTPException(
            status_code=400,
            detail="Chat only available for confirmed bookings"
        )

    # Get ride to check driver
    ride_result = await db.execute(
        select(Ride).where(Ride.id == booking.ride_id)
    )
    ride = ride_result.scalar_one_or_none()

    is_passenger = booking.passenger_id == user_id
    is_driver = ride and ride.driver_id == user_id

    if not is_passenger and not is_driver:
        raise HTTPException(status_code=403, detail="Not a participant")

    return booking


# ─── WebSocket Handler ────────────────────────
async def handle_websocket(
    websocket: WebSocket,
    booking_id: UUID,
    user_id: UUID,
    other_user_id: UUID,
    mongo_db,
):
    """
    Main WebSocket handler loop.
    1. Accept + register connection
    2. Receive messages → persist to MongoDB → forward or FCM
    3. On disconnect: unregister
    """
    await manager.connect(booking_id, user_id, websocket)

    try:
        while True:
            # Receive message from client
            data = await websocket.receive_json()
            content = data.get("content", "").strip()

            if not content:
                continue

            # Persist to MongoDB
            message = await persist_message(
                mongo_db=mongo_db,
                booking_id=booking_id,
                sender_id=user_id,
                content=content,
            )

            # Forward to recipient if online
            delivered = await manager.send_to_user(
                booking_id=booking_id,
                target_user_id=other_user_id,
                message=message,
            )

            # FCM fallback if recipient offline
            if not delivered:
                try:
                    from app.services import notification_service
                    await notification_service.send_chat_message(
                        receiver_id=other_user_id,
                        booking_id=booking_id,
                        content=content,
                    )
                except Exception:
                    pass

            # Echo back to sender with server timestamp
            await websocket.send_json(message)

    except WebSocketDisconnect:
        manager.disconnect(booking_id, user_id)


# ─── Persist Message ──────────────────────────
async def persist_message(
    mongo_db,
    booking_id: UUID,
    sender_id: UUID,
    content: str,
) -> dict:
    """Insert message into MongoDB chat_messages collection."""
    doc = {
        "booking_id": str(booking_id),
        "sender_id":  str(sender_id),
        "content":    content,
        "read":       False,
        "created_at": datetime.now(timezone.utc),
    }
    result = await mongo_db.chat_messages.insert_one(doc)
    doc["_id"] = str(result.inserted_id)
    doc["created_at"] = doc["created_at"].isoformat()
    return doc


# ─── Get Chat History ─────────────────────────
async def get_history(
    mongo_db,
    booking_id: UUID,
    before: datetime | None = None,
    limit: int = 50,
) -> list[dict]:
    """Cursor-based pagination — newest first."""
    query: dict[str, Any] = {"booking_id": str(booking_id)}

    if before:
        query["created_at"] = {"$lt": before}

    cursor = mongo_db.chat_messages.find(query) \
        .sort("created_at", -1) \
        .limit(limit)

    messages = []
    async for doc in cursor:
        doc["_id"] = str(doc["_id"])
        if isinstance(doc.get("created_at"), datetime):
            doc["created_at"] = doc["created_at"].isoformat()
        messages.append(doc)

    return messages


# ─── Get Unread Counts ────────────────────────
async def get_unread_counts(
    mongo_db,
    user_id: UUID,
) -> list[dict]:
    """
    Aggregation pipeline — unread messages per booking
    where sender is NOT the current user.
    """
    pipeline = [
        {
            "$match": {
                "sender_id": {"$ne": str(user_id)},
                "read": False,
            }
        },
        {
            "$group": {
                "_id": "$booking_id",
                "unread_count": {"$sum": 1},
            }
        },
        {
            "$project": {
                "booking_id": "$_id",
                "unread_count": 1,
                "_id": 0,
            }
        },
    ]

    results = []
    async for doc in mongo_db.chat_messages.aggregate(pipeline):
        results.append(doc)

    return results


# ─── Mark As Read ─────────────────────────────
async def mark_as_read(
    mongo_db,
    booking_id: UUID,
    user_id: UUID,
) -> None:
    """Mark all messages in a booking as read for the current user."""
    await mongo_db.chat_messages.update_many(
        {
            "booking_id": str(booking_id),
            "sender_id":  {"$ne": str(user_id)},
            "read":       False,
        },
        {"$set": {"read": True}},
    )