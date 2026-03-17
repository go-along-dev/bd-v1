# Module 12: Security, Observability & SLOs

> **This document covers everything that keeps the system safe, visible, and reliable.** Security hardening, rate limiting, role/permission enforcement, structured logging, metrics, alerting, backup/restore, and service-level objectives.

---

## Table of Contents

1. [Threat Model](#1-threat-model)
2. [Authentication Security](#2-authentication-security)
3. [Authorization & Role Matrix](#3-authorization--role-matrix)
4. [Input Validation & Injection Prevention](#4-input-validation--injection-prevention)
5. [Rate Limiting](#5-rate-limiting)
6. [Data Protection](#6-data-protection)
7. [Audit Logging](#7-audit-logging)
8. [Structured Logging](#8-structured-logging)
9. [Metrics & Monitoring](#9-metrics--monitoring)
10. [Alerting](#10-alerting)
11. [Backup & Recovery](#11-backup--recovery)
12. [Service-Level Objectives](#12-service-level-objectives)
13. [Incident Response](#13-incident-response)
14. [Security Checklist](#14-security-checklist)

---

## 1. Threat Model

### Attack Surface

| Surface                   | Threats                                           | Mitigation                          |
|---------------------------|---------------------------------------------------|-------------------------------------|
| Public API (`/api/v1/*`)  | Broken auth, injection, DDoS, scraping            | JWT verification, input validation, rate limiting |
| Admin panel (`/admin`)    | Credential stuffing, unauthorized access           | Env-based auth, IP allowlist, strong password |
| WebSocket (`/chat/ws/*`)  | Token hijack, message injection, connection flood  | JWT auth, message sanitization, connection limit |
| Supabase Storage          | Unauthorized file access, malicious uploads        | Private buckets, file type/size limits |
| Database                  | SQL injection, data exfiltration via leaked creds  | ORM parameterized queries, Secret Manager |
| Third-party services      | API key compromise (Supabase, MongoDB, FCM)        | Secret Manager, key rotation plan |
| Client app                | JWT stored insecurely, reverse engineering          | Secure storage, short-lived tokens, refresh flow |

### OWASP Top 10 Coverage

| Risk                              | Status | How                                                     |
|-----------------------------------|--------|---------------------------------------------------------|
| A01: Broken Access Control        | ✅     | Role checks on every endpoint, ownership validation      |
| A02: Cryptographic Failures       | ✅     | HTTPS everywhere, JWT HS256 via Supabase, no custom crypto |
| A03: Injection                    | ✅     | SQLAlchemy ORM (parameterized), Pydantic validation      |
| A04: Insecure Design              | ✅     | Threat model, defense in depth, principle of least privilege |
| A05: Security Misconfiguration    | ✅     | Secret Manager, no default credentials, hardened Docker  |
| A06: Vulnerable Components        | ⚠️     | Phase 2: Add `pip-audit` / `safety` to CI pipeline      |
| A07: Auth Failures                | ✅     | Supabase handles auth + OTP, JWT with short expiry       |
| A08: Data Integrity Failures      | ✅     | DB constraints, CHECK constraints, server-side validation|
| A09: Logging & Monitoring Failures| ✅     | Structured logging, Cloud Logging, audit trail           |
| A10: SSRF                         | ✅     | OSRM on internal VPC only, no user-supplied URLs fetched |

---

## 2. Authentication Security

### JWT Configuration

| Setting              | Value             | Rationale                                     |
|----------------------|-------------------|-----------------------------------------------|
| Algorithm            | HS256             | Supabase default, symmetric key               |
| Access token TTL     | 3600s (1 hour)    | Supabase default                              |
| Refresh token TTL    | 604800s (7 days)  | Supabase default                              |
| HS256 verification   | Yes               | Verify via Supabase JWT secret (HS256)         |
| Clock skew tolerance | 30 seconds        | Account for server time drift                 |

### JWT Verification Flow (FastAPI Middleware)

```python
async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> User:
    token = credentials.credentials

    # 1. Decode and verify JWT signature
    try:
        payload = jwt.decode(
            token,
            SUPABASE_JWT_SECRET,
            algorithms=["HS256"],
            audience="authenticated",
            leeway=30,           # 30s clock skew tolerance
        )
    except jwt.ExpiredSignatureError:
        raise HTTPException(401, detail="Token expired", headers={"code": "TOKEN_EXPIRED"})
    except jwt.InvalidTokenError:
        raise HTTPException(401, detail="Invalid token", headers={"code": "INVALID_TOKEN"})

    # 2. Extract Supabase UID
    supabase_uid = payload.get("sub")
    if not supabase_uid:
        raise HTTPException(401, detail="Invalid token payload")

    # 3. Find or create app user
    user = await get_or_create_by_supabase_uid(db, supabase_uid, payload)
    if not user.is_active:
        raise HTTPException(403, detail="Account deactivated")

    return user
```

### Token Refresh (Flutter Client)

```dart
// Dio interceptor handles automatic token refresh
class AuthInterceptor extends Interceptor {
  @override
  void onError(DioException err, ErrorInterceptorHandler handler) async {
    if (err.response?.statusCode == 401) {
      try {
        // Attempt refresh
        final session = await supabase.auth.refreshSession();
        if (session.session != null) {
          // Retry original request with new token
          err.requestOptions.headers['Authorization'] =
              'Bearer ${session.session!.accessToken}';
          final response = await dio.fetch(err.requestOptions);
          return handler.resolve(response);
        }
      } catch (_) {
        // Refresh failed — force re-login
        await supabase.auth.signOut();
        router.go('/login');
      }
    }
    return handler.next(err);
  }
}
```

### Session Security Rules
1. **Never store JWT in SharedPreferences.** Use `flutter_secure_storage` (Keychain on iOS, EncryptedSharedPreferences on Android).
2. **Logout must clear FCM token** (call `DELETE /auth/fcm-token` before signing out).
3. **One active session per device.** Supabase handles this.
4. **No "remember me" toggle.** Refresh token handles persistence transparently.

---

## 3. Authorization & Role Matrix

### Roles
| Role       | Description                          | Created via                              |
|------------|--------------------------------------|------------------------------------------|
| `passenger`| Default role for all users           | Auto on first `/auth/sync`               |
| `driver`   | User with approved driver profile    | Auto when driver registration submitted  |
| `admin`    | System administrator                 | Manual SQL: `UPDATE users SET role='admin'` |

### Endpoint Permission Matrix

| Endpoint Group           | passenger | driver | admin | Notes                                    |
|--------------------------|:---------:|:------:|:-----:|------------------------------------------|
| `POST /auth/sync`        | ✅        | ✅     | ✅    | Anyone with valid JWT                    |
| `POST /auth/fcm-token`   | ✅        | ✅     | ✅    |                                          |
| `GET /users/me`          | ✅        | ✅     | ✅    |                                          |
| `PUT /users/me`          | ✅        | ✅     | ✅    |                                          |
| `POST /drivers/register` | ✅        | ❌     | ❌    | Only passengers can become drivers       |
| `GET /drivers/me`        | ❌        | ✅     | ❌    | Must have driver profile                 |
| `PUT /drivers/me`        | ❌        | ✅     | ❌    | Only while status=pending                |
| `POST /drivers/documents`| ❌        | ✅     | ❌    |                                          |
| `POST /rides`            | ❌        | ✅*    | ❌    | *Only approved drivers                   |
| `GET /rides`             | ✅        | ✅     | ✅    | Public search                            |
| `GET /rides/{id}`        | ✅        | ✅     | ✅    |                                          |
| `PUT /rides/{id}`        | ❌        | ✅*    | ❌    | *Only ride owner                         |
| `DELETE /rides/{id}`     | ❌        | ✅*    | ❌    | *Only ride owner                         |
| `POST /bookings`         | ✅        | ✅     | ❌    | Anyone except ride driver                |
| `GET /bookings/my-*`     | ✅        | ✅     | ❌    | Own bookings only                        |
| `PUT /bookings/{id}/cancel` | ✅     | ✅     | ❌    | Booking owner only                       |
| `WS /chat/ws/{id}`       | ✅*       | ✅*    | ❌    | *Must be driver or passenger of booking  |
| `GET /chat/*`            | ✅*       | ✅*    | ❌    | *Must be part of the booking             |
| `GET /wallet/*`          | ❌        | ✅     | ❌    | Driver-only feature                      |
| `POST /wallet/*`         | ❌        | ✅     | ❌    | Driver-only feature                      |
| `GET /admin/stats`       | ❌        | ❌     | ✅    |                                          |
| `GET /admin/*`           | ❌        | ❌     | ✅    | SQLAdmin panel                           |

### Role Enforcement Implementation

```python
# dependencies/auth.py

from fastapi import Depends, HTTPException

async def require_driver(user: User = Depends(get_current_user)) -> Driver:
    """Dependency that ensures user is a registered driver."""
    driver = await get_driver_by_user(db, user)
    if not driver:
        raise HTTPException(403, detail="Driver registration required", code="NOT_A_DRIVER")
    return driver

async def require_approved_driver(driver: Driver = Depends(require_driver)) -> Driver:
    """Dependency that ensures driver is approved."""
    if driver.verification_status != "approved":
        raise HTTPException(403, detail="Driver not verified", code="DRIVER_NOT_APPROVED")
    return driver

async def require_admin(user: User = Depends(get_current_user)) -> User:
    """Dependency that ensures user is an admin."""
    if user.role != "admin":
        raise HTTPException(403, detail="Admin access required", code="NOT_ADMIN")
    return user
```

### Ownership Checks
Beyond role checks, every mutation verifies **resource ownership**:

```python
# Example: ride update
if ride.driver_id != driver.id:
    raise HTTPException(403, detail="Not your ride", code="NOT_RIDE_OWNER")

# Example: booking cancel
if booking.passenger_id != user.id:
    raise HTTPException(403, detail="Not your booking", code="NOT_BOOKING_OWNER")
```

---

## 4. Input Validation & Injection Prevention

### Server-Side Validation (Pydantic V2)

All request bodies are validated through Pydantic schemas before touching the database:

| Validation Type        | Implementation                                      |
|------------------------|-----------------------------------------------------|
| Type checking          | Pydantic field types (`str`, `int`, `float`, `UUID`) |
| Range validation       | `Field(ge=1, le=8)`, `Field(gt=0, le=5000)`         |
| String length          | `max_length=100`, `min_length=1`                     |
| Pattern matching       | `pattern=r'^[\w.\-]+@[\w]+$'` (UPI ID)              |
| Enum validation        | `Literal['hatchback','sedan','suv','muv']`           |
| Coordinate bounds      | `-90 ≤ lat ≤ 90`, `-180 ≤ lng ≤ 180`                |
| Timestamp validation   | `datetime` type with timezone awareness              |
| URL validation         | `HttpUrl` type for storage URLs                      |

### SQL Injection Prevention
- **SQLAlchemy ORM** — all queries use parameterized statements
- **Never use raw SQL** with string interpolation
- **Alembic migrations** — schema changes via migration files, not raw DDL in app code

```python
# SAFE — parameterized
result = await db.execute(
    select(Ride).where(Ride.id == ride_id)
)

# DANGEROUS — never do this
result = await db.execute(f"SELECT * FROM rides WHERE id = '{ride_id}'")
```

### XSS Prevention
- API returns JSON only (no HTML rendering)
- Flutter app doesn't use `webview` or `innerHtml`
- Chat messages are plain text, rendered as `Text()` widget (not HTML)
- SQLAdmin renders data server-side with Jinja2 auto-escaping

### File Upload Validation
```python
ALLOWED_MIME_TYPES = {
    "image/jpeg", "image/png", "image/webp", "application/pdf"
}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB

# Validation happens in Supabase Storage bucket configuration
# + additional server-side check on the URL pattern
```

---

## 5. Rate Limiting

### Strategy
Use **SlowAPI** (based on `limits`) as middleware in FastAPI. Rate limits are per-user (identified by JWT subject claim) or per-IP for unauthenticated endpoints.

```python
# core/rate_limit.py

from slowapi import Limiter
from slowapi.util import get_remote_address

def get_user_or_ip(request):
    """Rate limit key: user ID if authenticated, else IP."""
    auth = request.headers.get("authorization", "")
    if auth.startswith("Bearer "):
        try:
            payload = jwt.decode(auth[7:], SUPABASE_JWT_SECRET, algorithms=["HS256"])
            return payload.get("sub", get_remote_address(request))
        except Exception:
            pass
    return get_remote_address(request)

limiter = Limiter(key_func=get_user_or_ip)
```

### Rate Limits by Endpoint Category

| Category              | Limit                    | Rationale                                    |
|-----------------------|--------------------------|----------------------------------------------|
| Auth endpoints        | 10/minute per IP         | Prevent brute force                          |
| Read endpoints (GET)  | 60/minute per user       | Normal usage patterns                        |
| Write endpoints (POST/PUT) | 20/minute per user  | Prevent spam ride/booking creation           |
| Ride search           | 30/minute per user       | Allow frequent searches during browsing      |
| Chat WebSocket        | 60 messages/minute       | Prevent message flooding                     |
| File upload (implicit)| 10/minute per user       | Prevent storage abuse                        |
| Admin endpoints       | 120/minute per user      | Admin needs higher limits for batch work     |
| Health check          | No limit                 | Must always respond (used by Cloud Run)      |

### Implementation

```python
# routers/bookings.py
@router.post("/")
@limiter.limit("20/minute")
async def create_booking(request: Request, ...):
    ...

# routers/rides.py
@router.get("/")
@limiter.limit("30/minute")
async def search_rides(request: Request, ...):
    ...
```

### 429 Response
```json
{
  "detail": "Rate limit exceeded. Try again in 45 seconds.",
  "code": "RATE_LIMITED",
  "retry_after": 45
}
```

---

## 6. Data Protection

### Data Classification

| Level          | Data                                      | Storage            | Access              |
|----------------|-------------------------------------------|--------------------|---------------------|
| **Critical**   | Supabase service role key, DB passwords   | GCP Secret Manager | Cloud Run only      |
| **Sensitive**  | Phone numbers, email, Aadhar/PAN docs     | Supabase (DB/Storage) | User + Admin     |
| **Internal**   | Ride details, bookings, fares             | Supabase DB        | Authenticated users |
| **Public**     | Search results (no PII), health check     | API response       | Anyone              |

### PII Handling

| PII Field        | Storage              | Displayed To          | Redaction Rule          |
|------------------|----------------------|-----------------------|-------------------------|
| Phone number     | `users.phone`        | Only the user + admin | Mask in logs: `+91***7890` |
| Email            | `users.email`        | Only the user + admin | Mask in logs: `k***@example.com` |
| Aadhar number    | Document image only  | Admin only (via Storage URL) | Not stored as text |
| UPI ID           | `wallet_transactions.upi_id` | Driver + Admin | Logged when withdrawal created |
| Driver license   | `drivers.license_number` | Admin only       | Not exposed via API     |

### Secrets Management Rules
1. **Never commit secrets.** `.env` is in `.gitignore`.
2. **All production secrets in GCP Secret Manager.**
3. **Rotate Supabase service role key** if suspected compromise.
4. **Admin password** must be ≥16 characters with mixed case + numbers + symbols.
5. **MongoDB Atlas** credentials: stored in Secret Manager, rotated quarterly.

### HTTPS Enforcement
- Cloud Run provides automatic HTTPS with managed TLS certificates
- All API calls must use `https://` — HTTP is redirected
- WebSocket uses `wss://` in production
- Supabase Storage URLs are `https://` by default
- OSRM is internal-only (no HTTPS needed on VPC)

---

## 7. Audit Logging

### What Gets Logged

| Event                        | Log Level | Fields                                          |
|------------------------------|-----------|--------------------------------------------------|
| User login (auth/sync)       | INFO      | user_id, phone, is_new_user                      |
| Driver registration          | INFO      | user_id, driver_id, vehicle_number                |
| Driver approved/rejected     | INFO      | driver_id, admin_id, status, reason               |
| Ride created                 | INFO      | ride_id, driver_id, source_city, dest_city        |
| Ride cancelled               | WARN      | ride_id, driver_id, affected_bookings_count       |
| Booking created              | INFO      | booking_id, ride_id, passenger_id, fare            |
| Booking cancelled            | INFO      | booking_id, passenger_id, was_within_window        |
| Cashback requested           | INFO      | txn_id, driver_id, amount, ride_id                 |
| Cashback approved/rejected   | INFO      | txn_id, admin_id, amount, decision                 |
| Withdrawal requested         | INFO      | txn_id, driver_id, amount, upi_id                  |
| Withdrawal approved/rejected | INFO      | txn_id, admin_id, amount, decision                 |
| Platform config changed      | WARN      | key, old_value, new_value, admin_id                |
| Failed auth attempt          | WARN      | ip, token_prefix (first 10 chars), reason          |
| Rate limit hit               | WARN      | user_id or ip, endpoint, limit                     |
| OSRM failure                 | ERROR     | endpoint, status_code, response_time               |
| DB connection error          | ERROR     | exception, retry_count                             |

### Audit Log Structure

```python
import logging
import json

logger = logging.getLogger("audit")

def audit_log(event: str, **kwargs):
    """Structured audit log entry."""
    entry = {
        "event": event,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        **kwargs,
    }
    logger.info(json.dumps(entry))

# Usage:
audit_log(
    "booking_created",
    booking_id=str(booking.id),
    ride_id=str(booking.ride_id),
    passenger_id=str(booking.passenger_id),
    fare=str(booking.fare),
    seats=booking.seats_booked,
)
```

---

## 8. Structured Logging

### Log Format (Cloud Logging Compatible)

```python
# core/logging.py

import logging
import json
import sys
import uuid
from contextvars import ContextVar

# Request-scoped trace ID
request_trace_id: ContextVar[str] = ContextVar("request_trace_id", default="")

class StructuredFormatter(logging.Formatter):
    def format(self, record):
        log = {
            "severity": record.levelname,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "trace_id": request_trace_id.get(""),
            "timestamp": self.formatTime(record),
        }
        if record.exc_info:
            log["exception"] = self.formatException(record.exc_info)
        if hasattr(record, "extra_data"):
            log.update(record.extra_data)
        return json.dumps(log)


def setup_logging(log_level: str = "INFO"):
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(StructuredFormatter())

    root = logging.getLogger()
    root.setLevel(getattr(logging, log_level))
    root.handlers = [handler]

    # Silence noisy libraries
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
```

### Request Tracing Middleware

```python
# middleware/tracing.py

from starlette.middleware.base import BaseHTTPMiddleware
import uuid
import time

class TracingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        # Generate or propagate trace ID
        trace_id = request.headers.get("X-Trace-Id", str(uuid.uuid4())[:8])
        request_trace_id.set(trace_id)

        start = time.monotonic()
        response = await call_next(request)
        duration_ms = round((time.monotonic() - start) * 1000)

        # Log every request
        logger.info(
            json.dumps({
                "event": "http_request",
                "method": request.method,
                "path": request.url.path,
                "status": response.status_code,
                "duration_ms": duration_ms,
                "trace_id": trace_id,
                "user_agent": request.headers.get("user-agent", ""),
            })
        )

        response.headers["X-Trace-Id"] = trace_id
        return response
```

### Log Levels Usage

| Level    | When                                                        |
|----------|-------------------------------------------------------------|
| DEBUG    | Development only. SQL queries, OSRM request/response bodies |
| INFO     | Normal operations: login, ride created, booking confirmed    |
| WARNING  | Degraded state: rate limit hit, ride cancelled, retry triggered |
| ERROR    | Failures: OSRM down, DB connection lost, unhandled exception |
| CRITICAL | Never used in application code (reserved for infrastructure) |

---

## 9. Metrics & Monitoring

### Key Metrics to Track

#### Application Metrics (via structured logs → Cloud Logging queries)

| Metric                          | Source                  | Alert Threshold        |
|---------------------------------|-------------------------|------------------------|
| Request rate (req/min)          | HTTP logs               | > 500/min (unexpected) |
| Error rate (5xx/total)          | HTTP logs               | > 5% over 5 minutes   |
| p50/p95/p99 latency             | HTTP logs duration_ms   | p95 > 2000ms           |
| Auth failure rate               | Audit logs              | > 20/hour              |
| Active WebSocket connections    | ConnectionManager count | > 200 (Cloud Run limit)|
| OSRM response time              | Service logs            | p95 > 3000ms           |
| DB connection pool utilization  | SQLAlchemy events       | > 80%                  |

#### Business Metrics (via `/admin/stats` or direct SQL)

| Metric                          | Query Interval | Alerting?  |
|---------------------------------|----------------|------------|
| New users/day                   | Daily          | No         |
| New drivers/day                 | Daily          | No         |
| Pending driver verifications    | Hourly         | Yes (> 10) |
| Rides created/day               | Daily          | No         |
| Bookings/day                    | Daily          | No         |
| Pending cashback requests       | Hourly         | Yes (> 20) |
| Pending withdrawal requests     | Hourly         | Yes (> 10) |
| Total cashback paid (cumulative)| Daily          | No         |

### Cloud Run Built-in Metrics (GCP Console)
- Instance count (auto-scaling)
- Container CPU utilization
- Container memory utilization
- Request count
- Request latency (p50, p95, p99)
- Billable instance time

These are **automatically available** in GCP Console → Cloud Run → Metrics. No setup needed.

---

## 10. Alerting

### Phase 1: Email Alerts via GCP Monitoring

```
GCP Console → Monitoring → Alerting → Create Policy

Alert 1: High Error Rate
  Condition: Cloud Run → Request count where response_code_class = "5xx"
  Threshold: > 10 in 5 minutes
  Notification: Email to team

Alert 2: High Latency
  Condition: Cloud Run → Request latency (p95)
  Threshold: > 3000ms for 5 minutes
  Notification: Email to team

Alert 3: Instance Limit
  Condition: Cloud Run → Instance count
  Threshold: = 4 (max instances reached — might need scaling)
  Notification: Email to team

Alert 4: Health Check Failure
  Condition: Uptime check on /health endpoint
  Threshold: 2 consecutive failures
  Notification: Email to team

Alert 5: OSRM VM Down
  Condition: Compute Engine → CPU utilization = 0 (VM stopped)
  Notification: Email to team
```

### Phase 2 Enhancements
- Slack/Discord webhook integration
- PagerDuty for on-call rotation
- Sentry for application error tracking with stack traces

---

## 11. Backup & Recovery

### PostgreSQL (Supabase)

| Aspect             | Value                                              |
|--------------------|----------------------------------------------------|
| Automatic backups  | Supabase daily backups (free tier: 7-day retention)|
| Point-in-time      | Not on free tier. Available on Pro ($25/month)     |
| Manual backup      | `pg_dump` via Supabase CLI or direct connection    |
| RPO (Recovery Point)| 24 hours (daily backup) on free tier              |
| RTO (Recovery Time) | ~30 minutes (restore from Supabase dashboard)     |

```bash
# Manual backup script (run weekly as cron job or before deployments)
pg_dump "$DATABASE_URL" --format=custom --file="goalong_backup_$(date +%Y%m%d).dump"

# Restore
pg_restore --dbname="$DATABASE_URL" goalong_backup_20260301.dump
```

### MongoDB Atlas (Chat)

| Aspect             | Value                                    |
|--------------------|------------------------------------------|
| Automatic backups  | Not on M0 free tier                      |
| Manual backup      | `mongodump` via connection string        |
| RPO                | Acceptable loss: chat is non-critical    |
| RTO                | N/A — chat can be rebuilt from scratch   |

Chat messages are **ephemeral by design** (90-day TTL). If MongoDB data is lost, users lose chat history but no critical functionality is affected.

### OSRM VM

| Aspect             | Value                                        |
|--------------------|----------------------------------------------|
| Backup needed?     | No — data is re-downloadable from Geofabrik  |
| Recovery           | Re-run setup script on a new VM (~30 min)    |
| Disk snapshot      | Optional: create GCP disk snapshot weekly     |

### Disaster Recovery Plan

| Scenario                    | Impact        | Recovery Steps                              | RTO   |
|-----------------------------|---------------|---------------------------------------------|-------|
| Cloud Run outage            | API down      | Auto-recovers. If prolonged, deploy to backup region | 5 min |
| Supabase DB corruption      | Data loss     | Restore from daily backup                   | 30 min|
| MongoDB Atlas outage        | Chat down     | Wait for Atlas recovery. Chat is non-critical | 1-4 hr |
| OSRM VM crash               | No routing    | Re-provision VM + run setup script          | 30 min|
| Secret leak                 | Security      | Rotate all secrets immediately              | 15 min|
| GCP project compromise      | Full breach   | Supabase + MongoDB are external — isolate GCP, rotate all keys | 1 hr |

---

## 12. Service-Level Objectives

### SLOs for Phase 1 (MVP)

| SLI (Indicator)                      | SLO (Objective)  | Measurement                              |
|--------------------------------------|------------------|------------------------------------------|
| API availability                     | 99.5% monthly    | Successful requests / total requests     |
| API latency (p95)                    | < 2000ms         | Cloud Run request latency metric         |
| API latency (p50)                    | < 500ms          | Cloud Run request latency metric         |
| Ride search latency (p95)            | < 3000ms         | Includes OSRM call                       |
| Booking creation success rate        | > 99%            | Excludes client validation errors (4xx)  |
| Chat message delivery (real-time)    | > 95%            | When both users online                   |
| Chat message delivery (including FCM)| > 99%            | Real-time + FCM fallback                 |
| Push notification delivery           | > 95%            | FCM delivery rate                        |
| Admin panel availability             | 99%              | SQLAdmin accessible                      |
| Data durability                      | 99.9%            | Supabase backup coverage                 |

### Error Budget

With 99.5% availability SLO:
- **Monthly error budget:** 0.5% = ~3.6 hours of downtime/month
- **Weekly error budget:** ~54 minutes
- **Daily error budget:** ~7.2 minutes

**Rule:** If error budget is >50% consumed by mid-month, freeze deployments and investigate.

### SLO Monitoring

```
Monthly SLO Report (manual check):

1. Go to GCP Console → Cloud Run → Metrics
2. Set time range: Last 30 days
3. Check:
   □ Request success rate ≥ 99.5%
   □ p95 latency ≤ 2000ms
   □ p50 latency ≤ 500ms
   □ Max instances never sustained at limit
4. Check Supabase Dashboard:
   □ DB size < 400MB (80% of free tier limit)
   □ Auth MAU < 40,000 (80% of free tier limit)
   □ Storage < 800MB (80% of free tier limit)
5. Check MongoDB Atlas:
   □ Storage < 400MB (80% of M0 limit)
   □ Connection count < 400 (80% of limit)
```

---

## 13. Incident Response

### Severity Levels

| Level | Definition                              | Response Time | Example                          |
|-------|-----------------------------------------|---------------|----------------------------------|
| P1    | Service completely down                 | 15 minutes    | Cloud Run returning 503 for all requests |
| P2    | Major feature broken                    | 1 hour        | Bookings failing, chat down       |
| P3    | Minor feature degraded                  | 4 hours       | Slow search, FCM delays           |
| P4    | Cosmetic / non-urgent                   | 24 hours      | Admin UI glitch, log format issue  |

### Runbook: Common Incidents

#### Cloud Run 503 (P1)
```
1. Check GCP Console → Cloud Run → Logs
2. Look for OOM kills (memory), cold start failures, crash loops
3. If OOM: Increase memory (512MB → 1GB)
4. If crash: Check latest deployment → rollback:
   gcloud run services update-traffic goalong-api --to-revisions=PREVIOUS_REVISION=100
5. If sustained: Check DB connectivity (Supabase status page)
```

#### OSRM Unavailable (P2)
```
1. SSH into OSRM VM: gcloud compute ssh osrm-vm
2. Check Docker: sudo docker ps (is container running?)
3. If stopped: sudo docker start osrm
4. If OOM killed: sudo docker logs osrm → check memory
5. If VM is down: GCP Console → Compute Engine → Start VM
6. Nuclear option: Delete VM, recreate from setup script (30 min)
```

#### Supabase Auth Down (P1)
```
1. Check status.supabase.com
2. If Supabase outage: Nothing we can do. Wait.
3. If our config issue: Check Supabase Dashboard → Auth → Logs
4. Verify JWT secret hasn't changed
5. Test: curl -H "Authorization: Bearer <token>" https://api/health
```

#### MongoDB Connection Failure (P2 — chat only)
```
1. Check MongoDB Atlas → Cluster → Metrics (is it reachable?)
2. Check network access (0.0.0.0/0 should be allowed)
3. Verify credentials in Secret Manager haven't changed
4. Test from Cloud Run logs: look for "ServerSelectionTimeoutError"
5. If Atlas outage: Chat is degraded, rest of app works fine
```

---

## 14. Security Checklist

### Pre-Launch

```
Authentication & Authorization:
□ Supabase JWT verification working (test with expired token → 401)
□ Role checks on all endpoints (test passenger accessing driver endpoints → 403)
□ Ownership checks on all mutations (test editing someone else's ride → 403)
□ Admin panel password is ≥16 chars, not default
□ FCM token cleanup on logout tested

Input Validation:
□ All Pydantic schemas reject malformed input (fuzz test)
□ SQL injection attempted on all string params → blocked
□ Coordinate bounds checked (-90/90, -180/180)
□ File upload size/type limits configured in Supabase Storage
□ Chat message length enforced (≤1000 chars)

Secrets:
□ No secrets in codebase (TruffleHog scan passes)
□ All secrets in GCP Secret Manager
□ .env is in .gitignore
□ Service role key not exposed to Flutter client (only anon key)
□ ADMIN_PASSWORD rotated from development value

Network:
□ Cloud Run HTTPS enforced
□ OSRM accessible only via internal VPC (no external IP)
□ MongoDB Atlas requires authentication
□ Supabase RLS is OFF (intentional — documented)

Rate Limiting:
□ SlowAPI middleware configured
□ Auth endpoints: 10/min per IP
□ Write endpoints: 20/min per user
□ 429 responses include retry_after header

Monitoring:
□ Structured logging producing valid JSON
□ Trace IDs propagating across requests
□ GCP alerting policies created (error rate, latency, health)
□ Uptime check on /health configured
□ Audit logging for security events active
```

### Quarterly Review

```
□ Rotate ADMIN_PASSWORD
□ Rotate MongoDB credentials
□ Check Supabase security advisories
□ Run pip-audit on dependencies
□ Review Cloud Run access logs for anomalies
□ Verify backup restore process works (test restore)
□ Review rate limit thresholds against actual traffic
□ Check free tier usage against limits
```
