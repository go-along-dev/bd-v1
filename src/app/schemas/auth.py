from pydantic import BaseModel, Field
from uuid import UUID


# ─── Sync Request ─────────────────────────────
class AuthSyncRequest(BaseModel):
    name:          str | None = Field(None, alias="name")
    email:         str | None = None
    phone:         str | None = Field(None, alias="phone")
    role:          str | None = "passenger"
    profile_photo: str | None = None


# ─── Sync Response ────────────────────────────
class AuthSyncResponse(BaseModel):
    id:           UUID
    supabase_uid: str
    name:         str | None
    role:         str
    is_new_user:  bool

    model_config = {"from_attributes": True}


# ─── FCM Token Request ────────────────────────
class FCMTokenRequest(BaseModel):
    fcm_token: str = Field(..., min_length=1)


# ─── FCM Token Response ───────────────────────
class FCMTokenResponse(BaseModel):
    message: str
