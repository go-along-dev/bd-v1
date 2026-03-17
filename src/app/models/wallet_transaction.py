from sqlalchemy import (
    Column, String, Text, DateTime,
    ForeignKey, Index, CheckConstraint
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.types import Numeric
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.postgres import Base


class WalletTransaction(Base):
    __tablename__ = "wallet_transactions"

    # ─── Primary Key ──────────────────────────
    id              = Column(
                        UUID(as_uuid=True),
                        primary_key=True,
                        server_default=func.gen_random_uuid()
                    )

    # ─── Wallet ───────────────────────────────
    wallet_id       = Column(
                        UUID(as_uuid=True),
                        ForeignKey("wallets.id", ondelete="CASCADE"),
                        nullable=False
                    )

    # ─── Type ─────────────────────────────────
    type            = Column(String(30), nullable=False)
    # cashback_request | cashback_credited | cashback_rejected
    # withdrawal_request | withdrawal_approved | withdrawal_rejected

    # ─── Amount ───────────────────────────────
    amount          = Column(Numeric(10, 2), nullable=False)

    # ─── Status ───────────────────────────────
    status          = Column(
                        String(20),
                        nullable=False,
                        default="pending"
                    )

    # ─── Cashback specific ────────────────────
    ride_id         = Column(
                        UUID(as_uuid=True),
                        ForeignKey("rides.id"),
                        nullable=True
                    )
    toll_proof_url  = Column(Text,        nullable=True)

    # ─── Withdrawal specific ──────────────────
    upi_id          = Column(String(100), nullable=True)

    # ─── Admin ────────────────────────────────
    admin_note      = Column(Text,        nullable=True)
    processed_by    = Column(
                        UUID(as_uuid=True),
                        ForeignKey("users.id"),
                        nullable=True
                    )
    processed_at    = Column(DateTime(timezone=True), nullable=True)

    # ─── Timestamps ───────────────────────────
    created_at      = Column(DateTime(timezone=True),
                        nullable=False, server_default=func.now())

    # ─── Constraints ──────────────────────────
    __table_args__ = (
        CheckConstraint(
            "type IN ("
            "'cashback_request', 'cashback_credited', 'cashback_rejected',"
            "'withdrawal_request', 'withdrawal_approved', 'withdrawal_rejected'"
            ")",
            name="ck_wallet_txns_type"
        ),
        CheckConstraint(
            "amount > 0",
            name="ck_wallet_txns_amount"
        ),
        CheckConstraint(
            "status IN ('pending', 'approved', 'rejected')",
            name="ck_wallet_txns_status"
        ),
        Index("idx_wallet_txns_wallet_id", "wallet_id"),
        Index("idx_wallet_txns_status",    "status"),
        Index("idx_wallet_txns_type",      "type"),
    )

    # ─── Relationships ────────────────────────
    wallet          = relationship("Wallet", back_populates="transactions")