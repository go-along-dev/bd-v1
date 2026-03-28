from pathlib import Path
from pydantic_settings import BaseSettings
from typing import List
import json

# Locate the .env file (Works for both local and Docker)
_env_file = Path(__file__).resolve().parent.parent / ".env"

class Settings(BaseSettings):
    # ─── App ──────────────────────────────────
    APP_ENV: str = "development"
    SECRET_KEY: str
    BACKEND_CORS_ORIGINS: str = '["http://localhost:8000"]'

    # ─── PostgreSQL ───────────────────────────
    DATABASE_URL: str

    # ─── MongoDB ──────────────────────────────
    MONGODB_URL: str
    MONGODB_DB_NAME: str = "goalong_chat"

    # ─── Supabase ─────────────────────────────
    SUPABASE_URL: str
    SUPABASE_ANON_KEY: str
    SUPABASE_SERVICE_ROLE_KEY: str
    SUPABASE_JWT_SECRET: str

    # ─── OpenRouteService ─────────────────────
    ORS_API_KEY: str = ""

    # ─── FCM ──────────────────────────────────
    FCM_SERVER_KEY: str = ""

    # ─── Fare Engine ──────────────────────────
    FUEL_PRICE_PER_LITRE: float = 103.0
    DEFAULT_MILEAGE_KM_PER_LITRE: float = 15.0
    PLATFORM_MARGIN_PERCENT: float = 10.0

    # ─── Referral ─────────────────────────────
    REFERRAL_REWARD_AMOUNT: float = 50.0

    # ─── Toll Detection ───────────────────────
    TOLL_DETECTION_RADIUS_METERS: float = 100.0

    # ─── Admin Panel ──────────────────────────
    ADMIN_USERNAME: str = "admin"
    ADMIN_PASSWORD: str = "goalong_admin_2024"

    # ─── Razorpay ─────────────────────────────
    RAZORPAY_KEY_ID: str = ""
    RAZORPAY_KEY_SECRET: str = ""
    RAZORPAY_WEBHOOK_SECRET: str = ""

    @property
    def is_production(self) -> bool:
        return self.APP_ENV == "production"

    @property
    def cors_origins(self) -> List[str]:
        if self.is_production:
            return ["*"]
        try:
            return json.loads(self.BACKEND_CORS_ORIGINS)
        except json.JSONDecodeError:
            return ["http://localhost:8000"]

    # This MUST be inside the Settings class
    model_config = {
        "env_file": str(_env_file),
        "extra": "ignore"
    }

# Initialize the settings object
settings = Settings()