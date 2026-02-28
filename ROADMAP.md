# GoAlong — 3-Week Implementation Roadmap

> 28 calendar days. 3-5 developers. FastAPI + Flutter + Supabase.
> All design docs and scaffold are aligned — ready to code.
> work by adolf.

---

## Overview

```
Week 0 (Days 1-2)    → Dev environment setup, first migration
Week 1 (Days 3-9)    → Core backend: Auth, Users, Drivers, Rides, Fare
Week 2 (Days 10-16)  → Bookings, Wallet, Chat, Notifications, Admin
Week 3 (Days 17-23)  → Integration, Flutter MVP, Testing, Deploy
Days 24-28           → Buffer, bug fixes, demo prep
```

---

## Week 0 — Foundation (Days 1-2)

> **Goal:** Every developer can run the project locally. All design docs and scaffold are already aligned.

### Day 1: Dev Environment Setup

| Task | Owner | Time |
|------|-------|------|
| Run `docker compose -f docker-compose.dev.yml up -d` (PostgreSQL 16 + MongoDB 7) | All | 15m |
| Run `alembic init` + create first migration from scaffold models | Backend Lead | 1.5h |
| Set up Supabase project (free tier): enable Phone Auth, create storage buckets (`profile-photos`, `driver-docs`, `toll-proofs`) | Backend Lead | 30m |
| Copy `.env.example` → `.env`, fill in Supabase + MongoDB credentials | All | 15m |
| Confirm `uvicorn app.main:app --reload` starts and `/health` returns 200 | All | 30m |

### Day 2: Tooling + OSRM

| Task | Owner | Time |
|------|-------|------|
| Set up OSRM on local Docker (India extract) for dev | DevOps/Any | 1.5h |
| Set up CI: GitHub Actions → lint + pytest on PR | DevOps/Any | 1h |
| Review system-design/ docs as a team — agree on conventions | All | 1h |
| Seed `platform_config` table (base_fare_per_km, fuel_price_per_litre, commission_pct, etc.) | Backend Lead | 30m |

### Day 2 Deliverable:
- [ ] `docker-compose.dev.yml` running (PostgreSQL + MongoDB)
- [ ] First Alembic migration applied
- [ ] Supabase project created with auth + storage buckets
- [ ] All devs can run the project locally
- [ ] CI pipeline running

---

## Week 1 — Core Backend (Days 3-9)

> **Goal:** A user can sign up, create a ride, and see fare estimates.

### Day 3-4: Auth + User Module

| Task | Owner | Est | Files |
|------|-------|-----|-------|
| Implement `config.py` (pydantic-settings, all env vars) | Dev A | 2h | `config.py`, `.env.example` |
| Implement `db/postgres.py` (async engine, session factory) | Dev A | 2h | `db/postgres.py` |
| Implement `middleware/auth.py` helpers (`decode_supabase_jwt`) | Dev A | 2h | `middleware/auth.py` |
| Implement `dependencies.py` (`get_db`, `get_current_user`, `get_pagination`) | Dev A | 2h | `dependencies.py` |
| Implement `main.py` (lifespan, CORS, router mounting, exception handlers) | Dev A | 2h | `main.py` |
| Implement `auth_service.py` (Supabase OTP send/verify, sync user to DB, token refresh) | Dev B | 4h | `services/auth_service.py` |
| Implement `routers/auth.py` (all 4 endpoints) | Dev B | 2h | `routers/auth.py` |
| Implement `user_service.py` (get/update profile, photo upload) | Dev B | 3h | `services/user_service.py` |
| Implement `routers/users.py` (all 3 endpoints) | Dev B | 1h | `routers/users.py` |
| Implement `storage_service.py` (Supabase upload/signed URL) | Dev B | 2h | `services/storage_service.py` |
| Write `tests/test_auth.py` (at least: OTP send, verify, refresh, sync) | Dev A | 2h | `tests/test_auth.py` |
| Write `tests/test_users.py` (get profile, update, get by ID) | Dev B | 1h | `tests/test_users.py` |

**Day 4 Checkpoint:**
- [ ] Auth flow works end-to-end (OTP → JWT → protected endpoint)
- [ ] User CRUD works
- [ ] Photo upload to Supabase Storage works

### Day 5-6: Driver Module

| Task | Owner | Est | Files |
|------|-------|-----|-------|
| Implement `driver_service.py` (register, get profile, upload docs, check status) | Dev C | 4h | `services/driver_service.py` |
| Implement `routers/drivers.py` (all 4 endpoints) | Dev C | 2h | `routers/drivers.py` |
| Implement driver document upload flow (Supabase Storage + DB record) | Dev C | 3h | `services/driver_service.py`, `services/storage_service.py` |
| Write `tests/test_drivers.py` | Dev C | 2h | `tests/test_drivers.py` |
| Implement `admin/views.py` — Driver approval/rejection actions | Dev A | 3h | `admin/views.py` |

**Day 6 Checkpoint:**
- [ ] Driver can register with vehicle info
- [ ] Driver can upload documents (license, RC, insurance)
- [ ] Admin can approve/reject drivers via SQLAdmin
- [ ] Approved driver status reflected in API

### Day 7-9: Rides + Fare Engine

| Task | Owner | Est | Files |
|------|-------|-----|-------|
| Implement `osrm_service.py` (route distance + duration from OSRM on e2-medium) | Dev A | 3h | `services/osrm_service.py` |
| Implement `fare_engine.py` (fuel-cost-sharing model: distance × fuel price ÷ mileage ÷ seats) | Dev A | 3h | `services/fare_engine.py` |
| Implement `ride_service.py` — `create_ride()` (validate driver, geocode, OSRM distance, calc fare, save) | Dev B | 4h | `services/ride_service.py` |
| Implement `ride_service.py` — `search_rides()` (city-pair + date + seats filter, pagination) | Dev B | 3h | `services/ride_service.py` |
| Implement `ride_service.py` — `get_ride_by_id()`, `get_driver_rides()`, `cancel_ride()` | Dev B | 3h | `services/ride_service.py` |
| **NEW:** Implement `ride_service.py` — `update_ride()`, `complete_ride()` | Dev B | 3h | `services/ride_service.py` |
| Implement `routers/rides.py` (all endpoints including new ones) | Dev B | 2h | `routers/rides.py` |
| Implement `routers/fare.py` (estimate + partial fare) | Dev A | 1h | `routers/fare.py` |
| Add `RideUpdateRequest` schema | Dev B | 30m | `schemas/ride.py` |
| **NEW:** Add `GET /rides/{ride_id}/bookings` endpoint | Dev B | 2h | `routers/rides.py` |
| Implement geocoding wrapper (Nominatim with cache) | Dev A | 2h | `services/osrm_service.py`, `utils/helpers.py` |
| Write `tests/test_rides.py` + `tests/test_fare.py` | Dev A | 3h | `tests/` |
| Implement `platform_config` model seeding (base fare, per-km rate, commission) | Dev A | 1h | Alembic data migration |

**Day 9 Checkpoint (Week 1 DONE):**
- [ ] Driver creates a ride with auto-calculated fare
- [ ] Passengers search rides by city-pair + date
- [ ] Fare estimate endpoint works
- [ ] Driver sees their rides list
- [ ] Driver can cancel a ride
- [ ] **All core models migrated and tested**

---

## Week 2 — Transactions + Communication (Days 10-16)

> **Goal:** A passenger can book a ride, chat with driver, and see wallet balance.

### Day 10-11: Booking Module

| Task | Owner | Est | Files |
|------|-------|-----|-------|
| Implement `booking_service.py` — `create_booking()` (validate seats, check availability, atomic seat decrement) | Dev B | 4h | `services/booking_service.py` |
| Implement `booking_service.py` — `cancel_booking()` (restore seats, handle partial fare) | Dev B | 3h | `services/booking_service.py` |
| **NEW:** Implement `booking_service.py` — `cancel_bookings_for_ride()` (bulk cancel for driver cancellation) | Dev B | 2h | `services/booking_service.py` |
| **NEW:** Implement `booking_service.py` — `complete_booking()` + auto-trigger from `ride_service.complete_ride()` | Dev B | 2h | `services/booking_service.py` |
| Implement `routers/bookings.py` (all 4 endpoints) | Dev B | 2h | `routers/bookings.py` |
| Add DB transaction boundaries: `async with db.begin()` on booking create/cancel | Dev B | 1h | `services/booking_service.py` |
| Write `tests/test_bookings.py` | Dev B | 3h | `tests/test_bookings.py` |

**Day 11 Checkpoint:**
- [ ] Passenger books a ride (seats decremented atomically)
- [ ] Passenger cancels booking (seats restored)
- [ ] Driver cancels ride → all bookings auto-cancelled
- [ ] Driver completes ride → all bookings auto-completed

### Day 12-13: Wallet + Cashback

| Task | Owner | Est | Files |
|------|-------|-----|-------|
| Implement `wallet_service.py` — `get_or_create_wallet()` | Dev C | 1h | `services/wallet_service.py` |
| Implement `wallet_service.py` — `credit_cashback()` (with `SELECT ... FOR UPDATE` locking) | Dev C | 3h | `services/wallet_service.py` |
| Implement `wallet_service.py` — `request_withdrawal()`, `approve_transaction()` | Dev C | 3h | `services/wallet_service.py` |
| Implement `routers/wallet.py` (all 4 endpoints) | Dev C | 2h | `routers/wallet.py` |
| Wire cashback trigger: `complete_booking()` → `wallet_service.credit_cashback()` | Dev C | 2h | `services/booking_service.py` |
| Admin wallet actions in SQLAdmin (approve/reject withdrawal) | Dev C | 2h | `admin/views.py` |
| Write `tests/test_wallet.py` | Dev C | 2h | `tests/test_wallet.py` |

**Day 13 Checkpoint:**
- [ ] Wallet created on first auth
- [ ] Cashback auto-credited on booking completion
- [ ] Passenger requests withdrawal
- [ ] Admin approves/rejects withdrawal via SQLAdmin

### Day 14-15: Chat + Notifications

| Task | Owner | Est | Files |
|------|-------|-----|-------|
| Implement `db/mongo.py` (Motor async client, connection lifecycle) | Dev A | 1h | `db/mongo.py` |
| Implement `chat_service.py` — `save_message()`, `get_history()`, `get_unread_count()`, `mark_as_read()` | Dev A | 4h | `services/chat_service.py` |
| Implement WebSocket endpoint (`routers/chat.py`) — connect, auth, message relay, disconnect | Dev A | 4h | `routers/chat.py` |
| **NEW:** Add `PUT /chat/{booking_id}/read` endpoint | Dev A | 1h | `routers/chat.py` |
| Implement `notification_service.py` — FCM integration (`send_push`, all notification types) | Dev C | 4h | `services/notification_service.py` |
| **NEW:** Add `send_driver_approved()`, `send_driver_rejected()` notifications | Dev C | 1h | `services/notification_service.py` |
| Wire notifications into: booking created, booking cancelled, ride cancelled, chat message, ride completed | Dev C | 2h | Various services |
| Write `tests/test_chat.py` | Dev A | 2h | `tests/test_chat.py` |

**Day 15 Checkpoint:**
- [ ] WebSocket chat works between driver and passenger
- [ ] Chat history persisted in MongoDB
- [ ] Unread count works
- [ ] FCM push notifications fire on key events

### Day 16: Middleware + Utils + Polish

| Task | Owner | Est | Files |
|------|-------|-----|-------|
| Implement `middleware/logging.py` (structlog JSON logging, request ID) | Dev A | 2h | `middleware/logging.py` |
| Implement `utils/exceptions.py` (AppException + handler registration in main.py) | Dev A | 1h | `utils/exceptions.py`, `main.py` |
| Implement `utils/constants.py` (enums, status values) | Dev A | 1h | `utils/constants.py` |
| Add SlowAPI rate limiting to auth endpoints (OTP send: 3/min, verify: 5/min) | Dev A | 2h | `main.py`, `routers/auth.py` |
| API documentation review — Swagger descriptions, response models | Dev B | 2h | All routers |
| Admin panel security: add IP whitelist or API key check | Dev C | 2h | `admin/views.py` |

**Day 16 Checkpoint (Week 2 DONE):**
- [ ] Full booking lifecycle: search → book → chat → ride → complete → cashback
- [ ] All notifications working
- [ ] Logging structured and operational
- [ ] Rate limiting on auth
- [ ] Admin panel secured

---

## Week 3 — Integration + Flutter + Deploy (Days 17-23)

> **Goal:** Working app on real phones, deployed to GCP.

### Day 17-18: Flutter MVP (Parallel Track)

> Flutter development should ideally start mid-Week 1 with auth screens.
> These tasks assume Flutter screens for auth/user were started in Week 1-2 by a frontend dev.

| Task | Owner | Est |
|------|-------|-----|
| Auth screens: Phone OTP login, email signup | Flutter Dev | Done by now |
| User profile screen (view + edit + photo) | Flutter Dev | Done by now |
| **Ride search screen** (city picker, date, seats, results list) | Flutter Dev | 4h |
| **Ride detail screen** (map, driver info, fare, book button) | Flutter Dev | 4h |
| **Create ride screen** (driver: source/dest, date/time, seats, vehicle) | Flutter Dev | 4h |
| **My bookings screen** (passenger: list, status, cancel) | Flutter Dev | 3h |
| **My rides screen** (driver: list, passengers, complete) | Flutter Dev | 3h |
| **Chat screen** (WebSocket, message list, input) | Flutter Dev | 4h |
| **Wallet screen** (balance, transactions, withdraw request) | Flutter Dev | 3h |
| **Driver registration screen** (vehicle info + doc upload) | Flutter Dev | 3h |

### Day 19-20: Integration Testing

| Task | Owner | Est |
|------|-------|-----|
| End-to-end test: Driver signup → approve → create ride → passenger search → book → chat → complete → cashback | All | 4h |
| Fix all integration bugs found | All | 8h |
| Load test: 50 concurrent ride searches, 20 simultaneous bookings | Backend Lead | 3h |
| WebSocket stress test: 10 simultaneous chat connections | Backend Lead | 2h |
| Supabase auth edge cases: expired tokens, invalid OTP, rate limits | Dev A | 2h |
| OSRM edge cases: routes with no road connection, very long routes | Dev A | 1h |

### Day 21-22: Deploy to GCP

| Task | Owner | Est |
|------|-------|-----|
| Create GCP project, enable Cloud Run, Cloud Build, Secret Manager | DevOps | 2h |
| Push secrets to GCP Secret Manager (Supabase keys, MongoDB URI, JWT secret) | DevOps | 1h |
| Create `cloudbuild.yaml` (build → push to Artifact Registry → deploy to Cloud Run) | DevOps | 3h |
| Deploy backend to Cloud Run (asia-south1, min: 0, max: 4) | DevOps | 1h |
| Set up OSRM on GCP Compute Engine (e2-medium 4GB RAM, India OSM extract) | DevOps | 3h |
| Configure Supabase production project (separate from dev) | DevOps | 1h |
| Set up MongoDB Atlas M0 cluster (production) | DevOps | 30m |
| DNS + custom domain (optional for MVP) | DevOps | 1h |
| Deploy Flutter app as APK (internal testing track on Play Console) | Flutter Dev | 2h |
| Smoke test on production deployment | All | 2h |

### Day 23: Final Polish

| Task | Owner | Est |
|------|-------|-----|
| Fix production bugs | All | 4h |
| API response time check (<500ms p95) | Backend Lead | 1h |
| Security checklist: no exposed secrets, CORS locked to domain, admin secured | Backend Lead | 2h |
| README.md: setup instructions, API docs link, architecture overview | Any | 2h |

**Day 23 Checkpoint (Week 3 DONE):**
- [ ] App running on GCP Cloud Run
- [ ] Flutter APK distributed for testing
- [ ] Full ride lifecycle works in production
- [ ] Admin panel accessible and secured
- [ ] CI/CD pipeline: push to main → auto-deploy

---

## Days 24-28: Buffer

> **Reality buffer.** Things always take longer than estimated.

| Day | Purpose |
|-----|---------|
| 24 | Overflow from Week 3 tasks |
| 25 | Bug fixes from internal testing |
| 26 | Performance tuning if needed |
| 27 | Demo preparation + walkthrough |
| 28 | **Demo day** |

---

## Sprint Velocity Assumptions

| Metric | Value |
|--------|-------|
| Developers | 3 backend + 1 Flutter (minimum) |
| Hours/day/dev | 6 productive hours |
| Total dev-hours | ~420h (3 weeks × 5 devs × 6h × 5 days... adjusted for parallel work) |
| Backend estimated | ~180h |
| Flutter estimated | ~120h |
| DevOps/infra | ~40h |
| Testing/buffer | ~80h |

---

## Risk Register

| Risk | Probability | Impact | Mitigation |
|------|------------|--------|------------|
| Supabase free tier rate limits hit | Medium | High | Cache JWT verification, batch DB queries |
| OSRM processing India OSM takes too long | Medium | High | Pre-process locally, upload processed files |
| WebSocket cold start > 10s | High | Medium | Accept for MVP, add `min-instances: 1` if needed |
| Flutter dev bottleneck (1 dev) | High | High | Prioritize: auth → search → booking → chat → wallet |
| MongoDB Atlas M0 storage limit (512MB) | Low | Medium | 90-day TTL on chat messages, monitor usage |
| Scope creep | High | High | Stick to this roadmap. No new features until Day 28. |

---

## Definition of Done (MVP)

- [ ] Driver can: register → get approved → create ride → see passengers → complete ride
- [ ] Passenger can: sign up → search rides → book → chat with driver → get cashback
- [ ] Admin can: approve drivers → manage withdrawals → view platform stats
- [ ] Wallet: cashback credited on ride completion, withdrawal request flow works
- [ ] Chat: real-time messaging between matched driver-passenger
- [ ] Notifications: push notifications for booking, cancellation, ride completion
- [ ] Deployed: Cloud Run + Supabase + MongoDB Atlas + OSRM on GCP
- [ ] Tested: All critical paths have automated tests passing in CI

---

*End of roadmap.*
