# =============================================================================
# models/wallet_transaction.py — Wallet Transaction ORM Model
# =============================================================================
# See: system-design/11-db-schema-ddl.md §10 "Table: wallet_transactions"
# See: system-design/07-wallet.md §3-§4 for cashback and withdrawal flows
#
# Immutable ledger of wallet movements. Each row is a credit (cashback)
# or debit (withdrawal). Balance is derived from SUM of transactions.
#
# TODO: Define WalletTransaction model mapped to "wallet_transactions" table
# TODO: Columns:
#       - id: UUID PK
#       - wallet_id: UUID FK → wallets.id, NOT NULL
#       - txn_type: String(20), NOT NULL
#         CHECK: txn_type IN ('cashback', 'withdrawal')
#       - amount: Numeric(10,2), NOT NULL, CHECK (amount > 0)
#       - status: String(20), NOT NULL, default "pending"
#         CHECK: status IN ('pending', 'approved', 'rejected', 'completed')
#       - reference_id: UUID, nullable — links to booking_id for cashback context
#       - toll_proof_url: Text, nullable — Supabase Storage URL for toll receipt
#       - upi_id: String(100), nullable — for withdrawals
#       - admin_note: Text, nullable — admin can leave a note on approval/rejection
#       - processed_at: TIMESTAMPTZ, nullable — when admin processed it
#       - created_at: TIMESTAMPTZ
#
# TODO: Relationships:
#       - wallet: relationship("Wallet", back_populates="transactions")
#
# TODO: Indexes:
#       - idx_wallet_txns_wallet_id ON wallet_id
#       - idx_wallet_txns_status ON status (admin queries pending txns)
#
# Connects with:
#   → app/models/wallet.py (FK: wallet_id → wallets.id)
#   → app/services/wallet_service.py (create cashback request, process withdrawal)
#   → app/services/storage_service.py (toll proof upload)
#   → app/admin/views.py (admin approve/reject actions)
#
# work by adolf.
