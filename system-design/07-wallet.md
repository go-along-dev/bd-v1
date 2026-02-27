# Module 7: Wallet & Toll Cashback

## Overview

The wallet system is GoAlong's **core USP and driver acquisition feature**. For the first 3 months after onboarding, drivers get **cashback on toll expenses** for eligible rides. The cashback is credited to an in-app wallet. The driver can request withdrawal, and admin pays manually via UPI.

### Key Principle for Phase 1
**Everything is manual.** No automated toll detection, no auto-payout, no payment gateway. The admin verifies toll proofs and manually transfers money. This keeps the MVP simple while validating the concept.

---

## Wallet Flow

```
Driver completes a toll ride
         │
         ▼
┌──────────────────────────┐
│  Driver uploads toll     │
│  receipt via app          │
│  POST /wallet/cashback   │
│  { ride_id, amount,      │
│    toll_proof_url }       │
└───────────┬──────────────┘
            │
            ▼
  ┌────────────────────┐
  │  Status: PENDING    │  ← Waiting for admin review
  └─────────┬──────────┘
            │
      Admin reviews in dashboard
            │
     ┌──────┴───────┐
     ▼              ▼
┌──────────┐  ┌──────────┐
│ APPROVED │  │ REJECTED │
│          │  │          │
│ Wallet   │  │ Reason   │
│ balance  │  │ sent to  │
│ credited │  │ driver   │
└──────────┘  └──────────┘


Driver requests withdrawal
         │
         ▼
┌──────────────────────────┐
│  POST /wallet/withdraw   │
│  { amount, upi_id }      │
└───────────┬──────────────┘
            │
            ▼
  ┌────────────────────────┐
  │  Status: PENDING        │
  └────────────┬───────────┘
               │
         Admin processes
               │
        ┌──────┴───────┐
        ▼              ▼
  ┌──────────┐   ┌──────────┐
  │ APPROVED │   │ REJECTED │
  │          │   │          │
  │ Balance  │   │ Balance  │
  │ deducted │   │ restored │
  │ UPI paid │   │          │
  │ manually │   └──────────┘
  └──────────┘
```

---

## Database: Wallets Table

```sql
CREATE TABLE wallets (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    driver_id   UUID UNIQUE NOT NULL REFERENCES drivers(id) ON DELETE CASCADE,
    balance     DECIMAL(10,2) NOT NULL DEFAULT 0.00,
    created_at  TIMESTAMPTZ DEFAULT NOW(),
    updated_at  TIMESTAMPTZ DEFAULT NOW()
);

-- Wallet is created automatically when a driver is approved
CREATE INDEX idx_wallets_driver ON wallets(driver_id);
```

### Things To Note:
- **One wallet per driver.** Created automatically on driver approval (in the driver verification admin action).
- **Balance can never go negative.** Enforce at application level and add a CHECK constraint.
- **No currency field.** Phase 1 is India-only, everything is INR.

---

## Database: Wallet Transactions Table

```sql
CREATE TABLE wallet_transactions (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    wallet_id       UUID NOT NULL REFERENCES wallets(id) ON DELETE CASCADE,

    -- Transaction type
    type            VARCHAR(30) NOT NULL,
                    -- 'cashback_request'       → Driver submits toll proof
                    -- 'cashback_credited'      → Admin approves, balance increases
                    -- 'cashback_rejected'      → Admin rejects toll proof
                    -- 'withdrawal_request'     → Driver requests payout
                    -- 'withdrawal_approved'    → Admin approves, balance decreases
                    -- 'withdrawal_rejected'    → Admin rejects, balance restored

    amount          DECIMAL(10,2) NOT NULL,

    -- Cashback-specific
    ride_id         UUID REFERENCES rides(id),      -- Which ride the toll was for
    toll_proof_url  TEXT,                             -- Receipt image in Supabase Storage

    -- Withdrawal-specific
    upi_id          VARCHAR(100),                    -- Driver's UPI ID for payout

    -- Admin processing
    status          VARCHAR(20) NOT NULL DEFAULT 'pending',
                    -- 'pending' | 'approved' | 'rejected'
    admin_note      TEXT,                            -- Reason for approval/rejection
    processed_by    UUID REFERENCES users(id),       -- Admin who processed it
    processed_at    TIMESTAMPTZ,

    -- Timestamps
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_wallet_txn_wallet ON wallet_transactions(wallet_id);
CREATE INDEX idx_wallet_txn_status ON wallet_transactions(status);
CREATE INDEX idx_wallet_txn_type ON wallet_transactions(type);
```

---

## Cashback Eligibility Rules

| Rule                                      | Implementation                            |
|-------------------------------------------|-------------------------------------------|
| Driver must be verified (approved)        | Check `driver.verification_status`        |
| Within 3 months of onboarding            | Check `driver.onboarded_at + 90 days > NOW()` |
| Ride must exist and belong to driver      | Validate `ride.driver_id == driver.id`    |
| Ride must be completed                    | Check `ride.status == 'completed'`        |
| No duplicate cashback for same ride       | Check existing transaction with same `ride_id` |
| Toll proof required                       | `toll_proof_url` cannot be null           |
| Max cashback amount per ride              | Admin-configurable cap (e.g., ₹500)       |

```python
# Add to platform_config seed data
INSERT INTO platform_config (key, value, description) VALUES
    ('cashback_eligibility_days', '90', 'Number of days from onboarding that cashback is eligible'),
    ('max_cashback_per_ride', '500.00', 'Maximum cashback amount per ride in INR');
```

---

## API Endpoints

| Method | Endpoint                        | Auth    | Role    | Description                        |
|--------|---------------------------------|---------|---------|------------------------------------|
| GET    | `/api/v1/wallet/balance`        | Required| Driver  | Get current wallet balance         |
| GET    | `/api/v1/wallet/transactions`   | Required| Driver  | Get transaction history            |
| POST   | `/api/v1/wallet/cashback`       | Required| Driver  | Submit toll cashback request       |
| POST   | `/api/v1/wallet/withdraw`       | Required| Driver  | Request withdrawal                 |
| GET    | `/api/v1/wallet/eligibility`    | Required| Driver  | Check cashback eligibility status  |

---

## Pydantic Schemas

```python
# schemas/wallet.py

from pydantic import BaseModel, Field
from uuid import UUID
from datetime import datetime
from decimal import Decimal

class WalletBalanceResponse(BaseModel):
    balance: Decimal
    pending_cashback: Decimal        # Sum of pending cashback requests
    pending_withdrawal: Decimal      # Sum of pending withdrawal requests

class CashbackRequest(BaseModel):
    ride_id: UUID
    amount: Decimal = Field(..., gt=0, le=5000)     # Max ₹5000 per claim
    toll_proof_url: str                              # Supabase Storage URL

class WithdrawalRequest(BaseModel):
    amount: Decimal = Field(..., gt=0)
    upi_id: str = Field(..., max_length=100, pattern=r'^[\w.\-]+@[\w]+$')
    # UPI ID format: username@bankname (e.g., rahul@okaxis, 9876543210@ybl)

class TransactionResponse(BaseModel):
    id: UUID
    type: str
    amount: Decimal
    status: str
    ride_id: UUID | None
    toll_proof_url: str | None
    upi_id: str | None
    admin_note: str | None
    created_at: datetime
    processed_at: datetime | None

    model_config = {"from_attributes": True}

class TransactionListResponse(BaseModel):
    data: list[TransactionResponse]
    total: int
    page: int
    per_page: int

class EligibilityResponse(BaseModel):
    is_eligible: bool
    days_remaining: int             # Days left in the eligibility window
    onboarded_at: datetime
    eligibility_ends_at: datetime
```

---

## Service Layer

```python
# services/wallet_service.py

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from fastapi import HTTPException
from app.models.wallet import Wallet
from app.models.wallet_transaction import WalletTransaction
from app.models.driver import Driver
from app.models.ride import Ride
from app.models.platform_config import PlatformConfig


async def get_wallet(db: AsyncSession, driver: Driver) -> Wallet:
    """Get or create wallet for a driver."""
    result = await db.execute(
        select(Wallet).where(Wallet.driver_id == driver.id)
    )
    wallet = result.scalar_one_or_none()
    if not wallet:
        # Auto-create wallet (should already exist from verification)
        wallet = Wallet(driver_id=driver.id, balance=Decimal("0.00"))
        db.add(wallet)
        await db.commit()
        await db.refresh(wallet)
    return wallet


async def get_balance_summary(db: AsyncSession, wallet: Wallet) -> dict:
    """Get balance with pending amounts."""
    # Pending cashback
    pending_cb = await db.execute(
        select(func.coalesce(func.sum(WalletTransaction.amount), 0)).where(
            and_(
                WalletTransaction.wallet_id == wallet.id,
                WalletTransaction.type == "cashback_request",
                WalletTransaction.status == "pending",
            )
        )
    )
    # Pending withdrawal
    pending_wd = await db.execute(
        select(func.coalesce(func.sum(WalletTransaction.amount), 0)).where(
            and_(
                WalletTransaction.wallet_id == wallet.id,
                WalletTransaction.type == "withdrawal_request",
                WalletTransaction.status == "pending",
            )
        )
    )
    return {
        "balance": wallet.balance,
        "pending_cashback": pending_cb.scalar(),
        "pending_withdrawal": pending_wd.scalar(),
    }


async def check_eligibility(db: AsyncSession, driver: Driver) -> dict:
    """Check if driver is eligible for toll cashback."""
    if not driver.onboarded_at:
        return {"is_eligible": False, "days_remaining": 0}

    # Get eligibility window from config
    config = await db.execute(
        select(PlatformConfig).where(PlatformConfig.key == "cashback_eligibility_days")
    )
    config = config.scalar_one_or_none()
    eligibility_days = int(config.value) if config else 90

    eligibility_end = driver.onboarded_at + timedelta(days=eligibility_days)
    now = datetime.now(timezone.utc)

    is_eligible = now < eligibility_end
    days_remaining = max(0, (eligibility_end - now).days)

    return {
        "is_eligible": is_eligible,
        "days_remaining": days_remaining,
        "onboarded_at": driver.onboarded_at,
        "eligibility_ends_at": eligibility_end,
    }


async def submit_cashback_request(
    db: AsyncSession,
    driver: Driver,
    wallet: Wallet,
    data: CashbackRequest,
) -> WalletTransaction:
    """Submit a toll cashback request for admin review."""

    # 1. Check eligibility
    eligibility = await check_eligibility(db, driver)
    if not eligibility["is_eligible"]:
        raise HTTPException(
            status_code=400,
            detail="Cashback eligibility period has expired"
        )

    # 2. Validate ride
    ride = await db.get(Ride, data.ride_id)
    if not ride:
        raise HTTPException(status_code=404, detail="Ride not found")
    if ride.driver_id != driver.id:
        raise HTTPException(status_code=403, detail="This ride doesn't belong to you")
    if ride.status != "completed":
        raise HTTPException(status_code=400, detail="Cashback only for completed rides")

    # 3. Check for duplicate
    existing = await db.execute(
        select(WalletTransaction).where(
            and_(
                WalletTransaction.wallet_id == wallet.id,
                WalletTransaction.ride_id == data.ride_id,
                WalletTransaction.type == "cashback_request",
                WalletTransaction.status.in_(["pending", "approved"]),
            )
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=400,
            detail="Cashback already requested for this ride"
        )

    # 4. Check max cashback cap
    config = await db.execute(
        select(PlatformConfig).where(PlatformConfig.key == "max_cashback_per_ride")
    )
    config = config.scalar_one_or_none()
    max_cashback = Decimal(config.value) if config else Decimal("500.00")

    if data.amount > max_cashback:
        raise HTTPException(
            status_code=400,
            detail=f"Maximum cashback per ride is ₹{max_cashback}"
        )

    # 5. Create transaction
    txn = WalletTransaction(
        wallet_id=wallet.id,
        type="cashback_request",
        amount=data.amount,
        ride_id=data.ride_id,
        toll_proof_url=data.toll_proof_url,
        status="pending",
    )
    db.add(txn)
    await db.commit()
    await db.refresh(txn)

    return txn


async def request_withdrawal(
    db: AsyncSession,
    driver: Driver,
    wallet: Wallet,
    data: WithdrawalRequest,
) -> WalletTransaction:
    """Request a withdrawal from the wallet."""

    # 1. Check sufficient balance
    if data.amount > wallet.balance:
        raise HTTPException(
            status_code=400,
            detail=f"Insufficient balance. Available: ₹{wallet.balance}"
        )

    # 2. Check no existing pending withdrawal
    pending = await db.execute(
        select(WalletTransaction).where(
            and_(
                WalletTransaction.wallet_id == wallet.id,
                WalletTransaction.type == "withdrawal_request",
                WalletTransaction.status == "pending",
            )
        )
    )
    if pending.scalar_one_or_none():
        raise HTTPException(
            status_code=400,
            detail="You already have a pending withdrawal request"
        )

    # 3. Hold the amount (deduct from balance)
    wallet.balance -= data.amount
    wallet.updated_at = datetime.now(timezone.utc)

    # 4. Create transaction
    txn = WalletTransaction(
        wallet_id=wallet.id,
        type="withdrawal_request",
        amount=data.amount,
        upi_id=data.upi_id,
        status="pending",
    )
    db.add(txn)
    await db.commit()
    await db.refresh(txn)

    return txn
```

---

## Admin Actions (Processed in Admin Panel)

### Approve Cashback
```python
async def admin_approve_cashback(
    db: AsyncSession,
    txn_id: UUID,
    admin_user: User,
    note: str = None,
):
    txn = await db.get(WalletTransaction, txn_id)
    if txn.type != "cashback_request" or txn.status != "pending":
        raise HTTPException(status_code=400, detail="Invalid transaction")

    wallet = await db.get(Wallet, txn.wallet_id)

    # Credit the wallet
    wallet.balance += txn.amount
    wallet.updated_at = datetime.now(timezone.utc)

    # Update transaction
    txn.status = "approved"
    txn.processed_by = admin_user.id
    txn.processed_at = datetime.now(timezone.utc)
    txn.admin_note = note

    # Create a companion "credited" record for audit trail
    credit_txn = WalletTransaction(
        wallet_id=wallet.id,
        type="cashback_credited",
        amount=txn.amount,
        ride_id=txn.ride_id,
        status="approved",
        admin_note=f"Approved cashback from txn {txn.id}",
        processed_by=admin_user.id,
        processed_at=datetime.now(timezone.utc),
    )
    db.add(credit_txn)

    await db.commit()

    # Notify driver
    await notification_service.send_push(
        user_id=str((await db.execute(
            select(Driver.user_id).where(Driver.id == wallet.driver_id)
        )).scalar()),
        title="Cashback Approved! 🎉",
        body=f"₹{txn.amount} has been credited to your GoAlong wallet.",
    )
```

### Approve Withdrawal
```python
async def admin_approve_withdrawal(
    db: AsyncSession,
    txn_id: UUID,
    admin_user: User,
    note: str = None,
):
    txn = await db.get(WalletTransaction, txn_id)
    if txn.type != "withdrawal_request" or txn.status != "pending":
        raise HTTPException(status_code=400, detail="Invalid transaction")

    # Balance was already deducted when request was made
    # Just update transaction status
    txn.status = "approved"
    txn.processed_by = admin_user.id
    txn.processed_at = datetime.now(timezone.utc)
    txn.admin_note = note or f"Paid via UPI to {txn.upi_id}"

    await db.commit()

    # Admin now manually sends ₹{txn.amount} to {txn.upi_id} via their UPI app
    # This is a manual step — NOT automated in Phase 1

    # Notify driver
    await notification_service.send_push(
        user_id="...",
        title="Withdrawal Approved",
        body=f"₹{txn.amount} is being transferred to {txn.upi_id}.",
    )
```

### Reject Withdrawal — Restore Balance
```python
async def admin_reject_withdrawal(
    db: AsyncSession,
    txn_id: UUID,
    admin_user: User,
    reason: str,
):
    txn = await db.get(WalletTransaction, txn_id)
    if txn.type != "withdrawal_request" or txn.status != "pending":
        raise HTTPException(status_code=400, detail="Invalid transaction")

    wallet = await db.get(Wallet, txn.wallet_id)

    # RESTORE the held balance
    wallet.balance += txn.amount
    wallet.updated_at = datetime.now(timezone.utc)

    txn.status = "rejected"
    txn.processed_by = admin_user.id
    txn.processed_at = datetime.now(timezone.utc)
    txn.admin_note = reason

    await db.commit()
```

---

## Flutter — Wallet Screen

```
┌─────────────────────────────────────┐
│  My Wallet                          │
├─────────────────────────────────────┤
│                                     │
│  Balance: ₹1,250.00                 │
│                                     │
│  Pending Cashback: ₹300.00          │
│  Pending Withdrawal: ₹0.00         │
│                                     │
│  ┌─────────────┐ ┌───────────────┐  │
│  │ Request      │ │  Withdraw     │  │
│  │ Cashback     │ │               │  │
│  └─────────────┘ └───────────────┘  │
│                                     │
├─────────────────────────────────────┤
│  Transaction History                │
├─────────────────────────────────────┤
│  ▲ ₹200.00  Cashback Approved      │
│    Ride: BLR → MYS  |  Feb 20      │
│                                     │
│  ▽ ₹500.00  Withdrawal Approved    │
│    UPI: rahul@okaxis |  Feb 18      │
│                                     │
│  ⏳ ₹300.00  Cashback Pending       │
│    Ride: BLR → HAS  |  Feb 25      │
│                                     │
│  ✗ ₹150.00  Cashback Rejected      │
│    "Blurry receipt"  |  Feb 15      │
└─────────────────────────────────────┘
```

---

## Toll Proof Upload Flow

```
1. Driver opens "Request Cashback" screen
2. Selects a completed ride from dropdown (only their rides, only completed)
3. Enters toll amount (₹)
4. Takes photo of toll receipt or uploads from gallery
   → Image uploaded to Supabase Storage (private bucket: toll-proofs/)
5. Submits request
   → POST /wallet/cashback { ride_id, amount, toll_proof_url }
6. Transaction created with status "pending"
7. Driver sees it in transaction history as "Pending Review"
8. Admin reviews in dashboard → Approves or Rejects
9. Driver gets FCM notification with result
```

---

## Things To Note

1. **Withdrawal holds balance immediately.** When a driver requests withdrawal, the amount is deducted from balance right away (held). If rejected, it's restored. This prevents the driver from spending the same balance twice.

2. **Only one pending withdrawal at a time.** Simplifies admin workflow. Driver must wait for current request to be processed before submitting another.

3. **UPI ID validation.** The regex `^[\w.\-]+@[\w]+$` validates basic UPI format (e.g., `rahul@okaxis`, `9876543210@ybl`). Not comprehensive, but catches obvious errors.

4. **Admin pays manually.** After approving a withdrawal, the admin opens their UPI app (Google Pay, PhonePe, etc.) and transfers the amount to the driver's UPI ID. The platform does NOT automate this transfer in Phase 1. Phase 2 can integrate Razorpay Payouts or Cashfree.

5. **3-month eligibility is from approval date, not registration date.** `driver.onboarded_at` is set when admin approves the driver. This is important — the clock starts from approval, giving the driver the full 90 days of active driving.

6. **Cashback is per-ride, not per-toll.** A ride might pass through multiple tolls, but the driver submits one cashback request per ride with the total toll amount and proof. Multiple tolls on one ride = one receipt showing all.

7. **Transaction history is the audit trail.** Every balance change is recorded as a transaction. The wallet balance should always equal: `SUM(approved cashback credits) - SUM(approved withdrawals)`. Build a reconciliation check for admin.

8. **Max cashback cap prevents abuse.** Set a reasonable cap per ride (e.g., ₹500). India tolls typically range from ₹50–₹350 per toll plaza. If a route has multiple tolls, ₹500 is a generous cap.
