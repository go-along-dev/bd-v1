# =============================================================================
# models/driver.py — Driver ORM Model
# =============================================================================
# See: system-design/11-db-schema-ddl.md §4 "Table: drivers"
# See: system-design/02-user-driver.md §3-§5 for driver registration flow
#
# A user becomes a driver by submitting vehicle + license info.
# One-to-one with users table. Admin must approve (status → approved) before
# the user can create rides.
#
# TODO: Define Driver model mapped to "drivers" table
# TODO: Columns:
#       - id: UUID PK
#       - user_id: UUID FK → users.id, NOT NULL, UNIQUE (one driver per user)
#       - vehicle_number: String(20), NOT NULL
#       - vehicle_make: String(50), NOT NULL — e.g. "Maruti", "Hyundai"
#       - vehicle_model: String(100), NOT NULL — e.g. "Swift Dzire"
#       - vehicle_type: String(30), NOT NULL — enum: sedan|suv|hatchback|mini_bus
#       - vehicle_color: String(30)
#       - license_number: String(50), NOT NULL
#       - seat_capacity: Integer, NOT NULL, CHECK (seat_capacity BETWEEN 1 AND 8)
#       - mileage_kmpl: Numeric(5,2), NOT NULL, CHECK (mileage_kmpl BETWEEN 1 AND 50)
#       - verification_status: String(20), NOT NULL, default "pending"
#         CHECK: status IN ('pending', 'approved', 'rejected')
#       - rejection_reason: Text, nullable — admin fills on rejection
#       - verified_at: TIMESTAMPTZ, nullable — when admin approved/rejected
#       - verified_by: UUID, nullable — admin user who verified
#       - onboarded_at: TIMESTAMPTZ, nullable — set when approved (cashback window starts here)
#       - created_at, updated_at: TIMESTAMPTZ
#
# TODO: Relationships:
#       - user: relationship("User", back_populates="driver")
#       - documents: relationship("DriverDocument", back_populates="driver", cascade="all, delete-orphan")
#       - rides: relationship("Ride", back_populates="driver")
#       - wallet: relationship("Wallet", back_populates="driver", uselist=False)
#
# TODO: Indexes:
#       - idx_drivers_user_id ON user_id (UNIQUE)
#       - idx_drivers_status ON verification_status (admin queries pending drivers)
#
# Connects with:
#   → app/models/user.py (FK: user_id → users.id)
#   → app/models/driver_document.py (one-to-many: driver has multiple docs)
#   → app/models/ride.py (one-to-many: driver has multiple rides)
#   → app/models/wallet.py (one-to-one: wallet per driver)
#   → app/services/driver_service.py (registration, status checks)
#   → app/admin/views.py (admin approves/rejects drivers)
#   → app/services/ride_service.py (checks driver.verification_status == "approved")
#
# work by adolf.
