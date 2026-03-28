from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from decimal import Decimal
from uuid import UUID

from app.dependencies import get_db
from app.schemas.fare import FareCalcResponse, PartialFareResponse
from app.services.fare_engine import fare_engine
from app.services import ors_service
from app.models.ride import Ride

router = APIRouter(prefix="/fare", tags=["Fare"])

# ─── GET /fare/calculate ──────────────────────
@router.get("/calculate", response_model=FareCalcResponse)
async def calculate_fare(
    source_lat:   float = Query(..., ge=-90,  le=90),
    source_lng:   float = Query(..., ge=-180, le=180),
    dest_lat:     float = Query(..., ge=-90,  le=90),
    dest_lng:     float = Query(..., ge=-180, le=180),
    mileage_kmpl: float = Query(..., ge=1,    le=50),
    seats:        int   = Query(..., ge=1,    le=8),
    db: AsyncSession    = Depends(get_db),
):
    """
    Estimate full route fare before creating a ride.
    FUEL-COST-SHARING MODEL: Public endpoint, no auth required.
    """
    try:
        # 1. Get distance from OSRM
        distance_km = await ors_service.get_distance(
            src_lat=source_lat,
            src_lng=source_lng,
            dst_lat=dest_lat,
            dst_lng=dest_lng,
        )

        # 2. Calculate fare
        result = await fare_engine.calculate_full_fare(
            db=db,
            distance_km=distance_km,
            mileage_kmpl=mileage_kmpl,
            seats=seats,
        )

        # 3. Format response
        fuel_cost        = result["fuel_cost"]
        cost_with_margin = fuel_cost * (1 + result["platform_margin_pct"] / Decimal("100"))
        min_fare_applied = cost_with_margin < result["total_fare"]
        platform_margin  = result["total_fare"] - fuel_cost

        return FareCalcResponse(
            distance_km      = result["distance_km"],
            total_fare       = result["total_fare"],
            per_seat_fare    = result["per_seat_fare"],
            fuel_cost        = fuel_cost,
            platform_margin  = platform_margin,
            min_fare_applied = min_fare_applied,
        )
    except Exception as e:
        import traceback
        print(f"❌ FARE CALCULATION CRASH: {str(e)}")
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal Fare Error: {str(e)}"
        )


# ─── GET /fare/partial ────────────────────────
@router.get("/partial", response_model=PartialFareResponse)
async def calculate_partial_fare(
    ride_id:    UUID  = Query(...),
    pickup_lat: float = Query(..., ge=-90,  le=90),
    pickup_lng: float = Query(..., ge=-180, le=180),
    seats:      int   = Query(default=1, ge=1, le=6),
    db: AsyncSession  = Depends(get_db),
):
    """
    Estimate fare for a partial route booking.
    Public endpoint, no auth required.
    """
    try:
        # 1. Fetch ride
        result = await db.execute(select(Ride).where(Ride.id == ride_id))
        ride = result.scalar_one_or_none()

        if not ride:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ride not found")

        # 2. Get distance from pickup to ride destination
        partial_distance_km = await ors_service.get_distance(
            src_lat=pickup_lat,
            src_lng=pickup_lng,
            dst_lat=float(ride.dest_lat),
            dst_lng=float(ride.dest_lng),
        )

        # 3. Calculate proportional fare
        fare = fare_engine.calculate_partial_fare(
            per_seat_fare_full    = Decimal(str(ride.per_seat_fare)),
            total_distance_km     = Decimal(str(ride.total_distance_km)),
            passenger_distance_km = Decimal(str(partial_distance_km)),
            seats_booked          = seats,
        )

        return PartialFareResponse(
            partial_distance_km = Decimal(str(partial_distance_km)),
            fare                = fare,
            per_seat_fare_full  = Decimal(str(ride.per_seat_fare)),
        )
    except Exception as e:
        print(f"❌ PARTIAL FARE ERROR: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error calculating partial fare: {str(e)}"
        )
