# =============================================================================
# models/driver_document.py — Driver Document ORM Model
# =============================================================================
# See: system-design/11-db-schema-ddl.md §5 "Table: driver_documents"
# See: system-design/02-user-driver.md §4 "Document Upload Flow"
#
# Stores metadata about documents uploaded by drivers (license, RC, insurance).
# Actual files are stored in Supabase Storage bucket "driver-documents".
#
# TODO: Define DriverDocument model mapped to "driver_documents" table
# TODO: Columns:
#       - id: UUID PK
#       - driver_id: UUID FK → drivers.id, NOT NULL, ON DELETE CASCADE
#       - doc_type: String(30), NOT NULL
#         CHECK: doc_type IN ('license', 'rc_book', 'insurance', 'permit')
#       - file_url: Text, NOT NULL — Supabase Storage signed URL or path
#       - status: String(20), NOT NULL, default "pending"
#         CHECK: status IN ('pending', 'approved', 'rejected')
#       - created_at: TIMESTAMPTZ
#
# TODO: Relationships:
#       - driver: relationship("Driver", back_populates="documents")
#
# Connects with:
#   → app/models/driver.py (FK: driver_id → drivers.id)
#   → app/services/driver_service.py (upload flow)
#   → app/services/storage_service.py (actual file upload to Supabase Storage)
#   → app/admin/views.py (admin reviews uploaded documents)
#
# work by adolf.
