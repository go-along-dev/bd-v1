# =============================================================================
# config.py — Application Configuration (Pydantic Settings)
# =============================================================================
# See: system-design/00-architecture.md §6 "Environment Variables"
# See: system-design/09-infra.md for Cloud Run / Secret Manager integration
#
# Uses pydantic-settings to load all config from environment variables.
# In production, these come from GCP Secret Manager → Cloud Run env injection.
# In development, loaded from .env file.
#
# TODO: Create Settings class inheriting from pydantic_settings.BaseSettings
# TODO: Define all required fields:
#       - SUPABASE_URL: str
#       - SUPABASE_ANON_KEY: str
#       - SUPABASE_SERVICE_ROLE_KEY: str          (server-side only, never expose)
#       - SUPABASE_DB_URL: str                    (postgresql+asyncpg://...)
#       - SUPABASE_JWT_SECRET: str                (for HS256 JWT verification)
#       - MONGO_URI: str                          (mongodb+srv://...)
#       - OSRM_BASE_URL: str                      (http://osrm-vm-ip:5000)
#       - FCM_CREDENTIALS_JSON: str               (path to firebase-adminsdk.json)
#       - APP_ENV: str = "development"            (development | staging | production)
#       - APP_SECRET_KEY: str                     (used by SessionMiddleware for SQLAdmin)
#       - CORS_ORIGINS: list[str]                 (parse comma-separated string)
#       - ADMIN_USERNAME: str = "admin"           (SQLAdmin login username)
#       - ADMIN_PASSWORD: str                     (SQLAdmin login password)
# TODO: Configure model_config with env_file=".env", case_sensitive=True
# TODO: Create a cached get_settings() function using @lru_cache
#       so settings are loaded once and reused everywhere.
#
# Connects with:
#   → app/main.py (imports get_settings for app init)
#   → app/db/postgres.py (uses SUPABASE_DB_URL)
#   → app/db/mongo.py (uses MONGO_URI)
#   → app/middleware/auth.py (uses SUPABASE_JWT_SECRET)
#   → app/services/osrm_service.py (uses OSRM_BASE_URL)
#   → app/services/notification_service.py (uses FCM_CREDENTIALS_JSON)
#   → app/services/storage_service.py (uses SUPABASE_URL + SUPABASE_SERVICE_ROLE_KEY)
#
# work by adolf.
