# =============================================================================
# tests/test_users.py — User Endpoint Tests
# =============================================================================
# See: system-design/02-user-driver.md §3 "User Endpoints"
# See: system-design/10-api-contracts.md §3 "User Endpoints"
#
# Tests for:
#   GET  /api/v1/users/me         → fetch current user profile
#   PUT  /api/v1/users/me         → update profile (name, email, avatar_url)
#   POST /api/v1/users/me/avatar  → upload profile photo (≤5MB, JPEG/PNG)
#
# Fixtures used (from conftest.py):
#   - client:       httpx.AsyncClient with dependency overrides
#   - mock_user:    Fake User ORM object (role='passenger')
#   - db_session:   Test database session (transaction-scoped, auto-rollback)
#
# TODO: class TestGetMe:
#       async def test_get_me_success(client, mock_user)
#           - Assert 200, returns user fields (name, email, phone, role, avatar_url)
#       async def test_get_me_unauthenticated(client)
#           - No Bearer token → 401
#
# TODO: class TestUpdateMe:
#       async def test_update_name(client, mock_user)
#           - PUT with {"name": "New Name"} → 200, name updated
#       async def test_update_email(client, mock_user)
#           - PUT with {"email": "new@example.com"} → 200
#       async def test_update_invalid_email(client, mock_user)
#           - PUT with {"email": "not-an-email"} → 422
#       async def test_partial_update(client, mock_user)
#           - PUT with only {"name": "X"} → 200, email unchanged
#
# TODO: class TestUploadAvatar:
#       async def test_upload_avatar_jpeg(client, mock_user)
#           - POST with multipart JPEG file → 200, avatar_url populated
#       async def test_upload_avatar_too_large(client, mock_user)
#           - POST with >5MB file → 413
#       async def test_upload_avatar_invalid_type(client, mock_user)
#           - POST with .gif file → 400 INVALID_FILE_TYPE
#
# Connects with:
#   → app/routers/users.py (endpoint handlers)
#   → app/services/user_service.py (business logic)
#   → app/services/storage_service.py (avatar upload — mock in tests)
#   → tests/conftest.py (shared fixtures)
#
# work by adolf.
