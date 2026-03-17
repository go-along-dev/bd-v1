from sqladmin import Admin, ModelView
from sqladmin.authentication import AuthenticationBackend
from starlette.requests import Request
from fastapi import FastAPI
from sqlalchemy.ext.asyncio import AsyncEngine

from app.models.user import User
from app.models.driver import Driver
from app.models.driver_document import DriverDocument
from app.models.ride import Ride
from app.models.booking import Booking
from app.models.wallet import Wallet
from app.models.wallet_transaction import WalletTransaction
from app.models.platform_config import PlatformConfig
from app.config import settings


# ─── Auth Backend ─────────────────────────────
class AdminAuth(AuthenticationBackend):
    async def login(self, request: Request) -> bool:
        form     = await request.form()
        username = form.get("username")
        password = form.get("password")
        if username == settings.ADMIN_USERNAME and password == settings.ADMIN_PASSWORD:
            request.session.update({"admin_logged_in": True})
            return True
        return False

    async def logout(self, request: Request) -> bool:
        request.session.clear()
        return True

    async def authenticate(self, request: Request) -> bool:
        return request.session.get("admin_logged_in", False)


# ─── User Admin ───────────────────────────────
class UserAdmin(ModelView, model=User):
    name                   = "User"
    name_plural            = "Users"
    icon                   = "fa-solid fa-users"
    column_list            = [User.id, User.name, User.email, User.phone, User.role, User.is_active, User.created_at]
    column_searchable_list = [User.name, User.email, User.phone]
    column_filters         = [User.role, User.is_active]
    can_create             = False
    can_delete             = False


# ─── Driver Admin ─────────────────────────────
class DriverAdmin(ModelView, model=Driver):
    name           = "Driver"
    name_plural    = "Drivers"
    icon           = "fa-solid fa-car"
    column_list    = [
        Driver.id, Driver.vehicle_number, Driver.vehicle_make,
        Driver.vehicle_model, Driver.vehicle_type, Driver.seat_capacity,
        Driver.mileage_kmpl, Driver.verification_status, Driver.created_at,
    ]
    column_filters = [Driver.verification_status, Driver.vehicle_type]
    can_delete     = False
    # To approve/reject: edit the record directly and change verification_status


# ─── Driver Document Admin ────────────────────
class DriverDocumentAdmin(ModelView, model=DriverDocument):
    name        = "Driver Document"
    name_plural = "Driver Documents"
    icon        = "fa-solid fa-file"
    column_list = [
        DriverDocument.id, DriverDocument.driver_id,
        DriverDocument.doc_type, DriverDocument.status,
        DriverDocument.file_url, DriverDocument.created_at,
    ]
    can_create  = False
    can_delete  = False


# ─── Ride Admin ───────────────────────────────
class RideAdmin(ModelView, model=Ride):
    name           = "Ride"
    name_plural    = "Rides"
    icon           = "fa-solid fa-route"
    column_list    = [
        Ride.id, Ride.source_address, Ride.dest_address,
        Ride.source_city, Ride.dest_city, Ride.per_seat_fare,
        Ride.available_seats, Ride.status, Ride.departure_time,
    ]
    column_filters = [Ride.status, Ride.source_city, Ride.dest_city]
    can_create     = False
    can_delete     = False


# ─── Booking Admin ────────────────────────────
class BookingAdmin(ModelView, model=Booking):
    name           = "Booking"
    name_plural    = "Bookings"
    icon           = "fa-solid fa-ticket"
    column_list    = [
        Booking.id, Booking.ride_id, Booking.passenger_id,
        Booking.seats_booked, Booking.fare, Booking.status, Booking.booked_at,
    ]
    column_filters = [Booking.status]
    can_create     = False
    can_delete     = False


# ─── Wallet Admin ─────────────────────────────
class WalletAdmin(ModelView, model=Wallet):
    name        = "Wallet"
    name_plural = "Wallets"
    icon        = "fa-solid fa-wallet"
    column_list = [Wallet.id, Wallet.driver_id, Wallet.balance, Wallet.created_at]
    can_create  = False
    can_delete  = False


# ─── Wallet Transaction Admin ─────────────────
class WalletTransactionAdmin(ModelView, model=WalletTransaction):
    name           = "Transaction"
    name_plural    = "Wallet Transactions"
    icon           = "fa-solid fa-money-bill-transfer"
    column_list    = [
        WalletTransaction.id, WalletTransaction.wallet_id,
        WalletTransaction.type, WalletTransaction.amount,
        WalletTransaction.status, WalletTransaction.ride_id,
        WalletTransaction.upi_id, WalletTransaction.admin_note,
        WalletTransaction.created_at,
    ]
    column_filters = [WalletTransaction.type, WalletTransaction.status]
    can_create     = False
    can_delete     = False
    # To approve/reject: edit the record and change status + admin_note


# ─── Platform Config Admin ────────────────────
class PlatformConfigAdmin(ModelView, model=PlatformConfig):
    name        = "Platform Config"
    name_plural = "Platform Config"
    icon        = "fa-solid fa-gear"
    column_list = [
        PlatformConfig.key, PlatformConfig.value,
        PlatformConfig.description, PlatformConfig.updated_at,
    ]
    can_create  = True
    can_delete  = False


# ─── Setup Admin ──────────────────────────────
def setup_admin(app: FastAPI, engine: AsyncEngine) -> Admin:
    auth_backend = AdminAuth(secret_key=settings.SECRET_KEY)

    admin = Admin(
        app,
        engine,
        authentication_backend=auth_backend,
        title="GoAlong Admin",
        base_url="/admin",
    )

    admin.add_view(UserAdmin)
    admin.add_view(DriverAdmin)
    admin.add_view(DriverDocumentAdmin)
    admin.add_view(RideAdmin)
    admin.add_view(BookingAdmin)
    admin.add_view(WalletAdmin)
    admin.add_view(WalletTransactionAdmin)
    admin.add_view(PlatformConfigAdmin)

    return admin