# Module 8: Admin Dashboard

## Overview

The admin panel is built using **SQLAdmin** — an auto-generated admin interface that plugs directly into SQLAlchemy models. No separate frontend needed. No React. One dependency, full CRUD on all tables, with custom actions for GoAlong-specific workflows.

### Why SQLAdmin Over a Custom Dashboard
| Factor              | SQLAdmin             | Custom React Dashboard |
|---------------------|----------------------|------------------------|
| Dev time            | ~1 day to set up     | 1-2 weeks              |
| Maintenance         | Zero (auto-generated)| Ongoing                |
| CRUD on all tables  | Automatic            | Build manually         |
| Custom actions      | Supported            | Build manually         |
| Auth                | Built-in basic auth  | Build from scratch     |
| Good enough for MVP | Yes                  | Overkill               |

---

## Setup

```python
# admin/setup.py

from sqladmin import Admin
from app.core.database import engine
from app.admin.views import (
    UserAdmin,
    DriverAdmin,
    DriverDocumentAdmin,
    RideAdmin,
    BookingAdmin,
    WalletAdmin,
    WalletTransactionAdmin,
    PlatformConfigAdmin,
)
from app.admin.auth import AdminAuth


def setup_admin(app):
    """Mount SQLAdmin on the FastAPI app."""
    authentication_backend = AdminAuth(secret_key="your-admin-secret-key")

    admin = Admin(
        app,
        engine,
        authentication_backend=authentication_backend,
        title="GoAlong Admin",
        base_url="/admin",
    )

    # Register all views
    admin.add_view(UserAdmin)
    admin.add_view(DriverAdmin)
    admin.add_view(DriverDocumentAdmin)
    admin.add_view(RideAdmin)
    admin.add_view(BookingAdmin)
    admin.add_view(WalletAdmin)
    admin.add_view(WalletTransactionAdmin)
    admin.add_view(PlatformConfigAdmin)
```

```python
# main.py — mount admin

from fastapi import FastAPI
from app.admin.setup import setup_admin

app = FastAPI(title="GoAlong API")
setup_admin(app)
```

---

## Admin Authentication

SQLAdmin uses its own session-based auth, separate from the Supabase JWT auth used by the mobile app. Admin credentials are stored in environment variables — not in the database.

```python
# admin/auth.py

from sqladmin.authentication import AuthenticationBackend
from starlette.requests import Request
from starlette.responses import RedirectResponse
import os


class AdminAuth(AuthenticationBackend):
    async def login(self, request: Request) -> bool:
        form = await request.form()
        username = form.get("username")
        password = form.get("password")

        # Simple env-based auth for MVP
        valid_username = os.getenv("ADMIN_USERNAME", "admin")
        valid_password = os.getenv("ADMIN_PASSWORD")

        if username == valid_username and password == valid_password:
            request.session.update({"authenticated": True})
            return True
        return False

    async def logout(self, request: Request) -> bool:
        request.session.clear()
        return True

    async def authenticate(self, request: Request) -> RedirectResponse | None:
        if not request.session.get("authenticated"):
            return RedirectResponse(request.url_for("admin:login"), status_code=302)
        return None
```

### Things To Note:
- **Phase 1**: Single admin account via env vars. Good enough.
- **Phase 2**: Move to an `admins` table with hashed passwords and role-based access.
- **ADMIN_PASSWORD must be set** in production env vars. Never commit it.
- **Starlette sessions** require a `SECRET_KEY` — set via `SessionMiddleware`.

```python
# main.py — add session middleware (required for SQLAdmin auth)
from starlette.middleware.sessions import SessionMiddleware

app.add_middleware(SessionMiddleware, secret_key=os.getenv("SESSION_SECRET_KEY"))
```

---

## Admin Views

### User Management

```python
# admin/views.py

from sqladmin import ModelView, action
from app.models.user import User


class UserAdmin(ModelView, model=User):
    name = "User"
    name_plural = "Users"
    icon = "fa-solid fa-users"

    # List page
    column_list = [
        User.id,
        User.full_name,
        User.phone,
        User.email,
        User.role,
        User.is_active,
        User.created_at,
    ]
    column_searchable_list = [User.full_name, User.phone, User.email]
    column_sortable_list = [User.created_at, User.full_name, User.role]
    column_default_sort = ("created_at", True)  # Newest first

    # Detail page
    column_details_exclude_list = [User.supabase_uid]  # Don't show internal ID

    # Permissions
    can_create = False   # Users are created via the app
    can_delete = False   # Soft-deactivate only
    can_edit = True      # Admin can update role, is_active
```

### Driver Verification

```python
class DriverAdmin(ModelView, model=Driver):
    name = "Driver"
    name_plural = "Drivers"
    icon = "fa-solid fa-id-card"

    column_list = [
        Driver.id,
        Driver.user,                    # Shows relationship
        Driver.vehicle_number,
        Driver.vehicle_make,
        Driver.vehicle_model,
        Driver.verification_status,
        Driver.onboarded_at,
        Driver.created_at,
    ]
    column_searchable_list = [Driver.vehicle_number, Driver.vehicle_make]
    column_sortable_list = [Driver.created_at, Driver.verification_status]

    # Filter pending drivers quickly
    column_default_sort = ("created_at", True)

    can_create = False
    can_delete = False
    can_edit = True

    # Custom action: Approve Driver
    @action(
        name="approve_driver",
        label="Approve",
        confirmation_message="Approve this driver and start their cashback eligibility window?",
        add_in_detail=True,
        add_in_list=False,
    )
    async def approve_driver(self, request):
        pk = request.query_params.get("pks")
        async with get_async_session() as db:
            driver = await db.get(Driver, pk)
            driver.verification_status = "approved"
            driver.onboarded_at = datetime.now(timezone.utc)

            # Auto-create wallet
            wallet = Wallet(driver_id=driver.id, balance=Decimal("0.00"))
            db.add(wallet)

            await db.commit()

            # Notify driver
            await notification_service.send_push(
                db=db,
                user_id=str(driver.user_id),
                title="Driver Approved!",
                body="You can now publish rides on GoAlong.",
            )

        return RedirectResponse(request.url_for("admin:detail", identity="driver", pk=pk))


    @action(
        name="reject_driver",
        label="Reject",
        confirmation_message="Reject this driver application?",
        add_in_detail=True,
        add_in_list=False,
    )
    async def reject_driver(self, request):
        pk = request.query_params.get("pks")
        async with get_async_session() as db:
            driver = await db.get(Driver, pk)
            driver.verification_status = "rejected"
            await db.commit()
        return RedirectResponse(request.url_for("admin:detail", identity="driver", pk=pk))
```

### Driver Documents
```python
class DriverDocumentAdmin(ModelView, model=DriverDocument):
    name = "Document"
    name_plural = "Driver Documents"
    icon = "fa-solid fa-file"

    column_list = [
        DriverDocument.id,
        DriverDocument.driver,
        DriverDocument.doc_type,
        DriverDocument.file_url,          # Clickable link to view
        DriverDocument.created_at,
    ]
    can_create = False
    can_delete = False
    can_edit = False     # View only — admin reviews, then approves/rejects driver
```

### Ride Monitoring
```python
class RideAdmin(ModelView, model=Ride):
    name = "Ride"
    name_plural = "Rides"
    icon = "fa-solid fa-route"

    column_list = [
        Ride.id,
        Ride.driver,
        Ride.source_address,
        Ride.dest_address,
        Ride.departure_time,
        Ride.available_seats,
        Ride.per_seat_fare,
        Ride.status,
        Ride.created_at,
    ]
    column_searchable_list = [Ride.source_address, Ride.dest_address]
    column_sortable_list = [Ride.departure_time, Ride.created_at, Ride.per_seat_fare]
    column_default_sort = ("departure_time", True)

    can_create = False
    can_delete = False
    can_edit = False      # Admin is view-only for rides
```

### Booking Overview
```python
class BookingAdmin(ModelView, model=Booking):
    name = "Booking"
    name_plural = "Bookings"
    icon = "fa-solid fa-ticket"

    column_list = [
        Booking.id,
        Booking.ride,
        Booking.passenger,
        Booking.seats_booked,
        Booking.fare,
        Booking.status,
        Booking.booked_at,
    ]
    column_sortable_list = [Booking.booked_at, Booking.status]
    column_default_sort = ("booked_at", True)

    can_create = False
    can_delete = False
    can_edit = False
```

### Wallet Management
```python
class WalletAdmin(ModelView, model=Wallet):
    name = "Wallet"
    name_plural = "Wallets"
    icon = "fa-solid fa-wallet"

    column_list = [
        Wallet.id,
        Wallet.driver,
        Wallet.balance,
        Wallet.updated_at,
    ]
    column_sortable_list = [Wallet.balance, Wallet.updated_at]

    can_create = False
    can_delete = False
    can_edit = False
```

### Wallet Transactions — The Core Admin Workflow
```python
class WalletTransactionAdmin(ModelView, model=WalletTransaction):
    name = "Transaction"
    name_plural = "Wallet Transactions"
    icon = "fa-solid fa-money-bill-transfer"

    column_list = [
        WalletTransaction.id,
        WalletTransaction.wallet,
        WalletTransaction.type,
        WalletTransaction.amount,
        WalletTransaction.status,
        WalletTransaction.upi_id,
        WalletTransaction.toll_proof_url,
        WalletTransaction.admin_note,
        WalletTransaction.created_at,
        WalletTransaction.processed_at,
    ]
    column_searchable_list = [WalletTransaction.type, WalletTransaction.status]
    column_sortable_list = [WalletTransaction.created_at, WalletTransaction.status]
    column_default_sort = ("created_at", True)

    can_create = False
    can_delete = False
    can_edit = True   # Admin can update status, admin_note

    # Custom actions for cashback and withdrawal processing
    @action(
        name="approve_cashback",
        label="Approve Cashback",
        confirmation_message="Approve this cashback request and credit the driver's wallet?",
        add_in_detail=True,
        add_in_list=False,
    )
    async def approve_cashback(self, request):
        pk = request.query_params.get("pks")
        async with get_async_session() as db:
            await wallet_service.admin_approve_cashback(
                db=db,
                txn_id=pk,
                admin_user=request.state.admin_user,
            )
        return RedirectResponse(
            request.url_for("admin:detail", identity="wallet-transaction", pk=pk)
        )

    @action(
        name="reject_cashback",
        label="Reject Cashback",
        confirmation_message="Reject this cashback request?",
        add_in_detail=True,
        add_in_list=False,
    )
    async def reject_cashback(self, request):
        pk = request.query_params.get("pks")
        async with get_async_session() as db:
            txn = await db.get(WalletTransaction, pk)
            txn.status = "rejected"
            txn.admin_note = "Rejected by admin"  # Could capture reason from form
            txn.processed_at = datetime.now(timezone.utc)
            await db.commit()
        return RedirectResponse(
            request.url_for("admin:detail", identity="wallet-transaction", pk=pk)
        )

    @action(
        name="approve_withdrawal",
        label="Approve Withdrawal",
        confirmation_message="Approve this withdrawal? You must manually transfer the amount via UPI after approval.",
        add_in_detail=True,
        add_in_list=False,
    )
    async def approve_withdrawal(self, request):
        pk = request.query_params.get("pks")
        async with get_async_session() as db:
            await wallet_service.admin_approve_withdrawal(
                db=db,
                txn_id=pk,
                admin_user=request.state.admin_user,
            )
        return RedirectResponse(
            request.url_for("admin:detail", identity="wallet-transaction", pk=pk)
        )

    @action(
        name="reject_withdrawal",
        label="Reject Withdrawal",
        confirmation_message="Reject this withdrawal and restore balance?",
        add_in_detail=True,
        add_in_list=False,
    )
    async def reject_withdrawal(self, request):
        pk = request.query_params.get("pks")
        async with get_async_session() as db:
            await wallet_service.admin_reject_withdrawal(
                db=db,
                txn_id=pk,
                admin_user=request.state.admin_user,
                reason="Rejected by admin",
            )
        return RedirectResponse(
            request.url_for("admin:detail", identity="wallet-transaction", pk=pk)
        )
```

### Platform Config
```python
class PlatformConfigAdmin(ModelView, model=PlatformConfig):
    name = "Config"
    name_plural = "Platform Config"
    icon = "fa-solid fa-gear"

    column_list = [
        PlatformConfig.key,
        PlatformConfig.value,
        PlatformConfig.description,
        PlatformConfig.updated_at,
    ]
    column_searchable_list = [PlatformConfig.key]

    can_create = True    # Admin can add new config entries
    can_delete = False   # Prevent accidental deletion
    can_edit = True      # Admin can change values
```

---

## Admin Daily Workflow

```
Morning check:
1. Open /admin
2. Go to Drivers → Filter by verification_status = "pending"
   → Review documents → Approve or Reject
3. Go to Wallet Transactions → Filter by status = "pending"
   → Review cashback requests:
     • Click toll_proof_url to view receipt
     • Verify amount matches receipt
     • Approve or Reject with note
   → Review withdrawal requests:
     • Approve → Then open UPI app → Transfer ₹amount to upi_id → Done
     • Reject if something looks wrong → Balance restored automatically
```

---

## Reporting

Phase 1 does not need fancy charts. SQLAdmin's list views with sorting and filtering give the admin enough visibility. For quick stats, add a simple endpoint:

```python
# routers/admin_stats.py

from fastapi import APIRouter, Depends

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])

@router.get("/stats")
async def get_stats(db: AsyncSession = Depends(get_db)):
    """Quick stats for admin. Called from admin dashboard widget or separate page."""
    total_users = await db.scalar(select(func.count(User.id)))
    total_drivers = await db.scalar(select(func.count(Driver.id)))
    pending_verifications = await db.scalar(
        select(func.count(Driver.id)).where(Driver.verification_status == "pending")
    )
    total_rides = await db.scalar(select(func.count(Ride.id)))
    active_rides = await db.scalar(
        select(func.count(Ride.id)).where(Ride.status == "active")
    )
    total_bookings = await db.scalar(select(func.count(Booking.id)))
    pending_cashbacks = await db.scalar(
        select(func.count(WalletTransaction.id)).where(
            and_(
                WalletTransaction.type == "cashback_request",
                WalletTransaction.status == "pending",
            )
        )
    )
    pending_withdrawals = await db.scalar(
        select(func.count(WalletTransaction.id)).where(
            and_(
                WalletTransaction.type == "withdrawal_request",
                WalletTransaction.status == "pending",
            )
        )
    )
    total_cashback_paid = await db.scalar(
        select(func.coalesce(func.sum(WalletTransaction.amount), 0)).where(
            and_(
                WalletTransaction.type == "cashback_credited",
                WalletTransaction.status == "approved",
            )
        )
    )

    return {
        "users": total_users,
        "drivers": total_drivers,
        "pending_verifications": pending_verifications,
        "rides": total_rides,
        "active_rides": active_rides,
        "bookings": total_bookings,
        "pending_cashbacks": pending_cashbacks,
        "pending_withdrawals": pending_withdrawals,
        "total_cashback_paid": float(total_cashback_paid),
    }
```

---

## Things To Note

1. **SQLAdmin requires `async` engine.** Since GoAlong uses SQLAlchemy 2.0 async, pass the async engine to `Admin()`.

2. **`can_create = False` on most models.** Data is created through the app. Admin is primarily for viewing and processing actions.

3. **Custom actions appear as buttons** on the detail page (when `add_in_detail=True`). The admin clicks "Approve" on a specific driver or transaction — no form needed.

4. **Sessions middleware is required.** SQLAdmin login uses Starlette sessions, which requires `SessionMiddleware` on the FastAPI app.

5. **Admin URL is `/admin`.** Protect it behind VPN or IP allowlist in production. For Phase 1, env-based username/password is sufficient, but don't use weak credentials.

6. **No separate admin API.** The `/api/v1/admin/stats` endpoint is for convenience. All actual admin operations happen through the SQLAdmin UI. If the Flutter app ever needs admin features, that's Phase 2.

7. **Toll proof links.** The `toll_proof_url` column in WalletTransactionAdmin should be clickable. SQLAdmin renders URLs as links by default. The admin clicks it to view the toll receipt image in a new tab (served from Supabase Storage).

8. **SQLAdmin dependencies.** Install: `pip install sqladmin`. That's it. No extra frontend dependencies.
