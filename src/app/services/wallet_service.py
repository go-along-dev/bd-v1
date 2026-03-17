from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func
from fastapi import HTTPException, status
from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID

from app.models.wallet import Wallet
from app.models.wallet_transaction import WalletTransaction
from app.models.booking import Booking
from app.models.platform_config import PlatformConfig
from app.models.user import User


# ─── Helper: Get Platform Config ──────────────
async def get_config(db: AsyncSession, key: str, default: str) -> str:
    result = await db.execute(
        select(PlatformConfig).where(PlatformConfig.key == key)
    )
    config = result.scalar_one_or_none()
    return config.value if config else default


# ─── Get or Create Wallet ─────────────────────
async def get_or_create_wallet(
    db: AsyncSession,
    driver_id: UUID,
) -> Wallet:
    """Returns driver wallet. Creates one with balance=0 if not exists."""
    result = await db.execute(
        select(Wallet).where(Wallet.driver_id == driver_id)
    )
    wallet = result.scalar_one_or_none()

    if not wallet:
        wallet = Wallet(driver_id=driver_id, balance=Decimal("0.00"))
        db.add(wallet)
        await db.commit()
        await db.refresh(wallet)

    return wallet


# ─── Get Transactions ─────────────────────────
async def get_transactions(
    db: AsyncSession,
    wallet: Wallet,
    page: int = 1,
    per_page: int = 20,
) -> tuple[list[WalletTransaction], int]:
    """Paginated transaction history."""
    offset = (page - 1) * per_page

    total_result = await db.execute(
        select(func.count(WalletTransaction.id))
        .where(WalletTransaction.wallet_id == wallet.id)
    )
    total = total_result.scalar()

    result = await db.execute(
        select(WalletTransaction)
        .where(WalletTransaction.wallet_id == wallet.id)
        .order_by(WalletTransaction.created_at.desc())
        .limit(per_page)
        .offset(offset)
    )
    return result.scalars().all(), total


# ─── Request Cashback ─────────────────────────
async def request_cashback(
    db: AsyncSession,
    driver_id: UUID,
    wallet: Wallet,
    ride_id: UUID,
    amount: Decimal,
    toll_proof_url: str,
) -> WalletTransaction:
    """
    Driver submits toll cashback request.
    Admin reviews and approves/rejects from dashboard.
    """
    # 1. Get eligibility days from config
    eligibility_days = int(
        await get_config(db, "cashback_eligibility_days", "90")
    )
    max_cashback = Decimal(
        await get_config(db, "max_cashback_per_ride", "500.00")
    )

    # 2. Validate amount
    if amount > max_cashback:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cashback amount exceeds maximum of ₹{max_cashback}"
        )

    # 3. Check no duplicate cashback for same ride
    existing = await db.execute(
        select(WalletTransaction).where(
            and_(
                WalletTransaction.wallet_id == wallet.id,
                WalletTransaction.ride_id   == ride_id,
                WalletTransaction.type.in_([
                    "cashback_request",
                    "cashback_credited",
                ]),
            )
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cashback already claimed for this ride"
        )

    # 4. Create pending cashback transaction
    txn = WalletTransaction(
        wallet_id      = wallet.id,
        type           = "cashback_request",
        amount         = amount,
        status         = "pending",
        ride_id        = ride_id,
        toll_proof_url = toll_proof_url,
    )
    db.add(txn)
    await db.commit()
    await db.refresh(txn)
    return txn


# ─── Request Withdrawal ───────────────────────
async def request_withdrawal(
    db: AsyncSession,
    wallet: Wallet,
    amount: Decimal,
    upi_id: str,
) -> WalletTransaction:
    """
    Driver requests wallet withdrawal via UPI.
    Admin manually processes the transfer.
    """
    max_withdrawal = Decimal(
        await get_config(db, "max_withdrawal_amount", "5000.00")
    )

    # 1. Check sufficient balance
    if amount > wallet.balance:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Insufficient balance. Available: ₹{wallet.balance}"
        )

    # 2. Check max withdrawal limit
    if amount > max_withdrawal:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Amount exceeds maximum withdrawal of ₹{max_withdrawal}"
        )

    # 3. Check no existing pending withdrawal
    pending = await db.execute(
        select(WalletTransaction).where(
            and_(
                WalletTransaction.wallet_id == wallet.id,
                WalletTransaction.type      == "withdrawal_request",
                WalletTransaction.status    == "pending",
            )
        )
    )
    if pending.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You already have a pending withdrawal request"
        )

    # 4. Hold the amount immediately
    wallet.balance -= amount

    # 5. Create transaction
    txn = WalletTransaction(
        wallet_id = wallet.id,
        type      = "withdrawal_request",
        amount    = amount,
        status    = "pending",
        upi_id    = upi_id,
    )
    db.add(txn)
    await db.commit()
    await db.refresh(txn)
    return txn


# ─── Approve Transaction (Admin) ──────────────
async def approve_transaction(
    db: AsyncSession,
    txn: WalletTransaction,
    admin_user: User,
    admin_note: str | None = None,
) -> None:
    """
    Admin approves a cashback or withdrawal transaction.
    Cashback → credits wallet balance.
    Withdrawal → balance already deducted on request.
    """
    if txn.status != "pending":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only pending transactions can be approved"
        )

    wallet = await db.get(Wallet, txn.wallet_id)

    if txn.type == "cashback_request":
        # Credit wallet
        wallet.balance += txn.amount
        wallet.updated_at = datetime.now(timezone.utc)

        # Create companion credited record for audit trail
        credit_txn = WalletTransaction(
            wallet_id    = wallet.id,
            type         = "cashback_credited",
            amount       = txn.amount,
            status       = "approved",
            ride_id      = txn.ride_id,
            admin_note   = f"Approved cashback from txn {txn.id}",
            processed_by = admin_user.id,
            processed_at = datetime.now(timezone.utc),
        )
        db.add(credit_txn)

    elif txn.type == "withdrawal_request":
        # Balance already deducted on request — just update status
        pass

    # Update transaction
    txn.status       = "approved"
    txn.processed_by = admin_user.id
    txn.processed_at = datetime.now(timezone.utc)
    txn.admin_note   = admin_note

    await db.commit()


# ─── Reject Transaction (Admin) ───────────────
async def reject_transaction(
    db: AsyncSession,
    txn: WalletTransaction,
    admin_user: User,
    reason: str,
) -> None:
    """
    Admin rejects a transaction.
    Withdrawal rejection restores the held balance.
    """
    if txn.status != "pending":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only pending transactions can be rejected"
        )

    wallet = await db.get(Wallet, txn.wallet_id)

    # Restore held balance for rejected withdrawals
    if txn.type == "withdrawal_request":
        wallet.balance += txn.amount
        wallet.updated_at = datetime.now(timezone.utc)

    txn.status       = "rejected"
    txn.processed_by = admin_user.id
    txn.processed_at = datetime.now(timezone.utc)
    txn.admin_note   = reason

    await db.commit()