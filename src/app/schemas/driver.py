from pydantic import BaseModel, Field
from uuid import UUID
from datetime import datetime


# ─── Register Driver ──────────────────────────
class DriverRegisterRequest(BaseModel):
    vehicle_number: str   = Field(..., max_length=20)
    vehicle_make:   str   = Field(..., max_length=50)
    vehicle_model:  str   = Field(..., max_length=100)
    vehicle_type:   str   = Field(..., pattern="^(sedan|suv|hatchback|mini_bus)$")
    vehicle_color:  str | None = Field(None, max_length=30)
    license_number: str   = Field(..., max_length=50)
    seat_capacity:  int   = Field(..., ge=1, le=8)
    mileage_kmpl:   float = Field(..., ge=1, le=50)


# ─── Driver Document Response ─────────────────
class DriverDocumentResponse(BaseModel):
    id:         UUID
    doc_type:   str
    file_url:   str
    created_at: datetime

    model_config = {"from_attributes": True}


# ─── Driver Response ──────────────────────────
class DriverResponse(BaseModel):
    id:                  UUID
    user_id:             UUID
    vehicle_number:      str
    vehicle_make:        str
    vehicle_model:       str
    vehicle_type:        str
    vehicle_color:       str | None
    license_number:      str
    seat_capacity:       int
    mileage_kmpl:        float
    verification_status: str
    rejection_reason:    str | None
    onboarded_at:        datetime | None
    documents:           list[DriverDocumentResponse] = []
    created_at:          datetime

    model_config = {"from_attributes": True}


# ─── Driver Status Response ───────────────────
class DriverStatusResponse(BaseModel):
    verification_status: str
    rejection_reason:    str | None
    verified_at:         datetime | None
    onboarded_at:        datetime | None


# ─── Document Upload Request ──────────────────
class DriverDocumentUploadRequest(BaseModel):
    doc_type: str = Field(
        ...,
        pattern="^(driving_license|vehicle_rc|insurance|aadhar|pan)$"
    )
    # Note: actual file comes as UploadFile in router, not in this schema