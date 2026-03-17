# Module 10: API Contracts

> **This is the single source of truth for every HTTP endpoint and WebSocket channel.** Frontend devs read this, not the module files. Every request/response is documented with exact field names, types, validation rules, error codes, and curl examples.

---

## Table of Contents

1. [Conventions](#1-conventions)
2. [Auth Endpoints](#2-auth-endpoints)
3. [User Endpoints](#3-user-endpoints)
4. [Driver Endpoints](#4-driver-endpoints)
5. [Ride Endpoints](#5-ride-endpoints)
6. [Booking Endpoints](#6-booking-endpoints)
7. [Fare Engine Endpoints](#7-fare-engine-endpoints)
8. [Chat Endpoints](#8-chat-endpoints)
9. [Wallet Endpoints](#9-wallet-endpoints)
10. [Admin Endpoints](#10-admin-endpoints)
11. [Health](#11-health)
12. [Error Code Registry](#12-error-code-registry)
13. [Pagination Contract](#13-pagination-contract)
14. [Idempotency & Retry Policy](#14-idempotency--retry-policy)

---

## 1. Conventions

### Base URL
```
Production:  https://api.goalong.in/api/v1
Development: http://localhost:8080/api/v1
```

### Authentication
All endpoints except `/health` require a valid Supabase JWT in the `Authorization` header:
```
Authorization: Bearer <supabase_access_token>
```

### Standard Response Envelope

**Success (single resource):**
```json
{
  "data": { ... },
  "message": "optional human-readable message"
}
```

**Success (list with pagination):**
```json
{
  "data": [ ... ],
  "total": 42,
  "page": 1,
  "per_page": 20
}
```

**Error:**
```json
{
  "detail": "Human-readable error message",
  "code": "MACHINE_READABLE_ERROR_CODE"
}
```

### Request Rules
| Rule                        | Value                                         |
|-----------------------------|-----------------------------------------------|
| Content-Type                | `application/json` (unless file upload)       |
| Timestamps in requests      | ISO 8601 with timezone: `2026-03-15T08:30:00+05:30` |
| Timestamps in responses     | ISO 8601 UTC: `2026-03-15T03:00:00Z`         |
| UUIDs                       | Standard v4 format: `550e8400-e29b-41d4-a716-446655440000` |
| Money fields                | String-encoded Decimal, 2 decimal places: `"125.50"` |
| Coordinates                 | Float, latitude: `[-90, 90]`, longitude: `[-180, 180]` |
| Pagination defaults         | `page=1`, `per_page=20`, max `per_page=50`   |

---

## 2. Auth Endpoints

### POST /auth/sync
Sync Supabase user to the app database. Call this after first Supabase login.

**Request:** No body needed. User info is extracted from the JWT.

**Response `200`:**
```json
{
  "data": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "name": null,
    "email": "kuhan@example.com",
    "phone": "+919876543210",
    "profile_photo": null,
    "role": "passenger",
    "created_at": "2026-03-01T10:00:00Z"
  },
  "message": "User synced successfully"
}
```

**Errors:**
| HTTP | Code | Detail |
|------|------|--------|
| 401  | `INVALID_TOKEN` | Invalid or expired token |

---

### POST /auth/fcm-token
Register device FCM token for push notifications.

**Request:**
```json
{
  "token": "fMCtoken123abc..."
}
```

| Field   | Type   | Required | Validation       |
|---------|--------|----------|------------------|
| `token` | string | Yes      | max_length=500   |

**Response `200`:**
```json
{
  "message": "FCM token registered"
}
```

---

### DELETE /auth/fcm-token
Remove FCM token on logout.

**Response `200`:**
```json
{
  "message": "FCM token removed"
}
```

---

## 3. User Endpoints

### GET /users/me
Get current user's profile.

**Response `200`:**
```json
{
  "data": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "name": "Kuhan",
    "email": "kuhan@example.com",
    "phone": "+919876543210",
    "profile_photo": "https://xxxx.supabase.co/storage/v1/object/public/profile-photos/abc.jpg",
    "role": "driver",
    "created_at": "2026-03-01T10:00:00Z"
  }
}
```

---

### PUT /users/me
Update current user's profile.

**Request:**
```json
{
  "name": "Kuhan S",
  "email": "kuhan.s@example.com",
  "profile_photo": "https://xxxx.supabase.co/storage/v1/object/public/profile-photos/new.jpg"
}
```

| Field           | Type           | Required | Validation        |
|-----------------|----------------|----------|-------------------|
| `name`          | string \| null | No       | max_length=100    |
| `email`         | string \| null | No       | valid email, max_length=255 |
| `profile_photo` | string \| null | No       | valid URL         |

All fields are optional — only provided fields are updated.

**Response `200`:**
```json
{
  "data": { "...same as GET /users/me..." }
}
```

**Errors:**
| HTTP | Code | Detail |
|------|------|--------|
| 400  | `EMAIL_TAKEN` | Email already in use by another account |

---

## 4. Driver Endpoints

### POST /drivers/register
Submit driver registration (creates a pending driver profile).

**Request:**
```json
{
  "license_number": "KA0120200001234",
  "vehicle_make": "Maruti",
  "vehicle_model": "Swift",
  "vehicle_number": "KA-01-AB-1234",
  "vehicle_type": "hatchback",
  "vehicle_color": "White",
  "mileage_kmpl": 22.5,
  "seat_capacity": 3
}
```

| Field             | Type    | Required | Validation                                  |
|-------------------|---------|----------|---------------------------------------------|
| `license_number`  | string  | Yes      | max_length=50                               |
| `vehicle_make`    | string  | Yes      | max_length=50                               |
| `vehicle_model`   | string  | Yes      | max_length=50                               |
| `vehicle_number`  | string  | Yes      | max_length=20                               |
| `vehicle_type`    | string  | Yes      | enum: `hatchback`, `sedan`, `suv`, `muv`    |
| `vehicle_color`   | string  | No       | max_length=30                               |
| `mileage_kmpl`    | decimal | Yes      | 0 < value ≤ 50                              |
| `seat_capacity`   | integer | Yes      | 1 ≤ value ≤ 8                               |

**Response `201`:**
```json
{
  "data": {
    "id": "660e8400-e29b-41d4-a716-446655440001",
    "license_number": "KA0120200001234",
    "vehicle_make": "Maruti",
    "vehicle_model": "Swift",
    "vehicle_number": "KA-01-AB-1234",
    "vehicle_type": "hatchback",
    "vehicle_color": "White",
    "mileage_kmpl": "22.50",
    "seat_capacity": 3,
    "verification_status": "pending",
    "rejection_reason": null,
    "onboarded_at": null,
    "created_at": "2026-03-01T10:00:00Z"
  },
  "message": "Driver registration submitted for verification"
}
```

**Errors:**
| HTTP | Code | Detail |
|------|------|--------|
| 400  | `DRIVER_ALREADY_REGISTERED` | Driver profile already exists |
| 422  | `VALIDATION_ERROR`          | Field validation failures     |

---

### GET /drivers/me
Get current driver profile + verification status.

**Response `200`:** Same schema as POST /drivers/register response.

**Errors:**
| HTTP | Code | Detail |
|------|------|--------|
| 404  | `DRIVER_NOT_FOUND` | No driver profile found. Register first. |

---

### PUT /drivers/me
Update vehicle details. Only allowed while `verification_status == 'pending'`.

**Request:** Same fields as POST /drivers/register (all optional).

**Errors:**
| HTTP | Code | Detail |
|------|------|--------|
| 400  | `DRIVER_ALREADY_VERIFIED` | Cannot edit after approval. Contact support. |
| 404  | `DRIVER_NOT_FOUND`        | Register as driver first                     |

---

### POST /drivers/documents
Upload a document (URL from Supabase Storage).

**Request:**
```json
{
  "doc_type": "driving_license",
  "file_url": "https://xxxx.supabase.co/storage/v1/object/driver-documents/dl_abc.jpg"
}
```

| Field      | Type   | Required | Validation                                                         |
|------------|--------|----------|--------------------------------------------------------------------|
| `doc_type` | string | Yes      | enum: `driving_license`, `vehicle_rc`, `insurance`, `aadhar`, `pan`|
| `file_url` | string | Yes      | valid URL pointing to Supabase Storage                             |

**Response `201`:**
```json
{
  "data": {
    "id": "770e8400-e29b-41d4-a716-446655440002",
    "doc_type": "driving_license",
    "file_url": "https://xxxx.supabase.co/storage/v1/object/driver-documents/dl_abc.jpg",
    "uploaded_at": "2026-03-01T10:05:00Z"
  }
}
```

**Errors:**
| HTTP | Code | Detail |
|------|------|--------|
| 400  | `DOCUMENT_DUPLICATE` | Document of type 'driving_license' already uploaded. Delete and re-upload. |
| 404  | `DRIVER_NOT_FOUND`   | Register as driver first |

---

### GET /drivers/documents
List all uploaded documents for the current driver.

**Response `200`:**
```json
{
  "data": [
    {
      "id": "770e8400-...",
      "doc_type": "driving_license",
      "file_url": "https://...",
      "uploaded_at": "2026-03-01T10:05:00Z"
    },
    {
      "id": "880e8400-...",
      "doc_type": "vehicle_rc",
      "file_url": "https://...",
      "uploaded_at": "2026-03-01T10:06:00Z"
    }
  ]
}
```

---

## 5. Ride Endpoints

### POST /rides
Create a new ride. Only approved drivers.

**Request:**
```json
{
  "source_address": "Koramangala, Bangalore",
  "source_lat": 12.9352,
  "source_lng": 77.6245,
  "dest_address": "Mysore Palace, Mysore",
  "dest_lat": 12.3051,
  "dest_lng": 76.6551,
  "departure_time": "2026-03-15T08:30:00+05:30",
  "total_seats": 3
}
```

| Field              | Type     | Required | Validation                      |
|--------------------|----------|----------|---------------------------------|
| `source_address`   | string   | Yes      | non-empty                       |
| `source_lat`       | float    | Yes      | -90 ≤ value ≤ 90               |
| `source_lng`       | float    | Yes      | -180 ≤ value ≤ 180             |
| `dest_address`     | string   | Yes      | non-empty                       |
| `dest_lat`         | float    | Yes      | -90 ≤ value ≤ 90               |
| `dest_lng`         | float    | Yes      | -180 ≤ value ≤ 180             |
| `departure_time`   | datetime | Yes      | Must be in the future           |
| `total_seats`      | integer  | Yes      | 1 ≤ value ≤ driver's seat_capacity |

**Response `201`:**
```json
{
  "data": {
    "id": "990e8400-e29b-41d4-a716-446655440003",
    "driver_name": "Kuhan",
    "vehicle_info": "Maruti Swift (White) KA-01-AB-1234",
    "source_address": "Koramangala, Bangalore",
    "source_lat": 12.9352,
    "source_lng": 77.6245,
    "dest_address": "Mysore Palace, Mysore",
    "dest_lat": 12.3051,
    "dest_lng": 76.6551,
    "total_distance_km": "143.50",
    "estimated_duration": 178,
    "route_geometry": "encoded_polyline_string_here...",
    "departure_time": "2026-03-15T03:00:00Z",
    "total_seats": 3,
    "available_seats": 3,
    "total_fare": "420.00",
    "per_seat_fare": "140.00",
    "status": "active",
    "created_at": "2026-03-01T10:00:00Z"
  }
}
```

**Errors:**
| HTTP | Code | Detail |
|------|------|--------|
| 400  | `DEPARTURE_IN_PAST`      | Departure time must be in the future              |
| 400  | `SEATS_EXCEED_CAPACITY`  | Cannot offer more than {N} seats                  |
| 403  | `DRIVER_NOT_APPROVED`    | Driver not verified                               |
| 502  | `OSRM_UNAVAILABLE`       | Routing service unavailable                       |
| 400  | `NO_ROUTE_FOUND`         | Could not find a route between these locations    |

---

### GET /rides
Search for rides. Returns active rides matching source/destination area and date.

**Query Parameters:**
| Param        | Type   | Required | Default | Description                    |
|--------------|--------|----------|---------|--------------------------------|
| `src_lat`    | float  | Yes      | —       | Source latitude                |
| `src_lng`    | float  | Yes      | —       | Source longitude               |
| `dst_lat`    | float  | Yes      | —       | Destination latitude           |
| `dst_lng`    | float  | Yes      | —       | Destination longitude          |
| `date`       | string | Yes      | —       | Date in `YYYY-MM-DD`          |
| `radius_km`  | float  | No       | 15.0    | Search radius in km            |
| `page`       | int    | No       | 1       | Pagination page                |
| `per_page`   | int    | No       | 20      | Results per page (max 50)      |

**Response `200`:**
```json
{
  "data": [
    {
      "id": "990e8400-...",
      "driver_name": "Kuhan",
      "vehicle_info": "Maruti Swift (White) KA-01-AB-1234",
      "source_address": "Koramangala, Bangalore",
      "dest_address": "Mysore Palace, Mysore",
      "total_distance_km": "143.50",
      "estimated_duration": 178,
      "departure_time": "2026-03-15T03:00:00Z",
      "total_seats": 3,
      "available_seats": 2,
      "per_seat_fare": "140.00",
      "status": "active",
      "created_at": "2026-03-01T10:00:00Z"
    }
  ],
  "total": 5,
  "page": 1,
  "per_page": 20
}
```

**Matching Algorithm:**
1. Bounding box filter on `source_lat`/`source_lng` within `radius_km` of `src_lat`/`src_lng`
2. Bounding box filter on `dest_lat`/`dest_lng` within `radius_km` of `dst_lat`/`dst_lng`
3. Date filter: `departure_time` falls on the requested `date`
4. Only `status = 'active'` and `available_seats > 0`
5. Ordered by `departure_time ASC`

---

### GET /rides/{ride_id}
Get full ride details.

**Response `200`:** Full `RideDetailResponse` (includes lat/lng, geometry, total_fare).

**Errors:**
| HTTP | Code | Detail |
|------|------|--------|
| 404  | `RIDE_NOT_FOUND` | Ride not found |

---

### PUT /rides/{ride_id}
Edit a ride. Only the ride owner. Restricted fields.

**Request:**
```json
{
  "departure_time": "2026-03-15T09:00:00+05:30",
  "total_seats": 4
}
```

| Field            | Type     | Required | Rules                                               |
|------------------|----------|----------|-----------------------------------------------------|
| `departure_time` | datetime | No       | Must be future. Cannot change if bookings exist.    |
| `total_seats`    | integer  | No       | 1-8. Cannot reduce below currently booked seats.    |

**Source/destination cannot be changed.** Create a new ride instead.

**Errors:**
| HTTP | Code | Detail |
|------|------|--------|
| 400  | `RIDE_NOT_ACTIVE`               | Ride is not active                                              |
| 400  | `DEPARTURE_IN_PAST`             | Departure must be in the future                                 |
| 400  | `DEPARTURE_CHANGE_HAS_BOOKINGS` | Cannot change departure time — passengers already booked        |
| 400  | `SEATS_BELOW_BOOKED`            | Cannot reduce seats below {N} (already booked)                  |
| 403  | `NOT_RIDE_OWNER`                | Not your ride                                                   |
| 404  | `RIDE_NOT_FOUND`                | Ride not found                                                  |

---

### DELETE /rides/{ride_id}
Cancel a ride. All confirmed bookings are auto-cancelled + passengers notified via FCM.

**Response `200`:**
```json
{
  "data": { "...ride with status: cancelled..." },
  "message": "Ride cancelled. 2 passenger(s) notified."
}
```

**Errors:**
| HTTP | Code | Detail |
|------|------|--------|
| 400  | `RIDE_NOT_ACTIVE` | Ride is not active   |
| 403  | `NOT_RIDE_OWNER`  | Not your ride        |
| 404  | `RIDE_NOT_FOUND`  | Ride not found       |

---

### GET /rides/my-rides
List current driver's rides.

**Query Parameters:**
| Param      | Type   | Required | Default | Options                          |
|------------|--------|----------|---------|----------------------------------|
| `status`   | string | No       | all     | `active`, `completed`, `cancelled` |
| `page`     | int    | No       | 1       |                                  |
| `per_page` | int    | No       | 20      | max 50                           |

**Response `200`:** Paginated list of `RideResponse`.

---

### GET /rides/geocode
Geocode an address to coordinates using Nominatim.

**Query Parameters:**
| Param   | Type   | Required | Description              |
|---------|--------|----------|--------------------------|
| `q`     | string | Yes      | Address search query     |

**Response `200`:**
```json
{
  "data": {
    "lat": 12.9352,
    "lng": 77.6245,
    "display_name": "Koramangala, Bengaluru, Karnataka, India"
  }
}
```

**Errors:**
| HTTP | Code | Detail |
|------|------|--------|
| 404  | `GEOCODE_NOT_FOUND` | Could not geocode this address |

---

## 6. Booking Endpoints

### POST /bookings
Book seat(s) on a ride. Race-condition safe (row-level lock on ride).

**Request:**
```json
{
  "ride_id": "990e8400-e29b-41d4-a716-446655440003",
  "pickup_address": "Electronic City, Bangalore",
  "pickup_lat": 12.8399,
  "pickup_lng": 77.6770,
  "seats_booked": 1
}
```

| Field            | Type    | Required | Validation                |
|------------------|---------|----------|---------------------------|
| `ride_id`        | UUID    | Yes      | Must reference active ride |
| `pickup_address` | string  | Yes      | non-empty                  |
| `pickup_lat`     | float   | Yes      | -90 ≤ value ≤ 90          |
| `pickup_lng`     | float   | Yes      | -180 ≤ value ≤ 180        |
| `seats_booked`   | integer | No       | Default 1, 1 ≤ value ≤ 4  |

**What happens server-side:**
1. Lock ride row with `SELECT ... FOR UPDATE`
2. Validate ride is active, not departed, seats available
3. Calculate partial distance from pickup → ride destination via OSRM
4. Calculate proportional fare
5. Decrement `available_seats`
6. Create booking record
7. Notify driver via FCM

**Response `201`:**
```json
{
  "data": {
    "id": "aa0e8400-e29b-41d4-a716-446655440004",
    "ride_id": "990e8400-e29b-41d4-a716-446655440003",
    "passenger_id": "550e8400-e29b-41d4-a716-446655440000",
    "pickup_address": "Electronic City, Bangalore",
    "distance_km": "98.20",
    "fare": "96.00",
    "seats_booked": 1,
    "status": "confirmed",
    "booked_at": "2026-03-10T14:30:00Z",
    "cancelled_at": null,
    "ride_source": "Koramangala, Bangalore",
    "ride_destination": "Mysore Palace, Mysore",
    "departure_time": "2026-03-15T03:00:00Z",
    "driver_name": "Kuhan",
    "vehicle_info": "Maruti Swift (White) KA-01-AB-1234"
  }
}
```

**Errors:**
| HTTP | Code | Detail |
|------|------|--------|
| 400  | `RIDE_NOT_ACTIVE`     | Ride is not active                              |
| 400  | `RIDE_DEPARTED`       | Ride has already departed                       |
| 400  | `INSUFFICIENT_SEATS`  | Only {N} seat(s) available                      |
| 400  | `SELF_BOOKING`        | Cannot book your own ride                       |
| 400  | `DUPLICATE_BOOKING`   | You already have a booking on this ride         |
| 404  | `RIDE_NOT_FOUND`      | Ride not found                                  |
| 502  | `OSRM_UNAVAILABLE`    | Routing service unavailable (partial distance)  |

---

### GET /bookings/my-bookings
List current user's bookings (as passenger).

**Query Parameters:**
| Param      | Type   | Required | Default | Options                               |
|------------|--------|----------|---------|---------------------------------------|
| `status`   | string | No       | all     | `confirmed`, `completed`, `cancelled` |
| `page`     | int    | No       | 1       |                                       |
| `per_page` | int    | No       | 20      | max 50                                |

**Response `200`:** Paginated `BookingListResponse`.

---

### GET /bookings/{booking_id}
Get booking details.

**Errors:**
| HTTP | Code | Detail |
|------|------|--------|
| 403  | `NOT_BOOKING_OWNER` | Not your booking  |
| 404  | `BOOKING_NOT_FOUND` | Booking not found  |

---

### PUT /bookings/{booking_id}/cancel
Cancel a booking.

**Cancellation Rules:**
- Can cancel if `≥ 2 hours` before `departure_time` → free cancellation
- Cannot cancel if `< 2 hours` before departure → `CANCEL_WINDOW_CLOSED`
- Cannot cancel if already cancelled/completed

**Response `200`:**
```json
{
  "data": {
    "...booking with status: cancelled, cancelled_at: timestamp..."
  },
  "message": "Booking cancelled successfully"
}
```

**Errors:**
| HTTP | Code | Detail |
|------|------|--------|
| 400  | `BOOKING_NOT_ACTIVE`      | Booking is not active                                |
| 400  | `CANCEL_WINDOW_CLOSED`    | Cannot cancel within 2 hours of departure            |
| 403  | `NOT_BOOKING_OWNER`       | Not your booking                                     |
| 404  | `BOOKING_NOT_FOUND`       | Booking not found                                    |

---

## 7. Fare Engine Endpoints

### POST /fare/calculate
Preview fare for a full route (used during ride creation).

**Request:**
```json
{
  "source_lat": 12.9352,
  "source_lng": 77.6245,
  "dest_lat": 12.3051,
  "dest_lng": 76.6551,
  "mileage_kmpl": 22.5,
  "seats": 3
}
```

| Field         | Type    | Required | Validation |
|---------------|---------|----------|------------|
| `source_lat`  | float   | Yes      | -90 to 90  |
| `source_lng`  | float   | Yes      | -180 to 180|
| `dest_lat`    | float   | Yes      | -90 to 90  |
| `dest_lng`    | float   | Yes      | -180 to 180|
| `mileage_kmpl`| float   | Yes      | > 0        |
| `seats`       | integer | Yes      | 1-8        |

**Response `200`:**
```json
{
  "data": {
    "distance_km": "143.50",
    "estimated_duration_minutes": 178,
    "per_seat_fare": "140.00",
    "total_fare": "420.00",
    "fuel_cost": "669.33",
    "platform_fee_per_seat": "18.33"
  }
}
```

---

### POST /fare/calculate-partial
Preview fare for a partial route (used during booking).

**Request:**
```json
{
  "ride_id": "990e8400-e29b-41d4-a716-446655440003",
  "pickup_lat": 12.8399,
  "pickup_lng": 77.6770
}
```

**Response `200`:**
```json
{
  "data": {
    "total_route_distance_km": "143.50",
    "passenger_distance_km": "98.20",
    "full_route_per_seat_fare": "140.00",
    "partial_fare": "96.00"
  }
}
```

**Errors:**
| HTTP | Code | Detail |
|------|------|--------|
| 404  | `RIDE_NOT_FOUND`   | Ride not found          |
| 502  | `OSRM_UNAVAILABLE` | Routing service unavailable |

---

## 8. Chat Endpoints

### WebSocket /chat/ws/{booking_id}?token={jwt}
Real-time bidirectional chat. Only the booking's driver and passenger can connect.

**Connection:**
```
wss://api.goalong.in/api/v1/chat/ws/aa0e8400-...?token=eyJhbGciOiJIUzI1NiIs...
```

**Auth:** JWT passed as query parameter (WebSocket doesn't support headers).

**Client → Server Message:**
```json
{
  "message": "Hi, I'll be at the pickup at 8:25 AM"
}
```

| Field     | Type   | Required | Validation     |
|-----------|--------|----------|----------------|
| `message` | string | Yes      | max_length=1000, non-empty |

**Server → Client Message:**
```json
{
  "type": "message",
  "booking_id": "aa0e8400-...",
  "sender_id": "550e8400-...",
  "message": "Hi, I'll be at the pickup at 8:25 AM",
  "sent_at": "2026-03-14T10:30:00Z"
}
```

**Server → Client System Events:**
```json
{
  "type": "read_receipt",
  "booking_id": "aa0e8400-...",
  "read_by": "660e8400-...",
  "read_at": "2026-03-14T10:30:05Z"
}
```

**WebSocket Close Codes:**
| Code | Reason |
|------|--------|
| 4001 | Authentication failed (invalid/expired token) |
| 4003 | Chat access denied (not part of this booking) |

**Keep-alive:** Client must send `ping` frame every 25 seconds. Server responds with `pong`. Cloud Run kills idle connections at 300s.

---

### GET /chat/{booking_id}/history
Fetch paginated chat history.

**Query Parameters:**
| Param    | Type   | Required | Default | Description                    |
|----------|--------|----------|---------|--------------------------------|
| `limit`  | int    | No       | 50      | Messages to return (max 100)   |
| `before` | string | No       | —       | ISO timestamp cursor (load older messages) |

**Response `200`:**
```json
{
  "data": [
    {
      "id": "65f8a1b2c3d4e5f678901234",
      "booking_id": "aa0e8400-...",
      "sender_id": "550e8400-...",
      "receiver_id": "660e8400-...",
      "message": "Hi, I'll be at the pickup at 8:25 AM",
      "sent_at": "2026-03-14T10:30:00Z",
      "read": true
    }
  ]
}
```

Messages are ordered newest-first. Use `before` cursor to paginate backwards.

**Errors:**
| HTTP | Code | Detail |
|------|------|--------|
| 403  | `CHAT_ACCESS_DENIED` | You are not part of this booking |
| 404  | `BOOKING_NOT_FOUND`  | Booking not found                |

---

### GET /chat/unread-count
Get total unread message count across all bookings.

**Response `200`:**
```json
{
  "data": {
    "unread_count": 3
  }
}
```

---

### GET /chat/my-chats
Get list of active chats for current user.

**Response `200`:**
```json
{
  "data": [
    {
      "booking_id": "aa0e8400-...",
      "other_user": {
        "id": "660e8400-...",
        "name": "Kuhan",
        "profile_photo": "https://..."
      },
      "last_message": "See you at the pickup!",
      "last_message_at": "2026-03-14T10:35:00Z",
      "unread_count": 1,
      "ride_summary": "Bangalore → Mysore | Mar 15"
    }
  ]
}
```

---

## 9. Wallet Endpoints

### GET /wallet/balance
Get current wallet balance. Driver-only.

**Response `200`:**
```json
{
  "data": {
    "balance": "1250.00",
    "pending_cashback": "300.00",
    "pending_withdrawal": "0.00"
  }
}
```

**Errors:**
| HTTP | Code | Detail |
|------|------|--------|
| 403  | `NOT_A_DRIVER` | Wallet is only available for registered drivers |

---

### GET /wallet/eligibility
Check toll cashback eligibility.

**Response `200`:**
```json
{
  "data": {
    "is_eligible": true,
    "days_remaining": 67,
    "onboarded_at": "2026-01-15T10:00:00Z",
    "eligibility_ends_at": "2026-04-15T10:00:00Z"
  }
}
```

---

### GET /wallet/transactions
Get paginated transaction history.

**Query Parameters:**
| Param      | Type   | Required | Default | Options |
|------------|--------|----------|---------|---------|
| `type`     | string | No       | all     | `cashback_request`, `cashback_credited`, `withdrawal_request`, `withdrawal_approved` |
| `status`   | string | No       | all     | `pending`, `approved`, `rejected` |
| `page`     | int    | No       | 1       |         |
| `per_page` | int    | No       | 20      | max 50  |

**Response `200`:** Paginated `TransactionListResponse`.

---

### POST /wallet/cashback
Submit a toll cashback request.

**Request:**
```json
{
  "ride_id": "990e8400-e29b-41d4-a716-446655440003",
  "amount": 185.00,
  "toll_proof_url": "https://xxxx.supabase.co/storage/v1/object/toll-proofs/receipt_abc.jpg"
}
```

| Field            | Type    | Required | Validation                       |
|------------------|---------|----------|----------------------------------|
| `ride_id`        | UUID    | Yes      | Must be a completed ride by you  |
| `amount`         | decimal | Yes      | 0 < value ≤ 5000                 |
| `toll_proof_url` | string  | Yes      | valid URL                        |

**Response `201`:**
```json
{
  "data": {
    "id": "bb0e8400-...",
    "type": "cashback_request",
    "amount": "185.00",
    "status": "pending",
    "ride_id": "990e8400-...",
    "toll_proof_url": "https://...",
    "upi_id": null,
    "admin_note": null,
    "created_at": "2026-03-16T12:00:00Z",
    "processed_at": null
  },
  "message": "Cashback request submitted for review"
}
```

**Errors:**
| HTTP | Code | Detail |
|------|------|--------|
| 400  | `ELIGIBILITY_EXPIRED`      | Cashback eligibility period has expired         |
| 400  | `RIDE_NOT_COMPLETED`       | Cashback only for completed rides               |
| 400  | `DUPLICATE_CASHBACK`       | Cashback already requested for this ride        |
| 400  | `EXCEEDS_MAX_CASHBACK`     | Maximum cashback per ride is ₹{amount}          |
| 403  | `NOT_RIDE_OWNER`           | This ride doesn't belong to you                 |
| 404  | `RIDE_NOT_FOUND`           | Ride not found                                  |

---

### POST /wallet/withdraw
Request a withdrawal to UPI.

**Request:**
```json
{
  "amount": 500.00,
  "upi_id": "kuhan@okaxis"
}
```

| Field    | Type    | Required | Validation                                  |
|----------|---------|----------|---------------------------------------------|
| `amount` | decimal | Yes      | > 0, ≤ current balance                      |
| `upi_id` | string  | Yes      | max_length=100, pattern: `^[\w.\-]+@[\w]+$` |

**Response `201`:**
```json
{
  "data": {
    "id": "cc0e8400-...",
    "type": "withdrawal_request",
    "amount": "500.00",
    "status": "pending",
    "ride_id": null,
    "toll_proof_url": null,
    "upi_id": "kuhan@okaxis",
    "admin_note": null,
    "created_at": "2026-03-20T09:00:00Z",
    "processed_at": null
  },
  "message": "Withdrawal request submitted. Admin will process within 48 hours."
}
```

**Errors:**
| HTTP | Code | Detail |
|------|------|--------|
| 400  | `INSUFFICIENT_BALANCE`     | Insufficient balance. Available: ₹{amount}       |
| 400  | `PENDING_WITHDRAWAL_EXISTS`| You already have a pending withdrawal request     |

---

## 10. Admin Endpoints

### GET /admin/stats
Quick stats for admin dashboard. Requires admin role.

**Response `200`:**
```json
{
  "data": {
    "users": 1250,
    "drivers": 180,
    "pending_verifications": 5,
    "rides": 890,
    "active_rides": 23,
    "bookings": 2100,
    "pending_cashbacks": 8,
    "pending_withdrawals": 3,
    "total_cashback_paid": 45600.00
  }
}
```

**Errors:**
| HTTP | Code | Detail |
|------|------|--------|
| 403  | `NOT_ADMIN` | Admin access required |

---

## 11. Health

### GET /health
Liveness probe for Cloud Run. No auth required.

**Response `200`:**
```json
{
  "status": "healthy",
  "db": "connected"
}
```

**Response `503`:**
```json
{
  "status": "unhealthy",
  "db": "disconnected"
}
```

---

## 12. Error Code Registry

### Complete Error Code List

| Code                          | HTTP | Module   | When                                                |
|-------------------------------|------|----------|-----------------------------------------------------|
| `INVALID_TOKEN`               | 401  | Auth     | JWT is invalid, expired, or missing                 |
| `EMAIL_TAKEN`                 | 400  | User     | Email already used by another account               |
| `DRIVER_ALREADY_REGISTERED`   | 400  | Driver   | User already has a driver profile                   |
| `DRIVER_NOT_FOUND`            | 404  | Driver   | No driver profile exists for this user              |
| `DRIVER_NOT_APPROVED`         | 403  | Driver   | Driver verification_status ≠ approved               |
| `DRIVER_ALREADY_VERIFIED`     | 400  | Driver   | Can't edit profile after approval                   |
| `DOCUMENT_DUPLICATE`          | 400  | Driver   | Same doc_type already uploaded                      |
| `RIDE_NOT_FOUND`              | 404  | Ride     | Ride UUID doesn't exist                             |
| `RIDE_NOT_ACTIVE`             | 400  | Ride     | Ride status ≠ active                                |
| `NOT_RIDE_OWNER`              | 403  | Ride     | User is not the ride's driver                       |
| `DEPARTURE_IN_PAST`           | 400  | Ride     | departure_time < now                                |
| `SEATS_EXCEED_CAPACITY`       | 400  | Ride     | total_seats > driver's seat_capacity                |
| `SEATS_BELOW_BOOKED`          | 400  | Ride     | Can't reduce below booked count                     |
| `DEPARTURE_CHANGE_HAS_BOOKINGS` | 400 | Ride   | Can't change time with existing bookings            |
| `NO_ROUTE_FOUND`              | 400  | Ride     | OSRM can't find path between points                 |
| `OSRM_UNAVAILABLE`            | 502  | Ride     | OSRM service unreachable                            |
| `GEOCODE_NOT_FOUND`           | 404  | Ride     | Nominatim returned no results                       |
| `BOOKING_NOT_FOUND`           | 404  | Booking  | Booking UUID doesn't exist                          |
| `NOT_BOOKING_OWNER`           | 403  | Booking  | User is not the booking's passenger                 |
| `BOOKING_NOT_ACTIVE`          | 400  | Booking  | Booking status ≠ confirmed                          |
| `RIDE_DEPARTED`               | 400  | Booking  | departure_time has passed                           |
| `INSUFFICIENT_SEATS`          | 400  | Booking  | Not enough available_seats                          |
| `SELF_BOOKING`                | 400  | Booking  | Driver trying to book own ride                      |
| `DUPLICATE_BOOKING`           | 400  | Booking  | User already has a booking on this ride             |
| `CANCEL_WINDOW_CLOSED`        | 400  | Booking  | < 2 hours before departure                          |
| `CHAT_ACCESS_DENIED`          | 403  | Chat     | Not driver or passenger of this booking             |
| `NOT_A_DRIVER`                | 403  | Wallet   | Non-driver accessing wallet                         |
| `ELIGIBILITY_EXPIRED`         | 400  | Wallet   | > 90 days since onboarding                          |
| `RIDE_NOT_COMPLETED`          | 400  | Wallet   | Cashback requires completed ride                    |
| `DUPLICATE_CASHBACK`          | 400  | Wallet   | Cashback already requested for this ride            |
| `EXCEEDS_MAX_CASHBACK`        | 400  | Wallet   | Amount > max_cashback_per_ride config               |
| `INSUFFICIENT_BALANCE`        | 400  | Wallet   | Withdrawal amount > wallet balance                  |
| `PENDING_WITHDRAWAL_EXISTS`   | 400  | Wallet   | Already has pending withdrawal                      |
| `NOT_ADMIN`                   | 403  | Admin    | Non-admin accessing admin endpoints                 |

---

## 13. Pagination Contract

All list endpoints follow this contract:

**Request:**
```
?page=1&per_page=20
```

| Param      | Type | Default | Constraint |
|------------|------|---------|------------|
| `page`     | int  | 1       | ≥ 1        |
| `per_page` | int  | 20      | 1-50       |

**Response:**
```json
{
  "data": [ ... ],
  "total": 42,
  "page": 1,
  "per_page": 20
}
```

**Client-side calculation:**
```
total_pages = ceil(total / per_page)
has_next    = page < total_pages
has_prev    = page > 1
```

---

## 14. Idempotency & Retry Policy

### Idempotent Operations (safe to retry)
| Method | Endpoint | Why |
|--------|----------|-----|
| GET    | All      | Read-only |
| PUT    | All      | Same input = same result |
| DELETE | /rides/{id} | Already cancelled → returns current state |
| PUT    | /bookings/{id}/cancel | Already cancelled → returns current state |

### Non-Idempotent Operations (dangerous to retry blindly)
| Method | Endpoint | Risk | Mitigation |
|--------|----------|------|------------|
| POST   | /bookings | Double booking | DB unique constraint `(ride_id, passenger_id)` |
| POST   | /wallet/cashback | Double claim | DB check for existing `(wallet_id, ride_id)` with pending/approved status |
| POST   | /wallet/withdraw | Double deduction | Only one pending withdrawal allowed at a time |
| POST   | /rides | Duplicate ride | No DB-level protection — client should debounce. Consider adding idempotency key in Phase 2 |

### Retry Strategy (Flutter Client)
```
Attempt 1: Immediate
Attempt 2: 1 second delay
Attempt 3: 3 second delay
Max retries: 3
Retry on: 5xx, network timeout, OSRM_UNAVAILABLE
Do NOT retry on: 4xx (user error, won't fix itself)
```
