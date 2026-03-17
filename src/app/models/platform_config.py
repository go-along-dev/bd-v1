from sqlalchemy import (
    Column, String, Text,
    DateTime, UniqueConstraint
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from app.db.postgres import Base


class PlatformConfig(Base):
    __tablename__ = "platform_config"

    # ─── Primary Key ──────────────────────────
    id          = Column(
                    UUID(as_uuid=True),
                    primary_key=True,
                    server_default=func.gen_random_uuid()
                )

    # ─── Config Entry ─────────────────────────
    key         = Column(String(50),  nullable=False, unique=True)
    value       = Column(String(255), nullable=False)
    description = Column(Text,        nullable=True)

    # ─── Timestamps ───────────────────────────
    updated_at  = Column(DateTime(timezone=True),
                    nullable=False, server_default=func.now(),
                    onupdate=func.now())

    # ─── Expected Seed Keys ───────────────────
    # per_km_rate                → "2.50"
    # platform_commission_pct    → "10"
    # min_fare                   → "50.00"
    # max_seats_per_booking      → "4"
    # cancellation_window_hours  → "2"
    # cashback_eligibility_days  → "90"
    # max_withdrawal_amount      → "5000.00"