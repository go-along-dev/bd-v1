# =============================================================================
# tests/test_bookings.py — Booking Endpoint Tests
# =============================================================================
# See: system-design/10-api-contracts.md §6 "Booking Endpoints"
# See: system-design/04-bookings.md §5 for race condition tests
#
# TODO: test_create_booking_success
#       POST /api/v1/bookings → 201, fare calculated, seats decremented
#
# TODO: test_cannot_book_own_ride
#       Driver tries to book their own ride → 400 SELF_BOOKING
#
# TODO: test_cannot_book_full_ride
#       Ride with 0 available seats → 400 SEATS_FULL
#
# TODO: test_cannot_duplicate_booking
#       Book same ride twice → 409 DUPLICATE_BOOKING
#
# TODO: test_cannot_book_cancelled_ride
#       Book a cancelled ride → 400 RIDE_NOT_ACTIVE
#
# TODO: test_cancel_booking_within_window
#       Cancel with >2 hours to departure → 200, seats restored
#
# TODO: test_cancel_booking_outside_window
#       Cancel with <2 hours to departure → 400 CANCELLATION_WINDOW_CLOSED
#
# TODO: test_concurrent_booking_race_condition
#       Simulate 2 concurrent bookings for last seat → only 1 succeeds
#       (Use asyncio.gather to hit endpoint simultaneously)
#
# work by adolf.
