# Module 2: User & Driver Management

## Overview

This module handles two user types on GoAlong:

| User Type     | What They Can Do                                             |
|---------------|--------------------------------------------------------------|
| **Passenger** | Search rides, book seats, chat with driver, view history     |
| **Driver**    | Everything a passenger can do + create rides, earn cashback  |

A user starts as a `passenger`. To become a `driver`, they submit a driver registration with documents. An admin manually reviews and approves the driver. Until approved, the user cannot create rides.

---

## User Lifecycle

```
New User (Supabase Auth)
        │
        ▼
  ┌──────────┐
  │ Passenger │  ← Default role on first login
  │ (active)  │
  └─────┬─────┘
        │
        │  Submits driver registration + documents
        ▼
  ┌──────────────────┐
  │ Driver (pending)  │  ← Can't create rides yet
  └────────┬──────────┘
           │
     Admin reviews
           │
     ┌─────┴──────┐
     ▼            ▼
┌──────────┐  ┌──────────┐
│ Approved │  │ Rejected │
│ (active) │  │          │
└──────────┘  └──────────┘
     │              │
     │              │  Can resubmit with corrected docs
     │              └──────────────────────────────────►  (back to pending)
     │
     ▼
  Can create rides, earn cashback
```

---

## Database: Users Table

> Defined in `01-auth.md` — the users table is the same.

```sql
CREATE TABLE users (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    supabase_uid    TEXT UNIQUE NOT NULL,
    name            VARCHAR(100),
    email           VARCHAR(255) UNIQUE,
    phone           VARCHAR(15) UNIQUE,
    profile_photo   TEXT,               -- Supabase Storage URL
    role            VARCHAR(20) NOT NULL DEFAULT 'passenger',
    is_verified     BOOLEAN DEFAULT TRUE,
    fcm_token       TEXT,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);
```

---

## Database: Drivers Table

```sql
CREATE TABLE drivers (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id             UUID UNIQUE NOT NULL REFERENCES users(id) ON DELETE CASCADE,

    -- Personal
    license_number      VARCHAR(50) NOT NULL,

    -- Vehicle
    vehicle_make        VARCHAR(50) NOT NULL,       -- e.g., Maruti, Hyundai, Tata
    vehicle_model       VARCHAR(50) NOT NULL,       -- e.g., Swift, Creta, Nexon
    vehicle_number      VARCHAR(20) NOT NULL,       -- e.g., KA-01-AB-1234
    vehicle_type        VARCHAR(20) NOT NULL,       -- 'hatchback' | 'sedan' | 'suv' | 'muv'
    vehicle_color       VARCHAR(30),
    mileage_kmpl        DECIMAL(5,2) NOT NULL,      -- Used by fare engine
    seat_capacity       INT NOT NULL,               -- Total bookable seats (excluding driver)

    -- Verification
    verification_status VARCHAR(20) NOT NULL DEFAULT 'pending',
                                                    -- 'pending' | 'approved' | 'rejected'
    rejection_reason    TEXT,                        -- Filled by admin on rejection
    verified_at         TIMESTAMPTZ,
    verified_by         UUID REFERENCES users(id),  -- Admin who approved/rejected

    -- Timestamps
    onboarded_at        TIMESTAMPTZ DEFAULT NOW(),  -- Used for 3-month cashback eligibility
    created_at          TIMESTAMPTZ DEFAULT NOW(),
    updated_at          TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_drivers_user_id ON drivers(user_id);
CREATE INDEX idx_drivers_verification_status ON drivers(verification_status);
```

### Things To Note:
- `user_id` is UNIQUE — one user can have exactly one driver profile
- `mileage_kmpl` is entered by the driver but can be overridden by admin if needed. The fare engine uses this value.
- `seat_capacity` = total bookable seats. A 5-seater car has `seat_capacity = 4` (driver excluded).
- `onboarded_at` is set when the driver is **approved** (not when they register). This is the start date for the 3-month cashback window.

---

## Database: Driver Documents Table

```sql
CREATE TABLE driver_documents (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    driver_id   UUID NOT NULL REFERENCES drivers(id) ON DELETE CASCADE,
    doc_type    VARCHAR(30) NOT NULL,
                -- 'driving_license' | 'vehicle_rc' | 'insurance' | 'aadhar' | 'pan'
    file_url    TEXT NOT NULL,           -- Supabase Storage URL
    uploaded_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_driver_docs_driver_id ON driver_documents(driver_id);
```

### Required Documents for Verification:
| Document        | `doc_type` Value   | Required |
|-----------------|--------------------|----------|
| Driving License | `driving_license`  | ✅       |
| Vehicle RC      | `vehicle_rc`       | ✅       |
| Vehicle Insurance | `insurance`      | ✅       |
| Aadhar Card     | `aadhar`           | ✅       |
| PAN Card        | `pan`              | Optional |

---

## File Upload — Supabase Storage

### Bucket Configuration (Supabase Dashboard → Storage)

| Bucket Name        | Public | Max File Size | Allowed MIME Types                |
|--------------------|--------|---------------|-----------------------------------|
| `profile-photos`   | Yes    | 5 MB          | `image/jpeg`, `image/png`         |
| `driver-documents` | No     | 10 MB         | `image/jpeg`, `image/png`, `application/pdf` |

### Upload Flow

```
Flutter                          Supabase Storage                FastAPI
  │                                     │                          │
  │  1. Pick image from gallery/camera  │                          │
  │                                     │                          │
  │  2. Upload directly                 │                          │
  │  supabase.storage                   │                          │
  │    .from('driver-documents')        │                          │
  │    .upload(path, file)              │                          │
  │─────────────────────────────────────►│                         │
  │                                     │                          │
  │  3. Get public/signed URL           │                          │
  │◄─────────────────────────────────────│                         │
  │                                     │                          │
  │  4. Send URL to backend             │                          │
  │  POST /drivers/documents            │                          │
  │  { doc_type, file_url }             │                          │
  │─────────────────────────────────────────────────────────────────►
  │                                     │       Save URL to DB     │
  │  5. Success                         │                          │
  │◄─────────────────────────────────────────────────────────────────
```

### Flutter Upload Code

```dart
// driver_repository.dart

Future<String> uploadDocument(String docType, File file) async {
  final fileName = '${docType}_${DateTime.now().millisecondsSinceEpoch}.jpg';
  final userId = Supabase.instance.client.auth.currentUser!.id;
  final storagePath = '$userId/$fileName';

  // Upload to Supabase Storage
  await Supabase.instance.client.storage
      .from('driver-documents')
      .upload(storagePath, file);

  // Get signed URL (private bucket — URL expires in 1 year)
  final signedUrl = await Supabase.instance.client.storage
      .from('driver-documents')
      .createSignedUrl(storagePath, 60 * 60 * 24 * 365); // 1 year

  return signedUrl;
}

Future<String> uploadProfilePhoto(File file) async {
  final userId = Supabase.instance.client.auth.currentUser!.id;
  final storagePath = '$userId/profile.jpg';

  await Supabase.instance.client.storage
      .from('profile-photos')
      .upload(storagePath, file, fileOptions: const FileOptions(upsert: true));

  // Public bucket — get permanent public URL
  final publicUrl = Supabase.instance.client.storage
      .from('profile-photos')
      .getPublicUrl(storagePath);

  return publicUrl;
}
```

### Things To Note (File Upload):
1. **Upload directly from Flutter to Supabase Storage.** Don't route file uploads through FastAPI — it wastes bandwidth and slows things down.
2. **Profile photos → public bucket** (anyone can view). **Driver documents → private bucket** (only accessible via signed URLs with expiry).
3. **Use `upsert: true`** for profile photos so re-uploading replaces the old file.
4. **Supabase Storage free tier = 1GB.** Sufficient for MVP. Compress images on the client side before upload.

---

## API Endpoints

### User Profile

| Method | Endpoint                     | Auth     | Description                          |
|--------|------------------------------|----------|--------------------------------------|
| GET    | `/api/v1/users/me`           | Required | Get current user's profile           |
| PUT    | `/api/v1/users/me`           | Required | Update name, email, profile photo URL |

### Driver Registration & Management

| Method | Endpoint                         | Auth     | Description                               |
|--------|----------------------------------|----------|-------------------------------------------|
| POST   | `/api/v1/drivers/register`       | Required | Submit driver registration                |
| GET    | `/api/v1/drivers/me`             | Required | Get driver profile + verification status  |
| PUT    | `/api/v1/drivers/me`             | Required | Update vehicle details (if still pending) |
| POST   | `/api/v1/drivers/documents`      | Required | Add document URL to driver record         |
| GET    | `/api/v1/drivers/documents`      | Required | List uploaded documents                   |

---

## Pydantic Schemas

### User

```python
# schemas/user.py

from pydantic import BaseModel, Field
from uuid import UUID
from datetime import datetime

class UserUpdateRequest(BaseModel):
    name: str | None = Field(None, max_length=100)
    email: str | None = Field(None, max_length=255)
    profile_photo: str | None = None   # Supabase Storage URL

class UserResponse(BaseModel):
    id: UUID
    name: str | None
    email: str | None
    phone: str | None
    profile_photo: str | None
    role: str
    created_at: datetime

    model_config = {"from_attributes": True}
```

### Driver

```python
# schemas/driver.py

from pydantic import BaseModel, Field
from uuid import UUID
from datetime import datetime
from decimal import Decimal

class DriverRegisterRequest(BaseModel):
    license_number: str = Field(..., max_length=50)
    vehicle_make: str = Field(..., max_length=50)
    vehicle_model: str = Field(..., max_length=50)
    vehicle_number: str = Field(..., max_length=20)
    vehicle_type: str = Field(..., pattern="^(hatchback|sedan|suv|muv)$")
    vehicle_color: str | None = Field(None, max_length=30)
    mileage_kmpl: Decimal = Field(..., gt=0, le=50, decimal_places=2)
    seat_capacity: int = Field(..., ge=1, le=8)

class DriverResponse(BaseModel):
    id: UUID
    license_number: str
    vehicle_make: str
    vehicle_model: str
    vehicle_number: str
    vehicle_type: str
    vehicle_color: str | None
    mileage_kmpl: Decimal
    seat_capacity: int
    verification_status: str
    rejection_reason: str | None
    onboarded_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}

class DocumentUploadRequest(BaseModel):
    doc_type: str = Field(
        ...,
        pattern="^(driving_license|vehicle_rc|insurance|aadhar|pan)$"
    )
    file_url: str       # URL from Supabase Storage upload

class DocumentResponse(BaseModel):
    id: UUID
    doc_type: str
    file_url: str
    uploaded_at: datetime

    model_config = {"from_attributes": True}
```

---

## Service Layer

```python
# services/driver_service.py

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.driver import Driver
from app.models.driver_document import DriverDocument
from app.models.user import User
from app.schemas.driver import DriverRegisterRequest, DocumentUploadRequest
from fastapi import HTTPException

async def register_driver(
    db: AsyncSession,
    user: User,
    data: DriverRegisterRequest,
) -> Driver:
    """Register current user as a driver."""

    # Check if already registered
    existing = await db.execute(
        select(Driver).where(Driver.user_id == user.id)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=400,
            detail="Driver profile already exists",
            code="DRIVER_ALREADY_REGISTERED",
        )

    driver = Driver(
        user_id=user.id,
        license_number=data.license_number,
        vehicle_make=data.vehicle_make,
        vehicle_model=data.vehicle_model,
        vehicle_number=data.vehicle_number,
        vehicle_type=data.vehicle_type,
        vehicle_color=data.vehicle_color,
        mileage_kmpl=data.mileage_kmpl,
        seat_capacity=data.seat_capacity,
        verification_status="pending",
    )
    db.add(driver)

    # Update user role
    user.role = "driver"
    await db.commit()
    await db.refresh(driver)

    return driver


async def add_document(
    db: AsyncSession,
    driver: Driver,
    data: DocumentUploadRequest,
) -> DriverDocument:
    """Add a document to the driver's profile."""

    # Check for duplicate doc_type
    existing = await db.execute(
        select(DriverDocument).where(
            DriverDocument.driver_id == driver.id,
            DriverDocument.doc_type == data.doc_type,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=400,
            detail=f"Document of type '{data.doc_type}' already uploaded. Delete and re-upload.",
        )

    doc = DriverDocument(
        driver_id=driver.id,
        doc_type=data.doc_type,
        file_url=data.file_url,
    )
    db.add(doc)
    await db.commit()
    await db.refresh(doc)
    return doc


async def get_driver_by_user(db: AsyncSession, user: User) -> Driver | None:
    """Get driver profile for current user."""
    result = await db.execute(
        select(Driver).where(Driver.user_id == user.id)
    )
    return result.scalar_one_or_none()
```

---

## Router

```python
# routers/drivers.py

from fastapi import APIRouter, Depends
from app.dependencies import get_current_user, get_db
from app.services import driver_service
from app.schemas.driver import (
    DriverRegisterRequest,
    DriverResponse,
    DocumentUploadRequest,
    DocumentResponse,
)

router = APIRouter(prefix="/api/v1/drivers", tags=["drivers"])

@router.post("/register", response_model=dict, status_code=201)
async def register_driver(
    data: DriverRegisterRequest,
    current_user=Depends(get_current_user),
    db=Depends(get_db),
):
    driver = await driver_service.register_driver(db, current_user, data)
    return {
        "data": DriverResponse.model_validate(driver),
        "message": "Driver registration submitted. Awaiting verification.",
    }

@router.get("/me", response_model=dict)
async def get_driver_profile(
    current_user=Depends(get_current_user),
    db=Depends(get_db),
):
    driver = await driver_service.get_driver_by_user(db, current_user)
    if not driver:
        raise HTTPException(status_code=404, detail="No driver profile found")
    return {"data": DriverResponse.model_validate(driver)}

@router.post("/documents", response_model=dict, status_code=201)
async def upload_document(
    data: DocumentUploadRequest,
    current_user=Depends(get_current_user),
    db=Depends(get_db),
):
    driver = await driver_service.get_driver_by_user(db, current_user)
    if not driver:
        raise HTTPException(status_code=404, detail="Register as driver first")
    doc = await driver_service.add_document(db, driver, data)
    return {
        "data": DocumentResponse.model_validate(doc),
        "message": "Document uploaded successfully",
    }
```

---

## Driver Verification Flow (Admin Side)

Detailed in `08-admin.md`, but the key points:

```
Admin Dashboard (SQLAdmin)
    │
    ├── View pending drivers list
    │   └── Filter: verification_status = 'pending'
    │
    ├── Click on a driver → View profile + documents
    │   └── Documents open via signed URLs from Supabase Storage
    │
    ├── Approve
    │   ├── Set verification_status = 'approved'
    │   ├── Set verified_at = NOW()
    │   ├── Set verified_by = admin.user.id
    │   ├── Set onboarded_at = NOW()  ← Starts 3-month cashback clock
    │   └── Send FCM notification to driver: "Your driver account is approved!"
    │
    └── Reject
        ├── Set verification_status = 'rejected'
        ├── Set rejection_reason = "License photo unclear"
        └── Send FCM notification: "Registration rejected. Reason: ..."
            └── Driver can update docs and re-submit → status goes back to 'pending'
```

---

## Things To Note

1. **Role change is permanent-ish.** Once a user registers as a driver, their role becomes `driver` — but they can still use passenger features (search, book). A driver is a superset of a passenger.

2. **Vehicle details are per-driver, not per-ride.** In Phase 1, a driver has one vehicle. If they need to change vehicles, they update their driver profile. Phase 2 can support multiple vehicles.

3. **`seat_capacity` vs `available_seats` on a ride.** `seat_capacity` is a driver attribute (the car seats). `available_seats` is a ride attribute (how many seats the driver offers for THIS ride, which can be ≤ `seat_capacity`).

4. **Mileage validation.** `mileage_kmpl` is constrained to 0–50 km/l. If a driver enters unrealistic values, the fare engine produces wrong prices. Admin can override this during verification.

5. **Document re-upload.** If a driver is rejected and needs to re-upload documents, they should delete the old document and upload a new one. The `doc_type` unique constraint prevents duplicate types.

6. **Supabase Storage signed URLs have expiry.** For driver documents (private bucket), generate long-lived signed URLs (1 year). For admin review, generate short-lived URLs on demand.
