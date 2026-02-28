# =============================================================================
# schemas/wallet.py — Wallet & Transaction Schemas
# =============================================================================
# See: system-design/10-api-contracts.md §9 "Wallet Endpoints"
# See: system-design/07-wallet.md for wallet flows
#
# TODO: class WalletResponse(BaseModel):
#       - id: UUID
#       - balance: Decimal
#       - created_at: datetime
#       model_config: from_attributes = True
#
# TODO: class WalletTransactionResponse(BaseModel):
#       - id: UUID
#       - txn_type: str       ("cashback" | "withdrawal")
#       - amount: Decimal
#       - status: str          ("pending" | "approved" | "rejected" | "completed")
#       - reference_id: UUID | None
#       - toll_proof_url: str | None
#       - upi_id: str | None
#       - admin_note: str | None
#       - processed_at: datetime | None
#       - created_at: datetime
#       model_config: from_attributes = True
#
# TODO: class CashbackRequest(BaseModel):
#       - booking_id: UUID     (the completed booking for which cashback is claimed)
#       - amount: Decimal = Field(..., gt=0)
#       Note: toll_proof file comes as UploadFile in the router, not in this schema
#       Eligibility: booking must be 90+ days old (configurable via platform_config)
#
# TODO: class WithdrawalRequest(BaseModel):
#       - amount: Decimal = Field(..., gt=0)  (max from platform_config.max_withdrawal_amount)
#       - upi_id: str = Field(..., pattern=r"^[\w.\-]+@[\w]+$")
#
# Connects with:
#   → app/routers/wallet.py (GET /wallet, GET /wallet/transactions, POST /wallet/cashback,
#                             POST /wallet/withdraw)
#   → app/services/wallet_service.py
#
# work by adolf.
