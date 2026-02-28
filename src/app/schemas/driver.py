# =============================================================================
# schemas/driver.py — Driver Request/Response Schemas
# =============================================================================
# See: system-design/10-api-contracts.md §4 "Driver Endpoints"
# See: system-design/02-user-driver.md §3-§5 for the full driver flow
#
# TODO: class DriverRegisterRequest(BaseModel):
#       - vehicle_number: str = Field(..., max_length=20)
#       - vehicle_make: str = Field(..., max_length=50)   — e.g. "Maruti"
#       - vehicle_model: str = Field(..., max_length=100)  — e.g. "Swift Dzire"
#       - vehicle_type: str = Field(...)   — enum: sedan|suv|hatchback|mini_bus
#       - vehicle_color: str | None = Field(None, max_length=30)
#       - license_number: str = Field(..., max_length=50)
#       - seat_capacity: int = Field(..., ge=1, le=8)
#       - mileage_kmpl: float = Field(..., ge=1, le=50)
#
# TODO: class DriverResponse(BaseModel):
#       - id: UUID
#       - user_id: UUID
#       - vehicle_number: str
#       - vehicle_make: str
#       - vehicle_model: str
#       - vehicle_type: str
#       - vehicle_color: str | None
#       - license_number: str
#       - seat_capacity: int
#       - mileage_kmpl: float
#       - verification_status: str  ("pending" | "approved" | "rejected")
#       - rejection_reason: str | None
#       - onboarded_at: datetime | None
#       - documents: list[DriverDocumentResponse]
#       - created_at: datetime
#       model_config: from_attributes = True
#
# TODO: class DriverDocumentResponse(BaseModel):
#       - id: UUID
#       - doc_type: str
#       - file_url: str
#       - created_at: datetime
#
# TODO: class DriverDocumentUploadRequest(BaseModel):
#       - doc_type: str = Field(..., pattern="^(driving_license|vehicle_rc|insurance|aadhar|pan)$")
#       Note: actual file comes as UploadFile in the router, not in this schema
#
# Connects with:
#   → app/routers/drivers.py (POST /drivers/register, GET /drivers/me, POST /drivers/documents)
#   → app/services/driver_service.py
#
# work by adolf.
