from pydantic import BaseModel, Field
from uuid import UUID
from datetime import datetime
from decimal import Decimal


# ─── Create Booking ───────────────────────────
class BookingCreateRequest(BaseModel):
    ride_id:         UUID
    seats_booked:    int     = Field(default=1, ge=1, le=6)
    pickup_address:  str | None = Field(None, max_length=255)
    pickup_lat:      Decimal = Field(..., ge=-90,  le=90)
    pickup_lng:      Decimal = Field(..., ge=-180, le=180)


# ─── Booking Response ─────────────────────────
class BookingResponse(BaseModel):
    id:                   UUID
    ride_id:              UUID
    passenger_id:         UUID
    seats_booked:         int
    pickup_address:       str | None
    pickup_lat:           Decimal
    pickup_lng:           Decimal
    partial_distance_km:  Decimal | None
    fare_amount:          Decimal
    status:               str
    created_at:           datetime

    model_config = {"from_attributes": True}


# ─── Cancel Booking ───────────────────────────
class BookingCancelRequest(BaseModel):
    cancellation_reason: str | None = Field(None, max_length=500)
    # Cancellation only allowed if departure_time - now() > cancellation_window_hours
    # Value read from platform_config table