# =============================================================================
# services/notification_service.py — Push Notification Service (FCM)
# =============================================================================
# See: system-design/01-auth.md §5 for FCM token management
# See: system-design/06-chat.md §5 for chat offline notification flow
#
# Uses Firebase Admin SDK to send push notifications via FCM.
# Notifications are fire-and-forget — failure does not block the main flow.
#
# TODO: Initialize Firebase Admin SDK
#       - Load service account JSON from config.FCM_CREDENTIALS_JSON
#       - Initialize firebase_admin app (once, at startup or first use)
#       - Use firebase_admin.messaging module
#
# TODO: async def send_push(db: AsyncSession, user_id: UUID, title: str, body: str, data: dict | None = None) → bool:
#       """
#       Steps:
#       1. Lookup user.fcm_token from DB (needs db session)
#       2. If no token → return False (user hasn't registered for push)
#       3. Build firebase_admin.messaging.Message with notification + data payload
#       4. Send via messaging.send() (run in executor since it's sync)
#       5. Handle MessagingError — if token invalid, clear user.fcm_token
#       6. Return True on success
#
#       IMPORTANT: Run firebase calls in asyncio executor (run_in_executor)
#       since firebase_admin SDK is synchronous.
#       """
#
# TODO: async def send_booking_created(booking: Booking, passenger_name: str) → None:
#       """Push to ride driver: 'New booking from {passenger_name}' """
#
# TODO: async def send_booking_cancelled(booking: Booking, passenger_name: str) → None:
#       """Push to ride driver: 'Booking cancelled by {passenger_name}' """
#
# TODO: async def send_ride_cancelled(ride: Ride, affected_bookings: list[Booking]) → None:
#       """Push to all passengers with confirmed bookings on this ride."""
#
# TODO: async def send_chat_message(recipient_id: UUID, sender_name: str, preview: str) → None:
#       """Push for offline chat: '{sender_name}: {preview}' """
#
# TODO: async def send_cashback_approved(user_id: UUID, amount: Decimal) → None:
#       """Push: 'Your cashback of ₹{amount} has been approved!' """
#
# TODO: async def send_withdrawal_processed(user_id: UUID, amount: Decimal) → None:
#       """Push: 'Your withdrawal of ₹{amount} has been processed!' """
#
# TODO: async def send_driver_approved(db: AsyncSession, user_id: UUID) → None:
#       """Push: 'Your driver application has been approved! Start publishing rides.' """
#
# TODO: async def send_driver_rejected(db: AsyncSession, user_id: UUID, reason: str) → None:
#       """Push: 'Your driver application was rejected: {reason}' """
#
# TODO: async def send_ride_completed(db: AsyncSession, user_id: UUID, dest_address: str) → None:
#       """Push to passenger: 'Your ride to {dest_address} is complete. Thank you!' """
#
# Connects with:
#   → app/config.py (FCM_CREDENTIALS_JSON path)
#   → app/models/user.py (reads fcm_token)
#   → app/services/booking_service.py (calls send_booking_created, send_booking_cancelled)
#   → app/services/ride_service.py (calls send_ride_cancelled)
#   → app/services/chat_service.py (calls send_chat_message for offline users)
#   → app/services/wallet_service.py (calls send_cashback_approved, send_withdrawal_processed)
#   → app/admin/views.py (triggers notifications on approval actions)
#
# work by adolf.
