# =============================================================================
# dependencies.py — Shared FastAPI Dependencies
# =============================================================================
# See: system-design/01-auth.md for JWT verification flow
# See: system-design/00-architecture.md §8 "Things To Note" — RLS is OFF,
#      all access control is handled here in FastAPI.
#
# FastAPI Depends() functions used across multiple routers.
#
# TODO: get_db() → AsyncGenerator[AsyncSession, None]
#       - Yields an async SQLAlchemy session from the session factory (db/postgres.py)
#       - Must use `async with` and yield pattern for proper cleanup
#       - Every router endpoint that touches PostgreSQL depends on this
#
# TODO: get_mongo() → AsyncIOMotorDatabase
#       - Returns the Motor database instance from db/mongo.py
#       - Used only by chat endpoints
#
# TODO: get_current_user(token: str = Depends(oauth2_scheme), db = Depends(get_db)) → User
#       - Extracts Bearer token from Authorization header
#       - Verifies JWT signature using Supabase JWT secret (from config)
#       - Decodes payload, extracts supabase_uid from 'sub' claim
#       - Queries users table by supabase_uid
#       - Returns User ORM object (or raises 401 if invalid/expired)
#       - This is THE authentication gate for all protected endpoints
#
# TODO: require_role(allowed_roles: list[str]) → Callable
#       - Returns a dependency that checks current_user.role against allowed_roles
#       - Raises 403 Forbidden if role not in list
#       - Usage: Depends(require_role(["driver", "admin"]))
#
# TODO: get_pagination(page: int = Query(1, ge=1), per_page: int = Query(20, ge=1, le=100)) → dict
#       - Returns {"offset": (page - 1) * per_page, "limit": per_page}
#       - Used by all list endpoints via Depends(get_pagination)
#       - NOTE: No separate PaginationParams schema needed — FastAPI Query() handles validation
#
# Connects with:
#   → app/db/postgres.py (get_db uses async_session_factory)
#   → app/db/mongo.py (get_mongo uses global db reference)
#   → app/config.py (JWT secret for token verification)
#   → app/models/user.py (User model for DB lookup)
#   → app/routers/*.py (every router imports these deps)
#
# work by adolf.
