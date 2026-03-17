from pydantic import BaseModel, Field
from uuid import UUID
from datetime import datetime, date
from decimal import Decimal


# ─── Create Ride ──────────────────────────────
class RideCreateRequest(BaseModel):
    source_address: str   = Field(..., max_length=255)
    source_lat:     float = Field(..., ge=-90,  le=90)
    source_lng:     float = Field(..., ge=-180, le=180)
    source_city:    str | None = Field(None, max_length=100)
    dest_address:   str   = Field(..., max_length=255)
    dest_lat:       float = Field(..., ge=-90,  le=90)
    dest_lng:       float = Field(..., ge=-180, le=180)
    dest_city:      str | None = Field(None, max_length=100)
    departure_time: datetime   # Validated in service — must be future
    total_seats:    int   = Field(..., ge=1, le=8)


# ─── Update Ride ──────────────────────────────
class RideUpdateRequest(BaseModel):
    departure_time: datetime | None = None
    total_seats:    int | None      = Field(None, ge=1, le=8)
    # NOTE: source/destination cannot be changed after creation
    # Changing them would invalidate the fare calculation


# ─── Ride Response (list view) ────────────────
class RideResponse(BaseModel):
    id:                 UUID
    driver_name:        str         # joined from users via driver
    vehicle_info:       str         # e.g. "Maruti Swift · White · KA-01-AB-1234"
    source_address:     str
    dest_address:       str
    total_distance_km:  Decimal
    estimated_duration: int | None  # minutes
    departure_time:     datetime
    total_seats:        int
    available_seats:    int
    per_seat_fare:      Decimal
    status:             str
    created_at:         datetime

    model_config = {"from_attributes": True}


# ─── Ride Detail Response (single ride view) ──
class RideDetailResponse(RideResponse):
    source_lat:     float
    source_lng:     float
    dest_lat:       float
    dest_lng:       float
    total_fare:     Decimal
    route_geometry: str | None      # encoded polyline for map drawing


# ─── Search Params ────────────────────────────
class RideSearchParams(BaseModel):
    source_lat: float
    source_lng: float
    dest_lat:   float
    dest_lng:   float
    date:       date
    seats:      int   = Field(default=1, ge=1, le=8)
    radius_km:  float = Field(default=15.0, ge=1, le=100)


# ─── Geocoding Response ───────────────────────
class GeocodingResponse(BaseModel):
    display_name: str
    lat:          float
    lng:          float