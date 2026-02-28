# =============================================================================
# main.py — FastAPI Application Entrypoint
# =============================================================================
# See: system-design/00-architecture.md §4 "Project Structure"
# See: system-design/12-security-observability-slo.md for middleware ordering
#
# This file is the single entrypoint. Uvicorn targets this: uvicorn app.main:app
#
# TODO: Initialize FastAPI app instance with metadata (title, version, docs_url)
# TODO: Use the `lifespan` context manager (NOT deprecated @app.on_event):
#       @asynccontextmanager
#       async def lifespan(app: FastAPI):
#           # --- Startup ---
#           engine = create_async_engine(settings.SUPABASE_DB_URL, ...)
#           await connect_mongo()
#           logger.info("GoAlong API started", env=settings.APP_ENV)
#           yield
#           # --- Shutdown ---
#           await dispose_engine()
#           await close_mongo()
#       app = FastAPI(lifespan=lifespan, ...)
#
# TODO: Register custom AppException handler:
#       @app.exception_handler(AppException)
#       async def app_exception_handler(request, exc):
#           return JSONResponse(
#               status_code=exc.status_code,
#               content={"detail": exc.detail, "code": exc.code}
#           )
#
# TODO: Register middleware in correct order:
#       1. TracingMiddleware (outermost — assigns request_id to every request)
#       2. SessionMiddleware (required by SQLAdmin, uses APP_SECRET_KEY)
#       3. CORSMiddleware (allow Flutter app origins from config.CORS_ORIGINS)
#       4. SlowAPI rate limiter (see 12-security-observability-slo.md §3)
# TODO: Include all routers under /api/v1 prefix:
#       - auth_router      → /api/v1/auth
#       - users_router     → /api/v1/users
#       - drivers_router   → /api/v1/drivers
#       - rides_router     → /api/v1/rides
#       - bookings_router  → /api/v1/bookings
#       - fare_router      → /api/v1/fare
#       - chat_router      → /api/v1/chat
#       - wallet_router    → /api/v1/wallet
# TODO: Mount SQLAdmin at /admin:
#       from app.admin.views import setup_admin
#       setup_admin(app, engine)
# TODO: Add /health endpoint (GET, no auth) returning {"status": "ok"}
#       Cloud Run uses this as liveness probe.
# TODO: Configure structured JSON logging via structlog
#       (see 12-security-observability-slo.md §5)
#
# Connects with:
#   → app/config.py (loads all env vars)
#   → app/routers/*.py (all route handlers)
#   → app/db/postgres.py (DB engine lifecycle)
#   → app/db/mongo.py (MongoDB client lifecycle)
#   → app/admin/views.py (SQLAdmin mount)
#   → app/middleware/*.py (middleware classes)
#   → app/utils/exceptions.py (AppException handler)
#
# work by adolf.
