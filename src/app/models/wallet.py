import uuid
from sqlalchemy import (
    Column, DateTime, ForeignKey,
    Index, CheckConstraint
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.types import Numeric
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.postgres import Base


class Wallet(Base):
    __tablename__ = "wallets"

    # ─── Primary Key ──────────────────────────
    id              = Column(
                        UUID(as_uuid=True),
                        primary_key=True,
                        server_default=func.gen_random_uuid()
                    )

    # ─── Owner ────────────────────────────────
    # One wallet per user
    driver_id       = Column(
                        UUID(as_uuid=True),
                        ForeignKey("drivers.id"),
                        nullable=False,
                        unique=True
                    )
    # ─── Balance ──────────────────────────────
    balance         = Column(
                        Numeric(10, 2),
                        nullable=False,
                        default=0.00
                    )

    # ─── Timestamps ───────────────────────────
    created_at      = Column(DateTime(timezone=True),
                        nullable=False, server_default=func.now())
    updated_at      = Column(DateTime(timezone=True),
                        nullable=False, server_default=func.now(),
                        onupdate=func.now())

    # ─── Constraints ──────────────────────────
    __table_args__ = (
        CheckConstraint(
            "balance >= 0",
            name="ck_wallets_balance"
        ),
    )

    # ─── Relationships ────────────────────────
    driver          = relationship("Driver", back_populates="wallet")
    transactions    = relationship(
                        "WalletTransaction",
                        back_populates="wallet",
                        order_by="WalletTransaction.created_at.desc()"
                    )