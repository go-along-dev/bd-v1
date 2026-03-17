from pydantic import BaseModel
from decimal import Decimal
from uuid import UUID


# ─── Full Fare Calculation ────────────────────
# Used as Query params in GET /fare/calculate
# (not JSON body — see router)
class FareCalcResponse(BaseModel):
    distance_km:        Decimal
    total_fare:         Decimal
    per_seat_fare:      Decimal
    fuel_cost:          Decimal
    platform_margin:    Decimal
    min_fare_applied:   bool


# ─── Partial Fare Calculation ─────────────────
# Used as Query params in GET /fare/partial
# (not JSON body — see router)
class PartialFareResponse(BaseModel):
    partial_distance_km:  Decimal
    fare:                 Decimal
    per_seat_fare_full:   Decimal