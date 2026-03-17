from sqlalchemy import (
    Column, String, Integer, Text,
    DateTime, ForeignKey, Index, CheckConstraint
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.types import Numeric
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.postgres import Base


class Driver(Base):
    __tablename__ = "drivers"

    # ─── Primary Key ──────────────────────────
    id                  = Column(
                            UUID(as_uuid=True),
                            primary_key=True,
                            server_default=func.gen_random_uuid()
                        )

    # ─── User ─────────────────────────────────
    # One driver profile per user
    user_id             = Column(
                            UUID(as_uuid=True),
                            ForeignKey("users.id"),
                            nullable=False,
                            unique=True
                        )

    # ─── Vehicle ──────────────────────────────
    vehicle_number      = Column(String(20),  nullable=False)
    vehicle_make        = Column(String(50),  nullable=False)
    vehicle_model       = Column(String(100), nullable=False)
    vehicle_type        = Column(String(30),  nullable=False)
    # sedan | suv | hatchback | mini_bus
    vehicle_color       = Column(String(30),  nullable=True)

    # ─── License ──────────────────────────────
    license_number      = Column(String(50),  nullable=False)

    # ─── Capacity & Mileage ───────────────────
    seat_capacity       = Column(Integer,        nullable=False)
    mileage_kmpl        = Column(Numeric(5, 2),  nullable=False)
    # Used by fare_engine for fuel cost calculation

    # ─── Verification ─────────────────────────
    verification_status = Column(
                            String(20),
                            nullable=False,
                            default="pending"
                        )
    # pending → approved → rejected
    rejection_reason    = Column(Text,   nullable=True)
    verified_at         = Column(DateTime(timezone=True), nullable=True)
    verified_by         = Column(UUID(as_uuid=True),      nullable=True)
    # Admin user who verified

    # ─── Onboarding ───────────────────────────
    # Set when admin approves — cashback 3-month window starts here
    onboarded_at        = Column(DateTime(timezone=True), nullable=True)

    # ─── Timestamps ───────────────────────────
    created_at          = Column(DateTime(timezone=True),
                            nullable=False, server_default=func.now())
    updated_at          = Column(DateTime(timezone=True),
                            nullable=False, server_default=func.now(),
                            onupdate=func.now())

    # ─── Constraints ──────────────────────────
    __table_args__ = (
        CheckConstraint(
            "seat_capacity BETWEEN 1 AND 8",
            name="ck_drivers_seat_capacity"
        ),
        CheckConstraint(
            "mileage_kmpl BETWEEN 1 AND 50",
            name="ck_drivers_mileage"
        ),
        CheckConstraint(
            "vehicle_type IN ('sedan', 'suv', 'hatchback', 'mini_bus')",
            name="ck_drivers_vehicle_type"
        ),
        CheckConstraint(
            "verification_status IN ('pending', 'approved', 'rejected')",
            name="ck_drivers_verification_status"
        ),
        Index("idx_drivers_user_id", "user_id"),
        Index("idx_drivers_status",  "verification_status"),
    )

    # ─── Relationships ────────────────────────
    user        = relationship("User",           back_populates="driver")
    documents   = relationship("DriverDocument", back_populates="driver",
                    cascade="all, delete-orphan")
    rides       = relationship("Ride",           back_populates="driver")
    wallet      = relationship("Wallet",         back_populates="driver",
                    uselist=False)