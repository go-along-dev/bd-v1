"""
GoAlong — Toll Plaza Seeder
Fetches all toll booths in India from OpenStreetMap via Overpass API
and inserts them into the toll_plazas table.

Run once:
    python -m app.scripts.seed_toll_plazas
"""

import asyncio
import httpx
import json
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select
from app.models.toll import TollPlaza
from app.config import settings

# ─── Overpass Query ───────────────────────────────────────────────────────────
# Fetches all nodes tagged as toll booths in India
OVERPASS_QUERY = """
[out:json][timeout:120];
area["ISO3166-1"="IN"][admin_level=2]->.india;
(
  node["barrier"="toll_booth"](area.india);
  node["toll"="yes"](area.india);
  way["toll"="yes"](area.india);
);
out center tags;
"""

OVERPASS_URL = "https://overpass-api.de/api/interpreter"

# ─── Default Toll Rates by Vehicle Type ───────────────────────────────────────
# Based on approximate NHAI rates for car/jeep/van
DEFAULT_CAR_RATE = 65.0  # ₹ — will be overridden if OSM has fee tag


def parse_car_rate(tags: dict) -> float:
    """Try to extract toll fee from OSM tags."""
    for key in ["fee", "toll:car", "charge", "toll"]:
        value = tags.get(key, "")
        if value and value.replace(".", "").isdigit():
            return float(value)
    return DEFAULT_CAR_RATE


def extract_location(element: dict) -> tuple[float, float] | None:
    """Extract lat/lng from OSM element (node or way with center)."""
    if element["type"] == "node":
        return element.get("lat"), element.get("lon")
    elif element["type"] == "way":
        center = element.get("center", {})
        return center.get("lat"), center.get("lon")
    return None, None


def extract_name(tags: dict) -> str:
    """Get best available name from OSM tags."""
    return (
        tags.get("name:en")
        or tags.get("name")
        or tags.get("operator")
        or "Unnamed Toll Plaza"
    )


async def fetch_toll_data() -> list[dict]:
    """Fetch toll booth data from Overpass API."""
    print("🌐 Fetching toll data from OpenStreetMap Overpass API...")
    print("   This may take 30-60 seconds...")

    async with httpx.AsyncClient(timeout=180.0) as client:
        response = await client.post(
            OVERPASS_URL,
            data={"data": OVERPASS_QUERY}
        )
        response.raise_for_status()

    data = response.json()
    elements = data.get("elements", [])
    print(f"✅ Fetched {len(elements)} toll elements from OSM")
    return elements


async def seed_tolls(db: AsyncSession, elements: list[dict]):
    """Insert toll plazas into DB, skipping duplicates."""
    inserted = 0
    skipped = 0

    for element in elements:
        tags = element.get("tags", {})
        lat, lng = extract_location(element)

        # Skip if no valid location
        if not lat or not lng:
            skipped += 1
            continue

        osm_id = str(element.get("id"))

        # Check if already exists
        existing = await db.execute(
            select(TollPlaza).where(TollPlaza.osm_id == osm_id)
        )
        if existing.scalar_one_or_none():
            skipped += 1
            continue

        toll = TollPlaza(
            osm_id=osm_id,
            name=extract_name(tags),
            latitude=lat,
            longitude=lng,
            state=tags.get("addr:state") or tags.get("is_in:state"),
            highway=tags.get("ref") or tags.get("highway"),
            car_rate=parse_car_rate(tags),
        )
        db.add(toll)
        inserted += 1

        # Batch commit every 100 records
        if inserted % 100 == 0:
            await db.commit()
            print(f"   💾 Committed {inserted} records...")

    # Final commit
    await db.commit()
    print(f"\n✅ Seeding complete!")
    print(f"   Inserted : {inserted}")
    print(f"   Skipped  : {skipped} (no location or duplicates)")


async def main():
    print("=" * 50)
    print("  GoAlong — Toll Plaza Seeder")
    print("=" * 50)

    # Set up DB connection
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    try:
        elements = await fetch_toll_data()

        async with async_session() as db:
            await seed_tolls(db, elements)

    except httpx.HTTPError as e:
        print(f"❌ HTTP Error fetching from Overpass: {e}")
        print("   Try again in a few minutes — Overpass may be rate limiting")
    except Exception as e:
        print(f"❌ Error: {e}")
        raise
    finally:
        await engine.dispose()

    print("\n🚀 Toll plazas are ready in your DB!")
    print("   Detection will now work automatically on ride creation.")


if __name__ == "__main__":
    asyncio.run(main())