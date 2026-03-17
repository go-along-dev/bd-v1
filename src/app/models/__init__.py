from app.db.postgres import Base  # noqa: F401 — ensures Base is shared

from app.models.user import User
from app.models.driver import Driver
from app.models.driver_document import DriverDocument
from app.models.ride import Ride
from app.models.booking import Booking
from app.models.wallet import Wallet
from app.models.wallet_transaction import WalletTransaction
from app.models.platform_config import PlatformConfig

__all__ = [
    "Base",
    "User",
    "Driver",
    "DriverDocument",
    "Ride",
    "Booking",
    "Wallet",
    "WalletTransaction",
    "PlatformConfig",
]