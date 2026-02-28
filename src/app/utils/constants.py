# =============================================================================
# utils/constants.py — Application Constants
# =============================================================================
# See: system-design/10-api-contracts.md §12 "Error Code Registry"
#
# Centralized constants. No magic strings scattered across the codebase.
#
# TODO: API version prefix
#       API_V1_PREFIX = "/api/v1"
#
# TODO: User roles
#       ROLE_PASSENGER = "passenger"
#       ROLE_DRIVER = "driver"
#       ROLE_ADMIN = "admin"
#       VALID_ROLES = [ROLE_PASSENGER, ROLE_DRIVER, ROLE_ADMIN]
#
# TODO: Driver statuses
#       DRIVER_PENDING = "pending"
#       DRIVER_APPROVED = "approved"
#       DRIVER_REJECTED = "rejected"
#       DRIVER_SUSPENDED = "suspended"
#
# TODO: Ride statuses
#       RIDE_ACTIVE = "active"
#       RIDE_DEPARTED = "departed"
#       RIDE_COMPLETED = "completed"
#       RIDE_CANCELLED = "cancelled"
#
# TODO: Booking statuses
#       BOOKING_CONFIRMED = "confirmed"
#       BOOKING_CANCELLED = "cancelled"
#       BOOKING_COMPLETED = "completed"
#
# TODO: Wallet transaction types
#       TXN_CASHBACK = "cashback"
#       TXN_WITHDRAWAL = "withdrawal"
#
# TODO: Wallet transaction statuses
#       TXN_PENDING = "pending"
#       TXN_APPROVED = "approved"
#       TXN_REJECTED = "rejected"
#       TXN_COMPLETED = "completed"
#
# TODO: Document types
#       DOC_LICENSE = "license"
#       DOC_RC_BOOK = "rc_book"
#       DOC_INSURANCE = "insurance"
#       DOC_PERMIT = "permit"
#
# TODO: Storage buckets
#       BUCKET_PROFILE_PHOTOS = "profile-photos"
#       BUCKET_DRIVER_DOCS = "driver-documents"
#       BUCKET_TOLL_PROOFS = "toll-proofs"
#
# TODO: Search defaults
#       BOUNDING_BOX_DELTA = 0.5  # ±0.5 degrees (~55km) for ride search
#       DEFAULT_PAGE = 1
#       DEFAULT_PER_PAGE = 20
#       MAX_PER_PAGE = 100
#
# Connects with:
#   → Used everywhere — models, services, routers, schemas all import from here.
#
# work by adolf.
