# GoAlong – Phase 1 Development Scope Document

| Field                | Detail                                                        |
|----------------------|---------------------------------------------------------------|
| **Development Duration** | 28 Calendar Days                                          |
| **Document Version**     | 1.0                                                       |
| **Objective**            | MVP Launch with Controlled Communication & Driver Incentive System |

---

## Table of Contents

- [GoAlong – Phase 1 Development Scope Document](#goalong--phase-1-development-scope-document)
  - [Table of Contents](#table-of-contents)
  - [1. Project Objective](#1-project-objective)
  - [2. Core Feature Set – Phase 1](#2-core-feature-set--phase-1)
    - [A. User Authentication \& Account Management](#a-user-authentication--account-management)
    - [B. Ride Management – Driver Module](#b-ride-management--driver-module)
    - [C. Ride Discovery \& Booking – Passenger Module](#c-ride-discovery--booking--passenger-module)
    - [D. In-App Chat System (Booking-Based Access Only)](#d-in-app-chat-system-booking-based-access-only)
    - [E. Fare Calculation System (Rule-Based Engine)](#e-fare-calculation-system-rule-based-engine)
      - [E.1 Full Route Fare Calculation](#e1-full-route-fare-calculation)
      - [E.2 Partial Route Booking (Dynamic Distance Pricing)](#e2-partial-route-booking-dynamic-distance-pricing)
    - [F. Driver Toll Cashback Wallet System (Core USP)](#f-driver-toll-cashback-wallet-system-core-usp)
      - [How It Works](#how-it-works)
      - [Wallet Capabilities](#wallet-capabilities)
    - [G. Admin Web Dashboard](#g-admin-web-dashboard)
    - [H. Infrastructure \& Deployment](#h-infrastructure--deployment)
  - [3. Features Excluded from Phase 1](#3-features-excluded-from-phase-1)
  - [4. Change Control Policy](#4-change-control-policy)
  - [5. Acceptance Criteria](#5-acceptance-criteria)

---

## 1. Project Objective

Phase 1 aims to develop and deploy **GoAlong** — a secure intercity ride-sharing platform built around three core pillars:

| Pillar                        | Description                                                                 |
|-------------------------------|-----------------------------------------------------------------------------|
| **Controlled Communication**  | Privacy-first messaging; no public sharing of driver contact details        |
| **Distance-Based Fare System**| Transparent, rule-based pricing calculated on actual distance travelled      |
| **Driver Incentive Wallet**   | Toll cashback system designed to drive early driver adoption                |

This document defines the **complete and final scope** for the 28-day development cycle.

> **⚠️ Only features explicitly mentioned below are included in Phase 1. Everything else is out of scope.**

---

## 2. Core Feature Set – Phase 1

### A. User Authentication & Account Management

Secure onboarding for both passengers and drivers.

| Feature                          | Description                                              |
|----------------------------------|----------------------------------------------------------|
| User Registration                | Sign up via Mobile OTP or Email verification             |
| Secure Login & Logout            | Token-based session management                           |
| Profile Creation                 | Name, Profile Photo, Contact Information                 |
| Driver Registration              | Extended registration with document upload (license, RC, etc.) |
| Driver Verification              | Manual approval by Admin before driver can post rides    |

---

### B. Ride Management – Driver Module

Verified drivers can create, manage, and monitor their ride offerings.

| Feature        | Details                                                                  |
|----------------|--------------------------------------------------------------------------|
| **Create Ride**| Source Location, Destination Location, Date & Time, Available Seats, Vehicle Details |
| Edit Ride      | Modify ride details before departure (subject to booking constraints)    |
| Cancel Ride    | Cancel a posted ride with appropriate notification to booked passengers   |
| View Posted Rides | Dashboard view of all current and past rides posted by the driver     |

---

### C. Ride Discovery & Booking – Passenger Module

Passengers can search for available rides, view details, and book seats.

| Feature              | Details                                                          |
|----------------------|------------------------------------------------------------------|
| **Search Ride**      | Filter by Source → Destination → Date                            |
| **View Ride Details**| Driver Name, Vehicle Info, Available Seats, Calculated Fare      |
| Book Seat            | Reserve an available seat on a listed ride                       |
| Booking Confirmation | Confirmation notification upon successful booking                |
| View Booking History | Access all past and upcoming bookings                            |
| Cancel Booking       | Policy-based cancellation (terms defined by platform)            |

---

### D. In-App Chat System (Booking-Based Access Only)

Designed to ensure **user privacy and platform-controlled communication**.

| Rule                                              | Purpose                                      |
|---------------------------------------------------|-----------------------------------------------|
| Chat unlocked **only after successful booking**   | Prevents spam and unsolicited contact         |
| Driver contact details are **never publicly visible** | Protects driver privacy                   |
| One-to-one, ride-specific chat threads            | Keeps conversations contextual and traceable  |
| Chat history securely stored                      | Enables dispute resolution and accountability |

> **⚠️ Exclusion:** Direct call access and public phone number sharing are **NOT** included in Phase 1.

---

### E. Fare Calculation System (Rule-Based Engine)

GoAlong uses a **structured, non-AI, rule-based pricing model** to ensure transparency and predictability.

#### E.1 Full Route Fare Calculation

The fare for a complete route is derived from the following inputs:

| Input                    | Description                                |
|--------------------------|--------------------------------------------|
| Total Distance (km)     | End-to-end route distance                  |
| Vehicle Mileage (km/L)  | Average fuel efficiency of the vehicle     |
| Fuel Price (₹/L)        | Current fuel rate                          |
| Available Seats          | Number of bookable seats in the vehicle    |
| Platform Margin          | GoAlong's service fee                      |

**Conceptual Formula:**

```
Fuel Required  = Distance ÷ Mileage
Fuel Cost      = Fuel Required × Fuel Price
Per Seat Fare  = (Fuel Cost ÷ Seats) + Platform Margin
```

> **⚠️ Pre-Development Dependency:** Final margin percentage and mileage standards must be reviewed and approved by the client before development lock.

#### E.2 Partial Route Booking (Dynamic Distance Pricing)

If a passenger boards mid-route, the fare is **proportionally adjusted** based on the distance they actually travel.

**Formula:**

```
Fare = (Total Route Fare ÷ Total Route Distance) × Passenger's Distance Travelled
```

**Example:**

| Parameter                | Value     |
|--------------------------|-----------|
| Total Route Distance     | 150 km    |
| Passenger Joins At       | 60 km mark|
| Fare Charged For         | 60 km (proportional share of total fare) |

This ensures **fair, distance-based pricing** — passengers only pay for the portion of the ride they use.

---

### F. Driver Toll Cashback Wallet System (Core USP)

This is GoAlong's **primary driver acquisition and retention feature**, designed to offset toll costs for early adopters.

#### How It Works

| Step | Action                                                                           |
|------|----------------------------------------------------------------------------------|
| 1    | Driver completes a toll-eligible ride within **first 3 months** of onboarding    |
| 2    | Driver pays toll normally (FASTag or manual payment)                             |
| 3    | Driver submits toll receipt/proof via the app                                    |
| 4    | Admin **manually verifies** the toll proof                                       |
| 5    | Verified toll amount is **credited to the driver's in-app wallet**               |

#### Wallet Capabilities

| Role       | Capabilities                                              |
|------------|-----------------------------------------------------------|
| **Driver** | View Wallet Balance · View Cashback History · Request Withdrawal |
| **Admin**  | Credit Cashback · Approve/Reject Withdrawal Requests · Monitor All Wallet Transactions |

> **⚠️ Exclusion:** Automated toll detection API and auto-payout system are **NOT** included in Phase 1. All verifications and payouts are manual/admin-driven.

---

### G. Admin Web Dashboard

A centralized web-based control panel for platform operations and oversight.

| Module                       | Functionality                                               |
|------------------------------|-------------------------------------------------------------|
| User Management              | View, search, and manage all registered users               |
| Driver Verification          | Review submitted documents and approve/reject drivers       |
| Ride Monitoring              | Oversee all active and completed rides on the platform      |
| Booking Overview             | Track booking statuses, cancellations, and trends           |
| Wallet & Cashback Management | Review toll proofs, credit cashback, manage wallet balances |
| Withdrawal Approval System   | Approve or reject driver withdrawal requests                |
| Basic Reporting              | User count, ride count, and key operational metrics         |

---

### H. Infrastructure & Deployment

Production-grade infrastructure setup to support the MVP launch.

| Component                      | Scope                                                      |
|--------------------------------|------------------------------------------------------------|
| Secure Backend API Architecture| RESTful API layer with authentication and authorization     |
| Encrypted Communication        | HTTPS/TLS encryption for all data in transit               |
| Cloud Hosting Setup            | Scalable cloud deployment (server provisioning & config)   |
| CI/CD Deployment Pipeline      | Automated build, test, and deploy workflow                 |
| Basic Monitoring & Logging     | Server health checks, error logging, and uptime monitoring |
| Functional QA Testing          | End-to-end testing of all Phase 1 features before launch   |

---

## 3. Features Excluded from Phase 1

The following features are explicitly **out of scope** for the 28-day development cycle:

| Excluded Feature                | Rationale / Notes                                  |
|---------------------------------|----------------------------------------------------|
| Public Driver Contact Sharing   | Conflicts with privacy-first communication design  |
| Real-Time GPS Tracking          | Requires additional infrastructure; deferred       |
| Referral Program                | Growth feature; not required for MVP               |
| AI-Based Pricing                | Rule-based engine is sufficient for Phase 1        |
| Automated Toll Detection API    | Manual verification is the Phase 1 approach        |
| Subscription Model              | Monetization feature; planned for later phases     |
| Multi-Language Support           | English-only for MVP                              |
| Advanced Analytics              | Basic reporting covers Phase 1 needs               |

> These features may be considered for **Phase 2** based on user feedback and business priorities.

---

## 4. Change Control Policy

This document defines the **complete and final scope** of Phase 1.

Upon client approval and signature:

| Policy                                              | Enforcement                                    |
|-----------------------------------------------------|------------------------------------------------|
| **No additional features** shall be added to Phase 1| Strict — all additions are deferred to Phase 2 |
| Any feature modification post-approval              | Treated as a Phase 2 item                      |
| Timeline adjustments                                | May apply only for mutually approved scope changes |

---

## 5. Acceptance Criteria

Phase 1 will be considered **complete and delivered** when all of the following conditions are met:

| #  | Criteria                                                    | Status |
|----|-------------------------------------------------------------|--------|
| 1  | Users can register and log in successfully                  | ☐      |
| 2  | Verified drivers can create, edit, and cancel rides         | ☐      |
| 3  | Passengers can search for rides and book available seats    | ☐      |
| 4  | Fare calculation works for both full and partial distances  | ☐      |
| 5  | In-app chat is functional post-booking                      | ☐      |
| 6  | Toll cashback wallet system operates correctly              | ☐      |
| 7  | Admin dashboard functions as defined in Section 2G          | ☐      |
| 8  | Application is deployed in a production environment         | ☐      |

