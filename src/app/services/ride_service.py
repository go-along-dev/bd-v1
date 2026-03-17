from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func, cast, Date
from sqlalchemy.orm import selectinload
from fastapi import HTTPException, status
from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID
import httpx

from app.models.ride import Ride
from app.models.driver import Driver
from app.models.booking import Booking
from app.models.user import User
from app.schemas.ride import RideCreateRequest, RideUpdateRequest, RideSearchParams


# ─── Create Ride ──────────────────────────────
async def create_ride(
    db: AsyncSession,
    driver: Driver,
    data: RideCreateRequest,
) -> Ride:
    """
    Create a ride. Verifies driver approval, calculates
    distance via OSRM and fare via fare_engine.
    """
    from app.services import osrm_service
    from app.services.fare_engine import fare_engine

    # 1. Driver must be approved
    if driver.verification_status != "approved":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Driver must be approved before creating rides"
        )

    # 2. Departure must be in the future
    if data.departure_time <= datetime.now(timezone.utc):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Departure time must be in the future"
        )

    # 3. Seats must not exceed vehicle capacity
    if data.total_seats > driver.seat_capacity:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Seats cannot exceed vehicle capacity ({driver.seat_capacity})"
        )

    # 4. Get route from OSRM
    route = await osrm_service.get_route(
        src_lat=data.source_lat,
        src_lng=data.source_lng,
        dst_lat=data.dest_lat,
        dst_lng=data.dest_lng,
    )

    # 5. Calculate fare
    fare_result = await fare_engine.calculate_full_fare(
        db=db,
        distance_km=route["distance_km"],
        mileage_kmpl=float(driver.mileage_kmpl),
        seats=data.total_seats,
    )

    # 6. Create ride
    ride = Ride(
        driver_id         = driver.id,
        source_address    = data.source_address,
        source_lat        = data.source_lat,
        source_lng        = data.source_lng,
        source_city       = data.source_city,
        dest_address      = data.dest_address,
        dest_lat          = data.dest_lat,
        dest_lng          = data.dest_lng,
        dest_city         = data.dest_city,
        departure_time    = data.departure_time,
        total_seats       = data.total_seats,
        available_seats   = data.total_seats,
        total_distance_km = Decimal(str(route["distance_km"])),
        estimated_duration= route.get("duration_minutes"),
        route_geometry    = route.get("geometry"),
        total_fare        = fare_result["total_fare"],
        per_seat_fare     = fare_result["per_seat_fare"],
        status            = "active",
    )
    db.add(ride)
    await db.commit()
    await db.refresh(ride)
    return ride


# ─── Search Rides ─────────────────────────────
async def search_rides(
    db: AsyncSession,
    params: RideSearchParams,
) -> list[Ride]:
    """
    Bounding box search — no PostGIS needed.
    1 degree lat/lng ≈ 111 km.
    """
    radius_km = params.radius_km or 10.0
    offset    = radius_km / 111.0

    result = await db.execute(
        select(Ride)
        .options(selectinload(Ride.driver))
        .where(
            and_(
                Ride.status == "active",
                cast(Ride.departure_time, Date) == params.date,
                Ride.available_seats >= params.seats,
                Ride.source_lat.between(
                    params.source_lat - offset,
                    params.source_lat + offset
                ),
                Ride.source_lng.between(
                    params.source_lng - offset,
                    params.source_lng + offset
                ),
                Ride.dest_lat.between(
                    params.dest_lat - offset,
                    params.dest_lat + offset
                ),
                Ride.dest_lng.between(
                    params.dest_lng - offset,
                    params.dest_lng + offset
                ),
            )
        )
        .order_by(Ride.departure_time.asc())
        .limit(50)
    )
    return result.scalars().all()


# ─── Get Ride By ID ───────────────────────────
async def get_ride_by_id(
    db: AsyncSession,
    ride_id: UUID,
) -> Ride | None:
    """Fetch ride with driver info. Auto-transition stale active → departed."""
    result = await db.execute(
        select(Ride)
        .options(selectinload(Ride.driver))
        .where(Ride.id == ride_id)
    )
    ride = result.scalar_one_or_none()

    # Auto-transition if departure time has passed
    if (
        ride
        and ride.status == "active"
        and ride.departure_time <= datetime.now(timezone.utc)
    ):
        ride.status = "departed"
        await db.commit()

    return ride


# ─── Get Driver Rides ─────────────────────────
async def get_driver_rides(
    db: AsyncSession,
    driver: Driver,
    page: int = 1,
    per_page: int = 20,
) -> tuple[list[Ride], int]:
    offset = (page - 1) * per_page

    total_result = await db.execute(
        select(func.count(Ride.id)).where(Ride.driver_id == driver.id)
    )
    total = total_result.scalar()

    result = await db.execute(
        select(Ride)
        .where(Ride.driver_id == driver.id)
        .order_by(Ride.departure_time.desc())
        .limit(per_page)
        .offset(offset)
    )
    return result.scalars().all(), total


# ─── Get Ride Bookings ────────────────────────
async def get_ride_bookings(
    db: AsyncSession,
    ride_id: UUID,
    driver: Driver,
) -> list[Booking]:
    """All bookings for a ride — only callable by ride owner."""
    result = await db.execute(
        select(Ride).where(
            and_(Ride.id == ride_id, Ride.driver_id == driver.id)
        )
    )
    ride = result.scalar_one_or_none()

    if not ride:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ride not found or not yours"
        )

    bookings_result = await db.execute(
        select(Booking)
        .options(selectinload(Booking.passenger))
        .where(Booking.ride_id == ride_id)
    )
    return bookings_result.scalars().all()


# ─── Update Ride ──────────────────────────────
async def update_ride(
    db: AsyncSession,
    ride: Ride,
    data: RideUpdateRequest,
) -> Ride:
    """Edit ride if no confirmed bookings exist for departure_time changes."""
    # Check if bookings exist before allowing time changes
    if data.departure_time and data.departure_time != ride.departure_time:
        bookings_result = await db.execute(
            select(func.count(Booking.id)).where(
                and_(
                    Booking.ride_id == ride.id,
                    Booking.status == "confirmed"
                )
            )
        )
        if bookings_result.scalar() > 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot change departure time — active bookings exist"
            )

    # Apply updates
    if data.departure_time:
        ride.departure_time = data.departure_time
    if data.total_seats:
        booked = ride.total_seats - ride.available_seats
        ride.total_seats      = data.total_seats
        ride.available_seats  = max(0, data.total_seats - booked)
    if data.source_address:
        ride.source_address = data.source_address
    if data.dest_address:
        ride.dest_address = data.dest_address

    await db.commit()
    await db.refresh(ride)
    return ride


# ─── Cancel Ride ──────────────────────────────
async def cancel_ride(
    db: AsyncSession,
    ride: Ride,
) -> Ride:
    """Cancel ride and all confirmed bookings. Notify passengers."""
    from app.services import booking_service, notification_service

    if ride.status != "active":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot cancel a {ride.status} ride"
        )

    # 1. Set status cancelled
    ride.status = "cancelled"

    # 2. Cancel all bookings
    cancelled = await booking_service.cancel_bookings_for_ride(db, ride.id)

    # 3. Notify affected passengers
    for booking in cancelled:
        try:
            await notification_service.send_ride_cancelled(
                db=db,
                booking=booking,
            )
        except Exception:
            pass

    await db.commit()
    return ride


# ─── Depart Ride ──────────────────────────────
async def depart_ride(
    db: AsyncSession,
    ride: Ride,
) -> Ride:
    """Mark ride as departed. No new bookings accepted."""
    if ride.status != "active":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only active rides can be departed"
        )
    ride.status = "departed"
    await db.commit()
    await db.refresh(ride)
    return ride


# ─── Complete Ride ────────────────────────────
async def complete_ride(
    db: AsyncSession,
    ride: Ride,
) -> Ride:
    """Complete ride, complete bookings, notify passengers."""
    from app.services import booking_service, notification_service

    if ride.status not in ("active", "departed"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only active or departed rides can be completed"
        )

    # 1. Complete ride
    ride.status = "completed"

    # 2. Complete all bookings + get earnings
    completed, total_earnings = await booking_service.complete_bookings_for_ride(
        db, ride.id
    )

    # 3. Notify passengers
    for booking in completed:
        try:
            await notification_service.send_ride_completed(
                db=db,
                booking=booking,
            )
        except Exception:
            pass

    await db.commit()
    return ride


# ─── Geocode ──────────────────────────────────
async def geocode(query: str) -> list[dict]:
    """
    Proxy to Nominatim geocoding API.
    India-only results. Rate limit: 1 req/sec.
    """
    url = "https://nominatim.openstreetmap.org/search"
    params = {
        "q":            query,
        "format":       "json",
        "limit":        5,
        "countrycodes": "in",
    }
    headers = {
        "User-Agent": "GoAlong/1.0 (goalong.app)"
    }

    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(url, params=params, headers=headers)
        response.raise_for_status()
        data = response.json()

    return [
        {
            "display_name": item["display_name"],
            "lat":          float(item["lat"]),
            "lng":          float(item["lon"]),
        }
        for item in data
    ]

def build_ride_response(ride: Ride) -> dict:
    """Build ride response with driver_name and vehicle_info."""
    driver = ride.driver
    user   = driver.user if driver else None
    return {
        **ride.__dict__,
        "driver_name":  user.name if user else "Unknown",
        "vehicle_info": (
            f"{driver.vehicle_make} {driver.vehicle_model} · "
            f"{driver.vehicle_color or ''} · {driver.vehicle_number}"
        ) if driver else "Unknown",
    }