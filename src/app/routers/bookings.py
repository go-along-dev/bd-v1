from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID

from app.dependencies import get_db, get_current_user, get_pagination
from app.schemas.booking import (
    BookingCreateRequest,
    BookingResponse,
    BookingCancelRequest,
)
from app.services import booking_service
from app.models.user import User

router = APIRouter(prefix="/bookings", tags=["Bookings"])


# ─── POST /bookings ───────────────────────────
@router.post(
    "",
    response_model=BookingResponse,
    status_code=status.HTTP_201_CREATED
)
async def create_booking(
    payload: BookingCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Book a seat on a ride.
    CRITICAL: Uses SELECT FOR UPDATE to prevent race conditions.
    Calculates partial fare based on pickup → destination distance.
    """
    return await booking_service.create_booking(
        db=db,
        user=current_user,
        data=payload,
    )


# ─── GET /bookings ────────────────────────────
@router.get("", response_model=dict)
async def get_my_bookings(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    pagination: dict = Depends(get_pagination),
):
    """Get all bookings for the current user as passenger."""
    bookings, total = await booking_service.get_user_bookings(
        db=db,
        user=current_user,
        page=pagination["page"],
        per_page=pagination["per_page"],
    )
    return {
        "data":     [BookingResponse.model_validate(b) for b in bookings],
        "total":    total,
        "page":     pagination["page"],
        "per_page": pagination["per_page"],
    }


# ─── GET /bookings/{booking_id} ───────────────
@router.get("/{booking_id}", response_model=BookingResponse)
async def get_booking(
    booking_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a specific booking. Only accessible by booking owner or ride driver."""
    booking = await booking_service.get_booking_by_id(db, booking_id)

    if not booking:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Booking not found"
        )

    # Only passenger or ride's driver can view
    is_passenger = booking.passenger_id == current_user.id
    is_driver = booking.ride.driver_id == current_user.id

    if not is_passenger and not is_driver:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )

    return booking


# ─── DELETE /bookings/{booking_id} ────────────
@router.delete("/{booking_id}", response_model=dict)
async def cancel_booking(
    booking_id: UUID,
    payload: BookingCancelRequest = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Cancel a booking.
    Only allowed if departure_time - now() > cancellation_window_hours.
    Restores seats to ride. Notifies driver via FCM.
    """
    await booking_service.cancel_booking(
        db=db,
        user=current_user,
        booking_id=booking_id,
        reason=payload.cancellation_reason if payload else None,
    )
    return {"message": "Booking cancelled successfully"}