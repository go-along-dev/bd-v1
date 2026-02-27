# GoAlong – System Design: Architecture Overview

## Document Index

This system design is split into the following module documents:

| #  | Document                          | Covers                                              |
|----|-----------------------------------|------------------------------------------------------|
| 0  | `00-architecture.md` (this file)  | High-level architecture, tech stack, project structure |
| 1  | `01-auth.md`                      | Authentication, OTP, sessions, token management       |
| 2  | `02-user-driver.md`               | User profiles, driver registration, document upload, verification |
| 3  | `03-rides.md`                     | Ride creation, editing, cancellation, search           |
| 4  | `04-bookings.md`                  | Seat booking, cancellation policy, status management   |
| 5  | `05-fare-engine.md`               | Full route pricing, partial route pricing, config      |
| 6  | `06-chat.md`                      | WebSocket chat, message storage, booking-gated access  |
| 7  | `07-wallet.md`                    | Toll cashback, wallet balance, withdrawals, UPI payout |
| 8  | `08-admin.md`                     | Admin panel, verification workflows, reporting         |
| 9  | `09-infra.md`                     | Supabase, GCP, CI/CD, monitoring, deployment           |

---

## 1. Architecture Style

**Modular Monolith** — a single FastAPI application with clearly separated internal modules.

**Why not microservices:**
- 28-day timeline makes microservices a liability, not an asset
- 3–5 developers cannot maintain multiple services, message queues, and service discovery
- A well-structured monolith can be broken apart later if scale demands it
- Debugging, logging, and deployment are dramatically simpler

**Why not serverless functions:**
- WebSocket chat requires persistent connections (not possible with stateless functions)
- Shared database connections and ORM benefit from a long-running process
- FastAPI on Cloud Run already gives auto-scaling without the cold-start headaches

---

## 2. System Architecture Diagram

```
                    ┌─────────────────────────────────┐
                    │           CLIENTS               │
                    │                                  │
                    │  ┌────────────┐  ┌────────────┐  │
                    │  │ Flutter App│  │Admin Panel │  │
                    │  │(Android/iOS)│  │(SQLAdmin)  │  │
                    │  └─────┬──────┘  └─────┬──────┘  │
                    └────────┼───────────────┼─────────┘
                             │               │
                        HTTPS│          HTTPS│
                             ▼               ▼
                    ┌────────────────────────────────┐
                    │      GCP Cloud Run             │
                    │  ┌──────────────────────────┐  │
                    │  │     FastAPI Application   │  │
                    │  │                          │  │
                    │  │  ┌────┐ ┌────┐ ┌──────┐  │  │
                    │  │  │Auth│ │Ride│ │Book  │  │  │
                    │  │  └────┘ └────┘ └──────┘  │  │
                    │  │  ┌────┐ ┌────┐ ┌──────┐  │  │
                    │  │  │Chat│ │Fare│ │Wallet│  │  │
                    │  │  └────┘ └────┘ └──────┘  │  │
                    │  │  ┌──────┐ ┌───────────┐  │  │
                    │  │  │Admin │ │Notify(FCM)│  │  │
                    │  │  └──────┘ └───────────┘  │  │
                    │  └──────────────────────────┘  │
                    └──────┬─────────┬─────────┬─────┘
                           │         │         │
              ┌────────────┘         │         └────────────┐
              ▼                      ▼                      ▼
    ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐
    │    Supabase      │  │  MongoDB Atlas   │  │   External APIs  │
    │                  │  │                  │  │                  │
    │ • PostgreSQL DB  │  │ • chat_messages  │  │ • OSRM (routing) │
    │ • Auth (OTP)     │  │   collection     │  │ • Nominatim (geo)│
    │ • Storage (files)│  │ • Free M0 tier   │  │ • FCM (push)     │
    └──────────────────┘  └──────────────────┘  └──────────────────┘
```

---

## 3. Tech Stack — Final Decisions

### Backend

| Layer              | Technology               | Why                                                    |
|--------------------|--------------------------|--------------------------------------------------------|
| Framework          | **FastAPI**              | Async, fast, Pydantic validation built-in, great docs  |
| Language           | **Python 3.11+**         | Team familiarity, FastAPI ecosystem                    |
| ORM                | **SQLAlchemy 2.0 (async)** | Mature, async support, Supabase PostgreSQL compatible |
| Migrations         | **Alembic**              | Industry standard for SQLAlchemy                       |
| Auth               | **Supabase Auth**        | Handles OTP, email, phone — no custom auth code        |
| Database           | **Supabase PostgreSQL**  | Managed, free tier generous, built-in connection pooling |
| Chat Storage       | **MongoDB Atlas (M0)**   | Free tier, perfect for append-heavy chat data          |
| File Storage       | **Supabase Storage**     | Integrated with Supabase Auth policies                 |
| Push Notifications | **Firebase Cloud Messaging (FCM)** | Industry standard for mobile push            |
| Background Tasks   | **FastAPI BackgroundTasks** | Simple, no broker needed at MVP scale               |
| Admin Panel        | **SQLAdmin**             | Auto-generated from SQLAlchemy models                  |
| Validation         | **Pydantic V2**          | Built into FastAPI, zero extra setup                   |

### Mobile

| Layer              | Technology               | Why                                                    |
|--------------------|--------------------------|--------------------------------------------------------|
| Framework          | **Flutter 3.x**          | Single codebase, Android + iOS                         |
| State Management   | **Riverpod**             | Compile-safe, testable, no boilerplate                 |
| HTTP Client        | **Dio**                  | Interceptors for token refresh, retries                |
| WebSocket          | **web_socket_channel**   | Official Dart package, reliable                        |
| Local Storage      | **SharedPreferences**    | Tokens, user preferences                               |
| Maps               | **flutter_map**          | OpenStreetMap tiles, free                              |
| Location           | **geolocator**           | GPS access for pickup/drop                             |
| Geocoding          | **Nominatim API**        | Free, OSM-backed address ↔ coordinates                 |
| Push Notifications | **firebase_messaging**   | FCM integration for Flutter                            |
| Auth               | **supabase_flutter**     | Native Supabase Auth SDK                               |
| Image Picker       | **image_picker**         | Camera + gallery for document/profile uploads          |

### Infrastructure

| Component          | Service                  | Tier / Spec                                            |
|--------------------|--------------------------|--------------------------------------------------------|
| App Hosting        | **GCP Cloud Run**        | Min 0 → Max 4 instances, 1 vCPU / 512MB               |
| Database           | **Supabase**             | Free tier (500MB DB, 1GB storage, 50K MAU auth)        |
| Chat DB            | **MongoDB Atlas**        | Free M0 (512MB storage)                                |
| Routing Engine     | **OSRM** on GCP CE       | e2-small VM, India OSM extract                         |
| CI/CD              | **GCP Cloud Build**      | Trigger on git push to main                            |
| Container Registry | **GCP Artifact Registry** | Docker images for Cloud Run                           |
| Secrets            | **GCP Secret Manager**   | DB URLs, API keys, Supabase keys                       |
| Monitoring         | **GCP Cloud Logging**    | Built-in with Cloud Run                                |

---

## 4. Project Structure

```
goalong/
│
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                     # FastAPI app, middleware, router includes
│   │   ├── config.py                   # Pydantic Settings (env vars)
│   │   ├── dependencies.py             # Shared deps (get_db, get_current_user)
│   │   │
│   │   ├── db/
│   │   │   ├── __init__.py
│   │   │   ├── postgres.py             # SQLAlchemy async engine + session
│   │   │   ├── mongo.py                # Motor async MongoDB client
│   │   │   └── base.py                 # SQLAlchemy declarative base
│   │   │
│   │   ├── models/                     # SQLAlchemy ORM models (1 file per table)
│   │   │   ├── __init__.py
│   │   │   ├── user.py
│   │   │   ├── driver.py
│   │   │   ├── driver_document.py
│   │   │   ├── ride.py
│   │   │   ├── booking.py
│   │   │   ├── wallet.py
│   │   │   ├── wallet_transaction.py
│   │   │   ├── notification.py
│   │   │   └── platform_config.py
│   │   │
│   │   ├── schemas/                    # Pydantic request/response schemas
│   │   │   ├── __init__.py
│   │   │   ├── auth.py
│   │   │   ├── user.py
│   │   │   ├── driver.py
│   │   │   ├── ride.py
│   │   │   ├── booking.py
│   │   │   ├── chat.py
│   │   │   ├── wallet.py
│   │   │   └── common.py               # Pagination, error responses
│   │   │
│   │   ├── routers/                    # API route handlers (thin — delegate to services)
│   │   │   ├── __init__.py
│   │   │   ├── auth.py
│   │   │   ├── users.py
│   │   │   ├── drivers.py
│   │   │   ├── rides.py
│   │   │   ├── bookings.py
│   │   │   ├── chat.py
│   │   │   ├── wallet.py
│   │   │   └── fare.py
│   │   │
│   │   ├── services/                   # Business logic (all logic lives here)
│   │   │   ├── __init__.py
│   │   │   ├── auth_service.py
│   │   │   ├── user_service.py
│   │   │   ├── driver_service.py
│   │   │   ├── ride_service.py
│   │   │   ├── booking_service.py
│   │   │   ├── fare_engine.py
│   │   │   ├── chat_service.py
│   │   │   ├── wallet_service.py
│   │   │   ├── notification_service.py
│   │   │   ├── osrm_service.py
│   │   │   └── storage_service.py
│   │   │
│   │   ├── admin/                      # SQLAdmin views and custom actions
│   │   │   ├── __init__.py
│   │   │   └── views.py
│   │   │
│   │   ├── middleware/
│   │   │   ├── __init__.py
│   │   │   ├── auth.py                 # Supabase JWT verification
│   │   │   └── logging.py              # Request/response logging
│   │   │
│   │   └── utils/
│   │       ├── __init__.py
│   │       ├── constants.py
│   │       ├── exceptions.py           # Custom HTTP exceptions
│   │       └── helpers.py
│   │
│   ├── alembic/                        # Database migrations
│   │   ├── env.py
│   │   └── versions/
│   │
│   ├── tests/
│   │   ├── conftest.py
│   │   ├── test_auth.py
│   │   ├── test_rides.py
│   │   ├── test_bookings.py
│   │   ├── test_fare.py
│   │   ├── test_wallet.py
│   │   └── test_chat.py
│   │
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── alembic.ini
│   ├── .env.example
│   └── pyproject.toml
│
├── mobile/
│   └── goalong_app/
│       └── lib/
│           ├── main.dart
│           │
│           ├── core/
│           │   ├── config/
│           │   │   ├── app_config.dart         # Supabase URL, API base URL
│           │   │   ├── routes.dart              # GoRouter route definitions
│           │   │   └── theme.dart               # App theme, colors, fonts
│           │   ├── constants/
│           │   │   └── api_endpoints.dart
│           │   ├── errors/
│           │   │   └── exceptions.dart
│           │   └── utils/
│           │       └── validators.dart          # Form validation helpers
│           │
│           ├── data/
│           │   ├── models/                      # Data classes (freezed/json_serializable)
│           │   │   ├── user_model.dart
│           │   │   ├── ride_model.dart
│           │   │   ├── booking_model.dart
│           │   │   ├── chat_message_model.dart
│           │   │   └── wallet_model.dart
│           │   ├── repositories/                # Data access layer
│           │   │   ├── auth_repository.dart
│           │   │   ├── ride_repository.dart
│           │   │   ├── booking_repository.dart
│           │   │   ├── chat_repository.dart
│           │   │   └── wallet_repository.dart
│           │   └── services/                    # API clients
│           │       ├── api_client.dart           # Dio instance with interceptors
│           │       ├── websocket_service.dart
│           │       ├── notification_service.dart
│           │       └── location_service.dart
│           │
│           ├── providers/                       # Riverpod providers
│           │   ├── auth_provider.dart
│           │   ├── ride_provider.dart
│           │   ├── booking_provider.dart
│           │   ├── chat_provider.dart
│           │   └── wallet_provider.dart
│           │
│           ├── presentation/
│           │   ├── screens/
│           │   │   ├── auth/
│           │   │   │   ├── login_screen.dart
│           │   │   │   ├── otp_screen.dart
│           │   │   │   └── register_screen.dart
│           │   │   ├── home/
│           │   │   │   └── home_screen.dart
│           │   │   ├── ride/
│           │   │   │   ├── create_ride_screen.dart
│           │   │   │   ├── ride_search_screen.dart
│           │   │   │   ├── ride_detail_screen.dart
│           │   │   │   └── my_rides_screen.dart
│           │   │   ├── booking/
│           │   │   │   ├── booking_screen.dart
│           │   │   │   └── my_bookings_screen.dart
│           │   │   ├── chat/
│           │   │   │   ├── chat_list_screen.dart
│           │   │   │   └── chat_screen.dart
│           │   │   ├── wallet/
│           │   │   │   ├── wallet_screen.dart
│           │   │   │   └── withdrawal_screen.dart
│           │   │   └── profile/
│           │   │       ├── profile_screen.dart
│           │   │       └── driver_registration_screen.dart
│           │   └── widgets/                     # Shared UI components
│           │       ├── ride_card.dart
│           │       ├── booking_card.dart
│           │       ├── map_picker.dart
│           │       └── loading_overlay.dart
│           │
│           └── app.dart                         # MaterialApp root
│
├── docker-compose.yml                           # Local dev: Postgres + Mongo
├── cloudbuild.yaml                              # GCP CI/CD
├── Makefile                                     # Common commands
└── README.md
```

---

## 5. Data Flow Summary

```
User Action                  Flutter                    FastAPI                       Storage
───────────                  ───────                    ───────                       ───────
Register/Login       →  supabase_flutter Auth   →  (Supabase handles directly)  →  Supabase Auth
                         Get JWT token

API Call             →  Dio + Bearer JWT        →  Middleware verifies JWT       →  Process request
                                                   Route → Service → Model       →  Supabase PostgreSQL

Create Ride          →  POST /rides             →  ride_service                  →  OSRM (distance)
                                                   fare_engine (price)           →  PostgreSQL (save)

Book Seat            →  POST /bookings          →  booking_service               →  PostgreSQL
                                                   notification_service          →  FCM (push to driver)

Send Chat            →  WebSocket connect       →  chat_service                  →  MongoDB (persist)
                        Send message            →  Forward to recipient          →  FCM (if offline)

Upload File          →  Supabase Storage SDK    →  (Direct upload to Supabase)  →  Supabase Storage
                        Save URL via API        →  Update DB record              →  PostgreSQL

Toll Cashback        →  POST /wallet/cashback   →  wallet_service                →  PostgreSQL
                        Upload proof            →  Supabase Storage              →  Admin reviews later
```

---

## 6. Environment Variables

```env
# Supabase
SUPABASE_URL=https://<project-ref>.supabase.co
SUPABASE_ANON_KEY=<your-anon-key>
SUPABASE_SERVICE_ROLE_KEY=<your-service-role-key>   # Server-side only, never expose
SUPABASE_DB_URL=postgresql+asyncpg://<user>:<password>@<db-host>:5432/postgres

# MongoDB
MONGO_URI=mongodb+srv://<user>:<password>@<cluster>.mongodb.net/goalong

# OSRM
OSRM_BASE_URL=http://osrm-vm-ip:5000

# FCM
FCM_CREDENTIALS_JSON=/path/to/firebase-adminsdk.json

# App
APP_ENV=development                     # development | staging | production
APP_SECRET_KEY=random-secret-key
CORS_ORIGINS=http://localhost:3000,http://localhost:8080

# GCP
GCS_BUCKET_NAME=goalong-uploads         # Only if using GCS alongside Supabase Storage
```

---

## 7. API Conventions

All modules follow these conventions consistently:

| Convention          | Standard                                                      |
|---------------------|---------------------------------------------------------------|
| Base URL            | `/api/v1/{module}`                                            |
| Auth Header         | `Authorization: Bearer <supabase_jwt>`                        |
| Request Format      | JSON (`application/json`)                                     |
| Response Envelope   | `{ "data": {...}, "message": "..." }`                         |
| Error Response      | `{ "detail": "Error message", "code": "ERROR_CODE" }`        |
| Pagination          | `?page=1&per_page=20` → Response includes `total`, `page`, `per_page` |
| IDs                 | UUID v4 everywhere                                            |
| Timestamps          | ISO 8601 with timezone (`2026-02-26T14:30:00+05:30`)          |
| HTTP Status Codes   | 200 (OK), 201 (Created), 400 (Bad Request), 401 (Unauth), 403 (Forbidden), 404 (Not Found), 422 (Validation Error) |

### Standard Error Response
```json
{
  "detail": "Ride not found",
  "code": "RIDE_NOT_FOUND"
}
```

### Standard Paginated Response
```json
{
  "data": [...],
  "total": 45,
  "page": 1,
  "per_page": 20
}
```

---

## 8. Things To Note

1. **Supabase JWT flows through everything.** Flutter authenticates with Supabase, gets a JWT, sends it to FastAPI. FastAPI verifies the JWT using Supabase's public key. No custom token generation needed.

2. **Supabase ≠ your backend.** Supabase handles auth, database hosting, and file storage. FastAPI handles ALL business logic. Never put business logic in Supabase Edge Functions or RLS policies — keep it in Python where it's testable and debuggable.

3. **Row Level Security (RLS)** should be OFF on Supabase tables. FastAPI connects using the `service_role_key` which bypasses RLS. All access control is handled in FastAPI middleware and service layer. This keeps authorization logic in one place.

4. **One service per module.** Each module has exactly one service file containing all business logic. Routers are thin — they validate input (Pydantic) and call service methods. Never put logic in routers.

5. **Alembic manages schema, not Supabase Dashboard.** Even though the DB is hosted on Supabase, all schema changes go through Alembic migrations. This ensures reproducibility and version control.

6. **MongoDB is ONLY for chat.** Don't expand MongoDB usage. Everything else is PostgreSQL. Two databases is the maximum for an MVP.
