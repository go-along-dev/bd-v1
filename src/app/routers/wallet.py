from fastapi import APIRouter, Depends, UploadFile, File, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from decimal import Decimal

from app.dependencies import get_db, get_current_user, require_driver
from app.schemas.wallet import (
    WalletResponse,
    WalletTransactionResponse,
    CashbackRequest,
    WithdrawalRequest,
)
from app.schemas.common import PaginatedResponse, MessageResponse
from app.services import wallet_service, storage_service
from app.models.user import User
from app.models.driver import Driver
from datetime import datetime, timezone

router = APIRouter(prefix="/wallet", tags=["Wallet"])


# ─── Helper: Get Driver ───────────────────────
async def get_driver(db: AsyncSession, user: User) -> Driver:
    from fastapi import HTTPException
    result = await db.execute(
        select(Driver).where(Driver.user_id == user.id)
    )
    driver = result.scalar_one_or_none()
    if not driver:
        raise HTTPException(status_code=404, detail="Driver profile not found")
    return driver


# ─── GET /wallet ──────────────────────────────
@router.get("", response_model=WalletResponse)
async def get_wallet(
    db: AsyncSession   = Depends(get_db),
    current_user: User = Depends(require_driver),
):
    """Get current driver's wallet balance."""
    driver = await get_driver(db, current_user)
    wallet = await wallet_service.get_or_create_wallet(
        db=db, driver_id=driver.id
    )
    return wallet


# ─── GET /wallet/transactions ─────────────────
@router.get("/transactions", response_model=dict)
async def get_transactions(
    page:     int      = 1,
    per_page: int      = 20,
    db: AsyncSession   = Depends(get_db),
    current_user: User = Depends(require_driver),
):
    """Get paginated wallet transaction history."""
    driver = await get_driver(db, current_user)
    wallet = await wallet_service.get_or_create_wallet(
        db=db, driver_id=driver.id
    )
    transactions, total = await wallet_service.get_transactions(
        db=db, wallet=wallet, page=page, per_page=per_page
    )
    return {
        "data":     [WalletTransactionResponse.model_validate(t) for t in transactions],
        "total":    total,
        "page":     page,
        "per_page": per_page,
    }


# ─── POST /wallet/cashback ────────────────────
@router.post(
    "/cashback",
    response_model=WalletTransactionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def request_cashback(
    payload:           CashbackRequest,
    toll_proof:        UploadFile = File(...),
    db: AsyncSession   = Depends(get_db),
    current_user: User = Depends(require_driver),
):
    """
    Submit a toll cashback request.
    Driver uploads toll receipt — admin reviews and approves/rejects.
    Eligible within 90 days of driver onboarding.
    """
    driver = await get_driver(db, current_user)

    # Upload toll proof to Supabase Storage
    timestamp  = int(datetime.now(timezone.utc).timestamp())
    path       = f"toll-proofs/{driver.id}/{payload.ride_id}_{timestamp}"
    toll_url   = await storage_service.upload_file(
        bucket       = "toll-proofs",
        path         = path,
        file         = toll_proof,
        content_type = toll_proof.content_type or "image/jpeg",
    )

    wallet = await wallet_service.get_or_create_wallet(
        db=db, driver_id=driver.id
    )

    return await wallet_service.request_cashback(
        db             = db,
        driver_id      = driver.id,
        wallet         = wallet,
        ride_id        = payload.ride_id,
        amount         = payload.amount,
        toll_proof_url = toll_url,
    )


# ─── POST /wallet/withdraw ────────────────────
@router.post(
    "/withdraw",
    response_model=WalletTransactionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def request_withdrawal(
    payload:           WithdrawalRequest,
    db: AsyncSession   = Depends(get_db),
    current_user: User = Depends(require_driver),
):
    """
    Request a wallet withdrawal via UPI.
    Amount is held immediately. Admin manually transfers via UPI app.
    Only one pending withdrawal allowed at a time.
    """
    driver = await get_driver(db, current_user)
    wallet = await wallet_service.get_or_create_wallet(
        db=db, driver_id=driver.id
    )
    return await wallet_service.request_withdrawal(
        db     = db,
        wallet = wallet,
        amount = payload.amount,
        upi_id = payload.upi_id,
    )