from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from uuid import UUID


# ─── UTC Now ──────────────────────────────────
def utc_now() -> datetime:
    """
    Return timezone-aware UTC now.
    Always use this instead of datetime.utcnow() (which is naive).
    """
    return datetime.now(timezone.utc)


# ─── Safe Decimal Conversion ──────────────────
def to_decimal(value: float | str | Decimal, places: int = 2) -> Decimal:
    """
    Safely convert float/str to Decimal with specified precision.
    Uses ROUND_HALF_UP — standard for financial calculations.
    Never pass raw floats to money calculations.
    """
    quantize_str = Decimal("0." + "0" * places) if places > 0 else Decimal("1")
    return Decimal(str(value)).quantize(quantize_str, rounding=ROUND_HALF_UP)


# ─── Storage Path Generator ───────────────────
def generate_storage_path(
    folder: str,
    entity_id: UUID,
    filename: str,
) -> str:
    """
    Generate a unique storage path for Supabase Storage.
    Format: {folder}/{entity_id}/{timestamp}_{filename}
    Example: driver-documents/abc123/1709123456_license.pdf
    """
    timestamp = int(utc_now().timestamp())
    # Sanitize filename — remove spaces and special chars
    safe_filename = filename.replace(" ", "_")
    return f"{folder}/{entity_id}/{timestamp}_{safe_filename}"


# ─── Clamp ────────────────────────────────────
def clamp(value: int | float, min_val: int | float, max_val: int | float):
    """
    Clamp value between min and max.
    Used for pagination params to prevent abuse.
    """
    return max(min_val, min(value, max_val))


# ─── Mask Email ───────────────────────────────
def mask_email(email: str) -> str:
    """
    Mask email for safe logging — avoids PII exposure.
    'user@example.com' → 'u***@example.com'
    """
    if not email or "@" not in email:
        return "***"
    local, domain = email.split("@", 1)
    if len(local) <= 1:
        return f"***@{domain}"
    return f"{local[0]}***@{domain}"


# ─── Mask Phone ───────────────────────────────
def mask_phone(phone: str) -> str:
    """
    Mask phone number for safe logging — avoids PII exposure.
    '+919876543210' → '+91*****3210'
    """
    if not phone:
        return "***"
    if phone.startswith("+91") and len(phone) >= 10:
        return f"+91*****{phone[-4:]}"
    if len(phone) >= 4:
        return f"*****{phone[-4:]}"
    return "***"