from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse


# ─── Base Exception ───────────────────────────
class AppException(HTTPException):
    """
    Base exception for all GoAlong custom errors.
    Adds 'code' field to standard FastAPI HTTPException.
    Response shape: {"detail": "...", "code": "..."}
    """
    def __init__(self, status_code: int, detail: str, code: str):
        super().__init__(status_code=status_code, detail=detail)
        self.code = code


# ─── Exception Handler ────────────────────────
async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail, "code": exc.code},
    )


# ─── Auth Errors (401) ────────────────────────
class InvalidTokenError(AppException):
    def __init__(self, detail: str = "Invalid token"):
        super().__init__(401, detail, "INVALID_TOKEN")

class TokenExpiredError(AppException):
    def __init__(self, detail: str = "Token expired"):
        super().__init__(401, detail, "TOKEN_EXPIRED")


# ─── Permission Errors (403) ──────────────────
class ForbiddenError(AppException):
    def __init__(self, detail: str = "Access denied"):
        super().__init__(403, detail, "FORBIDDEN")

class DriverNotApprovedError(AppException):
    def __init__(self, detail: str = "Driver must be approved before creating rides"):
        super().__init__(403, detail, "DRIVER_NOT_APPROVED")


# ─── Not Found Errors (404) ───────────────────
class UserNotFoundError(AppException):
    def __init__(self, detail: str = "User not found"):
        super().__init__(404, detail, "USER_NOT_FOUND")

class RideNotFoundError(AppException):
    def __init__(self, detail: str = "Ride not found"):
        super().__init__(404, detail, "RIDE_NOT_FOUND")

class BookingNotFoundError(AppException):
    def __init__(self, detail: str = "Booking not found"):
        super().__init__(404, detail, "BOOKING_NOT_FOUND")


# ─── Conflict Errors (409) ────────────────────
class DriverAlreadyRegisteredError(AppException):
    def __init__(self, detail: str = "Driver profile already exists"):
        super().__init__(409, detail, "DRIVER_ALREADY_REGISTERED")

class DuplicateBookingError(AppException):
    def __init__(self, detail: str = "You already have a booking for this ride"):
        super().__init__(409, detail, "DUPLICATE_BOOKING")

class AlreadyClaimedError(AppException):
    def __init__(self, detail: str = "Cashback already claimed for this ride"):
        super().__init__(409, detail, "ALREADY_CLAIMED")


# ─── Business Logic Errors (400) ─────────────
class RideNotActiveError(AppException):
    def __init__(self, detail: str = "Ride is not active"):
        super().__init__(400, detail, "RIDE_NOT_ACTIVE")

class SeatsFullError(AppException):
    def __init__(self, detail: str = "No seats available"):
        super().__init__(400, detail, "SEATS_FULL")

class SelfBookingError(AppException):
    def __init__(self, detail: str = "You cannot book your own ride"):
        super().__init__(400, detail, "SELF_BOOKING")

class CancellationWindowClosedError(AppException):
    def __init__(self, detail: str = "Cancellation window has closed"):
        super().__init__(400, detail, "CANCELLATION_WINDOW_CLOSED")

class InsufficientBalanceError(AppException):
    def __init__(self, detail: str = "Insufficient wallet balance"):
        super().__init__(400, detail, "INSUFFICIENT_BALANCE")

class ExceedsMaxWithdrawalError(AppException):
    def __init__(self, detail: str = "Amount exceeds maximum withdrawal limit"):
        super().__init__(400, detail, "EXCEEDS_MAX_WITHDRAWAL")

class BookingNotEligibleError(AppException):
    def __init__(self, detail: str = "Booking not eligible for cashback"):
        super().__init__(400, detail, "BOOKING_NOT_ELIGIBLE")


# ─── External Service Errors (502/503) ────────
class ServiceUnavailableError(AppException):
    def __init__(self, detail: str = "External service unavailable"):
        super().__init__(503, detail, "SERVICE_UNAVAILABLE")

class NoRouteFoundError(AppException):
    def __init__(self, detail: str = "No route found between given coordinates"):
        super().__init__(502, detail, "NO_ROUTE_FOUND")