# =============================================================================
# routers/users.py — User Profile Endpoints
# =============================================================================
# See: system-design/10-api-contracts.md §3 "User Endpoints"
# See: system-design/02-user-driver.md §1 "User Profile"
#
# Prefix: /api/v1/users
#
# TODO: GET /users/me
#       - Requires: Bearer token
#       - Logic: Return current_user from dependency (already fetched from DB)
#       - Response: UserResponse
#
# TODO: PUT /users/me
#       - Requires: Bearer token
#       - Request body: UserUpdateRequest (partial update — only provided fields)
#       - Logic: Call user_service.update_profile()
#       - Response: UserResponse
#       - Note: phone cannot be changed here (managed by Supabase Auth)
#
# TODO: GET /users/{user_id}  (public profile — limited fields)
#       - Requires: Bearer token
#       - Logic: Return name, profile_photo, role, created_at only
#       - Response: UserResponse (subset)
#       - Used by: passenger viewing driver profile, driver viewing passenger
#
# Connects with:
#   → app/schemas/user.py (UserResponse, UserUpdateRequest)
#   → app/services/user_service.py (update_profile, get_user_by_id)
#   → app/dependencies.py (get_current_user, get_db)
#
# work by adolf.
