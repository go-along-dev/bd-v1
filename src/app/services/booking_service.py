from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from sqlalchemy.orm import selectinload
from fastapi import HTTPException, status
from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID

from app.models.booking import Booking
from app.models.ride import Ride
from app.models.user import User
from app.models.platform_config import PlatformConfig
from app.schemas.booking import BookingCreateRequest


# ─── Helper: Get Platform Config Value ────────
async def get_config(db: AsyncSession, key: str, default: str = "0") -> str:
    result = await db.execute(
        select(PlatformConfig).where(PlatformConfig.key == key)
    )
    config = result.scalar_one_or_none()
    return config.value if config else default


# ─── Create Booking ───────────────────────────
async def create_booking(
    db: AsyncSession,
    user: User,
    data: BookingCreateRequest,
) -> Booking:
    """
    CRITICAL — Handles race conditions via SELECT FOR UPDATE.
    All steps run in one atomic transaction.
    """
    async with db.begin():

        # 1. Lock ride row to prevent concurrent overbooking
        result = await db.execute(
            select(Ride)
            .where(Ride.id == data.ride_id)
            .with_for_update()
        )
        ride = result.scalar_one_or_none()

        if not ride:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Ride not found",
            )

        # 2a. Ride must be active
        if ride.status != "active":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Ride is not active",
            )

        # 2b. Ride must not have departed
        if ride.departure_time <= datetime.now(timezone.utc):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Ride has already departed",
            )

        # 2c. Enough seats available
        if ride.available_seats < data.seats_booked:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Only {ride.available_seats} seat(s) available",
            )

        # 2d. Driver cannot book their own ride
        driver_result = await db.execute(
            select(User).where(User.id == user.id)
        )
        if ride.driver_id == user.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="You cannot book your own ride",
            )

        # 2e. No duplicate confirmed booking
        existing = await db.execute(
            select(Booking).where(
                and_(
                    Booking.ride_id == data.ride_id,
                    Booking.passenger_id == user.id,
                    Booking.status == "confirmed",
                )
            )
        )
        if existing.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="You already have a booking for this ride",
            )

        # 3. Calculate distance from pickup to destination
        from app.services import osrm_service, fare_engine
        distance_km = await osrm_service.get_distance(
            src_lat=float(data.pickup_lat),
            src_lng=float(data.pickup_lng),
            dst_lat=float(ride.dest_lat),
            dst_lng=float(ride.dest_lng),
        )

        # 4. Calculate proportional fare
        fare = fare_engine.calculate_partial_fare(
            per_seat_fare=float(ride.per_seat_fare),
            total_distance_km=float(ride.total_distance_km),
            passenger_distance_km=distance_km,
        )

        # 5. Create booking
        booking = Booking(
            ride_id=data.ride_id,
            passenger_id=user.id,
            seats_booked=data.seats_booked,
            pickup_address=data.pickup_address,
            pickup_lat=data.pickup_lat,
            pickup_lng=data.pickup_lng,
            dropoff_address=data.dropoff_address,
            dropoff_lat=data.dropoff_lat,
            dropoff_lng=data.dropoff_lng,
            distance_km=distance_km,
            fare=fare,
            status="confirmed",
        )
        db.add(booking)

        # 6. Decrement available seats
        ride.available_seats -= data.seats_booked

        # 7. Commit handled by context manager

    await db.refresh(booking)

    # 8. Send FCM push to driver (after commit — non-critical)
    try:
        from app.services import notification_service
        await notification_service.send_booking_confirmed(
            db=db,
            ride=ride,
            booking=booking,
            passenger=user,
        )
    except Exception:
        pass  # Never fail booking because of notification failure

    return booking


# ─── Cancel Booking ───────────────────────────
async def cancel_booking(
    db: AsyncSession,
    user: User,
    booking_id: UUID,
    reason: str | None = None,
) -> None:
    result = await db.execute(
        select(Booking)
        .options(selectinload(Booking.ride))
        .where(Booking.id == booking_id)
    )
    booking = result.scalar_one_or_none()

    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")

    if booking.passenger_id != user.id:
        raise HTTPException(status_code=403, detail="Not your booking")

    if booking.status != "confirmed":
        raise HTTPException(
            status_code=400,
            detail=f"Cannot cancel a {booking.status} booking"
        )

    # Check cancellation window
    window_hours = float(await get_config(db, "cancellation_window_hours", "2"))
    ride = booking.ride
    time_until_departure = (
        ride.departure_time - datetime.now(timezone.utc)
    ).total_seconds() / 3600

    if time_until_departure < window_hours:
        raise HTTPException(
            status_code=400,
            detail=f"Cancellation window closed. Must cancel {window_hours}h before departure"
        )

    # Cancel booking
    booking.status = "cancelled"
    booking.cancelled_at = datetime.now(timezone.utc)
    if reason:
        booking.cancellation_reason = reason

    # Restore seats
    ride.available_seats += booking.seats_booked

    await db.commit()

    # Notify driver
    try:
        from app.services import notification_service
        await notification_service.send_booking_cancelled(
            db=db, booking=booking
        )
    except Exception:
        pass


# ─── Get User Bookings ────────────────────────
async def get_user_bookings(
    db: AsyncSession,
    user: User,
    page: int = 1,
    per_page: int = 20,
) -> tuple[list[Booking], int]:
    offset = (page - 1) * per_page

    total_result = await db.execute(
        select(func.count(Booking.id))
        .where(Booking.passenger_id == user.id)
    )
    total = total_result.scalar()

    result = await db.execute(
        select(Booking)
        .options(selectinload(Booking.ride))
        .where(Booking.passenger_id == user.id)
        .order_by(Booking.booked_at.desc())
        .limit(per_page)
        .offset(offset)
    )
    bookings = result.scalars().all()

    return bookings, total


# ─── Get Booking By ID ────────────────────────
async def get_booking_by_id(
    db: AsyncSession,
    booking_id: UUID,
) -> Booking | None:
    result = await db.execute(
        select(Booking)
        .options(
            selectinload(Booking.ride),
            selectinload(Booking.passenger),
        )
        .where(Booking.id == booking_id)
    )
    return result.scalar_one_or_none()


# ─── Complete Booking ─────────────────────────
async def complete_booking(
    db: AsyncSession,
    booking_id: UUID,
) -> None:
    result = await db.execute(
        select(Booking).where(Booking.id == booking_id)
    )
    booking = result.scalar_one_or_none()

    if booking and booking.status == "confirmed":
        booking.status = "completed"
        booking.completed_at = datetime.now(timezone.utc)
        await db.commit()


# ─── Cancel All Bookings For A Ride ──────────
async def cancel_bookings_for_ride(
    db: AsyncSession,
    ride_id: UUID,
) -> list[Booking]:
    """Called when driver cancels ride."""
    result = await db.execute(
        select(Booking).where(
            and_(
                Booking.ride_id == ride_id,
                Booking.status == "confirmed",
            )
        )
    )
    bookings = result.scalars().all()

    now = datetime.now(timezone.utc)
    for booking in bookings:
        booking.status = "cancelled"
        booking.cancelled_at = now
        booking.cancellation_reason = "Ride cancelled by driver"

    await db.commit()
    return bookings


# ─── Complete All Bookings For A Ride ────────
async def complete_bookings_for_ride(
    db: AsyncSession,
    ride_id: UUID,
) -> tuple[list[Booking], Decimal]:
    """Called when driver completes ride."""
    result = await db.execute(
        select(Booking).where(
            and_(
                Booking.ride_id == ride_id,
                Booking.status == "confirmed",
            )
        )
    )
    bookings = result.scalars().all()

    now = datetime.now(timezone.utc)
    total_earnings = Decimal("0.00")

    for booking in bookings:
        booking.status = "completed"
        booking.completed_at = now
        total_earnings += Decimal(str(booking.fare))

    await db.commit()
    return bookings, total_earnings