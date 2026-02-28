# =============================================================================
# middleware/logging.py — Request/Response Logging & Tracing Middleware
# =============================================================================
# See: system-design/12-security-observability-slo.md §5 "Structured Logging"
# See: system-design/12-security-observability-slo.md §6 "Distributed Tracing"
#
# Structured JSON logging for Cloud Run → Cloud Logging integration.
#
# TODO: class TracingMiddleware(BaseHTTPMiddleware):
#       """
#       Outermost middleware. Runs on every request.
#
#       On request:
#       1. Generate request_id (UUID4) or read from X-Request-ID header
#       2. Attach to request.state.request_id
#       3. Start timer
#
#       On response:
#       4. Calculate duration_ms
#       5. Log structured JSON:
#          {
#              "request_id": "...",
#              "method": "GET",
#              "path": "/api/v1/rides",
#              "status_code": 200,
#              "duration_ms": 45,
#              "user_id": "..." (if available from request.state),
#              "timestamp": "ISO8601"
#          }
#       6. Add X-Request-ID to response headers
#
#       GCP Cloud Logging picks up stdout JSON automatically.
#       """
#
# TODO: Configure Python logging:
#       - Use structlog or stdlib logging with JSON formatter
#       - Log level from config: DEBUG in development, INFO in production
#       - Suppress noisy loggers (uvicorn.access, sqlalchemy.engine)
#
# Connects with:
#   → app/main.py (add as first middleware)
#   → app/config.py (APP_ENV determines log level)
#   → All services (import logger and use structured logging)
#
# work by adolf.
