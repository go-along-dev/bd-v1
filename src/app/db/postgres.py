# =============================================================================
# db/postgres.py — SQLAlchemy 2.0 Async Engine & Session Factory
# =============================================================================
# See: system-design/00-architecture.md §3 Tech Stack → "ORM: SQLAlchemy 2.0 (async)"
# See: system-design/11-db-schema-ddl.md for the full DDL
# See: system-design/09-infra.md §3 for Cloud Run connection pooling notes
#
# This file manages the async PostgreSQL connection to Supabase.
# Supabase uses standard PostgreSQL — we connect via asyncpg driver.
#
# TODO: Create async engine using create_async_engine()
#       - Connection string from config.SUPABASE_DB_URL
#       - pool_size=5, max_overflow=10 (Cloud Run has max 4 instances,
#         so total pool = 4 * 5 = 20 connections — within Supabase free tier limit of 60)
#       - echo=True only if APP_ENV == "development"
#
# TODO: Create async_session_factory using async_sessionmaker()
#       - class_=AsyncSession
#       - expire_on_commit=False (needed for returning data after commit)
#
# TODO: async def get_engine() → AsyncEngine
#       - Returns the engine singleton (created at startup in main.py)
#
# TODO: async def dispose_engine()
#       - Called on app shutdown to close all connections cleanly
#
# IMPORTANT: Supabase has RLS disabled (see 00-architecture.md §8 note 3).
# We connect using service_role credentials which bypass RLS.
# All authorization is handled in app/dependencies.py (get_current_user, require_role)
#
# Connects with:
#   → app/config.py (SUPABASE_DB_URL)
#   → app/main.py (startup/shutdown lifecycle)
#   → app/dependencies.py (get_db yields sessions from this factory)
#   → app/models/*.py (all models use the Base from db/base.py)
#   → alembic/env.py (Alembic uses the same engine URL for migrations)
#
# work by adolf.
