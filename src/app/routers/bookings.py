# =============================================================================
# routers/bookings.py — Booking Endpoints
# =============================================================================
# See: system-design/10-api-contracts.md §6 "Booking Endpoints"
# See: system-design/04-bookings.md for the complete booking module design
# See: HLD diagram §2.4 in 00-architecture.md for end-to-end booking flow
#
# Prefix: /api/v1/bookings
#
# TODO: POST /bookings
#       - Requires: Bearer token (role: passenger or driver booking someone else's ride)
#       - Request body: BookingCreateRequest
#       - Logic: Call booking_service.create_booking()
#         CRITICAL — this is the most complex endpoint:
#         1. SELECT ride FOR UPDATE (row lock — prevents race conditions)
#         2. Validate: ride active, not departed, seats available, not own ride, not duplicate
#         3. Call osrm_service.get_route_distance(pickup → ride destination) for partial_distance_km
#         4. Call fare_engine.calculate_partial_fare(distance, ride.per_km_rate) for fare_amount
#         5. INSERT booking, UPDATE ride.available_seats (atomic in same transaction)
#         6. COMMIT
#         7. Send FCM push to driver: "New booking from {passenger_name}"
#       - Response: BookingResponse (201 Created)
#       - Errors: RIDE_NOT_FOUND, RIDE_NOT_ACTIVE, SEATS_FULL, SELF_BOOKING, DUPLICATE_BOOKING
#
# TODO: GET /bookings
#       - Requires: Bearer token
#       - Logic: Return all bookings for current user (as passenger)
#       - Response: PaginatedResponse[BookingResponse]
#
# TODO: GET /bookings/{booking_id}
#       - Requires: Bearer token (booking owner or ride driver)
#       - Response: BookingResponse
#
# TODO: DELETE /bookings/{booking_id}
#       - Requires: Bearer token (booking owner only)
#       - Request body: BookingCancelRequest (optional reason)
#       - Logic: Call booking_service.cancel_booking()
#         1. Check cancellation window: departure_time - now() > 2 hours
#         2. Set booking.status = 'cancelled'
#         3. Increment ride.available_seats
#         4. Send FCM push to driver: "Booking cancelled"
#       - Response: MessageResponse
#       - Error: CANCELLATION_WINDOW_CLOSED if < 2 hours to departure
#
# Connects with:
#   → app/schemas/booking.py (BookingCreateRequest, BookingResponse, BookingCancelRequest)
#   → app/services/booking_service.py (create, cancel, list)
#   → app/services/fare_engine.py (partial fare calc)
#   → app/services/osrm_service.py (partial distance)
#   → app/services/notification_service.py (FCM push to driver)
#   → app/dependencies.py (get_current_user, get_db)
#
# work by adolf.
