from fastapi import APIRouter, Depends, UploadFile, File, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db, get_current_user, require_driver
from app.schemas.driver import (
    DriverRegisterRequest,
    DriverResponse,
    DriverDocumentResponse,
    DriverDocumentUploadRequest,
    DriverStatusResponse,
)
from app.services import driver_service
from app.models.user import User

router = APIRouter(prefix="/drivers", tags=["Drivers"])


# ─── POST /drivers/register ───────────────────
@router.post(
    "/register",
    response_model=DriverResponse,
    status_code=status.HTTP_201_CREATED,
)
async def register_driver(
    payload: DriverRegisterRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Register current user as a driver.
    Creates driver record with status=pending.
    Admin must approve before driver can create rides.
    """
    return await driver_service.register_driver(
        db=db,
        user=current_user,
        data=payload,
    )


# ─── GET /drivers/me ──────────────────────────
@router.get("/me", response_model=DriverResponse)
async def get_my_driver_profile(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_driver),
):
    """Get current driver's profile with documents."""
    return await driver_service.get_driver_profile(
        db=db,
        user=current_user,
    )


# ─── POST /drivers/documents ──────────────────
@router.post(
    "/documents",
    response_model=DriverDocumentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_document(
    doc_type: str = Query(
        ...,
        pattern="^(driving_license|vehicle_rc|insurance|aadhar|pan)$"
    ),
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_driver),
):
    """
    Upload a driver document to Supabase Storage.
    Allowed types: driving_license, vehicle_rc, insurance, aadhar, pan
    Max size: 5MB. Allowed formats: jpg, png, pdf
    """
    # Get driver profile first
    driver = await driver_service.get_driver_profile(db, current_user)

    return await driver_service.upload_document(
        db=db,
        driver=driver,
        doc_type=doc_type,
        file=file,
    )


# ─── GET /drivers/status ──────────────────────
@router.get("/status", response_model=DriverStatusResponse)
async def get_driver_status(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_driver),
):
    """Get current driver verification status and rejection reason if any."""
    return await driver_service.get_driver_status(
        db=db,
        user=current_user,
    )