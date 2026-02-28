# =============================================================================
# utils/helpers.py — General Utility Functions
# =============================================================================
#
# Small utility functions used across the codebase.
#
# TODO: def utc_now() → datetime:
#       """Return timezone-aware UTC now. Use this instead of datetime.utcnow()."""
#
# TODO: def to_decimal(value: float | str, places: int = 2) → Decimal:
#       """Safely convert to Decimal with specified decimal places. Uses ROUND_HALF_UP."""
#
# TODO: def generate_storage_path(bucket: str, entity_id: UUID, filename: str) → str:
#       """Generate a unique storage path: {bucket}/{entity_id}/{timestamp}_{filename}"""
#
# TODO: def clamp(value, min_val, max_val):
#       """Clamp a value between min and max. Used for pagination params."""
#
# TODO: def mask_email(email: str) → str:
#       """Mask email for logging: 'user@example.com' → 'u***@example.com' """
#       Used in structured logs to avoid PII exposure.
#       See: system-design/12-security-observability-slo.md §4 "PII Handling"
#
# TODO: def mask_phone(phone: str) → str:
#       """Mask phone for logging: '+919876543210' → '+91*****3210' """
#
# Connects with:
#   → app/services/fare_engine.py (to_decimal for money calculations)
#   → app/services/storage_service.py (generate_storage_path)
#   → app/middleware/logging.py (mask_email, mask_phone for PII redaction)
#   → app/dependencies.py (clamp for pagination)
#
# work by adolf.
