# =============================================================================
# services/booking_service.py — Booking Service
# =============================================================================
# See: system-design/04-bookings.md for the complete booking module
# See: system-design/04-bookings.md §5 for race condition handling
# See: HLD diagram §2.4 in 00-architecture.md for end-to-end booking flow
#
# This is the most critical service — handles money, seat inventory, and notifications.
#
# TODO: async def create_booking(db: AsyncSession, user: User, data: BookingCreateRequest) → Booking:
#       """
#       CRITICAL — Must handle race conditions for seat inventory.
#
#       Steps (ALL in one transaction):
#       1. SELECT ride WHERE id = ride_id FOR UPDATE
#          → Row-level lock prevents concurrent overbooking
#          → 404 if ride not found
#       2. Validate:
#          a. ride.status == 'active' → else RIDE_NOT_ACTIVE
#          b. ride.departure_time > now() → else RIDE_DEPARTED
#          c. ride.available_seats >= seats_booked → else SEATS_FULL
#          d. ride.driver_id != user.driver.id (if user is also driver) → else SELF_BOOKING
#          e. No existing confirmed booking for this user+ride → else DUPLICATE_BOOKING
#       3. Call osrm_service.get_distance_from_pickup(pickup → ride.dest)
#          → distance_km
#       4. Call fare_engine.calculate_partial_fare(per_seat_fare, total_distance_km, distance_km)
#          → fare
#       5. INSERT booking row with fare, distance_km, seats_booked
#       6. UPDATE ride SET available_seats = available_seats - seats_booked
#       7. COMMIT
#       8. (After commit) Send FCM push to driver via notification_service
#       9. Return booking
#       """
#
# TODO: async def cancel_booking(db: AsyncSession, user: User, booking_id: UUID, reason: str | None) → None:
#       """
#       Steps:
#       1. Fetch booking, verify ownership
#       2. Check cancellation window:
#          ride.departure_time - now() > cancellation_window_hours (from platform_config)
#          → else CANCELLATION_WINDOW_CLOSED
#       3. SET booking.status = 'cancelled', cancelled_at = now()
#       4. UPDATE ride.available_seats += booking.seats_booked
#       5. Send FCM push to driver
#       """
#
# TODO: async def get_user_bookings(db: AsyncSession, user: User, page, per_page) → tuple[list[Booking], int]:
#       """All bookings where passenger_id = user.id, ordered by created_at desc."""
#
# TODO: async def get_booking_by_id(db: AsyncSession, booking_id: UUID) → Booking | None:
#       """Fetch booking with ride and passenger info."""
#
# TODO: async def complete_booking(db: AsyncSession, booking_id: UUID) → None:
#       """Mark booking as completed. Called when ride is completed by driver."""
#
# TODO: async def cancel_bookings_for_ride(db: AsyncSession, ride_id: UUID) → list[Booking]:
#       """
#       Cancel all confirmed bookings for a ride (used when ride is cancelled).
#       Returns list of cancelled bookings for notification dispatch.
#       Steps:
#       1. SELECT all bookings WHERE ride_id = ride_id AND status = 'confirmed'
#       2. Set each booking.status = 'cancelled', booking.cancelled_at = now()
#       3. Return list of cancelled bookings (caller sends FCM notifications)
#       """
#
# TODO: async def complete_bookings_for_ride(db: AsyncSession, ride_id: UUID) → tuple[list[Booking], Decimal]:
#       """
#       Complete all confirmed bookings for a ride (used when ride is completed).
#       Returns (list of completed bookings, total_earnings).
#       """
#
# Connects with:
#   → app/routers/bookings.py (all booking endpoints)
#   → app/models/booking.py (Booking model)
#   → app/models/ride.py (Ride model — FOR UPDATE lock, seat updates)
#   → app/models/platform_config.py (cancellation_window_hours)
#   → app/services/osrm_service.py (partial distance)
#   → app/services/fare_engine.py (partial fare)
#   → app/services/notification_service.py (FCM push)
#   → app/schemas/booking.py (BookingCreateRequest)
#
# work by adolf.
