from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import UUID
from datetime import datetime

from app.dependencies import get_db, get_current_user
from app.db.mongo import get_mongo_db
from app.middleware.auth import decode_supabase_jwt
from app.models.user import User
from app.models.booking import Booking
from app.models.ride import Ride
from app.schemas.chat import ChatMessageOut, ChatHistoryResponse, UnreadCountResponse
from app.services import chat_service

router = APIRouter(prefix="/chat", tags=["Chat"])


# ─── WebSocket /chat/ws/{booking_id} ──────────
@router.websocket("/ws/{booking_id}")
async def websocket_chat(
    websocket: WebSocket,
    booking_id: UUID,
    token: str = Query(...),        # JWT passed as query param
    db: AsyncSession = Depends(get_db),
):
    """
    Real-time chat between passenger and driver.
    JWT passed as query param (WebSocket can't use headers).
    Cloud Run: 60-min timeout. Client sends ping every 25s.
    """
    # 1. Verify JWT manually
    try:
        payload = decode_supabase_jwt(token)
        supabase_uid = payload.get("sub")
    except HTTPException:
        await websocket.close(code=4001)
        return

    # 2. Get user from DB
    from sqlalchemy import select as sa_select
    result = await db.execute(
        sa_select(User).where(User.supabase_uid == supabase_uid)
    )
    user = result.scalar_one_or_none()
    if not user:
        await websocket.close(code=4001)
        return

    # 3. Verify user is booking participant
    try:
        booking = await chat_service.verify_participant(
            db=db,
            booking_id=booking_id,
            user_id=user.id,
        )
    except HTTPException:
        await websocket.close(code=4003)
        return

    # 4. Determine other participant
    ride_result = await db.execute(
        sa_select(Ride).where(Ride.id == booking.ride_id)
    )
    ride = ride_result.scalar_one()
    other_user_id = (
        ride.driver_id
        if booking.passenger_id == user.id
        else booking.passenger_id
    )

    # 5. Get MongoDB
    mongo_db = get_mongo_db()

    # 6. Mark existing messages as read (user opened chat)
    await chat_service.mark_as_read(mongo_db, booking_id, user.id)

    # 7. Handle WebSocket loop
    await chat_service.handle_websocket(
        websocket=websocket,
        booking_id=booking_id,
        user_id=user.id,
        other_user_id=other_user_id,
        mongo_db=mongo_db,
    )


# ─── GET /chat/{booking_id}/history ──────────
@router.get("/{booking_id}/history", response_model=ChatHistoryResponse)
async def get_chat_history(
    booking_id: UUID,
    limit: int = Query(default=50, ge=1, le=100),
    before: datetime | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Fetch chat history for a booking.
    Cursor-based pagination using created_at.
    Also marks all messages as read for current user.
    """
    # Verify participant
    await chat_service.verify_participant(
        db=db,
        booking_id=booking_id,
        user_id=current_user.id,
    )

    mongo_db = get_mongo_db()

    # Mark as read when history is fetched
    await chat_service.mark_as_read(mongo_db, booking_id, current_user.id)

    messages = await chat_service.get_history(
        mongo_db=mongo_db,
        booking_id=booking_id,
        before=before,
        limit=limit + 1,    # fetch one extra to check has_more
    )

    has_more = len(messages) > limit
    if has_more:
        messages = messages[:limit]

    # Reverse to return oldest first
    messages.reverse()

    return {
        "messages": messages,
        "has_more": has_more,
    }


# ─── GET /chat/unread-count ───────────────────
@router.get("/unread-count", response_model=dict)
async def get_unread_count(
    current_user: User = Depends(get_current_user),
):
    """Get total unread message count across all bookings."""
    mongo_db = get_mongo_db()

    unread_data = await chat_service.get_unread_counts(
        mongo_db=mongo_db,
        user_id=current_user.id,
    )

    total = sum(item["unread_count"] for item in unread_data)

    return {"data": {"unread_count": total}}


# ─── PUT /chat/{booking_id}/read ──────────────
@router.put("/{booking_id}/read", response_model=dict)
async def mark_chat_as_read(
    booking_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Explicitly mark all messages in this booking as read."""
    # Verify participant
    await chat_service.verify_participant(
        db=db,
        booking_id=booking_id,
        user_id=current_user.id,
    )

    mongo_db = get_mongo_db()
    await chat_service.mark_as_read(
        mongo_db=mongo_db,
        booking_id=booking_id,
        user_id=current_user.id,
    )

    return {"data": {"marked_read": True}}