# =============================================================================
# schemas/fare.py — Fare Calculation Schemas
# =============================================================================
# See: system-design/10-api-contracts.md §7 "Fare Engine Endpoints"
# See: system-design/05-fare-engine.md for the fare calculation algorithm
#
# Fare endpoints are read-only calculations — they don't create DB records.
# Used by the Flutter app to show estimated fare before booking.
# Fare model: fuel-cost-sharing — driver's fuel cost split among passengers + margin.
#
# TODO: class FareCalcRequest — used as Query params, NOT JSON body:
#       - source_lat: float = Query(..., ge=-90, le=90)
#       - source_lng: float = Query(..., ge=-180, le=180)
#       - dest_lat: float = Query(..., ge=-90, le=90)
#       - dest_lng: float = Query(..., ge=-180, le=180)
#       - mileage_kmpl: float = Query(..., ge=1, le=50)  — vehicle mileage
#       - seats: int = Query(..., ge=1, le=8)  — seats offered
#
# TODO: class FareCalcResponse(BaseModel):
#       - distance_km: Decimal
#       - total_fare: Decimal
#       - per_seat_fare: Decimal
#       - fuel_cost: Decimal           — breakdown for transparency
#       - platform_margin: Decimal      — breakdown for transparency
#       - min_fare_applied: bool  (True if the min_fare floor was used)
#
# TODO: class PartialFareRequest — used as Query params, NOT JSON body:
#       For calculating a passenger's proportional fare for a partial route.
#       - ride_id: UUID = Query(...)
#       - pickup_lat: float = Query(...)
#       - pickup_lng: float = Query(...)
#
# TODO: class PartialFareResponse(BaseModel):
#       - partial_distance_km: Decimal
#       - fare: Decimal
#       - per_seat_fare_full: Decimal  — ride's full per_seat_fare for context
#
# Connects with:
#   → app/routers/fare.py (GET /fare/calculate, GET /fare/partial)
#   → app/services/fare_engine.py
#   → app/services/osrm_service.py (distance calculation)
#
# work by adolf.
