# Module 5: Fare Engine

## Overview

The fare engine is a **pure calculation module** — no database tables, no external API calls, no side effects. It takes inputs (distance, mileage, seats, fuel price, margin) and produces a fare. It's used by two other modules:

| Called By           | When                                  | Function Used              |
|---------------------|---------------------------------------|----------------------------|
| **Ride Module**     | Driver creates a ride                 | `calculate_full_fare()`    |
| **Booking Module**  | Passenger books a partial route seat  | `calculate_partial_fare()` |

---

## How Pricing Works

### Full Route Fare

The total cost of the ride is derived from **actual fuel cost** shared among passengers, plus a platform margin.

```
    ┌───────────────────────────────────────────────┐
    │              FARE BREAKDOWN                    │
    │                                               │
    │  Distance: 150 km                             │
    │  Vehicle Mileage: 15 km/l                     │
    │  Fuel Price: ₹105/litre                       │
    │  Seats Offered: 3                             │
    │  Platform Margin: 15%                         │
    │                                               │
    │  Fuel Required = 150 ÷ 15 = 10 litres         │
    │  Fuel Cost     = 10 × ₹105 = ₹1,050           │
    │  Base Per Seat = ₹1,050 ÷ 3 = ₹350            │
    │  Margin        = ₹350 × 0.15 = ₹52.50         │
    │  Per Seat Fare = ₹350 + ₹52.50 = ₹402.50      │
    │                                               │
    │  Total Fare    = ₹402.50 × 3 = ₹1,207.50      │
    └───────────────────────────────────────────────┘
```

### Partial Route Fare

If a passenger boards mid-route, they pay proportionally for the distance they travel.

```
    ┌───────────────────────────────────────────────┐
    │           PARTIAL ROUTE EXAMPLE                │
    │                                               │
    │  Full Route: Bangalore → Mysore (150 km)       │
    │  Per Seat Fare (full): ₹402.50                 │
    │                                               │
    │  Passenger boards at Ramanagara (60 km mark)   │
    │  Passenger's distance: 150 - 60 = 90 km        │
    │                                               │
    │  Actually: OSRM calculates Ramanagara → Mysore │
    │  OSRM says: 95 km (road distance)              │
    │                                               │
    │  Rate per km = ₹402.50 ÷ 150 = ₹2.68/km       │
    │  Passenger fare = ₹2.68 × 95 = ₹254.87         │
    └───────────────────────────────────────────────┘
```

---

## Configuration — Platform Config Table

Fuel price and margin percentage are **admin-configurable**, not hardcoded.

```sql
CREATE TABLE platform_config (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    key         VARCHAR(50) UNIQUE NOT NULL,
    value       TEXT NOT NULL,
    description TEXT,
    updated_at  TIMESTAMPTZ DEFAULT NOW(),
    updated_by  UUID REFERENCES users(id)
);

-- Seed data
INSERT INTO platform_config (key, value, description) VALUES
    ('fuel_price_per_litre', '105.00', 'Current petrol price in INR per litre'),
    ('platform_margin_pct', '15', 'Platform margin percentage on top of fuel cost share'),
    ('min_fare', '50.00', 'Minimum fare per seat regardless of distance'),
    ('fare_rounding', '5', 'Round fare to nearest X rupees');
```

### Things To Note:
- **Fuel price should be updated regularly** by admin. India's petrol price changes every day. Admin updates it weekly or bi-weekly.
- **Margin percentage** is the platform's earning on each seat. 15% is a reasonable starting point. Can be adjusted based on competitive analysis.
- **Minimum fare** prevents absurdly low fares for very short distances.
- **Fare rounding** makes prices look cleaner. ₹402.50 → ₹405. Set to `1` to disable rounding.

---

## Implementation

```python
# services/fare_engine.py

from decimal import Decimal, ROUND_HALF_UP
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.platform_config import PlatformConfig

class FareEngine:
    """
    Rule-based fare calculation engine.
    No AI. No dynamic pricing. Transparent and predictable.
    """

    def __init__(self):
        # Defaults — overridden by DB config on each call
        self._fuel_price = Decimal("105.00")
        self._margin_pct = Decimal("15")
        self._min_fare = Decimal("50.00")
        self._fare_rounding = Decimal("5")

    async def load_config(self, db: AsyncSession):
        """Load current config values from platform_config table."""
        result = await db.execute(select(PlatformConfig))
        configs = {row.key: row.value for row in result.scalars().all()}

        self._fuel_price = Decimal(configs.get("fuel_price_per_litre", "105.00"))
        self._margin_pct = Decimal(configs.get("platform_margin_pct", "15"))
        self._min_fare = Decimal(configs.get("min_fare", "50.00"))
        self._fare_rounding = Decimal(configs.get("fare_rounding", "5"))

    async def calculate_full_fare(
        self,
        db: AsyncSession,
        distance_km: float,
        mileage_kmpl: float,
        seats: int,
    ) -> dict:
        """
        Calculate fare for a complete route.

        Args:
            distance_km:  Total driving distance (from OSRM)
            mileage_kmpl: Vehicle's fuel efficiency (from driver profile)
            seats:        Number of seats offered

        Returns:
            {
                "total_fare": Decimal,
                "per_seat_fare": Decimal,
                "fuel_cost": Decimal,
                "fuel_required_litres": Decimal,
                "platform_fee_per_seat": Decimal,
            }
        """
        await self.load_config(db)

        distance = Decimal(str(distance_km))
        mileage = Decimal(str(mileage_kmpl))

        # Step 1: Fuel required
        fuel_required = distance / mileage

        # Step 2: Total fuel cost
        fuel_cost = fuel_required * self._fuel_price

        # Step 3: Base cost per seat (fuel cost shared equally)
        base_per_seat = fuel_cost / Decimal(str(seats))

        # Step 4: Platform margin
        margin = base_per_seat * (self._margin_pct / Decimal("100"))

        # Step 5: Per seat fare
        per_seat_fare = base_per_seat + margin

        # Step 6: Apply minimum fare
        per_seat_fare = max(per_seat_fare, self._min_fare)

        # Step 7: Round to nearest X rupees
        if self._fare_rounding > 0:
            per_seat_fare = (
                per_seat_fare / self._fare_rounding
            ).quantize(Decimal("1"), rounding=ROUND_HALF_UP) * self._fare_rounding

        # Total fare
        total_fare = per_seat_fare * Decimal(str(seats))

        return {
            "total_fare": total_fare,
            "per_seat_fare": per_seat_fare,
            "fuel_cost": fuel_cost.quantize(Decimal("0.01")),
            "fuel_required_litres": fuel_required.quantize(Decimal("0.01")),
            "platform_fee_per_seat": margin.quantize(Decimal("0.01")),
        }

    def calculate_partial_fare(
        self,
        per_seat_fare_full: float,
        total_distance_km: float,
        passenger_distance_km: float,
    ) -> Decimal:
        """
        Calculate proportional fare for a partial route.

        This is a pure calculation — no DB call needed.
        Uses the already-stored per_seat_fare from the ride.

        Args:
            per_seat_fare_full:   Per seat fare for full route (from rides table)
            total_distance_km:    Total route distance (from rides table)
            passenger_distance_km: Distance from passenger's pickup to destination (from OSRM)

        Returns:
            Decimal: Proportional fare for the partial route
        """
        full_fare = Decimal(str(per_seat_fare_full))
        total_dist = Decimal(str(total_distance_km))
        pass_dist = Decimal(str(passenger_distance_km))

        if total_dist == 0:
            return self._min_fare

        # Rate per km
        rate_per_km = full_fare / total_dist

        # Proportional fare
        partial_fare = rate_per_km * pass_dist

        # Apply minimum fare
        partial_fare = max(partial_fare, self._min_fare)

        # Round
        if self._fare_rounding > 0:
            partial_fare = (
                partial_fare / self._fare_rounding
            ).quantize(Decimal("1"), rounding=ROUND_HALF_UP) * self._fare_rounding

        return partial_fare


# Singleton instance
fare_engine = FareEngine()
```

---

## API Endpoint — Fare Preview

Passengers can preview the fare before booking.

| Method | Endpoint                     | Auth     | Description                       |
|--------|------------------------------|----------|-----------------------------------|
| POST   | `/api/v1/fare/calculate`     | Required | Preview fare for a route          |
| POST   | `/api/v1/fare/calculate-partial` | Required | Preview fare for a partial route |

```python
# schemas/fare.py

class FareCalculateRequest(BaseModel):
    source_lat: float
    source_lng: float
    dest_lat: float
    dest_lng: float
    mileage_kmpl: float = Field(..., gt=0)
    seats: int = Field(..., ge=1, le=8)

class FareCalculateResponse(BaseModel):
    distance_km: Decimal
    estimated_duration_minutes: int
    per_seat_fare: Decimal
    total_fare: Decimal
    fuel_cost: Decimal
    platform_fee_per_seat: Decimal

class PartialFareRequest(BaseModel):
    ride_id: UUID
    pickup_lat: float
    pickup_lng: float

class PartialFareResponse(BaseModel):
    total_route_distance_km: Decimal
    passenger_distance_km: Decimal
    full_route_per_seat_fare: Decimal
    partial_fare: Decimal
```

```python
# routers/fare.py

@router.post("/calculate", response_model=dict)
async def calculate_fare(
    data: FareCalculateRequest,
    db=Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Preview fare for a route. Used by drivers when creating a ride."""

    # Get distance from OSRM
    route = await osrm_service.get_route(
        data.source_lat, data.source_lng,
        data.dest_lat, data.dest_lng,
    )

    # Calculate fare
    fare = await fare_engine.calculate_full_fare(
        db=db,
        distance_km=route["distance_km"],
        mileage_kmpl=data.mileage_kmpl,
        seats=data.seats,
    )

    return {
        "data": {
            "distance_km": route["distance_km"],
            "estimated_duration_minutes": route["duration_minutes"],
            **fare,
        }
    }


@router.post("/calculate-partial", response_model=dict)
async def calculate_partial_fare(
    data: PartialFareRequest,
    db=Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Preview fare for a partial route. Used by passengers before booking."""

    ride = await db.get(Ride, data.ride_id)
    if not ride:
        raise HTTPException(status_code=404, detail="Ride not found")

    # Get distance from pickup to destination
    passenger_distance = await osrm_service.get_distance_from_pickup(
        data.pickup_lat, data.pickup_lng,
        float(ride.dest_lat), float(ride.dest_lng),
    )

    # Cap at total distance
    passenger_distance = min(passenger_distance, float(ride.total_distance_km))

    partial_fare = fare_engine.calculate_partial_fare(
        per_seat_fare_full=float(ride.per_seat_fare),
        total_distance_km=float(ride.total_distance_km),
        passenger_distance_km=passenger_distance,
    )

    return {
        "data": {
            "total_route_distance_km": ride.total_distance_km,
            "passenger_distance_km": passenger_distance,
            "full_route_per_seat_fare": ride.per_seat_fare,
            "partial_fare": partial_fare,
        }
    }
```

---

## Fare Breakdown Display (Flutter)

When a passenger views a ride, show a transparent fare breakdown:

```
┌─────────────────────────────────────┐
│  Fare Breakdown                     │
├─────────────────────────────────────┤
│  Route Distance     150.00 km       │
│  Fuel Required      10.00 litres    │
│  Fuel Cost          ₹1,050.00       │
│  Your Share (1/3)   ₹350.00         │
│  Platform Fee       ₹52.50          │
│                                     │
│  ─────────────────────────────────  │
│  Per Seat Fare      ₹405.00         │
│  (rounded to nearest ₹5)           │
└─────────────────────────────────────┘
```

For partial routes:
```
┌─────────────────────────────────────┐
│  Your Fare                          │
├─────────────────────────────────────┤
│  Full Route          150.00 km      │
│  Your Distance       95.00 km       │
│  Full Seat Fare      ₹405.00        │
│  Your Fare (63.3%)   ₹255.00        │
└─────────────────────────────────────┘
```

---

## Things To Note

1. **Use `Decimal`, never `float`, for money.** Float arithmetic causes rounding errors (e.g., `0.1 + 0.2 = 0.30000000000000004`). All fare calculations use Python's `Decimal` type with explicit rounding.

2. **Config is loaded fresh on every fare calculation.** This ensures admin changes to fuel price or margin take effect immediately for new rides. Already-created rides retain their original fare.

3. **The driver doesn't set the price.** The fare is auto-calculated from distance, mileage, and config. Drivers cannot manually set or override fares. This prevents price gouging and keeps the platform fair.

4. **Mileage varies by vehicle.** A Maruti Swift (20 km/l) will have a lower fare than a Toyota Fortuner (10 km/l) for the same route. This is by design — fuel cost sharing is based on the actual vehicle's efficiency.

5. **Fare rounding makes prices user-friendly.** ₹402.50 → ₹405. ₹398 → ₹400. Passengers see clean numbers. Set `fare_rounding = 1` in config to disable.

6. **Minimum fare prevents ₹5 rides.** Very short distances (1–2 km) would produce very low fares. The minimum fare (₹50) ensures every ride generates a baseline revenue.

7. **No surge pricing in Phase 1.** Intentionally excluded. The price is deterministic — same inputs always produce the same output. Surge/dynamic pricing is a Phase 2 consideration.

8. **Fare transparency builds trust.** Show the full breakdown (fuel required, fuel cost, share, margin) to passengers. Ride-sharing users value knowing exactly why they're paying what they're paying.
