# =============================================================================
# services/auth_service.py — Authentication & User Sync Service
# =============================================================================
# See: system-design/01-auth.md for the complete auth flow
# See: system-design/10-api-contracts.md §2 for request/response contracts
#
# Supabase handles actual authentication. This service handles:
# 1. Syncing Supabase Auth users into our users table
# 2. Managing FCM tokens for push notifications
#
# TODO: async def sync_user(db: AsyncSession, supabase_uid: str, data: AuthSyncRequest) → tuple[User, bool]:
#       """
#       Called after Flutter authenticates with Supabase.
#       Upserts user row — creates if first time, updates if existing.
#
#       Steps:
#       1. Query users WHERE supabase_uid = uid
#       2. If not found:
#          a. INSERT new user row
#          b. Create an empty wallet for the user (auto-create)
#          c. Return (user, is_new_user=True)
#       3. If found:
#          a. Update name, email, phone, profile_photo if provided
#          b. Return (user, is_new_user=False)
#       """
#
# TODO: async def update_fcm_token(db: AsyncSession, user: User, fcm_token: str) → None:
#       """
#       Updates user.fcm_token. Called on every app launch and when
#       Firebase token refreshes.
#       """
#
# Connects with:
#   → app/routers/auth.py (calls sync_user, update_fcm_token)
#   → app/models/user.py (User model)
#   → app/models/wallet.py (creates wallet on new user)
#   → app/schemas/auth.py (AuthSyncRequest)
#   → app/dependencies.py (JWT verification happens there, not here)
#
# work by adolf.
