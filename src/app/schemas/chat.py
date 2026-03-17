from pydantic import BaseModel, Field
from uuid import UUID
from datetime import datetime


# ─── Message Out (from server) ────────────────
class ChatMessageOut(BaseModel):
    id:         str       # MongoDB ObjectId as string
    booking_id: UUID
    sender_id:  UUID
    content:    str
    read:       bool
    created_at: datetime


# ─── Message In (from client over WebSocket) ──
class ChatMessageIn(BaseModel):
    booking_id: UUID
    content:    str = Field(..., min_length=1, max_length=1000)


# ─── Chat History Response ────────────────────
class ChatHistoryResponse(BaseModel):
    messages: list[ChatMessageOut]
    has_more: bool
    # Cursor-based pagination on created_at
    # Next page: GET /chat/{booking_id}/history?before=<oldest_created_at>


# ─── Unread Count Response ────────────────────
class UnreadCountResponse(BaseModel):
    booking_id:   UUID
    unread_count: int