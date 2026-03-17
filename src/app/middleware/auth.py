from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
import jwt

from app.config import settings

# ─── Routes that don't need auth ──────────────
PUBLIC_ROUTES = {
    "/health",
    "/docs",
    "/redoc",
    "/openapi.json",
}


class AuthMiddleware(BaseHTTPMiddleware):
    """
    Optional global middleware for logging/tracing.
    Actual JWT verification is handled in dependencies.py
    via get_current_user — this middleware is lightweight.
    """

    async def dispatch(self, request: Request, call_next):
        # Allow public routes through
        if request.url.path in PUBLIC_ROUTES:
            return await call_next(request)

        # Allow admin panel through (has its own auth)
        if request.url.path.startswith("/admin"):
            return await call_next(request)

        # All other routes — pass through
        # JWT verification happens in get_current_user dependency
        response = await call_next(request)
        return response


def decode_supabase_jwt(token: str) -> dict:
    """
    Decode and verify a Supabase JWT.
    Raises HTTPException on failure.
    Used directly in dependencies.py
    """
    try:
        payload = jwt.decode(
            token,
            settings.SUPABASE_JWT_SECRET,
            algorithms=["HS256"],
            audience="authenticated",
            leeway=30,
        )
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        )