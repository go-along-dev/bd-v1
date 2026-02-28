# =============================================================================
# models/booking.py — Booking ORM Model
# =============================================================================
# See: system-design/11-db-schema-ddl.md §7 "Table: bookings"
# See: system-design/04-bookings.md for booking lifecycle
# See: system-design/04-bookings.md §5 for race condition handling (FOR UPDATE)
#
# A booking is a passenger reserving seat(s) on a driver's ride.
# Fare is proportional to the passenger's partial distance (pickup → destination).
# Cancellation allowed until 2 hours before departure.
#
# TODO: Define Booking model mapped to "bookings" table
# TODO: Columns:
#       - id: UUID PK
#       - ride_id: UUID FK → rides.id, NOT NULL
#       - passenger_id: UUID FK → users.id, NOT NULL
#       - seats_booked: Integer, NOT NULL, default 1, CHECK (seats_booked BETWEEN 1 AND 4)
#       - pickup_address: Text, NOT NULL
#       - pickup_lat: Numeric(10,7), NOT NULL
#       - pickup_lng: Numeric(10,7), NOT NULL
#       - dropoff_address: Text, nullable — Phase 1: NULL (= ride destination)
#       - dropoff_lat: Numeric(10,7), nullable
#       - dropoff_lng: Numeric(10,7), nullable
#       - distance_km: Numeric(8,2), NOT NULL — OSRM: pickup → ride destination
#       - fare: Numeric(10,2), NOT NULL — proportional fare for this booking
#       - status: String(20), NOT NULL, default "confirmed"
#         CHECK: status IN ('confirmed', 'cancelled', 'completed')
#       - booked_at: TIMESTAMPTZ, NOT NULL, default NOW()
#       - cancelled_at: TIMESTAMPTZ, nullable
#
# TODO: Relationships:
#       - ride: relationship("Ride", back_populates="bookings")
#       - passenger: relationship("User", back_populates="bookings")
#
# TODO: Indexes:
#       - idx_bookings_ride_id ON ride_id
#       - idx_bookings_passenger_id ON passenger_id
#       - Partial unique index: (ride_id, passenger_id) WHERE status = 'confirmed'
#         Prevents duplicate active bookings per passenger per ride, allows rebooking after cancel
#
# TODO: Constraint: passenger cannot book their own ride (enforced in service layer)
#
# Connects with:
#   → app/models/ride.py (FK: ride_id → rides.id)
#   → app/models/user.py (FK: passenger_id → users.id)
#   → app/services/booking_service.py (create, cancel, complete)
#   → app/services/fare_engine.py (proportional fare calculation)
#   → app/services/osrm_service.py (partial distance: pickup → destination)
#   → app/services/notification_service.py (FCM push to driver on new booking)
#   → app/services/chat_service.py (chat thread keyed by booking_id)
#
# work by adolf.
