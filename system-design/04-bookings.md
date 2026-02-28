# Module 4: Bookings

## Overview

A booking represents a passenger reserving a seat (or seats) on a driver's ride. Bookings can be for the **full route** or a **partial route** (passenger joins at a mid-point). Fare is calculated proportionally based on the distance the passenger actually travels.

---

## Booking Flow

```
Passenger                         FastAPI                        Driver
   │                                 │                              │
   │  1. View ride details           │                              │
   │  GET /rides/{id}                │                              │
   │────────────────────────────────►│                              │
   │  ◄── Ride details + fare ──────│                              │
   │                                 │                              │
   │  2. Select pickup point         │                              │
   │     (full route or mid-route)   │                              │
   │                                 │                              │
   │  3. Book seat                   │                              │
   │  POST /bookings                 │                              │
   │  { ride_id, pickup_lat/lng,     │                              │
   │    seats_booked }               │                              │
   │────────────────────────────────►│                              │
   │                                 │── Validate seats available   │
   │                                 │── Calculate partial distance  │
   │                                 │   (OSRM: pickup → dest)      │
   │                                 │── Calculate proportional fare │
   │                                 │── Decrement available_seats   │
   │                                 │── Create booking record       │
   │                                 │── Send FCM to driver ────────►│
   │  ◄── Booking confirmed ────────│                              │
   │      { booking_id, fare }       │                              │
```

---

## Database: Bookings Table

```sql
CREATE TABLE bookings (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    ride_id         UUID NOT NULL REFERENCES rides(id) ON DELETE CASCADE,
    passenger_id    UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,

    -- Pickup point (may differ from ride source if partial route)
    pickup_address  TEXT NOT NULL,
    pickup_lat      DECIMAL(10,7) NOT NULL,
    pickup_lng      DECIMAL(10,7) NOT NULL,

    -- Distance & Fare
    distance_km     DECIMAL(8,2) NOT NULL,      -- Distance from pickup to ride destination
    fare            DECIMAL(10,2) NOT NULL,      -- Proportional fare for this segment
    seats_booked    INT NOT NULL DEFAULT 1,

    -- Status
    status          VARCHAR(20) NOT NULL DEFAULT 'confirmed',
                                                 -- 'confirmed' | 'cancelled' | 'completed'

    -- Timestamps
    booked_at       TIMESTAMPTZ DEFAULT NOW(),
    cancelled_at    TIMESTAMPTZ,

    -- Constraints
    CHECK (seats_booked BETWEEN 1 AND 4)
);

-- Partial unique: one active/confirmed booking per passenger per ride
CREATE UNIQUE INDEX idx_bookings_unique_active
    ON bookings(ride_id, passenger_id)
    WHERE status IN ('confirmed', 'active');

CREATE INDEX idx_bookings_ride ON bookings(ride_id);
CREATE INDEX idx_bookings_passenger ON bookings(passenger_id);
CREATE INDEX idx_bookings_status ON bookings(status);
```

### Things To Note:
- **Partial unique index on `(ride_id, passenger_id) WHERE status IN ('confirmed', 'active')`** — a passenger cannot have two active bookings on the same ride, but CAN rebook after cancellation.
- **`distance_km`** is the passenger's actual travel distance, not the ride's total distance. If pickup matches ride source, it equals `ride.total_distance_km`.
- **`fare`** is calculated at booking time using the fare engine's partial route logic.
- **`seats_booked` CHECK 1-4** — a single passenger can book at most 4 seats (group booking).

---

## API Endpoints

| Method | Endpoint                         | Auth     | Role      | Description                    |
|--------|----------------------------------|----------|-----------|--------------------------------|
| POST   | `/api/v1/bookings`               | Required | Passenger | Book a seat on a ride          |
| GET    | `/api/v1/bookings/my-bookings`   | Required | Any       | List user's bookings           |
| GET    | `/api/v1/bookings/{booking_id}`  | Required | Any       | Get booking details            |
| PUT    | `/api/v1/bookings/{booking_id}/cancel` | Required | Booking owner | Cancel booking        |

---

## Pydantic Schemas

```python
# schemas/booking.py

from pydantic import BaseModel, Field
from uuid import UUID
from datetime import datetime
from decimal import Decimal

class BookingCreateRequest(BaseModel):
    ride_id: UUID
    pickup_address: str
    pickup_lat: float = Field(..., ge=-90, le=90)
    pickup_lng: float = Field(..., ge=-180, le=180)
    seats_booked: int = Field(default=1, ge=1, le=4)

class BookingResponse(BaseModel):
    id: UUID
    ride_id: UUID
    passenger_id: UUID
    pickup_address: str
    distance_km: Decimal
    fare: Decimal
    seats_booked: int
    status: str
    booked_at: datetime
    cancelled_at: datetime | None

    # Ride summary (joined)
    ride_source: str
    ride_destination: str
    departure_time: datetime
    driver_name: str
    vehicle_info: str

    model_config = {"from_attributes": True}

class BookingListResponse(BaseModel):
    data: list[BookingResponse]
    total: int
    page: int
    per_page: int
```

---

## Service Layer

```python
# services/booking_service.py

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from app.models.booking import Booking
from app.models.ride import Ride
from app.models.user import User
from app.services.osrm_service import osrm_service
from app.services.fare_engine import fare_engine
from app.services.notification_service import notification_service
from fastapi import HTTPException
from datetime import datetime, timezone

async def create_booking(
    db: AsyncSession,
    passenger: User,
    data: BookingCreateRequest,
) -> Booking:
    """Book a seat on a ride. Calculates proportional fare based on pickup point."""

    # 1. Get the ride
    ride = await db.get(Ride, data.ride_id)
    if not ride:
        raise HTTPException(status_code=404, detail="Ride not found")

    # 2. Validations
    if ride.status != "active":
        raise HTTPException(status_code=400, detail="Ride is not active")

    if ride.departure_time <= datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="Ride has already departed")

    if ride.available_seats < data.seats_booked:
        raise HTTPException(
            status_code=400,
            detail=f"Only {ride.available_seats} seat(s) available"
        )

    # Prevent driver from booking their own ride
    driver = await db.execute(
        select(Driver).where(Driver.id == ride.driver_id)
    )
    driver = driver.scalar_one()
    if driver.user_id == passenger.id:
        raise HTTPException(status_code=400, detail="Cannot book your own ride")

    # Check if already booked
    existing = await db.execute(
        select(Booking).where(
            and_(
                Booking.ride_id == ride.id,
                Booking.passenger_id == passenger.id,
                Booking.status == "confirmed",
            )
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="You already have a booking on this ride")

    # 3. Calculate distance from pickup to destination
    distance_km = await osrm_service.get_distance_from_pickup(
        pickup_lat=data.pickup_lat,
        pickup_lng=data.pickup_lng,
        dst_lat=float(ride.dest_lat),
        dst_lng=float(ride.dest_lng),
    )

    # Cap distance to total ride distance (pickup can't be before source)
    if distance_km > float(ride.total_distance_km):
        distance_km = float(ride.total_distance_km)

    # 4. Calculate proportional fare
    fare_per_seat = fare_engine.calculate_partial_fare(
        total_fare=float(ride.per_seat_fare),  # Per seat fare for full route
        total_distance=float(ride.total_distance_km),
        passenger_distance=distance_km,
    )
    total_fare = round(fare_per_seat * data.seats_booked, 2)

    # 5. Create booking
    booking = Booking(
        ride_id=ride.id,
        passenger_id=passenger.id,
        pickup_address=data.pickup_address,
        pickup_lat=data.pickup_lat,
        pickup_lng=data.pickup_lng,
        distance_km=distance_km,
        fare=total_fare,
        seats_booked=data.seats_booked,
        status="confirmed",
    )
    db.add(booking)

    # 6. Decrement available seats
    ride.available_seats -= data.seats_booked
    ride.updated_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(booking)

    # 7. Notify driver via FCM
    await notification_service.send_push(
        user_id=driver.user_id,
        title="New Booking!",
        body=f"{passenger.name or 'A passenger'} booked {data.seats_booked} seat(s) on your ride to {ride.dest_address}.",
        data={"type": "new_booking", "booking_id": str(booking.id)},
    )

    return booking
```

---

## Cancellation Policy

GoAlong Phase 1 uses a simple, transparent cancellation policy:

| Condition                               | Rule                              |
|-----------------------------------------|-----------------------------------|
| Cancel **≥ 2 hours** before departure   | ✅ Free cancellation              |
| Cancel **< 2 hours** before departure   | ❌ Cancellation not allowed       |
| Driver cancels the ride                 | ✅ All bookings auto-cancelled    |
| Ride already departed or completed      | ❌ Cannot cancel                  |

### Why this policy:
- Simple to implement — no refund calculations needed (Phase 1 has no in-app payments)
- Fair to drivers — prevents last-minute no-shows
- Not punitive — 2-hour window gives plenty of flexibility

```python
# services/booking_service.py

from datetime import timedelta

CANCEL_WINDOW_HOURS = 2

async def cancel_booking(
    db: AsyncSession,
    booking: Booking,
    passenger: User,
) -> Booking:
    """Cancel a booking. Only allowed ≥ 2 hours before departure."""

    if booking.passenger_id != passenger.id:
        raise HTTPException(status_code=403, detail="Not your booking")

    if booking.status != "confirmed":
        raise HTTPException(status_code=400, detail="Booking is not active")

    # Get the ride to check departure time
    ride = await db.get(Ride, booking.ride_id)

    time_until_departure = ride.departure_time - datetime.now(timezone.utc)
    if time_until_departure < timedelta(hours=CANCEL_WINDOW_HOURS):
        raise HTTPException(
            status_code=400,
            detail=f"Cannot cancel within {CANCEL_WINDOW_HOURS} hours of departure"
        )

    # Cancel the booking
    booking.status = "cancelled"
    booking.cancelled_at = datetime.now(timezone.utc)

    # Restore available seats
    ride.available_seats += booking.seats_booked
    ride.updated_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(booking)

    # Notify driver
    await notification_service.send_push(
        user_id=(await db.execute(
            select(Driver.user_id).where(Driver.id == ride.driver_id)
        )).scalar_one(),
        title="Booking Cancelled",
        body=f"A passenger cancelled their booking on your ride to {ride.dest_address}. {booking.seats_booked} seat(s) are now available again.",
        data={"type": "booking_cancelled", "ride_id": str(ride.id)},
    )

    return booking
```

---

## Booking History

```python
async def get_passenger_bookings(
    db: AsyncSession,
    passenger: User,
    page: int = 1,
    per_page: int = 20,
) -> tuple[list[Booking], int]:
    """Get paginated booking history for a passenger."""

    # Count total
    count_query = select(func.count(Booking.id)).where(
        Booking.passenger_id == passenger.id
    )
    total = (await db.execute(count_query)).scalar()

    # Fetch paginated results
    query = (
        select(Booking)
        .where(Booking.passenger_id == passenger.id)
        .order_by(Booking.booked_at.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
    )
    result = await db.execute(query)
    bookings = result.scalars().all()

    return bookings, total
```

---

## Important Edge Cases

### 1. Race Condition on Seat Booking
Two passengers booking the last seat at the same time.

**Solution:** Use PostgreSQL row-level locking.

```python
# In create_booking, lock the ride row before checking seats:
ride = await db.execute(
    select(Ride)
    .where(Ride.id == data.ride_id)
    .with_for_update()          # Locks the row until transaction commits
)
ride = ride.scalar_one_or_none()
```

This ensures only one transaction can decrement `available_seats` at a time.

### 2. Passenger Picks Up a Point Not On the Route
The pickup point might be far from the actual route.

**Solution for MVP:** Accept any pickup point. The OSRM distance from pickup to destination is the authoritative distance. If the pickup is off-route, the distance will naturally be larger, and the fare will be proportionally fair.

**Phase 2 improvement:** Validate that the pickup point is within X km of the actual route polyline.

### 3. Booking After Ride is Full
If `available_seats = 0`, the booking should be rejected.

Already handled in the `create_booking` validation. The search also excludes rides with `available_seats = 0`.

### 4. Driver Cancels Ride After Bookings Exist
Covered in `03-rides.md` — all confirmed bookings are auto-cancelled and passengers are notified.

---

## Flutter — Booking Screen Flow

```
1. Passenger taps "Book" on a ride card
2. Booking screen opens:
   ├── Shows ride summary (driver, vehicle, time, per_seat_fare)
   ├── Map with route drawn
   ├── "Pickup Point" selector
   │   ├── Default: ride source (full route)
   │   └── "Select different pickup" → opens map picker
   ├── "Number of seats" selector (1–4, max = available_seats)
   ├── "Estimated Fare" (auto-calculated as they change pickup/seats)
   └── "Confirm Booking" button
3. On confirm → POST /bookings
4. Success → Navigate to booking confirmation screen
5. Chat with driver now available
```

---

## Things To Note

1. **No in-app payment in Phase 1.** Fare is informational — passengers pay the driver directly (cash, UPI, etc.). In-app payments can be added in Phase 2.

2. **Fare is locked at booking time.** Even if the admin changes fuel price or margin, the booking's fare doesn't change retroactively.

3. **`seats_booked` allows group bookings.** A passenger can book up to 4 seats. Fare = `per_seat_fare × seats_booked × (distance_ratio)`.

4. **The UNIQUE constraint on `(ride_id, passenger_id)` prevents double bookings.** If a passenger cancels and wants to rebook, the cancelled record exists but `status = 'cancelled'`. The check should be `status = 'confirmed'` to allow rebooking.

5. **Booking completion is tied to ride completion.** When a ride transitions to `completed`, all its `confirmed` bookings should also be marked `completed`. Handle this in the ride completion logic.

6. **Time zone awareness is critical.** All comparisons use UTC. Flutter displays local time but sends UTC to the API. Never compare naive datetimes.
