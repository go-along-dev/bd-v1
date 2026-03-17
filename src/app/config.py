from pathlib import Path
from pydantic_settings import BaseSettings
from typing import List
import json

_env_file = Path(__file__).resolve().parent.parent.parent / ".env"


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

    # ─── OSRM ─────────────────────────────────
    OSRM_BASE_URL: str = "http://localhost:5000"

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

    @property
    def cors_origins(self) -> List[str]:
        return json.loads(self.BACKEND_CORS_ORIGINS)

    @property
    def is_production(self) -> bool:
        return self.APP_ENV == "production"

    model_config = {
        "env_file": str(_env_file),
        "extra": "ignore"
    }


settings = Settings()