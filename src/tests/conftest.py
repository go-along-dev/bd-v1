# =============================================================================
# tests/conftest.py — Pytest Fixtures & Test Configuration
# =============================================================================
# See: system-design/12-security-observability-slo.md §8 "Testing Standards"
#
# Shared fixtures for all test modules.
# NOTE: pyproject.toml should have: [tool.pytest.ini_options] asyncio_mode = "auto"
#
# TODO: @pytest.fixture(scope="session")
#       def event_loop():
#           """Create a shared event loop for async tests."""
#
# TODO: @pytest.fixture
#       async def db_session():
#           """
#           Provide a test database session.
#           Option A: Use a separate test database on Supabase
#           Option B: Use SQLite async for unit tests (faster, no external deps)
#           Option C: Use testcontainers-python with PostgreSQL (most accurate)
#           Each test runs in a transaction that rolls back after.
#           """
#
# TODO: @pytest.fixture
#       async def client(db_session):
#           """
#           httpx.AsyncClient pointed at the FastAPI test app.
#           Override get_db dependency to use test db_session.
#           Override get_current_user dependency with a mock user.
#           """
#
# TODO: @pytest.fixture
#       def mock_user():
#           """Return a fake User object for authenticated test requests."""
#
# TODO: @pytest.fixture
#       def mock_driver_user():
#           """Return a fake User with role='driver' and approved driver record."""
#
# TODO: @pytest.fixture
#       async def mongo_db():
#           """
#           Test MongoDB instance.
#           Use mongomock or a test database on Atlas.
#           """
#
# Connects with:
#   → app/main.py (test client wraps the FastAPI app)
#   → app/dependencies.py (override get_db, get_current_user for tests)
#   → app/db/postgres.py (test DB engine)
#   → app/db/mongo.py (test MongoDB)
#
# work by adolf.
