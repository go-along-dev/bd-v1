# Module 3: Ride Management

## Overview

Rides are the core entity of GoAlong. A **verified driver** creates a ride offering (source → destination → date/time → seats), and the system calculates the fare using OSRM for distance and the fare engine for pricing. Passengers discover and book these rides.

This module covers ride creation, editing, cancellation, search, and the OSRM integration.

---

## Ride Lifecycle

```
Driver creates ride
        │
        ▼
  ┌──────────┐
  │  Active   │  ← Visible in search results, bookable
  └─────┬─────┘
        │
        ├──── Driver edits (if no bookings yet) ────► Still Active
        │
        ├──── Driver cancels ────────────────────► Cancelled
        │     └── All passengers notified via FCM
        │
        ├──── Departure time passed ─────────────► Completed
        │     └── Auto-updated by background task or on next access
        │
        └──── All seats booked ──────────────────► Active (full)
              └── Still active but available_seats = 0, not shown in search
```

---

## Database: Rides Table

```sql
CREATE TABLE rides (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    driver_id           UUID NOT NULL REFERENCES drivers(id) ON DELETE CASCADE,

    -- Source
    source_address      TEXT NOT NULL,               -- Human-readable
    source_lat          DECIMAL(10,7) NOT NULL,
    source_lng          DECIMAL(10,7) NOT NULL,

    -- Destination
    dest_address        TEXT NOT NULL,
    dest_lat            DECIMAL(10,7) NOT NULL,
    dest_lng            DECIMAL(10,7) NOT NULL,

    -- Route (from OSRM)
    total_distance_km   DECIMAL(8,2) NOT NULL,       -- Driving distance, not straight line
    estimated_duration  INT,                          -- Minutes (from OSRM)
    route_geometry      TEXT,                          -- Encoded polyline for map display

    -- Schedule
    departure_time      TIMESTAMPTZ NOT NULL,

    -- Seats
    total_seats         INT NOT NULL,                 -- Seats offered for this ride (≤ driver.seat_capacity)
    available_seats     INT NOT NULL,                 -- Decremented on booking, incremented on cancel

    -- Fare (computed by fare engine at creation)
    total_fare          DECIMAL(10,2) NOT NULL,
    per_seat_fare       DECIMAL(10,2) NOT NULL,

    -- Status
    status              VARCHAR(20) NOT NULL DEFAULT 'active',
                                                      -- 'active' | 'completed' | 'cancelled'

    -- Timestamps
    created_at          TIMESTAMPTZ DEFAULT NOW(),
    updated_at          TIMESTAMPTZ DEFAULT NOW()
);

-- Search optimization: passengers search by source area + destination area + date
CREATE INDEX idx_rides_search ON rides(status, departure_time);
CREATE INDEX idx_rides_source ON rides(source_lat, source_lng);
CREATE INDEX idx_rides_dest ON rides(dest_lat, dest_lng);
CREATE INDEX idx_rides_driver ON rides(driver_id);
```

### Things To Note:
- `total_seats` is how many seats the driver offers for **this ride** (may be less than their car's capacity — e.g., driver has a 7-seater SUV but offers only 3 seats)
- `available_seats` starts at `total_seats` and is decremented on each booking. It's the live counter.
- `route_geometry` stores the OSRM-returned polyline so the Flutter app can draw the route on the map without re-calling OSRM.
- `total_fare` is the full route fare. `per_seat_fare` = fare per seat for the full route. Partial route fares are calculated at booking time.

---

## OSRM Integration

### What is OSRM?
Open Source Routing Machine — calculates driving distance and duration between two points using OpenStreetMap road data. Free and self-hostable.

### API Call
```
GET http://<osrm-host>:5000/route/v1/driving/{src_lng},{src_lat};{dst_lng},{dst_lat}?overview=full&geometries=polyline
```

### Response (relevant parts)
```json
{
  "routes": [
    {
      "distance": 156432.5,       // meters
      "duration": 9120.3,          // seconds
      "geometry": "encoded_polyline_string"
    }
  ]
}
```

### Service Implementation

```python
# services/osrm_service.py

import httpx
from app.config import settings
from fastapi import HTTPException

class OSRMService:
    def __init__(self):
        self.base_url = settings.OSRM_BASE_URL  # e.g., "http://10.0.0.5:5000"

    async def get_route(
        self,
        src_lat: float, src_lng: float,
        dst_lat: float, dst_lng: float,
    ) -> dict:
        """
        Get driving distance, duration, and route geometry between two points.
        Returns dict with distance_km, duration_minutes, geometry.
        """
        url = (
            f"{self.base_url}/route/v1/driving/"
            f"{src_lng},{src_lat};{dst_lng},{dst_lat}"
            f"?overview=full&geometries=polyline"
        )

        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url)

        if response.status_code != 200:
            raise HTTPException(
                status_code=502,
                detail="Routing service unavailable"
            )

        data = response.json()

        if data.get("code") != "Ok" or not data.get("routes"):
            raise HTTPException(
                status_code=400,
                detail="Could not find a route between these locations"
            )

        route = data["routes"][0]

        return {
            "distance_km": round(route["distance"] / 1000, 2),
            "duration_minutes": round(route["duration"] / 60),
            "geometry": route["geometry"],  # Encoded polyline
        }

    async def get_distance_from_pickup(
        self,
        pickup_lat: float, pickup_lng: float,
        dst_lat: float, dst_lng: float,
    ) -> float:
        """
        Get driving distance from a pickup point to the ride destination.
        Used for partial route fare calculation.
        """
        route = await self.get_route(pickup_lat, pickup_lng, dst_lat, dst_lng)
        return route["distance_km"]

osrm_service = OSRMService()
```

### Things To Note (OSRM):
1. **OSRM returns driving distance, not straight-line distance.** This is the actual road distance — critical for accurate fare calculation.
2. **OSRM coordinates are `longitude,latitude`** (not `lat,lng`). Very common bug — double check the order.
3. **For development**, use the public OSRM demo: `https://router.project-osrm.org`. **For production**, self-host on a GCP VM with India OSM data (~2GB extract).
4. **Timeout handling.** Always set a timeout on OSRM calls. If OSRM is down, the ride creation should fail gracefully — not hang.
5. **Geometry is polyline-encoded.** Flutter's `flutter_map` + `flutter_polyline_points` can decode and draw it on the map.

---

## Geocoding with Nominatim

When a user types an address, convert it to coordinates using Nominatim (OpenStreetMap's geocoder).

```python
# services/osrm_service.py (additional method)

async def geocode_address(self, address: str) -> dict | None:
    """Convert address text to lat/lng using Nominatim."""
    url = "https://nominatim.openstreetmap.org/search"
    params = {
        "q": address,
        "format": "json",
        "countrycodes": "in",   # Restrict to India
        "limit": 5,
    }
    headers = {"User-Agent": "GoAlong/1.0"}  # Required by Nominatim ToS

    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(url, params=params, headers=headers)

    results = response.json()
    if not results:
        return None

    return {
        "lat": float(results[0]["lat"]),
        "lng": float(results[0]["lon"]),
        "display_name": results[0]["display_name"],
    }
```

### Things To Note (Nominatim):
- **Rate limit: 1 request/second.** Nominatim is free but rate-limited. For MVP this is fine. For production, consider self-hosting Nominatim or using a paid geocoding API.
- **Always set `User-Agent` header.** Nominatim blocks requests without it.
- **Prefer map picker over text geocoding.** Let users tap on a map to select location (more accurate). Use Nominatim as a fallback for text search.

---

## API Endpoints

| Method | Endpoint                  | Auth     | Role              | Description                       |
|--------|---------------------------|----------|-------------------|-----------------------------------|
| POST   | `/api/v1/rides`           | Required | Approved driver   | Create a new ride                 |
| GET    | `/api/v1/rides`           | Required | Any               | Search rides (query params)       |
| GET    | `/api/v1/rides/{ride_id}` | Required | Any               | Get ride details                  |
| PUT    | `/api/v1/rides/{ride_id}` | Required | Ride owner        | Edit ride (restricted)            |
| DELETE | `/api/v1/rides/{ride_id}` | Required | Ride owner        | Cancel ride                       |
| GET    | `/api/v1/rides/my-rides`  | Required | Driver            | List driver's own rides           |
| GET    | `/api/v1/rides/geocode`   | Required | Any               | Geocode an address (Nominatim)    |

---

## Pydantic Schemas

```python
# schemas/ride.py

from pydantic import BaseModel, Field
from uuid import UUID
from datetime import datetime
from decimal import Decimal

class RideCreateRequest(BaseModel):
    source_address: str
    source_lat: float = Field(..., ge=-90, le=90)
    source_lng: float = Field(..., ge=-180, le=180)
    dest_address: str
    dest_lat: float = Field(..., ge=-90, le=90)
    dest_lng: float = Field(..., ge=-180, le=180)
    departure_time: datetime
    total_seats: int = Field(..., ge=1, le=8)

class RideUpdateRequest(BaseModel):
    departure_time: datetime | None = None
    total_seats: int | None = Field(None, ge=1, le=8)
    # Source/destination CANNOT be changed after creation (fare would change)

class RideSearchParams(BaseModel):
    src_lat: float
    src_lng: float
    dst_lat: float
    dst_lng: float
    date: str                   # YYYY-MM-DD
    radius_km: float = 15.0    # Search radius around source/destination

class RideResponse(BaseModel):
    id: UUID
    driver_name: str            # Joined from users table
    vehicle_info: str           # "Maruti Swift · White · KA-01-AB-1234"
    source_address: str
    dest_address: str
    total_distance_km: Decimal
    estimated_duration: int | None
    departure_time: datetime
    total_seats: int
    available_seats: int
    per_seat_fare: Decimal
    status: str
    created_at: datetime

class RideDetailResponse(RideResponse):
    source_lat: float
    source_lng: float
    dest_lat: float
    dest_lng: float
    total_fare: Decimal
    route_geometry: str | None  # For map drawing
    driver_rating: float | None # Future — not in Phase 1
```

---

## Service Layer — Ride Creation

```python
# services/ride_service.py

from app.services.osrm_service import osrm_service
from app.services.fare_engine import fare_engine
from app.models.ride import Ride
from app.models.driver import Driver

async def create_ride(
    db: AsyncSession,
    driver: Driver,
    data: RideCreateRequest,
) -> Ride:
    """Create a new ride with auto-calculated distance and fare."""

    # Validation
    if driver.verification_status != "approved":
        raise HTTPException(status_code=403, detail="Driver not verified")

    if data.departure_time <= datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="Departure time must be in the future")

    if data.total_seats > driver.seat_capacity:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot offer more than {driver.seat_capacity} seats"
        )

    # 1. Get route from OSRM
    route = await osrm_service.get_route(
        src_lat=data.source_lat,
        src_lng=data.source_lng,
        dst_lat=data.dest_lat,
        dst_lng=data.dest_lng,
    )

    # 2. Calculate fare
    fare = await fare_engine.calculate_full_fare(
        distance_km=route["distance_km"],
        mileage_kmpl=float(driver.mileage_kmpl),
        seats=data.total_seats,
    )

    # 3. Create ride
    ride = Ride(
        driver_id=driver.id,
        source_address=data.source_address,
        source_lat=data.source_lat,
        source_lng=data.source_lng,
        dest_address=data.dest_address,
        dest_lat=data.dest_lat,
        dest_lng=data.dest_lng,
        total_distance_km=route["distance_km"],
        estimated_duration=route["duration_minutes"],
        route_geometry=route["geometry"],
        departure_time=data.departure_time,
        total_seats=data.total_seats,
        available_seats=data.total_seats,
        total_fare=fare["total_fare"],
        per_seat_fare=fare["per_seat_fare"],
        status="active",
    )
    db.add(ride)
    await db.commit()
    await db.refresh(ride)

    return ride
```

---

## Ride Search

The most critical query. Passengers search by:
- **Source area** — rides starting near a location
- **Destination area** — rides going near a location
- **Date** — rides departing on a specific day
- **Available seats** — must have at least 1 seat

### Search Logic

```python
# services/ride_service.py

from sqlalchemy import select, and_, func, cast, Float
from math import radians, cos

async def search_rides(
    db: AsyncSession,
    src_lat: float, src_lng: float,
    dst_lat: float, dst_lng: float,
    date: str,
    radius_km: float = 15.0,
) -> list[Ride]:
    """
    Find rides matching source area, destination area, and date.

    Uses bounding box approximation for location matching.
    Not geodesically perfect, but absolutely sufficient for MVP.
    """

    # Approximate degree offset for the search radius
    # 1 degree latitude ≈ 111 km
    # 1 degree longitude ≈ 111 km × cos(latitude)
    lat_offset = radius_km / 111.0
    lng_offset = radius_km / (111.0 * cos(radians(src_lat)))

    # Parse target date
    from datetime import datetime, timedelta
    target_date = datetime.strptime(date, "%Y-%m-%d").date()
    day_start = datetime.combine(target_date, datetime.min.time())
    day_end = day_start + timedelta(days=1)

    query = (
        select(Ride)
        .where(
            and_(
                Ride.status == "active",
                Ride.available_seats > 0,
                Ride.departure_time >= day_start,
                Ride.departure_time < day_end,
                # Source within bounding box
                Ride.source_lat.between(src_lat - lat_offset, src_lat + lat_offset),
                Ride.source_lng.between(src_lng - lng_offset, src_lng + lng_offset),
                # Destination within bounding box
                Ride.dest_lat.between(dst_lat - lat_offset, dst_lat + lat_offset),
                Ride.dest_lng.between(dst_lng - lng_offset, dst_lng + lng_offset),
            )
        )
        .order_by(Ride.departure_time.asc())
        .limit(50)
    )

    result = await db.execute(query)
    return result.scalars().all()
```

### Things To Note (Search):
1. **Bounding box, not Haversine.** For an MVP, a rectangular bounding box search is fast and good enough. PostGIS with `ST_DWithin` is an option for Phase 2 if precision matters.
2. **Default search radius is 15 km.** Intercity rides have flexible pickup/drop points — a 15 km radius catches most reasonable matches.
3. **Results are ordered by departure time.** Soonest departure first.
4. **Limit to 50 results.** Pagination can be added, but for MVP, 50 results per search is plenty.
5. **Only active rides with available seats appear.** Cancelled, completed, and fully-booked rides are excluded.

---

## Ride Edit Rules

| Field              | Editable? | Condition                                           |
|--------------------|-----------|-----------------------------------------------------|
| `departure_time`   | ✅ Yes    | Only if no bookings exist yet                       |
| `total_seats`      | ✅ Yes    | Only if new value ≥ currently booked seats          |
| `source/dest`      | ❌ No     | Changing route changes distance and fare — not allowed |
| `vehicle_details`  | ❌ No     | Tied to driver profile, not ride                    |

```python
async def update_ride(
    db: AsyncSession,
    ride: Ride,
    data: RideUpdateRequest,
) -> Ride:
    booked_seats = ride.total_seats - ride.available_seats

    if data.departure_time:
        if booked_seats > 0:
            raise HTTPException(
                status_code=400,
                detail="Cannot change departure time — passengers already booked"
            )
        if data.departure_time <= datetime.now(timezone.utc):
            raise HTTPException(status_code=400, detail="Departure must be in the future")
        ride.departure_time = data.departure_time

    if data.total_seats:
        if data.total_seats < booked_seats:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot reduce seats below {booked_seats} (already booked)"
            )
        difference = data.total_seats - ride.total_seats
        ride.total_seats = data.total_seats
        ride.available_seats += difference

    ride.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(ride)
    return ride
```

---

## Ride Cancellation

```python
async def cancel_ride(
    db: AsyncSession,
    ride: Ride,
    notification_service,
) -> Ride:
    """Cancel a ride and notify all booked passengers."""

    if ride.status != "active":
        raise HTTPException(status_code=400, detail="Ride is not active")

    ride.status = "cancelled"
    ride.updated_at = datetime.now(timezone.utc)

    # Cancel all associated bookings
    bookings = await db.execute(
        select(Booking).where(
            Booking.ride_id == ride.id,
            Booking.status == "confirmed",
        )
    )
    for booking in bookings.scalars().all():
        booking.status = "cancelled"
        booking.cancelled_at = datetime.now(timezone.utc)

        # Notify passenger via FCM
        await notification_service.send_push(
            user_id=booking.passenger_id,
            title="Ride Cancelled",
            body=f"Your ride to {ride.dest_address} has been cancelled by the driver.",
        )

    await db.commit()
    await db.refresh(ride)
    return ride
```

---

## Flutter — Map Picker for Source/Destination

```dart
// widgets/map_picker.dart

import 'package:flutter/material.dart';
import 'package:flutter_map/flutter_map.dart';
import 'package:latlong2/latlong.dart';

class MapPicker extends StatefulWidget {
  final String title;          // "Select Pickup" or "Select Destination"
  final LatLng? initialCenter; // Default map center
  final Function(LatLng, String) onLocationSelected;

  const MapPicker({
    required this.title,
    this.initialCenter,
    required this.onLocationSelected,
  });

  @override
  State<MapPicker> createState() => _MapPickerState();
}

class _MapPickerState extends State<MapPicker> {
  LatLng? _selectedPoint;
  final MapController _mapController = MapController();

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text(widget.title)),
      body: FlutterMap(
        mapController: _mapController,
        options: MapOptions(
          initialCenter: widget.initialCenter ?? const LatLng(12.9716, 77.5946), // Bangalore
          initialZoom: 12,
          onTap: (tapPosition, point) {
            setState(() => _selectedPoint = point);
          },
        ),
        children: [
          TileLayer(
            urlTemplate: 'https://tile.openstreetmap.org/{z}/{x}/{y}.png',
            userAgentPackageName: 'com.goalong.app',
          ),
          if (_selectedPoint != null)
            MarkerLayer(
              markers: [
                Marker(
                  point: _selectedPoint!,
                  child: const Icon(Icons.location_pin, color: Colors.red, size: 40),
                ),
              ],
            ),
        ],
      ),
      floatingActionButton: FloatingActionButton.extended(
        onPressed: _selectedPoint == null ? null : () async {
          // Reverse geocode the point to get address
          final address = await _reverseGeocode(_selectedPoint!);
          widget.onLocationSelected(_selectedPoint!, address);
          Navigator.pop(context);
        },
        label: const Text('Confirm Location'),
        icon: const Icon(Icons.check),
      ),
    );
  }

  Future<String> _reverseGeocode(LatLng point) async {
    // Call Nominatim reverse geocoding
    final url = 'https://nominatim.openstreetmap.org/reverse'
        '?lat=${point.latitude}&lon=${point.longitude}&format=json';
    // ... make HTTP request and return display_name
    return 'Selected Location'; // Placeholder
  }
}
```

---

## Completed Ride Auto-Cleanup

Rides should auto-transition to `completed` once departure time has passed. Two approaches for MVP:

### Option A: Check on Read (Recommended for MVP)
```python
# Wherever rides are fetched, filter out past rides or mark them
async def get_ride(db, ride_id):
    ride = await db.get(Ride, ride_id)
    if ride and ride.status == "active" and ride.departure_time < datetime.now(timezone.utc):
        ride.status = "completed"
        await db.commit()
    return ride
```

### Option B: Scheduled Task (Better but more complex)
A background task that runs every hour to mark past rides as completed. Defer to Phase 2 or implement if time permits.

---

## Things To Note

1. **Distance comes from OSRM, not user input.** Never let the driver or passenger specify distance. Always compute via OSRM to prevent fare manipulation.

2. **Fare is calculated at ride creation time.** It's stored in the ride record. This means if fuel price or margin changes, existing rides keep their original fare. Only new rides use updated settings.

3. **Route geometry enables map drawing.** Store the polyline so passengers can see the exact route on the map. Don't re-call OSRM every time someone views a ride.

4. **One ride per driver at a time (recommended).** Prevent drivers from creating overlapping rides. Check if the driver has another active ride with an overlapping departure window (±2 hours).

5. **Departure time must be at least 1 hour in the future.** Prevents accidentally creating "current" rides that can't be booked in time.

6. **All times are stored in UTC with timezone (TIMESTAMPTZ).** Flutter handles display in local time. Never store local time in the database.
