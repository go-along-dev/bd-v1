from pydantic import BaseModel, Field, EmailStr
from uuid import UUID
from datetime import datetime


# ─── User Response ────────────────────────────
class UserResponse(BaseModel):
    id:            UUID
    name:          str | None
    email:         str | None
    phone:         str | None
    profile_photo: str | None
    role:          str
    is_active:     bool
    created_at:    datetime

    model_config = {"from_attributes": True}


# ─── Update Request ───────────────────────────
class UserUpdateRequest(BaseModel):
    name:          str | None      = Field(None, max_length=100)
    email:         EmailStr | None = None
    profile_photo: str | None      = None
    # Phone NOT updatable — managed by Supabase Auth