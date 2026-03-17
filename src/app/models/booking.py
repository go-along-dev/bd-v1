from sqlalchemy import (
    Column, String, Integer, Text,
    DateTime, ForeignKey, Index, CheckConstraint
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.types import Numeric
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.postgres import Base


class Booking(Base):
    __tablename__ = "bookings"

    # ─── Primary Key ──────────────────────────
    id              = Column(
                        UUID(as_uuid=True),
                        primary_key=True,
                        server_default=func.gen_random_uuid()
                    )

    # ─── References ───────────────────────────
    ride_id         = Column(
                        UUID(as_uuid=True),
                        ForeignKey("rides.id"),
                        nullable=False
                    )
    passenger_id    = Column(
                        UUID(as_uuid=True),
                        ForeignKey("users.id"),
                        nullable=False
                    )

    # ─── Seats ────────────────────────────────
    seats_booked    = Column(Integer, nullable=False, default=1)

    # ─── Pickup ───────────────────────────────
    pickup_address  = Column(Text,           nullable=False)
    pickup_lat      = Column(Numeric(10, 7), nullable=False)
    pickup_lng      = Column(Numeric(10, 7), nullable=False)

    # ─── Dropoff ──────────────────────────────
    # Phase 1: NULL means ride destination
    dropoff_address = Column(Text,           nullable=True)
    dropoff_lat     = Column(Numeric(10, 7), nullable=True)
    dropoff_lng     = Column(Numeric(10, 7), nullable=True)

    # ─── Fare ─────────────────────────────────
    # OSRM: pickup → ride destination
    distance_km     = Column(Numeric(8, 2),  nullable=False)
    # Proportional fare for this booking
    fare            = Column(Numeric(10, 2), nullable=False)

    # ─── Status ───────────────────────────────
    status          = Column(
                        String(20),
                        nullable=False,
                        default="confirmed"
                    )

    # ─── Timestamps ───────────────────────────
    booked_at       = Column(DateTime(timezone=True),
                        nullable=False, server_default=func.now())
    cancelled_at    = Column(DateTime(timezone=True), nullable=True)

    # ─── Constraints ──────────────────────────
    __table_args__ = (
        CheckConstraint(
            "seats_booked BETWEEN 1 AND 4",
            name="ck_bookings_seats"
        ),
        CheckConstraint(
            "status IN ('confirmed', 'cancelled', 'completed')",
            name="ck_bookings_status"
        ),
        Index("idx_bookings_ride_id",      "ride_id"),
        Index("idx_bookings_passenger_id", "passenger_id"),
        # Prevents duplicate active bookings per passenger per ride
        # Still allows rebooking after cancellation
        Index(
            "idx_bookings_unique_active",
            "ride_id", "passenger_id",
            unique=True,
            postgresql_where="status = 'confirmed'"
        ),
    )

    # ─── Relationships ────────────────────────
    # NOTE: passenger cannot book their own ride — enforced in service layer
    ride            = relationship("Ride",  back_populates="bookings")
    passenger       = relationship("User",  back_populates="bookings")