# =============================================================================
# schemas/auth.py — Auth Request/Response Schemas
# =============================================================================
# See: system-design/10-api-contracts.md §2 "Auth Endpoints"
# See: system-design/01-auth.md for the full auth flow
#
# Auth is handled by Supabase (OTP, email). These schemas handle
# the sync endpoint that creates/updates the user row in our DB
# after Supabase authentication, and FCM token registration.
#
# TODO: class AuthSyncRequest(BaseModel):
#       Called after Flutter authenticates with Supabase.
#       - name: str | None
#       - email: str | None
#       - phone: str | None
#       - profile_photo: str | None
#
# TODO: class AuthSyncResponse(BaseModel):
#       - id: UUID
#       - supabase_uid: str
#       - name: str | None
#       - role: str
#       - is_new_user: bool  (True if this was first sync / user creation)
#
# TODO: class FCMTokenRequest(BaseModel):
#       - fcm_token: str = Field(..., min_length=1)
#
# TODO: class FCMTokenResponse(BaseModel):
#       - message: str
#
# Connects with:
#   → app/routers/auth.py (request/response models for POST /auth/sync, POST /auth/fcm-token)
#   → app/services/auth_service.py (processes sync logic)
#
# work by adolf.
