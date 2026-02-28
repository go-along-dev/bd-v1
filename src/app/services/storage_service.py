# =============================================================================
# services/storage_service.py — Supabase Storage Service
# =============================================================================
# See: system-design/02-user-driver.md §4 "Document Upload Flow"
# See: HLD diagram §2.5 in 00-architecture.md — File Storage section
#
# Handles file uploads to Supabase Storage.
# Three buckets: profile-photos (public), driver-documents (private), toll-proofs (private)
#
# TODO: Initialize Supabase client (server-side, using service_role_key).
#       Use supabase-py library or direct REST calls to Supabase Storage API.
#       Base URL: {SUPABASE_URL}/storage/v1
#       Auth header: Bearer {SUPABASE_SERVICE_ROLE_KEY}
#
# TODO: async def upload_file(bucket: str, path: str, file_data: bytes, content_type: str) → str:
#       """
#       Upload a file to Supabase Storage.
#
#       Steps:
#       1. POST {SUPABASE_URL}/storage/v1/object/{bucket}/{path}
#          Headers: Authorization, Content-Type, x-upsert: true
#          Body: raw file bytes
#       2. Return public URL for public buckets, or signed URL for private
#
#       Buckets:
#       - "profile-photos": public, ≤2MB, jpg/png only
#       - "driver-documents": private, ≤5MB, jpg/png/pdf
#       - "toll-proofs": private, ≤5MB, jpg/png/pdf
#       """
#
# TODO: async def get_signed_url(bucket: str, path: str, expires_in: int = 3600) → str:
#       """Generate a temporary signed URL for private files (1-hour default)."""
#
# TODO: async def delete_file(bucket: str, path: str) → bool:
#       """Delete a file from storage. Used when replacing profile photo or cleaning up."""
#
# TODO: def validate_upload(file_data: bytes, content_type: str, max_size_mb: int) → bool:
#       """
#       Validate file before uploading:
#       - Check size <= max_size_mb * 1024 * 1024
#       - Check content_type is allowed (image/jpeg, image/png, application/pdf)
#       - Raise 400 if invalid
#       """
#
# Connects with:
#   → app/config.py (SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)
#   → app/services/driver_service.py (driver document upload)
#   → app/services/wallet_service.py (toll proof upload, called from router)
#   → app/services/user_service.py (profile photo upload)
#   → app/routers/drivers.py (UploadFile handling)
#   → app/routers/wallet.py (UploadFile handling)
#
# work by adolf.
