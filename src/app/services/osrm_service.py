# =============================================================================
# services/osrm_service.py — OSRM Routing & Distance Service
# =============================================================================
# See: system-design/03-rides.md §2 for OSRM integration
# See: system-design/09-infra.md §5 for OSRM self-hosting on GCP
#
# OSRM (Open Source Routing Machine) runs self-hosted on a GCP Compute Engine
# e2-medium VM (4GB RAM, 2 vCPU) with India OSM data extract.
# Provides driving distance and ETA — no API key needed, no cost per request.
#
# TODO: Create a shared httpx.AsyncClient (reuse connections, connection pooling).
#       Initialize once, close on app shutdown.
#       Base URL from config.OSRM_BASE_URL (e.g., http://10.128.0.2:5000)
#
# TODO: async def get_route_distance(
#           src_lat: Decimal, src_lng: Decimal,
#           dst_lat: Decimal, dst_lng: Decimal
#       ) → dict:
#       """
#       Calls OSRM route API:
#       GET {OSRM_BASE_URL}/route/v1/driving/{src_lng},{src_lat};{dst_lng},{dst_lat}
#           ?overview=false&alternatives=false
#
#       Note: OSRM uses lng,lat order (not lat,lng!)
#
#       Parse response:
#       - distance_km = response.routes[0].legs[0].distance / 1000  (meters → km)
#       - duration_min = response.routes[0].legs[0].duration / 60    (seconds → min)
#
#       Return: {"distance_km": Decimal, "duration_min": Decimal}
#
#       Error handling:
#       - If OSRM is unreachable → raise ServiceUnavailableError
#       - If no route found → raise NoRouteFoundError
#       - Timeout: 5 seconds
#       """
#
# TODO: async def get_distance_matrix(origins: list, destinations: list) → list:
#       """
#       For future use — batch distance calculations.
#       OSRM table API: {base}/table/v1/driving/{coords}
#       Not needed for MVP but good to scaffold.
#       """
#
# Connects with:
#   → app/config.py (OSRM_BASE_URL)
#   → app/services/ride_service.py (calls get_route_distance on ride creation)
#   → app/services/booking_service.py (calls get_route_distance for partial distance)
#   → app/services/fare_engine.py (uses distance to calculate fare)
#   → app/routers/fare.py (fare estimation endpoint calls this)
#   → app/utils/exceptions.py (ServiceUnavailableError, NoRouteFoundError)
#
# work by adolf.
