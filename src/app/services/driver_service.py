# =============================================================================
# services/driver_service.py — Driver Registration & Management Service
# =============================================================================
# See: system-design/02-user-driver.md §3-§5 for driver flows
# See: system-design/10-api-contracts.md §4 "Driver Endpoints"
#
# TODO: async def register_driver(db: AsyncSession, user: User, data: DriverRegisterRequest) → Driver:
#       """
#       Steps:
#       1. Check user doesn't already have a driver record (409 Conflict if exists)
#       2. Create Driver row with status="pending"
#       3. Update user.role = "driver"
#       4. Return the created driver
#       """
#
# TODO: async def get_driver_profile(db: AsyncSession, user: User) → Driver:
#       """
#       Return driver record with eager-loaded documents.
#       Use selectinload(Driver.documents) to avoid N+1.
#       Raises 404 if user is not a registered driver.
#       """
#
# TODO: async def upload_document(db: AsyncSession, driver: Driver, doc_type: str, file: UploadFile) → DriverDocument:
#       """
#       Steps:
#       1. Validate file type (jpg, png, pdf) and size (≤5MB)
#       2. Generate storage path: f"driver-documents/{driver.id}/{doc_type}_{timestamp}.{ext}"
#       3. Call storage_service.upload_file(bucket="driver-documents", path=..., file=...)
#       4. Insert DriverDocument row with file_url from storage
#       5. Return the created document record
#       """
#
# TODO: async def get_driver_status(db: AsyncSession, user: User) → dict:
#       """Return current driver approval status and rejection reason if any."""
#
# Connects with:
#   → app/routers/drivers.py (calls register, get_profile, upload_document, get_status)
#   → app/models/driver.py (Driver model)
#   → app/models/driver_document.py (DriverDocument model)
#   → app/models/user.py (updates user.role)
#   → app/services/storage_service.py (file upload)
#   → app/schemas/driver.py (DriverRegisterRequest)
#
# work by adolf.
