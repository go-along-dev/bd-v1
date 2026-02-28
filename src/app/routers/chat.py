# =============================================================================
# routers/chat.py — Chat Endpoints (WebSocket + REST)
# =============================================================================
# See: system-design/10-api-contracts.md §8 "Chat Endpoints"
# See: system-design/06-chat.md for the complete chat architecture
#
# Prefix: /api/v1/chat
#
# Real-time chat between passenger and driver for a specific booking.
# WebSocket for live messaging, REST for history, unread counts, and mark-as-read.
#
# TODO: WebSocket /chat/ws/{booking_id}?token={jwt}
#       - Auth: JWT passed as query param (WebSocket can't use headers)
#       - Logic: Call chat_service.handle_websocket()
#         1. Verify JWT from query param (HS256 + JWT_SECRET)
#         2. Verify user is part of the booking (passenger or ride driver)
#         3. Add to ConnectionManager
#         4. Mark existing messages as read (user just opened chat)
#         5. On message received:
#            a. Validate with ChatMessageIn schema
#            b. Persist to MongoDB chat_messages collection
#            c. Forward to other participant if online
#            d. If offline → send FCM push via notification_service
#         6. On disconnect: remove from ConnectionManager
#       - IMPORTANT: Cloud Run has 60-min WebSocket timeout. Client sends ping every 25s.
#
# TODO: GET /chat/{booking_id}/history
#       - Requires: Bearer token (participant only)
#       - Query params: limit (default 50)
#       - Logic: Fetch chat history from MongoDB. Returns messages in ascending order.
#         Also marks all messages as read for current user.
#       - Response: {"data": list[ChatMessageOut]}
#
# TODO: GET /chat/unread-count
#       - Requires: Bearer token
#       - Logic: Get total unread message count across all bookings for current user
#       - Response: {"data": {"unread_count": int}}
#
# TODO: PUT /chat/{booking_id}/read
#       - Requires: Bearer token (participant only)
#       - Logic: Explicitly mark all messages in this booking's chat as read
#       - Response: {"data": {"marked_read": int}}
#
# Connects with:
#   → app/schemas/chat.py (ChatMessageIn, ChatMessageOut)
#   → app/services/chat_service.py (ConnectionManager, save_message, get_chat_history, mark_as_read)
#   → app/services/notification_service.py (FCM push for offline users)
#   → app/dependencies.py (get_current_user for REST, manual JWT verify for WebSocket)
#   → app/db/mongo.py (chat_messages collection)
#
# work by adolf.
