# =============================================================================
# services/wallet_service.py — Wallet & Cashback Service
# =============================================================================
# See: system-design/07-wallet.md for the complete wallet design
# See: system-design/07-wallet.md §3 "Cashback Eligibility" (90-day rule)
# See: system-design/10-api-contracts.md §9 "Wallet Endpoints"
#
# TODO: async def get_or_create_wallet(db: AsyncSession, user: User) → Wallet:
#       """
#       Returns the user's wallet. Creates one with balance=0 if it doesn't exist.
#       Called on every wallet endpoint access.
#       """
#
# TODO: async def get_transactions(db: AsyncSession, wallet: Wallet, page, per_page) → tuple[list[WalletTransaction], int]:
#       """Paginated transaction history for a wallet."""
#
# TODO: async def request_cashback(
#           db: AsyncSession, user: User, booking_id: UUID, amount: Decimal, toll_proof_url: str
#       ) → WalletTransaction:
#       """
#       Steps:
#       1. Verify booking exists and belongs to user
#       2. Verify booking.status == 'completed'
#       3. Verify booking age >= cashback_eligibility_days (90 days from platform_config)
#          → else BOOKING_NOT_ELIGIBLE
#       4. Verify no existing cashback claim for this booking
#          → else ALREADY_CLAIMED
#       5. Create wallet_transaction (txn_type='cashback', status='pending')
#       6. Return transaction — admin will approve/reject from dashboard
#       """
#
# TODO: async def request_withdrawal(db: AsyncSession, user: User, amount: Decimal, upi_id: str) → WalletTransaction:
#       """
#       Steps:
#       1. Get wallet, verify balance >= amount → else INSUFFICIENT_BALANCE
#       2. Verify amount <= max_withdrawal_amount → else EXCEEDS_MAX_WITHDRAWAL
#       3. Create wallet_transaction (txn_type='withdrawal', status='pending')
#       4. Return transaction — admin manually processes UPI transfer
#       """
#
# TODO: async def approve_transaction(db: AsyncSession, txn: WalletTransaction, admin_note: str | None) → None:
#       """
#       Called by admin via SQLAdmin custom action.
#       For cashback: add amount to wallet.balance
#       For withdrawal: subtract amount from wallet.balance
#       Set status='approved', processed_at=now()
#       """
#
# TODO: async def reject_transaction(db: AsyncSession, txn: WalletTransaction, admin_note: str) → None:
#       """Called by admin. Set status='rejected', no balance change."""
#
# Connects with:
#   → app/routers/wallet.py (all wallet endpoints)
#   → app/models/wallet.py (Wallet model)
#   → app/models/wallet_transaction.py (WalletTransaction model)
#   → app/models/booking.py (verify booking for cashback)
#   → app/models/platform_config.py (eligibility days, max withdrawal)
#   → app/admin/views.py (approve/reject custom actions)
#   → app/services/storage_service.py (toll proof upload in router, URL passed here)
#
# work by adolf.
