# Module 1: Authentication

## Overview

Authentication is handled by **Supabase Auth** — GoAlong does NOT implement custom auth logic. Supabase manages OTP delivery, token generation, session management, and user creation. FastAPI's role is to **verify the Supabase JWT** on every request and map the Supabase user to the application's internal user record.

---

## How It Works

```
┌──────────────┐         ┌──────────────┐         ┌──────────────┐
│  Flutter App │         │   Supabase   │         │   FastAPI    │
│              │         │   Auth       │         │   Backend    │
└──────┬───────┘         └──────┬───────┘         └──────┬───────┘
       │                        │                        │
       │  1. signInWithOtp()    │                        │
       │───────────────────────►│                        │
       │                        │── Send OTP via SMS     │
       │  2. OTP sent           │                        │
       │◄───────────────────────│                        │
       │                        │                        │
       │  3. verifyOTP()        │                        │
       │───────────────────────►│                        │
       │                        │── Verify, create user  │
       │  4. Session (JWT +     │                        │
       │     refresh token)     │                        │
       │◄───────────────────────│                        │
       │                        │                        │
       │  5. GET /api/v1/users/me                        │
       │  Authorization: Bearer <jwt>                    │
       │────────────────────────────────────────────────►│
       │                        │       Verify JWT using │
       │                        │       Supabase JWT     │
       │                        │       secret (HS256)   │
       │                        │                        │
       │                        │   6. If first login:   │
       │                        │      Create user row   │
       │                        │      in users table    │
       │  7. User profile       │                        │
       │◄────────────────────────────────────────────────│
```

---

## Supabase Auth Configuration

### In Supabase Dashboard → Authentication → Settings:

| Setting                    | Value                                    |
|----------------------------|------------------------------------------|
| Enable Phone Auth          | ✅ ON                                    |
| SMS Provider               | Twilio (or Supabase built-in for dev)    |
| Enable Email Auth          | ✅ ON                                    |
| Enable Email Confirmations | ✅ ON                                    |
| JWT Expiry                 | 3600 seconds (1 hour)                    |
| Refresh Token Rotation     | ✅ ON                                    |
| OTP Expiry                 | 60 seconds                               |

### Things To Note:
- Supabase's **free tier supports 50,000 monthly active users** — more than enough for MVP
- Phone auth on free tier uses Supabase's built-in SMS (limited). For production, configure **Twilio** as the SMS provider
- Supabase auto-creates a user in its `auth.users` table. Your application's `public.users` table is separate — linked by `supabase_uid`

---

## Flutter Side Implementation

### Package
```yaml
# pubspec.yaml
dependencies:
  supabase_flutter: ^2.0.0
```

### Initialization
```dart
// main.dart
import 'package:supabase_flutter/supabase_flutter.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();

  await Supabase.initialize(
    url: 'https://xxxxx.supabase.co',
    anonKey: 'eyJ...',
  );

  runApp(const GoAlongApp());
}

final supabase = Supabase.instance.client;
```

### Phone OTP Login
```dart
// auth_repository.dart

class AuthRepository {
  final SupabaseClient _client = Supabase.instance.client;

  /// Step 1: Send OTP to phone number
  Future<void> sendOtp(String phone) async {
    await _client.auth.signInWithOtp(
      phone: phone,     // Format: +91XXXXXXXXXX
    );
  }

  /// Step 2: Verify OTP
  Future<AuthResponse> verifyOtp(String phone, String otp) async {
    final response = await _client.auth.verifyOTP(
      phone: phone,
      token: otp,
      type: OtpType.sms,
    );
    return response;
  }

  /// Get current session (JWT)
  Session? get currentSession => _client.auth.currentSession;

  /// Get current access token (to send to FastAPI)
  String? get accessToken => _client.auth.currentSession?.accessToken;

  /// Logout
  Future<void> signOut() async {
    await _client.auth.signOut();
  }

  /// Listen to auth state changes (auto-refresh handled by SDK)
  Stream<AuthState> get authStateChanges => _client.auth.onAuthStateChange;
}
```

### Dio Interceptor — Attach JWT to all FastAPI calls
```dart
// api_client.dart

class ApiClient {
  late final Dio dio;

  ApiClient() {
    dio = Dio(BaseOptions(
      baseUrl: 'https://your-cloud-run-url.run.app/api/v1',
      connectTimeout: const Duration(seconds: 10),
      receiveTimeout: const Duration(seconds: 10),
    ));

    dio.interceptors.add(InterceptorsWrapper(
      onRequest: (options, handler) {
        // Attach Supabase JWT to every request
        final token = Supabase.instance.client.auth.currentSession?.accessToken;
        if (token != null) {
          options.headers['Authorization'] = 'Bearer $token';
        }
        handler.next(options);
      },
      onError: (error, handler) async {
        if (error.response?.statusCode == 401) {
          // Token expired — Supabase SDK auto-refreshes
          // Retry the request with new token
          final session = await Supabase.instance.client.auth.refreshSession();
          if (session.session != null) {
            error.requestOptions.headers['Authorization'] =
                'Bearer ${session.session!.accessToken}';
            final retryResponse = await dio.fetch(error.requestOptions);
            handler.resolve(retryResponse);
            return;
          }
        }
        handler.next(error);
      },
    ));
  }
}
```

### Things To Note (Flutter):
1. **Never store tokens manually.** `supabase_flutter` handles token storage in secure storage automatically.
2. **Token refresh is automatic.** The SDK refreshes the JWT before it expires. The Dio interceptor above is a safety net for edge cases.
3. **Phone format must include country code.** Always `+91XXXXXXXXXX` for India.
4. **Listen to `onAuthStateChange`** to handle session expiry and auto-redirect to login screen.

---

## FastAPI Side Implementation

### JWT Verification Middleware

FastAPI does NOT issue tokens. It only **verifies** the Supabase JWT.

```python
# middleware/auth.py

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    Verify the Supabase JWT and return the application user.
    Creates the user row on first login.
    """
    token = credentials.credentials

    try:
        # Verify and decode the JWT using Supabase JWT secret (HS256)
        payload = jwt.decode(
            token,
            settings.SUPABASE_JWT_SECRET,
            algorithms=["HS256"],
            audience="authenticated",
            leeway=30,  # 30s clock skew tolerance
        )
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    supabase_uid = payload.get("sub")  # Supabase user ID
    if not supabase_uid:
        raise HTTPException(status_code=401, detail="Invalid token payload")

    # Find or create the application user
    user = await user_service.get_or_create_by_supabase_uid(
        db=db,
        supabase_uid=supabase_uid,
        phone=payload.get("phone"),
        email=payload.get("email"),
    )

    return user
```

### User Auto-Creation on First Login

```python
# services/auth_service.py

async def get_or_create_by_supabase_uid(
    db: AsyncSession,
    supabase_uid: str,
    phone: str | None = None,
    email: str | None = None,
) -> User:
    """
    Look up user by Supabase UID.
    If not found, create a new user row (first login).
    """
    result = await db.execute(
        select(User).where(User.supabase_uid == supabase_uid)
    )
    user = result.scalar_one_or_none()

    if user is None:
        user = User(
            supabase_uid=supabase_uid,
            phone=phone,
            email=email,
            role="passenger",       # Default role
            is_active=True,         # Active by default, admin can deactivate
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)

    return user
```

### Using in Routes

```python
# routers/users.py

from app.dependencies import get_current_user
from app.models.user import User

@router.get("/me")
async def get_profile(current_user: User = Depends(get_current_user)):
    return {"data": UserResponse.model_validate(current_user)}
```

### Things To Note (FastAPI):
1. **HS256 with JWT secret.** Supabase defaults to HS256 symmetric signing. Use the `SUPABASE_JWT_SECRET` from your Supabase project settings to verify tokens. No JWKS/RS256 needed.
2. **`sub` claim = Supabase user ID.** This is the UUID that links Supabase's `auth.users` to your `public.users` table.
3. **The `audience` must be `"authenticated"`.** Supabase sets this claim on all user tokens. If you skip audience validation, you risk accepting tokens from other Supabase projects.
4. **No password storage.** GoAlong never sees or stores passwords. Supabase handles all credential management.
5. **Role is application-level.** Supabase doesn't know about `driver` vs `passenger`. That's stored in your `users` table and checked in your service layer.

---

## Database: Users Table

```sql
CREATE TABLE users (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    supabase_uid    TEXT UNIQUE NOT NULL,    -- Links to Supabase auth.users.id
    name            VARCHAR(100),
    email           VARCHAR(255) UNIQUE,
    phone           VARCHAR(15) UNIQUE,
    profile_photo   TEXT,                    -- Supabase Storage URL
    role            VARCHAR(20) NOT NULL DEFAULT 'passenger',
                                             -- 'passenger' | 'driver' | 'admin'
    is_active        BOOLEAN DEFAULT TRUE,    -- Admin can deactivate; always TRUE on creation
    fcm_token       TEXT,                    -- For push notifications
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_users_supabase_uid ON users(supabase_uid);
CREATE INDEX idx_users_phone ON users(phone);
```

---

## API Endpoints

| Method | Endpoint               | Auth     | Description                        |
|--------|------------------------|----------|------------------------------------|
| POST   | `/api/v1/auth/sync`    | Required | Sync Supabase user to app DB (first login) |
| POST   | `/api/v1/auth/fcm-token` | Required | Register FCM device token         |
| DELETE | `/api/v1/auth/fcm-token` | Required | Remove FCM token (logout)         |

> **Note:** Registration, OTP, login, and token refresh are handled entirely by `supabase_flutter` on the client. FastAPI has NO registration or login endpoints. The `/auth/sync` endpoint is called once after first Supabase login to create the app user row.

---

## Auth Flow — Complete Sequence

```
1. User opens app
2. Flutter checks Supabase session → if valid, go to home
3. If no session → show login screen
4. User enters phone number
5. Flutter calls supabase.auth.signInWithOtp(phone: "+91...")
6. Supabase sends OTP via SMS
7. User enters OTP
8. Flutter calls supabase.auth.verifyOTP(phone, otp)
9. Supabase returns JWT + refresh token
10. Flutter stores session automatically (secure storage)
11. Flutter calls FastAPI: POST /api/v1/auth/sync
12. FastAPI verifies JWT → creates user row if first login
13. Flutter navigates to home screen
14. All subsequent API calls include: Authorization: Bearer <jwt>
15. On token expiry → Supabase SDK auto-refreshes
16. On logout → Flutter calls supabase.auth.signOut() + DELETE /auth/fcm-token
```

---

## Security Considerations

| Concern                | Mitigation                                                |
|------------------------|----------------------------------------------------------|
| OTP brute force        | Supabase has built-in rate limiting (max 30 OTP requests/hour per phone) |
| Token theft            | Short JWT expiry (1 hour) + refresh token rotation        |
| Man-in-the-middle      | HTTPS everywhere (Supabase, Cloud Run, all endpoints)    |
| Firebase token abuse   | FCM tokens stored per-user, deleted on logout             |
| Supabase service key   | Never exposed to client. Only used server-side in FastAPI |
