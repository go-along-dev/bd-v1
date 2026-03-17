# Module 11: Database Schema (DDL)

> **This is the canonical schema.** Copy-paste into your initial Alembic migration. Every table, column, constraint, index, trigger, and seed row is here. If it's not here, it doesn't exist.

---

## Table of Contents

1. [Schema Conventions](#1-schema-conventions)
2. [Extensions](#2-extensions)
3. [Table: users](#3-table-users)
4. [Table: drivers](#4-table-drivers)
5. [Table: driver_documents](#5-table-driver_documents)
6. [Table: rides](#6-table-rides)
7. [Table: bookings](#7-table-bookings)
8. [Table: platform_config](#8-table-platform_config)
9. [Table: wallets](#9-table-wallets)
10. [Table: wallet_transactions](#10-table-wallet_transactions)
11. [MongoDB: chat_messages](#11-mongodb-chat_messages)
12. [Auto-Updated Timestamps Trigger](#12-auto-updated-timestamps-trigger)
13. [Seed Data](#13-seed-data)
14. [Entity Relationship Diagram](#14-entity-relationship-diagram)
15. [Index Strategy](#15-index-strategy)
16. [Migration Checklist](#16-migration-checklist)

---

## 1. Schema Conventions

| Convention                  | Rule                                                    |
|-----------------------------|---------------------------------------------------------|
| Primary keys                | `UUID`, `gen_random_uuid()` default                     |
| Table names                 | Plural, snake_case: `users`, `wallet_transactions`      |
| Column names                | snake_case: `created_at`, `driver_id`                   |
| Foreign keys                | `{related_table_singular}_id`: `driver_id`, `ride_id`   |
| Timestamps                  | `TIMESTAMPTZ` (timezone-aware), default `NOW()`         |
| Money                       | `DECIMAL(10,2)` — never `FLOAT` or `REAL`               |
| Coordinates                 | `DECIMAL(10,7)` — 7 decimal places = ~1cm precision     |
| Soft deletes                | Not used. Status fields instead: `active/cancelled/completed` |
| Enums                       | `VARCHAR` with CHECK constraints — not Postgres ENUMs (easier to migrate) |
| Cascades                    | `ON DELETE CASCADE` for owned entities, `ON DELETE SET NULL` for references |
| Booleans                    | `BOOLEAN DEFAULT FALSE` — explicit, no NULLs            |

---

## 2. Extensions

```sql
-- Required PostgreSQL extensions
CREATE EXTENSION IF NOT EXISTS "pgcrypto";    -- For gen_random_uuid()
-- Note: Supabase PostgreSQL has pgcrypto enabled by default
```

---

## 3. Table: users

```sql
CREATE TABLE users (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    supabase_uid    TEXT NOT NULL,
    name            VARCHAR(100),
    email           VARCHAR(255),
    phone           VARCHAR(15),
    profile_photo   TEXT,
    role            VARCHAR(20) NOT NULL DEFAULT 'passenger',
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    fcm_token       TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Constraints
    CONSTRAINT uq_users_supabase_uid UNIQUE (supabase_uid),
    CONSTRAINT uq_users_email UNIQUE (email),
    CONSTRAINT uq_users_phone UNIQUE (phone),
    CONSTRAINT ck_users_role CHECK (role IN ('passenger', 'driver', 'admin'))
);

-- Indexes
CREATE INDEX idx_users_supabase_uid ON users (supabase_uid);
CREATE INDEX idx_users_phone ON users (phone);
CREATE INDEX idx_users_role ON users (role);
CREATE INDEX idx_users_created_at ON users (created_at DESC);

-- Comments
COMMENT ON TABLE users IS 'Application users synced from Supabase Auth';
COMMENT ON COLUMN users.supabase_uid IS 'Maps to auth.users.id in Supabase. Set on first login via /auth/sync';
COMMENT ON COLUMN users.role IS 'passenger: default. driver: set when driver registration is submitted. admin: manually set.';
COMMENT ON COLUMN users.fcm_token IS 'Firebase Cloud Messaging device token for push notifications. Updated on each login.';
```

---

## 4. Table: drivers

```sql
CREATE TABLE drivers (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id                 UUID NOT NULL,
    license_number          VARCHAR(50) NOT NULL,
    vehicle_make            VARCHAR(50) NOT NULL,
    vehicle_model           VARCHAR(50) NOT NULL,
    vehicle_number          VARCHAR(20) NOT NULL,
    vehicle_type            VARCHAR(20) NOT NULL,
    vehicle_color           VARCHAR(30),
    mileage_kmpl            DECIMAL(5,2) NOT NULL,
    seat_capacity           INT NOT NULL,
    verification_status     VARCHAR(20) NOT NULL DEFAULT 'pending',
    rejection_reason        TEXT,
    verified_at             TIMESTAMPTZ,
    verified_by             UUID,
    onboarded_at            TIMESTAMPTZ,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Constraints
    CONSTRAINT uq_drivers_user_id UNIQUE (user_id),
    CONSTRAINT fk_drivers_user FOREIGN KEY (user_id)
        REFERENCES users(id) ON DELETE CASCADE,
    CONSTRAINT fk_drivers_verified_by FOREIGN KEY (verified_by)
        REFERENCES users(id) ON DELETE SET NULL,
    CONSTRAINT ck_drivers_vehicle_type CHECK (
        vehicle_type IN ('hatchback', 'sedan', 'suv', 'muv')
    ),
    CONSTRAINT ck_drivers_verification_status CHECK (
        verification_status IN ('pending', 'approved', 'rejected')
    ),
    CONSTRAINT ck_drivers_mileage CHECK (mileage_kmpl > 0 AND mileage_kmpl <= 50),
    CONSTRAINT ck_drivers_seat_capacity CHECK (seat_capacity >= 1 AND seat_capacity <= 8)
);

-- Indexes
CREATE INDEX idx_drivers_user_id ON drivers (user_id);
CREATE INDEX idx_drivers_verification_status ON drivers (verification_status);
CREATE INDEX idx_drivers_vehicle_number ON drivers (vehicle_number);
CREATE INDEX idx_drivers_created_at ON drivers (created_at DESC);

-- Comments
COMMENT ON TABLE drivers IS 'Driver profiles. One per user. Created via POST /drivers/register.';
COMMENT ON COLUMN drivers.onboarded_at IS 'Set when admin approves the driver. Starts the 90-day cashback eligibility window.';
COMMENT ON COLUMN drivers.mileage_kmpl IS 'Vehicle fuel efficiency. Used by fare engine to calculate per-seat cost.';
COMMENT ON COLUMN drivers.seat_capacity IS 'Max bookable seats offered by this vehicle, excluding the driver.';
```

---

## 5. Table: driver_documents

```sql
CREATE TABLE driver_documents (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    driver_id   UUID NOT NULL,
    doc_type    VARCHAR(30) NOT NULL,
    file_url    TEXT NOT NULL,
    uploaded_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Constraints
    CONSTRAINT fk_driver_docs_driver FOREIGN KEY (driver_id)
        REFERENCES drivers(id) ON DELETE CASCADE,
    CONSTRAINT uq_driver_docs_type UNIQUE (driver_id, doc_type),
    CONSTRAINT ck_driver_docs_type CHECK (
        doc_type IN ('driving_license', 'vehicle_rc', 'insurance', 'aadhar', 'pan')
    )
);

-- Indexes
CREATE INDEX idx_driver_docs_driver_id ON driver_documents (driver_id);

-- Comments
COMMENT ON TABLE driver_documents IS 'Uploaded verification documents (stored in Supabase Storage, URLs referenced here).';
COMMENT ON COLUMN driver_documents.file_url IS 'Supabase Storage URL. Private bucket: driver-documents/';
```

---

## 6. Table: rides

```sql
CREATE TABLE rides (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    driver_id           UUID NOT NULL,
    source_address      TEXT NOT NULL,
    source_lat          DECIMAL(10,7) NOT NULL,
    source_lng          DECIMAL(10,7) NOT NULL,
    source_city         VARCHAR(100),
    dest_address        TEXT NOT NULL,
    dest_lat            DECIMAL(10,7) NOT NULL,
    dest_lng            DECIMAL(10,7) NOT NULL,
    dest_city           VARCHAR(100),
    total_distance_km   DECIMAL(8,2) NOT NULL,
    estimated_duration  INT,
    route_geometry      TEXT,
    departure_time      TIMESTAMPTZ NOT NULL,
    total_seats         INT NOT NULL,
    available_seats     INT NOT NULL,
    total_fare          DECIMAL(10,2) NOT NULL,
    per_seat_fare       DECIMAL(10,2) NOT NULL,
    status              VARCHAR(20) NOT NULL DEFAULT 'active',
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Constraints
    CONSTRAINT fk_rides_driver FOREIGN KEY (driver_id)
        REFERENCES drivers(id) ON DELETE CASCADE,
    CONSTRAINT ck_rides_status CHECK (status IN ('active', 'departed', 'completed', 'cancelled')),
    CONSTRAINT ck_rides_seats_positive CHECK (total_seats >= 1 AND total_seats <= 8),
    CONSTRAINT ck_rides_available_seats CHECK (available_seats >= 0),
    CONSTRAINT ck_rides_available_le_total CHECK (available_seats <= total_seats),
    CONSTRAINT ck_rides_fare_positive CHECK (total_fare >= 0 AND per_seat_fare >= 0),
    CONSTRAINT ck_rides_distance_positive CHECK (total_distance_km > 0),
    CONSTRAINT ck_rides_lat_range CHECK (
        source_lat BETWEEN -90 AND 90
        AND dest_lat BETWEEN -90 AND 90
    ),
    CONSTRAINT ck_rides_lng_range CHECK (
        source_lng BETWEEN -180 AND 180
        AND dest_lng BETWEEN -180 AND 180
    )
);

-- Indexes
CREATE INDEX idx_rides_driver_id ON rides (driver_id);
CREATE INDEX idx_rides_status_departure ON rides (status, departure_time);
CREATE INDEX idx_rides_source_geo ON rides (source_lat, source_lng);
CREATE INDEX idx_rides_dest_geo ON rides (dest_lat, dest_lng);
CREATE INDEX idx_rides_search ON rides (status, departure_time, source_lat, source_lng, dest_lat, dest_lng)
    WHERE status = 'active';
CREATE INDEX idx_rides_created_at ON rides (created_at DESC);

-- Comments
COMMENT ON TABLE rides IS 'Published rides by verified drivers. Found via geo + date search.';
COMMENT ON COLUMN rides.source_city IS 'Extracted city name for admin search/display. Populated via Nominatim reverse-geocode at ride creation, or parsed from source_address. Optional — NULL if extraction fails.';
COMMENT ON COLUMN rides.route_geometry IS 'OSRM encoded polyline for displaying route on map.';
COMMENT ON COLUMN rides.estimated_duration IS 'Travel time in minutes from OSRM.';
COMMENT ON COLUMN rides.available_seats IS 'Decremented on booking, incremented on cancellation. Protected by row-level lock.';
```

---

## 7. Table: bookings

```sql
CREATE TABLE bookings (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    ride_id         UUID NOT NULL,
    passenger_id    UUID NOT NULL,
    pickup_address  TEXT NOT NULL,
    pickup_lat      DECIMAL(10,7) NOT NULL,
    pickup_lng      DECIMAL(10,7) NOT NULL,
    dropoff_address TEXT,
    dropoff_lat     DECIMAL(10,7),
    dropoff_lng     DECIMAL(10,7),
    distance_km     DECIMAL(8,2) NOT NULL,
    fare            DECIMAL(10,2) NOT NULL,
    seats_booked    INT NOT NULL DEFAULT 1,
    status          VARCHAR(20) NOT NULL DEFAULT 'confirmed',
    booked_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    cancelled_at    TIMESTAMPTZ,

    -- Constraints
    CONSTRAINT fk_bookings_ride FOREIGN KEY (ride_id)
        REFERENCES rides(id) ON DELETE CASCADE,
    CONSTRAINT fk_bookings_passenger FOREIGN KEY (passenger_id)
        REFERENCES users(id) ON DELETE CASCADE,
    -- Partial unique: one active booking per passenger per ride (allows rebooking after cancel)
    -- CONSTRAINT uq_bookings_ride_passenger — replaced by partial index below
    CONSTRAINT ck_bookings_status CHECK (status IN ('confirmed', 'cancelled', 'completed')),
    CONSTRAINT ck_bookings_seats CHECK (seats_booked >= 1 AND seats_booked <= 4),
    CONSTRAINT ck_bookings_fare_positive CHECK (fare >= 0),
    CONSTRAINT ck_bookings_distance_positive CHECK (distance_km > 0),
    CONSTRAINT ck_bookings_lat_range CHECK (pickup_lat BETWEEN -90 AND 90),
    CONSTRAINT ck_bookings_lng_range CHECK (pickup_lng BETWEEN -180 AND 180)
);

-- Indexes
CREATE INDEX idx_bookings_ride_id ON bookings (ride_id);
CREATE INDEX idx_bookings_passenger_id ON bookings (passenger_id);
CREATE INDEX idx_bookings_status ON bookings (status);
CREATE INDEX idx_bookings_booked_at ON bookings (booked_at DESC);
CREATE INDEX idx_bookings_active_ride ON bookings (ride_id)
    WHERE status = 'confirmed';
CREATE UNIQUE INDEX uq_bookings_ride_passenger_active
    ON bookings (ride_id, passenger_id)
    WHERE status IN ('confirmed');

-- Comments
COMMENT ON TABLE bookings IS 'Seat reservations. Partial unique index prevents duplicate active bookings but allows rebooking after cancellation.';
COMMENT ON COLUMN bookings.distance_km IS 'Partial distance: pickup → ride destination. Calculated via OSRM at booking time.';
COMMENT ON COLUMN bookings.fare IS 'Proportional fare based on distance ratio. Informational — no payment in Phase 1.';
COMMENT ON COLUMN bookings.dropoff_address IS 'Phase 1: dropoff = ride destination. Phase 2: custom dropoff point.';
```

---

## 8. Table: platform_config

```sql
CREATE TABLE platform_config (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    key         VARCHAR(50) NOT NULL,
    value       TEXT NOT NULL,
    description TEXT,
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_by  UUID,

    -- Constraints
    CONSTRAINT uq_platform_config_key UNIQUE (key),
    CONSTRAINT fk_platform_config_updated_by FOREIGN KEY (updated_by)
        REFERENCES users(id) ON DELETE SET NULL
);

-- Indexes (unique on key is sufficient, no additional index needed)

-- Comments
COMMENT ON TABLE platform_config IS 'Key-value configuration managed by admin. Used by fare engine, cashback eligibility, etc.';
COMMENT ON COLUMN platform_config.key IS 'Machine-readable config key: fuel_price_per_litre, platform_margin_pct, etc.';
```

---

## 9. Table: wallets

```sql
CREATE TABLE wallets (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    driver_id   UUID NOT NULL,
    balance     DECIMAL(10,2) NOT NULL DEFAULT 0.00,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Constraints
    CONSTRAINT uq_wallets_driver_id UNIQUE (driver_id),
    CONSTRAINT fk_wallets_driver FOREIGN KEY (driver_id)
        REFERENCES drivers(id) ON DELETE CASCADE,
    CONSTRAINT ck_wallets_balance_non_negative CHECK (balance >= 0)
);

-- Indexes
CREATE INDEX idx_wallets_driver_id ON wallets (driver_id);

-- Comments
COMMENT ON TABLE wallets IS 'One wallet per approved driver. Auto-created on driver approval.';
COMMENT ON COLUMN wallets.balance IS 'Current available balance in INR. Can never be negative (CHECK constraint).';
```

---

## 10. Table: wallet_transactions

```sql
CREATE TABLE wallet_transactions (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    wallet_id       UUID NOT NULL,
    type            VARCHAR(30) NOT NULL,
    amount          DECIMAL(10,2) NOT NULL,
    ride_id         UUID,
    toll_proof_url  TEXT,
    upi_id          VARCHAR(100),
    status          VARCHAR(20) NOT NULL DEFAULT 'pending',
    admin_note      TEXT,
    processed_by    UUID,
    processed_at    TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Constraints
    CONSTRAINT fk_wallet_txn_wallet FOREIGN KEY (wallet_id)
        REFERENCES wallets(id) ON DELETE CASCADE,
    CONSTRAINT fk_wallet_txn_ride FOREIGN KEY (ride_id)
        REFERENCES rides(id) ON DELETE SET NULL,
    CONSTRAINT fk_wallet_txn_processed_by FOREIGN KEY (processed_by)
        REFERENCES users(id) ON DELETE SET NULL,
    CONSTRAINT ck_wallet_txn_type CHECK (
        type IN (
            'cashback_request',
            'cashback_credited',
            'cashback_rejected',
            'withdrawal_request',
            'withdrawal_approved',
            'withdrawal_rejected'
        )
    ),
    CONSTRAINT ck_wallet_txn_status CHECK (status IN ('pending', 'approved', 'rejected')),
    CONSTRAINT ck_wallet_txn_amount_positive CHECK (amount > 0)
);

-- Prevent duplicate cashback for same ride (only one pending or approved per ride per wallet)
CREATE UNIQUE INDEX uq_wallet_txn_cashback_per_ride
    ON wallet_transactions (wallet_id, ride_id)
    WHERE type = 'cashback_request' AND status IN ('pending', 'approved');

-- Indexes
CREATE INDEX idx_wallet_txn_wallet_id ON wallet_transactions (wallet_id);
CREATE INDEX idx_wallet_txn_status ON wallet_transactions (status);
CREATE INDEX idx_wallet_txn_type ON wallet_transactions (type);
CREATE INDEX idx_wallet_txn_created_at ON wallet_transactions (created_at DESC);
CREATE INDEX idx_wallet_txn_pending ON wallet_transactions (status, type)
    WHERE status = 'pending';

-- Comments
COMMENT ON TABLE wallet_transactions IS 'Full audit trail of every wallet balance change. Read-heavy.';
COMMENT ON COLUMN wallet_transactions.type IS 'cashback_request: driver submits toll proof. cashback_credited: admin approves. withdrawal_request: driver requests payout. withdrawal_approved: admin pays.';
COMMENT ON COLUMN wallet_transactions.toll_proof_url IS 'Supabase Storage URL of the toll receipt image. Required for cashback_request type.';
COMMENT ON COLUMN wallet_transactions.upi_id IS 'Driver UPI ID for withdrawal payout. Required for withdrawal_request type.';
```

---

## 11. MongoDB: chat_messages

```javascript
// Database: goalong
// Collection: chat_messages

// Document Schema:
{
  _id: ObjectId,                           // Auto-generated
  booking_id: "uuid-string",               // Maps to bookings.id
  sender_id: "uuid-string",                // Maps to users.id
  receiver_id: "uuid-string",              // Maps to users.id
  message: "string",                       // Max 1000 characters
  sent_at: ISODate("2026-03-14T10:30:00Z"),
  read: false                              // Default: false
}

// Validation (optional — enforce at app level):
db.createCollection("chat_messages", {
  validator: {
    $jsonSchema: {
      bsonType: "object",
      required: ["booking_id", "sender_id", "receiver_id", "message", "sent_at"],
      properties: {
        booking_id:  { bsonType: "string" },
        sender_id:   { bsonType: "string" },
        receiver_id: { bsonType: "string" },
        message:     { bsonType: "string", maxLength: 1000 },
        sent_at:     { bsonType: "date" },
        read:        { bsonType: "bool" }
      }
    }
  }
});

// Indexes:
db.chat_messages.createIndex(
  { booking_id: 1, sent_at: 1 },
  { name: "idx_booking_timeline" }
);

db.chat_messages.createIndex(
  { receiver_id: 1, read: 1 },
  { name: "idx_unread_by_receiver" }
);

// TTL Index — auto-delete after 90 days (stay within M0 512MB limit):
db.chat_messages.createIndex(
  { sent_at: 1 },
  { expireAfterSeconds: 7776000, name: "ttl_auto_delete_90_days" }
);
```

---

## 12. Auto-Updated Timestamps Trigger

```sql
-- Generic trigger function for auto-updating `updated_at`
CREATE OR REPLACE FUNCTION trigger_set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply to all tables with updated_at
CREATE TRIGGER set_updated_at_users
    BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION trigger_set_updated_at();

CREATE TRIGGER set_updated_at_drivers
    BEFORE UPDATE ON drivers
    FOR EACH ROW EXECUTE FUNCTION trigger_set_updated_at();

CREATE TRIGGER set_updated_at_rides
    BEFORE UPDATE ON rides
    FOR EACH ROW EXECUTE FUNCTION trigger_set_updated_at();

CREATE TRIGGER set_updated_at_platform_config
    BEFORE UPDATE ON platform_config
    FOR EACH ROW EXECUTE FUNCTION trigger_set_updated_at();

CREATE TRIGGER set_updated_at_wallets
    BEFORE UPDATE ON wallets
    FOR EACH ROW EXECUTE FUNCTION trigger_set_updated_at();
```

---

## 13. Seed Data

```sql
-- Platform configuration (required before first ride can be created)
INSERT INTO platform_config (key, value, description) VALUES
    ('fuel_price_per_litre', '105.00', 'Current petrol price in INR per litre'),
    ('platform_margin_pct', '15', 'Platform margin percentage on top of fuel cost share'),
    ('min_fare', '50.00', 'Minimum fare per seat regardless of distance'),
    ('fare_rounding', '5', 'Round fare to nearest X rupees'),
    ('cashback_eligibility_days', '90', 'Days from onboarding that toll cashback is eligible'),
    ('max_cashback_per_ride', '500.00', 'Maximum cashback amount per ride in INR');

-- Admin user (create manually after first Supabase login)
-- 1. Login via Supabase as the admin email
-- 2. Hit POST /auth/sync to create the user record
-- 3. Run this SQL to promote to admin:
-- UPDATE users SET role = 'admin' WHERE email = 'admin@goalong.in';
```

---

## 14. Entity Relationship Diagram

```
┌──────────────────┐
│      users        │
│──────────────────│
│ id (PK)           │
│ supabase_uid (UQ) │
│ name              │
│ email (UQ)        │
│ phone (UQ)        │
│ role              │
│ fcm_token         │
└────┬──────────────┘
     │ 1
     │
     ├──────────────────────────────────────────────┐
     │ 1                                             │ 0..N
     ▼                                               ▼
┌──────────────────┐                        ┌──────────────────┐
│     drivers       │                        │    bookings       │
│──────────────────│                        │──────────────────│
│ id (PK)           │                        │ id (PK)           │
│ user_id (FK,UQ)   │──┐                    │ ride_id (FK)      │
│ license_number    │  │                    │ passenger_id (FK) │
│ vehicle_*         │  │                    │ pickup_*          │
│ mileage_kmpl      │  │                    │ distance_km       │
│ verification_*    │  │                    │ fare              │
│ onboarded_at      │  │                    │ seats_booked      │
└────┬──────────────┘  │                    │ status            │
     │ 1               │                    └──────────────────┘
     │                 │                             ▲
     ├────────┐        │ 1                           │ 0..N
     │        │        │                             │
     │ 0..N   │ 0..1   │ 0..N                       │
     ▼        ▼        ▼                             │
┌──────────┐ ┌────────┐ ┌──────────────────┐         │
│ driver_  │ │wallets │ │     rides         │─────────┘
│ documents│ │────────│ │──────────────────│
│──────────│ │ id(PK) │ │ id (PK)           │
│ id (PK)  │ │ driver │ │ driver_id (FK)    │
│ driver_id│ │ balance│ │ source_*          │
│ doc_type │ └───┬────┘ │ dest_*            │
│ file_url │     │ 1    │ total_distance_km │
└──────────┘     │      │ departure_time    │
                 │      │ *_seats, *_fare   │
                 │      │ status            │
            0..N │      └──────────────────┘
                 ▼                │
         ┌──────────────────┐    │ 0..N (cashback ref)
         │wallet_transactions│    │
         │──────────────────│    │
         │ id (PK)           │◄───┘
         │ wallet_id (FK)    │
         │ type              │
         │ amount            │
         │ ride_id (FK)      │
         │ toll_proof_url    │
         │ upi_id            │
         │ status            │
         └──────────────────┘

┌──────────────────┐
│ platform_config   │     (standalone — no FK relationships)
│──────────────────│
│ id (PK)           │
│ key (UQ)          │
│ value             │
│ description       │
└──────────────────┘

MongoDB (separate):
┌──────────────────┐
│ chat_messages     │     (references booking_id, sender_id, receiver_id as strings)
│──────────────────│
│ _id               │
│ booking_id        │
│ sender_id         │
│ receiver_id       │
│ message           │
│ sent_at           │
│ read              │
└──────────────────┘
```

---

## 15. Index Strategy

### Lookup Indexes (Equality Queries)
| Table                | Index                          | Query Pattern                          |
|----------------------|--------------------------------|----------------------------------------|
| `users`              | `supabase_uid`                 | JWT verification → find user           |
| `users`              | `phone`                        | Phone-based lookup                     |
| `drivers`            | `user_id`                      | Get driver profile for user            |
| `drivers`            | `verification_status`          | Admin filter pending drivers           |
| `driver_documents`   | `driver_id`                    | List documents for a driver            |
| `bookings`           | `ride_id`                      | All bookings for a ride                |
| `bookings`           | `passenger_id`                 | Booking history for a user             |
| `wallet_transactions`| `wallet_id`                    | Transaction history for a wallet       |

### Search Indexes (Range + Composite)
| Table    | Index                                          | Query Pattern                     |
|----------|------------------------------------------------|-----------------------------------|
| `rides`  | `(status, departure_time, source_*, dest_*)`   | Ride search by geo + date         |
| `rides`  | `(source_lat, source_lng)`                     | Bounding box source filter        |
| `rides`  | `(dest_lat, dest_lng)`                         | Bounding box destination filter   |

### Partial Indexes (Conditional)
| Table                | Index                                    | Condition               | Why                              |
|----------------------|------------------------------------------|-------------------------|----------------------------------|
| `rides`              | `idx_rides_search`                       | `status = 'active'`     | Only active rides are searchable |
| `bookings`           | `idx_bookings_active_ride`               | `status = 'confirmed'`  | Seat count only from confirmed   |
| `wallet_transactions`| `uq_wallet_txn_cashback_per_ride`        | `type='cashback_request' AND status IN ('pending','approved')` | Prevent duplicate cashback |
| `wallet_transactions`| `idx_wallet_txn_pending`                 | `status = 'pending'`    | Admin queue                      |

### Estimated Table Growth (6 months)

| Table                | Rows/month | 6-month total | Row size | Total size |
|----------------------|------------|---------------|----------|------------|
| `users`              | 500        | 3,000         | ~500B    | ~1.5 MB    |
| `drivers`            | 100        | 600           | ~600B    | ~360 KB    |
| `driver_documents`   | 300        | 1,800         | ~200B    | ~360 KB    |
| `rides`              | 600        | 3,600         | ~800B    | ~2.9 MB    |
| `bookings`           | 1,500      | 9,000         | ~500B    | ~4.5 MB    |
| `platform_config`    | 0          | 6             | ~200B    | ~1 KB      |
| `wallets`            | 100        | 600           | ~100B    | ~60 KB     |
| `wallet_transactions`| 200        | 1,200         | ~500B    | ~600 KB    |
| **Total PostgreSQL** |            |               |          | **~10 MB** |
| `chat_messages` (Mongo) | 5,000  | 30,000        | ~300B    | ~9 MB      |

**Supabase Free Tier: 500 MB → Plenty of headroom for 2+ years at MVP scale.**

---

## 16. Migration Checklist

```
□ Alembic initialized (alembic init alembic)
□ alembic/env.py imports all models
□ First migration generated: alembic revision --autogenerate -m "initial_schema"
□ Review generated migration — verify all tables, constraints, indexes
□ Apply locally: alembic upgrade head
□ Seed data inserted: platform_config rows
□ MongoDB collection + indexes created via Atlas shell
□ Run on staging/production before deploying new app version
□ Verify all CHECK constraints work with sample inserts
□ Verify CASCADE deletes work correctly
□ Verify unique constraints reject duplicates
□ Verify partial indexes are being used (EXPLAIN ANALYZE)
```
