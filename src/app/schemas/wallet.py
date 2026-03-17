from pydantic import BaseModel, Field
from uuid import UUID
from datetime import datetime
from decimal import Decimal


# ─── Wallet Response ──────────────────────────
class WalletResponse(BaseModel):
    id:         UUID
    balance:    Decimal
    created_at: datetime

    model_config = {"from_attributes": True}


# ─── Transaction Response ─────────────────────
class WalletTransactionResponse(BaseModel):
    id:             UUID
    type:           str
    amount:         Decimal
    status:         str
    ride_id:        UUID | None
    toll_proof_url: str | None
    upi_id:         str | None
    admin_note:     str | None
    processed_at:   datetime | None
    created_at:     datetime

    model_config = {"from_attributes": True}


# ─── Cashback Request ─────────────────────────
class CashbackRequest(BaseModel):
    ride_id: UUID
    amount:  Decimal = Field(..., gt=0, le=500)
    # toll_proof comes as UploadFile in router — not in this schema
    # Eligibility: driver must be within 90 days of onboarding
    # Ride must be completed and belong to driver


# ─── Withdrawal Request ───────────────────────
class WithdrawalRequest(BaseModel):
    amount: Decimal = Field(..., gt=0)
    upi_id: str     = Field(
        ...,
        pattern=r"^[\w.\-]+@[\w]+$"
    )
    # UPI format: username@bankname
    # e.g. rahul@okaxis, 9876543210@ybl