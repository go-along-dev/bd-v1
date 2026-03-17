# =============================================================================
# tests/test_fare.py — Fare Engine Tests
# =============================================================================
# See: system-design/05-fare-engine.md for the fare algorithm
# See: system-design/10-api-contracts.md §7 "Fare Engine Endpoints"
#
# TODO: test_fare_basic_calculation
#       distance=100km, per_km_rate=2.50 → fare=250.00
#
# TODO: test_fare_min_fare_applied
#       distance=5km, per_km_rate=2.50 → raw=12.50, min_fare=50 → fare=50.00
#
# TODO: test_fare_decimal_precision
#       Verify Decimal(10,2) — no floating point issues
#       distance=33.33km, rate=2.50 → fare=83.33 (not 83.32500000001)
#
# TODO: test_partial_fare_proportional
#       Ride: 200km, fare=500.00
#       Passenger rides 100km → partial_fare=250.00
#       Passenger rides 60km → partial_fare=150.00
#
# TODO: test_fare_endpoint_returns_estimate
#       GET /api/v1/fare/calculate?src_lat=...&dst_lat=... → 200 with fare
#       (mock OSRM response)
#
# work by adolf.
