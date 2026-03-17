from pydantic import BaseModel
from typing import TypeVar, Generic

T = TypeVar("T")


# ─── Paginated Response ───────────────────────
class PaginatedResponse(BaseModel, Generic[T]):
    data:     list[T]
    total:    int
    page:     int
    per_page: int


# ─── Message Response ─────────────────────────
class MessageResponse(BaseModel):
    message: str


# ─── Error Response ───────────────────────────
class ErrorResponse(BaseModel):
    detail: str
    code:   str
    # e.g. "RIDE_NOT_FOUND", "SEATS_FULL", "DUPLICATE_BOOKING"


# ─── Health Response ──────────────────────────
class HealthResponse(BaseModel):
    status: str = "ok"