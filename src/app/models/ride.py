import uuid
from sqlalchemy import (
    Column, String, Integer, Text, Boolean,
    DateTime, Index, CheckConstraint, ForeignKey
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.types import Numeric
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.postgres import Base


class Ride(Base):
    __tablename__ = "rides"

    # ─── Primary Key ──────────────────────────
    id                  = Column(
                            UUID(as_uuid=True),
                            primary_key=True,
                            server_default=func.gen_random_uuid()
                        )

    # ─── Driver ───────────────────────────────
    # FK → drivers.id (NOT users.id)
    driver_id           = Column(
                            UUID(as_uuid=True),
                            ForeignKey("drivers.id"),
                            nullable=False
                        )

    # ─── Source ───────────────────────────────
    source_address      = Column(Text,          nullable=False)
    source_lat          = Column(Numeric(10, 7), nullable=False)
    source_lng          = Column(Numeric(10, 7), nullable=False)
    source_city         = Column(String(100),   nullable=True)

    # ─── Destination ──────────────────────────
    dest_address        = Column(Text,          nullable=False)
    dest_lat            = Column(Numeric(10, 7), nullable=False)
    dest_lng            = Column(Numeric(10, 7), nullable=False)
    dest_city           = Column(String(100),   nullable=True)

    # ─── Schedule ─────────────────────────────
    departure_time      = Column(DateTime(timezone=True), nullable=False)

    # ─── Seats ────────────────────────────────
    total_seats         = Column(Integer, nullable=False)
    available_seats     = Column(Integer, nullable=False)

    # ─── Route (from OSRM) ────────────────────
    total_distance_km   = Column(Numeric(8, 2), nullable=False)
    estimated_duration  = Column(Integer,       nullable=True)   # minutes
    route_geometry      = Column(Text,          nullable=True)   # encoded polyline

    # ─── Fare (from fare_engine) ──────────────
    total_fare          = Column(Numeric(10, 2), nullable=False)
    per_seat_fare       = Column(Numeric(10, 2), nullable=False)

    # ─── Status ───────────────────────────────
    status              = Column(
                            String(20),
                            nullable=False,
                            default="active"
                        )

    # ─── Timestamps ───────────────────────────
    created_at          = Column(DateTime(timezone=True),
                            nullable=False, server_default=func.now())
    updated_at          = Column(DateTime(timezone=True),
                            nullable=False, server_default=func.now(),
                            onupdate=func.now())

    # ─── Constraints ──────────────────────────
    __table_args__ = (
        CheckConstraint(
            "total_seats BETWEEN 1 AND 8",
            name="ck_rides_total_seats"
        ),
        CheckConstraint(
            "available_seats >= 0 AND available_seats <= total_seats",
            name="ck_rides_available_seats"
        ),
        CheckConstraint(
            "status IN ('active', 'departed', 'completed', 'cancelled')",
            name="ck_rides_status"
        ),
        # Partial index — only active rides (hot path for search)
        Index(
            "idx_rides_search",
            "status", "departure_time",
            postgresql_where=("status = 'active'")
        ),
        Index("idx_rides_source_geo", "source_lat", "source_lng"),
        Index("idx_rides_dest_geo",   "dest_lat",   "dest_lng"),
        Index("idx_rides_driver_id",  "driver_id"),
    )

    # ─── Relationships ────────────────────────
    driver              = relationship("Driver",   back_populates="rides")
    bookings            = relationship("Booking",  back_populates="ride")