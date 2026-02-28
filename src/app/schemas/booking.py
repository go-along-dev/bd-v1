# =============================================================================
# schemas/booking.py — Booking Request/Response Schemas
# =============================================================================
# See: system-design/10-api-contracts.md §6 "Booking Endpoints"
# See: system-design/04-bookings.md for booking lifecycle
#
# TODO: class BookingCreateRequest(BaseModel):
#       - ride_id: UUID
#       - seats_booked: int = Field(default=1, ge=1, le=6)
#       - pickup_address: str | None = Field(None, max_length=255)
#       - pickup_lat: Decimal = Field(..., ge=-90, le=90)
#       - pickup_lng: Decimal = Field(..., ge=-180, le=180)
#
# TODO: class BookingResponse(BaseModel):
#       - id: UUID
#       - ride_id: UUID
#       - passenger_id: UUID
#       - seats_booked: int
#       - pickup_address: str | None
#       - pickup_lat, pickup_lng: Decimal
#       - partial_distance_km: Decimal | None
#       - fare_amount: Decimal
#       - status: str
#       - created_at: datetime
#       model_config: from_attributes = True
#
# TODO: class BookingCancelRequest(BaseModel):
#       - cancellation_reason: str | None = Field(None, max_length=500)
#       Note: cancellation only allowed if departure_time - now() > 2 hours
#       (configurable via platform_config.cancellation_window_hours)
#
# Connects with:
#   → app/routers/bookings.py (POST /bookings, DELETE /bookings/{id}, GET /bookings)
#   → app/services/booking_service.py
#
# work by adolf.
