# =============================================================================
# schemas/chat.py — Chat Message Schemas
# =============================================================================
# See: system-design/10-api-contracts.md §8 "Chat Endpoints"
# See: system-design/06-chat.md for WebSocket protocol and MongoDB schema
#
# Chat messages are stored in MongoDB (not PostgreSQL).
# The WebSocket endpoint handles real-time; REST endpoints handle history.
#
# TODO: class ChatMessageOut(BaseModel):
#       - id: str          (MongoDB ObjectId as string)
#       - booking_id: UUID (chat thread = one booking)
#       - sender_id: UUID
#       - content: str
#       - created_at: datetime
#
# TODO: class ChatMessageIn(BaseModel):
#       Sent over WebSocket as JSON.
#       - booking_id: UUID
#       - content: str = Field(..., min_length=1, max_length=1000)
#
# TODO: class ChatHistoryResponse(BaseModel):
#       - messages: list[ChatMessageOut]
#       - has_more: bool  (cursor-based pagination, not offset)
#       See: system-design/06-chat.md §4 for cursor pagination on created_at
#
# TODO: class UnreadCountResponse(BaseModel):
#       - booking_id: UUID
#       - unread_count: int
#
# Connects with:
#   → app/routers/chat.py (WebSocket /chat/ws, GET /chat/{booking_id}/history, GET /chat/unread)
#   → app/services/chat_service.py
#
# work by adolf.
