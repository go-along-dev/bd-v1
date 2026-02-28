# =============================================================================
# tests/test_auth.py — Auth Endpoint Tests
# =============================================================================
# See: system-design/10-api-contracts.md §2 "Auth Endpoints"
#
# TODO: test_sync_creates_new_user
#       POST /api/v1/auth/sync with valid JWT of unknown user
#       → 200, is_new_user = True, user created in DB, wallet created
#
# TODO: test_sync_returns_existing_user
#       POST /api/v1/auth/sync with valid JWT of known user
#       → 200, is_new_user = False
#
# TODO: test_sync_without_token_returns_401
#       POST /api/v1/auth/sync without Authorization header → 401
#
# TODO: test_fcm_token_update
#       POST /api/v1/auth/fcm-token with {"fcm_token": "test-token"}
#       → 200, user.fcm_token updated in DB
#
# work by adolf.
