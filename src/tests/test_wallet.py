# =============================================================================
# tests/test_wallet.py — Wallet & Cashback Tests
# =============================================================================
# See: system-design/07-wallet.md for wallet flows
# See: system-design/10-api-contracts.md §9 "Wallet Endpoints"
#
# TODO: test_get_wallet_auto_creates
#       GET /api/v1/wallet for user with no wallet → creates wallet, balance=0
#
# TODO: test_request_cashback_eligible
#       Booking completed 91 days ago → cashback request succeeds
#
# TODO: test_request_cashback_too_early
#       Booking completed 30 days ago → 400 BOOKING_NOT_ELIGIBLE
#
# TODO: test_request_cashback_duplicate
#       Request cashback twice for same booking → 409 ALREADY_CLAIMED
#
# TODO: test_withdrawal_sufficient_balance
#       Balance=500, withdraw 300 → 201, transaction pending
#
# TODO: test_withdrawal_insufficient_balance
#       Balance=100, withdraw 300 → 400 INSUFFICIENT_BALANCE
#
# TODO: test_withdrawal_exceeds_max
#       Withdraw amount > platform_config.max_withdrawal_amount → 400
#
# work by adolf.
