import httpx
from decimal import Decimal
from app.config import settings


# ─── Shared HTTP Client ───────────────────────
# Reuse connections across requests (connection pooling)
_client: httpx.AsyncClient | None = None


def get_client() -> httpx.AsyncClient:
    global _client
    if _client is None or _client.is_closed:
        _client = httpx.AsyncClient(
            base_url=settings.OSRM_BASE_URL,
            timeout=5.0,
        )
    return _client


async def close_client() -> None:
    """Call on app shutdown."""
    global _client
    if _client and not _client.is_closed:
        await _client.aclose()
        _client = None


# ─── Get Route ────────────────────────────────
async def get_route(
    src_lat: float,
    src_lng: float,
    dst_lat: float,
    dst_lng: float,
) -> dict:
    """
    Get full route from OSRM including distance, duration, geometry.
    Note: OSRM uses lng,lat order (not lat,lng!)
    """
    # OSRM coordinate format: lng,lat
    coords = f"{src_lng},{src_lat};{dst_lng},{dst_lat}"
    url    = f"/route/v1/driving/{coords}"
    params = {
        "overview":     "full",
        "alternatives": "false",
        "geometries":   "polyline",
    }

    try:
        client   = get_client()
        response = await client.get(url, params=params)
        response.raise_for_status()
        data = response.json()
    except httpx.ConnectError:
        raise Exception("OSRM service is unreachable. Check if OSRM is running.")
    except httpx.TimeoutException:
        raise Exception("OSRM request timed out.")

    if data.get("code") != "Ok" or not data.get("routes"):
        raise Exception("No route found between the given coordinates.")

    route = data["routes"][0]
    leg   = route["legs"][0]

    return {
        "distance_km":      round(leg["distance"] / 1000, 2),
        "duration_minutes": round(leg["duration"] / 60),
        "geometry":         route.get("geometry"),   # encoded polyline
    }


# ─── Get Distance Only ────────────────────────
async def get_distance(
    src_lat: float,
    src_lng: float,
    dst_lat: float,
    dst_lng: float,
) -> float:
    """
    Lightweight — returns only distance_km.
    Used by booking_service for partial fare calculation.
    """
    coords = f"{src_lng},{src_lat};{dst_lng},{dst_lat}"
    url    = f"/route/v1/driving/{coords}"
    params = {
        "overview":     "false",
        "alternatives": "false",
    }

    try:
        client   = get_client()
        response = await client.get(url, params=params)
        response.raise_for_status()
        data = response.json()
    except httpx.ConnectError:
        raise Exception("OSRM service is unreachable.")
    except httpx.TimeoutException:
        raise Exception("OSRM request timed out.")

    if data.get("code") != "Ok" or not data.get("routes"):
        raise Exception("No route found between the given coordinates.")

    distance_m = data["routes"][0]["legs"][0]["distance"]
    return round(distance_m / 1000, 2)


# ─── Get Distance Matrix ──────────────────────
async def get_distance_matrix(
    origins: list[tuple[float, float]],
    destinations: list[tuple[float, float]],
) -> list[list[float]]:
    """
    Batch distance calculations via OSRM table API.
    Scaffolded for Phase 2 — not used in MVP.
    coords format: [(lat, lng), ...]
    """
    # Combine all coords — OSRM table API takes all points together
    all_coords = origins + destinations
    coord_str  = ";".join(f"{lng},{lat}" for lat, lng in all_coords)
    url        = f"/table/v1/driving/{coord_str}"

    src_indices = ";".join(str(i) for i in range(len(origins)))
    dst_indices = ";".join(
        str(i) for i in range(len(origins), len(origins) + len(destinations))
    )

    params = {
        "sources":      src_indices,
        "destinations": dst_indices,
        "annotations":  "distance",
    }

    try:
        client   = get_client()
        response = await client.get(url, params=params)
        response.raise_for_status()
        data = response.json()
    except httpx.ConnectError:
        raise Exception("OSRM service is unreachable.")
    except httpx.TimeoutException:
        raise Exception("OSRM request timed out.")

    # Convert meters → km
    distances = data.get("distances", [])
    return [
        [round(d / 1000, 2) if d else 0 for d in row]
        for row in distances
    ]