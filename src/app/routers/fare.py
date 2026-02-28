# =============================================================================
# routers/fare.py — Fare Calculation Endpoints
# =============================================================================
# See: system-design/10-api-contracts.md §7 "Fare Engine Endpoints"
# See: system-design/05-fare-engine.md for the fare algorithm
#
# Prefix: /api/v1/fare
#
# These are read-only endpoints. They calculate estimates — no DB writes.
# Used by the Flutter app to show "Estimated fare: ₹X" before booking.
# Fuel-cost-sharing model: driver's fuel cost split among passengers + margin.
#
# TODO: GET /fare/calculate
#       - Requires: Bearer token
#       - Query params (NOT JSON body):
#         source_lat, source_lng, dest_lat, dest_lng, mileage_kmpl, seats
#       - Logic: Call fare_engine.calculate_full_fare(db, distance, mileage, seats)
#         1. Call osrm_service.get_route(src, dst) for distance_km
#         2. fuel_cost = distance / mileage * fuel_price
#         3. Apply margin, enforce min_fare, round to nearest ₹5
#       - Response: FareCalcResponse
#
# TODO: GET /fare/partial
#       - Requires: Bearer token
#       - Query params (NOT JSON body): ride_id, pickup_lat, pickup_lng
#       - Logic: Call fare_engine.calculate_partial_fare()
#         1. Fetch ride from DB
#         2. Call osrm_service.get_distance_from_pickup(pickup → ride.dest)
#         3. fare = per_seat_fare * (passenger_distance / total_distance) * seats
#       - Response: PartialFareResponse
#
# Connects with:
#   → app/schemas/fare.py (FareCalcResponse, PartialFareResponse — query params, not schemas)
#   → app/services/fare_engine.py (calculate_full_fare, calculate_partial_fare)
#   → app/services/osrm_service.py (get_route, get_distance_from_pickup)
#   → app/dependencies.py (get_current_user, get_db)
#
# work by adolf.
