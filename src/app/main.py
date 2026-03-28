from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware

from app.config import settings
from app.db.postgres import engine
from app.db.mongo import connect_mongo, close_mongo
from app.services import ors_service
from app.middleware.logging import TracingMiddleware, configure_logging
from app.middleware.auth import AuthMiddleware
from app.utils.exceptions import AppException, app_exception_handler
from app.admin.views import setup_admin
from app.routers import (
    auth, users, drivers,
    rides, bookings,
    wallet, chat, fare,
)

# ─── Lifespan ─────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    try:
        await connect_mongo()
        print("✅ MongoDB connected")
    except Exception as e:
        print(f"⚠️ MongoDB connection failed: {e}. Chat services will be unavailable.")
    print("✅ GoAlong API started")
    yield
    await close_mongo()
    await ors_service.close_client()
    print("🔴 GoAlong API stopped")

# ─── App ──────────────────────────────────────
app = FastAPI(
    title       = "GoAlong API",
    description = "Intercity ride-sharing platform",
    version     = "1.0.0",
    docs_url    = "/docs",
    redoc_url   = "/redoc",
    lifespan    = lifespan,
)

# ─── Middleware ───────────────────────────────
app.add_middleware(TracingMiddleware)
app.add_middleware(AuthMiddleware)
app.add_middleware(SessionMiddleware, secret_key=settings.SECRET_KEY)
app.add_middleware(
    CORSMiddleware,
    allow_origins     = settings.cors_origins,
    allow_credentials = True,
    allow_methods     = ["*"],
    allow_headers     = ["*"],
)

# ─── Exception Handlers ───────────────────────
app.add_exception_handler(AppException, app_exception_handler)

# ─── Admin Panel ──────────────────────────────
setup_admin(app, engine)

# ─── Routers ──────────────────────────────────
app.include_router(auth.router,     prefix="/api/v1")
app.include_router(users.router,    prefix="/api/v1")
app.include_router(drivers.router,  prefix="/api/v1")
app.include_router(rides.router,    prefix="/api/v1")
app.include_router(bookings.router, prefix="/api/v1")
app.include_router(wallet.router,   prefix="/api/v1")
app.include_router(chat.router,     prefix="/api/v1")
app.include_router(fare.router,     prefix="/api/v1")

# ─── Health Check ─────────────────────────────
@app.get("/health", tags=["Health"])
async def health():
    return {"status": "ok", "env": settings.APP_ENV}


