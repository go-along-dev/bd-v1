# =============================================================================
# db/base.py — SQLAlchemy Declarative Base
# =============================================================================
# See: system-design/11-db-schema-ddl.md §1 "Schema Conventions"
#
# Single source of truth for the ORM base class.
# All models in app/models/ inherit from this Base.
#
# TODO: Create DeclarativeBase subclass (SQLAlchemy 2.0 style)
# TODO: Add common columns as a mixin or in the base:
#       - id: UUID primary key with server_default=gen_random_uuid()
#       - created_at: TIMESTAMPTZ with server_default=now()
#       - updated_at: TIMESTAMPTZ with server_default=now(), onupdate=now()
# TODO: The mixin approach is preferred — create a TimestampMixin class
#       that provides created_at and updated_at, then mix into each model.
#
# Convention: Table names are plural, snake_case (e.g., users, rides, bookings)
# Convention: All PKs are UUID, never auto-increment integers
# Convention: Money is Numeric(10,2), coordinates are Numeric(10,7)
# Convention: No Postgres ENUMs — use VARCHAR with CheckConstraint instead
#
# Connects with:
#   → app/models/*.py (every model imports Base from here)
#   → alembic/env.py (imports Base.metadata for migration autogeneration)
#   → app/db/postgres.py (engine that these models map onto)
#
# work by adolf.
