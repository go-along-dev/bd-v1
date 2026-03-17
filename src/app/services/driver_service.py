from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from fastapi import HTTPException, status, UploadFile
from datetime import datetime, timezone

from app.models.driver import Driver
from app.models.driver_document import DriverDocument
from app.models.user import User
from app.schemas.driver import DriverRegisterRequest


# ─── Allowed File Types & Max Size ────────────
ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png", "pdf"}
MAX_FILE_SIZE_MB   = 5
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024


# ─── Register Driver ──────────────────────────
async def register_driver(
    db: AsyncSession,
    user: User,
    data: DriverRegisterRequest,
) -> Driver:
    """
    Register a user as a driver.
    Creates driver record with status=pending.
    Updates user.role to driver.
    """
    # 1. Check if driver record already exists
    existing = await db.execute(
        select(Driver).where(Driver.user_id == user.id)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Driver profile already exists"
        )

    # 2. Create driver row
    driver = Driver(
        user_id=user.id,
        vehicle_number=data.vehicle_number,
        vehicle_make=data.vehicle_make,
        vehicle_model=data.vehicle_model,
        vehicle_type=data.vehicle_type,
        vehicle_color=data.vehicle_color,
        license_number=data.license_number,
        seat_capacity=data.seat_capacity,
        mileage_kmpl=data.mileage_kmpl,
        verification_status="pending",
    )
    db.add(driver)

    # 3. Update user role
    user.role = "driver"

    await db.commit()
    await db.refresh(driver)
    return driver


# ─── Get Driver Profile ───────────────────────
async def get_driver_profile(
    db: AsyncSession,
    user: User,
) -> Driver:
    """
    Return driver record with documents eager-loaded.
    Raises 404 if not a registered driver.
    """
    result = await db.execute(
        select(Driver)
        .options(selectinload(Driver.documents))
        .where(Driver.user_id == user.id)
    )
    driver = result.scalar_one_or_none()

    if not driver:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Driver profile not found"
        )

    return driver


# ─── Upload Document ──────────────────────────
async def upload_document(
    db: AsyncSession,
    driver: Driver,
    doc_type: str,
    file: UploadFile,
) -> DriverDocument:
    """
    Validate, upload to Supabase Storage, save record to DB.
    """
    from app.services import storage_service

    # 1. Validate file extension
    filename = file.filename or ""
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file type. Allowed: {', '.join(ALLOWED_EXTENSIONS)}"
        )

    # 2. Validate file size
    contents = await file.read()
    if len(contents) > MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File too large. Maximum size: {MAX_FILE_SIZE_MB}MB"
        )
    await file.seek(0)  # Reset for upload

    # 3. Generate storage path
    timestamp = int(datetime.now(timezone.utc).timestamp())
    path = f"driver-documents/{driver.id}/{doc_type}_{timestamp}.{ext}"

    # 4. Upload to Supabase Storage
    file_url = await storage_service.upload_file(
        bucket="driver-documents",
        path=path,
        file=file,
        content_type=file.content_type or "application/octet-stream",
    )

    # 5. Save document record
    doc = DriverDocument(
        driver_id=driver.id,
        doc_type=doc_type,
        file_url=file_url,
        status="pending",
    )
    db.add(doc)
    await db.commit()
    await db.refresh(doc)

    return doc


# ─── Get Driver Status ────────────────────────
async def get_driver_status(
    db: AsyncSession,
    user: User,
) -> dict:
    """Return current verification status and rejection reason."""
    result = await db.execute(
        select(Driver).where(Driver.user_id == user.id)
    )
    driver = result.scalar_one_or_none()

    if not driver:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Driver profile not found"
        )

    return {
        "verification_status": driver.verification_status,
        "rejection_reason":    driver.rejection_reason,
        "verified_at":         driver.verified_at,
        "onboarded_at":        driver.onboarded_at,
    }