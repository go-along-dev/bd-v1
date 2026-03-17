# =============================================================================
# tests/test_rides.py — Ride Endpoint Tests
# =============================================================================
# See: system-design/10-api-contracts.md §5 "Ride Endpoints"
# See: system-design/03-rides.md §3 for bounding box search tests
#
# TODO: test_create_ride_as_approved_driver
#       POST /api/v1/rides → 201, ride created with fare and distance
#
# TODO: test_create_ride_as_non_driver_returns_403
#       POST /api/v1/rides as passenger → 403
#
# TODO: test_create_ride_as_pending_driver_returns_403
#       POST /api/v1/rides as pending driver → 403 DRIVER_NOT_APPROVED
#
# TODO: test_search_rides_bounding_box
#       Create rides in Bangalore-Mysore corridor
#       Search with Bangalore/Mysore coords → matches returned
#       Search with Delhi coords → no matches
#
# TODO: test_search_rides_filters_departed
#       Create a ride with past departure_time → should not appear in search
#
# TODO: test_search_rides_filters_cancelled
#       Create a cancelled ride → should not appear in search
#
# TODO: test_cancel_ride_cancels_bookings
#       Create ride → book it → cancel ride → booking also cancelled
#
# TODO: test_geocode_returns_coordinates
#       GET /api/v1/rides/geocode?q=Bangalore → lat/lng returned
#       (mock Nominatim API response)
#
# work by adolf.
