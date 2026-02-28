# =============================================================================
# utils/exceptions.py — Custom HTTP Exceptions
# =============================================================================
# See: system-design/10-api-contracts.md §12 "Error Code Registry" for all 34 error codes
# See: system-design/12-security-observability-slo.md §1 for error handling standards
#
# All custom exceptions follow the standard error response shape:
#   {"detail": "Human-readable message", "code": "MACHINE_READABLE_CODE"}
#
# TODO: class AppException(HTTPException):
#       """
#       Base exception for all custom errors.
#       Adds 'code' field to the standard FastAPI HTTPException.
#       """
#       def __init__(self, status_code: int, detail: str, code: str):
#           super().__init__(status_code=status_code, detail=detail)
#           self.code = code
#
# TODO: Register a custom exception handler in main.py that catches AppException
#       and returns {"detail": exc.detail, "code": exc.code} as JSON.
#
# TODO: Define domain-specific exceptions:
#
#   # Auth errors (401)
#   class InvalidTokenError(AppException):     code = "INVALID_TOKEN"
#   class TokenExpiredError(AppException):      code = "TOKEN_EXPIRED"
#
#   # Permission errors (403)
#   class ForbiddenError(AppException):         code = "FORBIDDEN"
#   class DriverNotApprovedError(AppException): code = "DRIVER_NOT_APPROVED"
#
#   # Not found errors (404)
#   class UserNotFoundError(AppException):      code = "USER_NOT_FOUND"
#   class RideNotFoundError(AppException):      code = "RIDE_NOT_FOUND"
#   class BookingNotFoundError(AppException):   code = "BOOKING_NOT_FOUND"
#
#   # Conflict/business rule errors (409)
#   class DriverAlreadyRegisteredError(AppException): code = "DRIVER_ALREADY_REGISTERED"
#   class DuplicateBookingError(AppException):  code = "DUPLICATE_BOOKING"
#   class AlreadyClaimedError(AppException):    code = "ALREADY_CLAIMED"
#
#   # Business logic errors (400)
#   class RideNotActiveError(AppException):     code = "RIDE_NOT_ACTIVE"
#   class SeatsFullError(AppException):         code = "SEATS_FULL"
#   class SelfBookingError(AppException):       code = "SELF_BOOKING"
#   class CancellationWindowClosedError(AppException): code = "CANCELLATION_WINDOW_CLOSED"
#   class InsufficientBalanceError(AppException): code = "INSUFFICIENT_BALANCE"
#   class ExceedsMaxWithdrawalError(AppException): code = "EXCEEDS_MAX_WITHDRAWAL"
#   class BookingNotEligibleError(AppException): code = "BOOKING_NOT_ELIGIBLE"
#
#   # External service errors (502/503)
#   class ServiceUnavailableError(AppException): code = "SERVICE_UNAVAILABLE"
#   class NoRouteFoundError(AppException):       code = "NO_ROUTE_FOUND"
#
# Connects with:
#   → app/main.py (register custom exception handler)
#   → app/services/*.py (all services raise these exceptions)
#   → app/dependencies.py (get_current_user raises auth exceptions)
#   → app/schemas/common.py (ErrorResponse mirrors the shape)
#
# work by adolf.
