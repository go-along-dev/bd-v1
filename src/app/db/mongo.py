# =============================================================================
# db/mongo.py — Motor Async MongoDB Client
# =============================================================================
# See: system-design/06-chat.md for why MongoDB is used for chat
# See: system-design/00-architecture.md §8 note 6 — "MongoDB is ONLY for chat"
#
# Motor is the async Python driver for MongoDB.
# We connect to MongoDB Atlas (M0 free tier) for chat_messages collection ONLY.
#
# TODO: Create global references:
#       - mongo_client: AsyncIOMotorClient = None
#       - mongo_db: AsyncIOMotorDatabase = None
#
# TODO: async def connect_mongo()
#       - Create AsyncIOMotorClient from config.MONGO_URI
#       - Select database "goalong"
#       - Verify connection with a ping
#       - Called from main.py startup event
#
# TODO: async def close_mongo()
#       - Close the client connection
#       - Called from main.py shutdown event
#
# TODO: async def get_mongo_db() → AsyncIOMotorDatabase
#       - Returns mongo_db reference for use in dependencies.py
#
# TODO: Ensure TTL index on chat_messages collection:
#       - sent_at field with expireAfterSeconds = 7776000 (90 days)
#       - This auto-deletes old messages to stay within M0 512MB limit
#       - Create index in connect_mongo() using create_index()
#       - See: system-design/11-db-schema-ddl.md §11 "MongoDB: chat_messages"
#
# IMPORTANT: MongoDB is only used for the chat_messages collection.
# Do NOT store any other data here. Everything else is PostgreSQL.
#
# Connects with:
#   → app/config.py (MONGO_URI)
#   → app/main.py (startup/shutdown lifecycle)
#   → app/dependencies.py (get_mongo returns this db)
#   → app/services/chat_service.py (reads/writes chat_messages)
#
# work by adolf.
