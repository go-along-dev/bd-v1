# =============================================================================
# routers/drivers.py — Driver Registration & Management Endpoints
# =============================================================================
# See: system-design/10-api-contracts.md §4 "Driver Endpoints"
# See: system-design/02-user-driver.md §3-§5 for driver registration flow
#
# Prefix: /api/v1/drivers
#
# TODO: POST /drivers/register
#       - Requires: Bearer token (any authenticated user)
#       - Request body: DriverRegisterRequest
#       - Logic: Call driver_service.register()
#         1. Check user doesn't already have a driver record
#         2. Create driver row with status="pending"
#         3. Update user.role to "driver"
#       - Response: DriverResponse
#       - Error: 409 if already registered
#
# TODO: GET /drivers/me
#       - Requires: Bearer token (role: driver)
#       - Logic: Return driver record with documents
#       - Response: DriverResponse (includes documents list)
#
# TODO: POST /drivers/documents
#       - Requires: Bearer token (role: driver)
#       - Request: UploadFile (multipart) + doc_type query param
#       - Logic: Call driver_service.upload_document()
#         1. Validate file type (jpg, png, pdf) and size (≤5MB)
#         2. Upload to Supabase Storage bucket "driver-documents" via storage_service
#         3. Create driver_documents row
#       - Response: DriverDocumentResponse
#
# TODO: GET /drivers/status
#       - Requires: Bearer token (role: driver)
#       - Logic: Return current approval status
#       - Response: {"status": "pending|approved|rejected", "rejection_reason": "..."}
#
# Connects with:
#   → app/schemas/driver.py (DriverRegisterRequest, DriverResponse, DriverDocumentResponse)
#   → app/services/driver_service.py (register, upload_document, get_status)
#   → app/services/storage_service.py (file upload to Supabase Storage)
#   → app/dependencies.py (get_current_user, require_role, get_db)
#
# work by adolf.
