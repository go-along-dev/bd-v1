from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from app.config import settings

# ─── Module-level client ──────────────────────
_client: AsyncIOMotorClient | None = None


def get_mongo_client() -> AsyncIOMotorClient:
    global _client
    if _client is None:
        _client = AsyncIOMotorClient(settings.MONGODB_URL)
    return _client


def get_mongo_db() -> AsyncIOMotorDatabase:
    return get_mongo_client()[settings.MONGODB_DB_NAME]


async def connect_mongo():
    """Call this on app startup."""
    client = get_mongo_client()
    # Ping to verify connection
    await client.admin.command("ping")
    print("✅ MongoDB connected")


async def close_mongo():
    """Call this on app shutdown."""
    global _client
    if _client:
        _client.close()
        _client = None
        print("🔴 MongoDB disconnected")