# =============================================================================
# schemas/user.py — User Request/Response Schemas
# =============================================================================
# See: system-design/10-api-contracts.md §3 "User Endpoints"
# See: system-design/02-user-driver.md §1 "User Profile"
#
# TODO: class UserResponse(BaseModel):
#       - id: UUID
#       - name: str | None
#       - email: str | None
#       - phone: str | None
#       - profile_photo: str | None
#       - role: str
#       - is_active: bool
#       - created_at: datetime
#       model_config: from_attributes = True (so it works with ORM objects)
#
# TODO: class UserUpdateRequest(BaseModel):
#       All optional — only provided fields are updated.
#       - name: str | None = Field(None, max_length=100)
#       - email: EmailStr | None = None
#       - profile_photo: str | None = None
#
# Connects with:
#   → app/routers/users.py (GET /users/me, PUT /users/me)
#   → app/services/user_service.py (profile CRUD)
#
# work by adolf.
