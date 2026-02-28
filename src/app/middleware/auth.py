# =============================================================================
# middleware/auth.py — Supabase JWT Verification Middleware
# =============================================================================
# See: system-design/01-auth.md §3 "JWT Verification on FastAPI"
# See: system-design/12-security-observability-slo.md §2 for auth security
#
# NOTE: JWT verification is implemented as a FastAPI dependency (get_current_user
# in dependencies.py), NOT as middleware. This file provides helper utilities
# for JWT decoding that the dependency uses.
#
# Supabase issues JWTs signed with HS256 using the project's JWT secret.
# We verify the signature, check expiry, and extract the user's supabase_uid.
#
# TODO: def decode_supabase_jwt(token: str, jwt_secret: str) → dict:
#       """
#       Decode and verify a Supabase JWT.
#
#       Steps:
#       1. Use PyJWT (import jwt) to decode
#       2. Verify signature with jwt_secret (HS256 algorithm)
#       3. Verify expiry (exp claim)
#       4. Verify audience matches Supabase project ("authenticated")
#       5. Extract 'sub' claim → this is the supabase_uid
#       6. Return decoded payload
#
#       Raises:
#       - 401 Unauthorized if token is expired
#       - 401 Unauthorized if signature is invalid
#       - 401 Unauthorized if token is malformed
#       """
#
# TODO: class OAuth2BearerScheme:
#       """
#       Custom OAuth2 scheme that extracts Bearer token from Authorization header.
#       Use FastAPI's OAuth2PasswordBearer or a lightweight custom one.
#       """
#
# Connects with:
#   → app/dependencies.py (get_current_user uses decode_supabase_jwt)
#   → app/config.py (SUPABASE_JWT_SECRET)
#   → app/routers/chat.py (WebSocket auth also calls decode_supabase_jwt with query param)
#
# work by adolf.
