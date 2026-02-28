# =============================================================================
# routers/auth.py — Auth Endpoints
# =============================================================================
# See: system-design/10-api-contracts.md §2 "Auth Endpoints"
# See: system-design/01-auth.md for the complete auth architecture
#
# Prefix: /api/v1/auth
#
# Supabase handles actual authentication (OTP, email signup, JWT issuance).
# These endpoints handle post-authentication sync with our database.
#
# TODO: POST /auth/sync
#       - Requires: Bearer token (Supabase JWT)
#       - Request body: AuthSyncRequest
#       - Logic: Call auth_service.sync_user() which:
#         1. Verifies JWT and extracts supabase_uid
#         2. Upserts user row in users table
#         3. Returns user data + is_new_user flag
#       - Response: AuthSyncResponse
#       - Called by Flutter app immediately after Supabase login/signup
#
# TODO: POST /auth/fcm-token
#       - Requires: Bearer token
#       - Request body: FCMTokenRequest
#       - Logic: Call auth_service.update_fcm_token()
#         Updates the user's fcm_token column for push notifications
#       - Response: FCMTokenResponse
#       - Called by Flutter on app launch and when FCM token refreshes
#
# Connects with:
#   → app/schemas/auth.py (AuthSyncRequest, AuthSyncResponse, FCMTokenRequest)
#   → app/services/auth_service.py (sync_user, update_fcm_token)
#   → app/dependencies.py (get_current_user, get_db)
#
# work by adolf.
