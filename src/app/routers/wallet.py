# =============================================================================
# routers/wallet.py — Wallet & Transaction Endpoints
# =============================================================================
# See: system-design/10-api-contracts.md §9 "Wallet Endpoints"
# See: system-design/07-wallet.md for the complete wallet design
#
# Prefix: /api/v1/wallet
#
# TODO: GET /wallet
#       - Requires: Bearer token
#       - Logic: Return current user's wallet balance
#         Auto-create wallet on first access if it doesn't exist
#       - Response: WalletResponse
#
# TODO: GET /wallet/transactions
#       - Requires: Bearer token
#       - Logic: Return paginated transaction history for current user's wallet
#       - Response: PaginatedResponse[WalletTransactionResponse]
#
# TODO: POST /wallet/cashback
#       - Requires: Bearer token
#       - Request: CashbackRequest (JSON) + UploadFile (toll_proof, multipart)
#       - Logic: Call wallet_service.request_cashback()
#         1. Verify booking exists and belongs to current user
#         2. Verify booking is completed
#         3. Verify booking is older than cashback_eligibility_days (90 days)
#         4. Upload toll proof to Supabase Storage bucket "toll-proofs"
#         5. Create wallet_transaction with txn_type="cashback", status="pending"
#         6. Admin will approve/reject from SQLAdmin dashboard
#       - Response: WalletTransactionResponse (201 Created)
#       - Error: BOOKING_NOT_ELIGIBLE, ALREADY_CLAIMED
#
# TODO: POST /wallet/withdraw
#       - Requires: Bearer token
#       - Request body: WithdrawalRequest
#       - Logic: Call wallet_service.request_withdrawal()
#         1. Verify balance >= amount
#         2. Verify amount <= max_withdrawal_amount (from platform_config)
#         3. Create wallet_transaction with txn_type="withdrawal", status="pending"
#         4. Admin manually processes UPI transfer and approves from dashboard
#       - Response: WalletTransactionResponse (201 Created)
#       - Error: INSUFFICIENT_BALANCE, EXCEEDS_MAX_WITHDRAWAL
#
# Connects with:
#   → app/schemas/wallet.py (WalletResponse, WalletTransactionResponse, CashbackRequest, WithdrawalRequest)
#   → app/services/wallet_service.py (get_balance, request_cashback, request_withdrawal)
#   → app/services/storage_service.py (toll proof upload)
#   → app/dependencies.py (get_current_user, get_db)
#
# work by adolf.
