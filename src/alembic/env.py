# =============================================================================
# alembic/env.py — Alembic Migration Environment
# =============================================================================
# See: system-design/11-db-schema-ddl.md §16 "Migration Checklist"
# See: system-design/00-architecture.md §8 note 5 — "Alembic manages schema, not Supabase Dashboard"
#
# Alembic connects to the same Supabase PostgreSQL as the app.
# Auto-generates migrations by comparing models to actual DB schema.
#
# TODO: Import Base.metadata from app.db.base
#       (Ensure all models are imported in app/models/__init__.py so Alembic discovers them)
#
# TODO: Configure target_metadata = Base.metadata
#
# TODO: def run_migrations_offline():
#       """Generate SQL without connecting to DB. For review before applying."""
#
# TODO: async def run_migrations_online():
#       """Connect to DB and apply migrations."""
#       - Use config.SUPABASE_DB_URL (from alembic.ini or env var)
#       - Must use async engine: create_async_engine + run_sync
#
# TODO: First migration should:
#       1. Create all 8 tables (copy DDL from 11-db-schema-ddl.md)
#       2. Create pgcrypto extension
#       3. Create auto-update trigger for updated_at columns
#       4. Seed platform_config with initial values
#
# Commands:
#   alembic revision --autogenerate -m "initial schema"
#   alembic upgrade head
#
# Connects with:
#   → app/db/base.py (Base.metadata)
#   → app/models/*.py (all models must be imported for autogenerate)
#   → app/config.py (SUPABASE_DB_URL)
#   → alembic.ini (points to this env.py)
#
# work by adolf.
