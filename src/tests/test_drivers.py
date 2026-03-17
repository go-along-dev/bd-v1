# =============================================================================
# tests/test_drivers.py — Driver Endpoint Tests
# =============================================================================
# See: system-design/02-user-driver.md §4 "Driver Onboarding"
# See: system-design/10-api-contracts.md §4 "Driver Endpoints"
#
# Tests for:
#   POST /api/v1/drivers/register            → register as driver
#   GET  /api/v1/drivers/me                  → get driver profile + status
#   POST /api/v1/drivers/documents           → upload verification doc
#   GET  /api/v1/drivers/documents           → list uploaded docs
#
# Fixtures used (from conftest.py):
#   - client:            httpx.AsyncClient with dependency overrides
#   - mock_user:         Fake User ORM object (role='passenger')
#   - mock_driver_user:  Fake User with role='driver' + approved Driver record
#   - db_session:        Test database session (transaction-scoped, auto-rollback)
#
# TODO: class TestDriverRegistration:
#       async def test_register_success(client, mock_user)
#           - POST with valid vehicle details → 201
#           - Check user.role promoted to 'driver'
#           - Check Driver record created with verification_status='pending'
#       async def test_register_already_driver(client, mock_driver_user)
#           - POST when already registered → 409 DRIVER_ALREADY_REGISTERED
#       async def test_register_missing_fields(client, mock_user)
#           - POST without vehicle_number → 422
#
# TODO: class TestGetDriverProfile:
#       async def test_get_driver_me(client, mock_driver_user)
#           - GET → 200, returns driver fields (vehicle_number, vehicle_make,
#             vehicle_model, vehicle_type, seat_capacity, mileage_kmpl,
#             verification_status)
#       async def test_get_driver_not_registered(client, mock_user)
#           - GET as non-driver → 404
#
# TODO: class TestDocumentUpload:
#       async def test_upload_driving_license(client, mock_driver_user)
#           - POST with doc_type='driving_license', file=JPEG → 201
#       async def test_upload_invalid_doc_type(client, mock_driver_user)
#           - POST with doc_type='passport' → 422
#       async def test_upload_duplicate_doc_type(client, mock_driver_user)
#           - POST same doc_type twice → 409 or overwrites (design decision)
#       async def test_list_documents(client, mock_driver_user)
#           - GET after upload → 200, includes uploaded doc with signed URL
#
# Connects with:
#   → app/routers/drivers.py (endpoint handlers)
#   → app/services/driver_service.py (business logic)
#   → app/services/storage_service.py (document upload — mock in tests)
#   → tests/conftest.py (shared fixtures)
#
# work by adolf.
