import uuid
from sqlalchemy import (
    Column, String, Boolean, Text, Index,
    DateTime, CheckConstraint
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.postgres import Base


class User(Base):
    __tablename__ = "users"

    # ─── Primary Key ──────────────────────────
    id              = Column(
                        UUID(as_uuid=True),
                        primary_key=True,
                        server_default=func.gen_random_uuid()
                    )

    # ─── Identity ─────────────────────────────
    supabase_uid    = Column(String,      nullable=False, unique=True)
    name            = Column(String(100), nullable=True)
    email           = Column(String(255), nullable=True,  unique=True)
    phone           = Column(String(15),  nullable=True,  unique=True)
    profile_photo   = Column(Text,        nullable=True)

    # ─── Role ─────────────────────────────────
    role            = Column(
                        String(20),
                        nullable=False,
                        default="passenger"
                    )

    # ─── Status ───────────────────────────────
    is_active       = Column(Boolean,  nullable=False, default=True)

    # ─── FCM ──────────────────────────────────
    fcm_token       = Column(Text, nullable=True)

    # ─── Timestamps ───────────────────────────
    created_at      = Column(DateTime(timezone=True),
                        nullable=False, server_default=func.now())
    updated_at      = Column(DateTime(timezone=True),
                        nullable=False, server_default=func.now(),
                        onupdate=func.now())

    # ─── Constraints ──────────────────────────
    __table_args__ = (
        CheckConstraint(
            "role IN ('passenger', 'driver', 'admin')",
            name="ck_users_role"
        ),
        # Hot path index — JWT auth lookup
        Index("idx_users_supabase_uid", "supabase_uid"),
    )

 # ─── Relationships ────────────────────────
    # NOTE: wallet is on Driver, NOT User
    # NOTE: rides is on Driver, NOT User
    driver      = relationship("Driver",  back_populates="user", uselist=False)
    bookings    = relationship("Booking", back_populates="passenger")