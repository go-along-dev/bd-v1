# =============================================================================
# admin/views.py — SQLAdmin Dashboard Views & Custom Actions
# =============================================================================
# See: system-design/08-admin.md for the complete admin panel design
# See: system-design/08-admin.md §3 for custom admin actions
#
# SQLAdmin auto-generates CRUD views from SQLAlchemy models.
# Mounted at /admin in main.py. Session-based auth (separate from API JWT).
#
# TODO: Create admin authentication backend
#       - Simple username/password auth for admin panel
#       - Validate against config.ADMIN_USERNAME + config.ADMIN_PASSWORD
#       - Use SQLAdmin's AuthenticationBackend with session-based login
#       - SessionMiddleware (with APP_SECRET_KEY) must be registered in main.py
#
# TODO: Define ModelAdmin classes for each model:
#
#   class UserAdmin(ModelAdmin, model=User):
#       - column_list: [id, name, email, phone, role, is_active, created_at]
#       - column_searchable_list: [name, email, phone]
#       - column_filters: [role, is_active]
#       - can_create = False  (users created via app only)
#       - can_delete = False  (deactivate instead)
#
#   class DriverAdmin(ModelAdmin, model=Driver):
#       - column_list: [id, user.name, vehicle_number, vehicle_make, vehicle_model,
#                        vehicle_type, seat_capacity, verification_status, created_at]
#       - column_filters: [verification_status, vehicle_type]
#       - Custom actions:
#         TODO: "Approve Driver" → set verification_status='approved',
#               verified_at=now(), verified_by=admin_id,
#               send notification_service.send_driver_approved(db, user_id)
#         TODO: "Reject Driver" → set verification_status='rejected' +
#               rejection_reason, send notification_service.send_driver_rejected(db, user_id, reason)
#
#   class DriverDocumentAdmin(ModelAdmin, model=DriverDocument):
#       - column_list: [id, driver.user.name, doc_type, status, file_url]
#       - Make file_url clickable (opens in new tab to view document)
#
#   class RideAdmin(ModelAdmin, model=Ride):
#       - column_list: [id, driver.user.name, source_address, dest_address,
#                        source_city, dest_city, per_seat_fare, status, departure_time]
#       - column_filters: [status, source_city, dest_city]
#       - Read-only for now (admin observes, doesn't modify rides)
#
#   class BookingAdmin(ModelAdmin, model=Booking):
#       - column_list: [id, ride_id, passenger.name, seats_booked, fare,
#                        status, booked_at]
#       - Read-only
#
#   class WalletAdmin(ModelAdmin, model=Wallet):
#       - column_list: [id, driver.user.name, balance]
#
#   class WalletTransactionAdmin(ModelAdmin, model=WalletTransaction):
#       - column_list: [id, wallet.driver.user.name, txn_type, amount, status, created_at]
#       - column_filters: [txn_type, status]
#       - Custom actions:
#         TODO: "Approve Cashback" → wallet_service.approve_transaction()
#         TODO: "Reject Cashback" → wallet_service.reject_transaction()
#         TODO: "Approve Withdrawal" → wallet_service.approve_transaction()
#         TODO: "Reject Withdrawal" → wallet_service.reject_transaction()
#
#   class PlatformConfigAdmin(ModelAdmin, model=PlatformConfig):
#       - column_list: [key, value, description, updated_at]
#       - can_create = True
#       - can_delete = False
#       Allow admin to edit fare rates, limits, etc. without code deploy.
#
# TODO: Register all admin views in a function called from main.py:
#       def setup_admin(app: FastAPI, engine: AsyncEngine) → Admin:
#           admin = Admin(app, engine, authentication_backend=...)
#           admin.add_view(UserAdmin)
#           admin.add_view(DriverAdmin)
#           ... etc ...
#           return admin
#
# Connects with:
#   → app/main.py (mounts admin at /admin)
#   → app/models/*.py (all models registered as admin views)
#   → app/services/wallet_service.py (approve/reject transaction actions)
#   → app/services/notification_service.py (FCM push on approval/rejection)
#   → app/db/postgres.py (admin uses same async engine)
#
# work by adolf.
