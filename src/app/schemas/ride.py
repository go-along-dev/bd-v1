# =============================================================================
# schemas/ride.py — Ride Request/Response Schemas
# =============================================================================
# See: system-design/10-api-contracts.md §5 "Ride Endpoints"
# See: system-design/03-rides.md for ride lifecycle
#
# TODO: class RideCreateRequest(BaseModel):
#       - source_address: str
#       - source_lat: float = Field(..., ge=-90, le=90)
#       - source_lng: float = Field(..., ge=-180, le=180)
#       - dest_address: str
#       - dest_lat: float = Field(..., ge=-90, le=90)
#       - dest_lng: float = Field(..., ge=-180, le=180)
#       - departure_time: datetime  (must be in the future)
#       - total_seats: int = Field(..., ge=1, le=8)
#
# TODO: class RideUpdateRequest(BaseModel):
#       - departure_time: datetime | None = None
#       - total_seats: int | None = Field(None, ge=1, le=8)
#       Note: source/destination CANNOT be changed after creation (fare would change)
#
# TODO: class RideResponse(BaseModel):
#       - id: UUID
#       - driver_name: str     (joined from users table via driver)
#       - vehicle_info: str    (e.g. "Maruti Swift · White · KA-01-AB-1234")
#       - source_address, dest_address: str
#       - total_distance_km: Decimal
#       - estimated_duration: int | None
#       - departure_time: datetime
#       - total_seats, available_seats: int
#       - per_seat_fare: Decimal
#       - status: str
#       - created_at: datetime
#       model_config: from_attributes = True
#
# TODO: class RideDetailResponse(RideResponse):
#       - source_lat, source_lng: float
#       - dest_lat, dest_lng: float
#       - total_fare: Decimal
#       - route_geometry: str | None  (for map drawing)
#
# TODO: class RideSearchParams(BaseModel):
#       Used as Query params, not JSON body.
#       - src_lat: float
#       - src_lng: float
#       - dst_lat: float
#       - dst_lng: float
#       - date: str  (YYYY-MM-DD)
#       - radius_km: float = 15.0
#       See: system-design/03-rides.md for bounding box search logic
#
# TODO: class GeocodingResponse(BaseModel):
#       - display_name: str
#       - lat: float
#       - lng: float
#
# Connects with:
#   → app/routers/rides.py (POST /rides, GET /rides, GET /rides/{id}, PUT, DELETE, complete, depart)
#   → app/services/ride_service.py
#   → app/services/osrm_service.py (distance on creation)
#   → app/services/fare_engine.py (total_fare calculation)
#
# work by adolf.
