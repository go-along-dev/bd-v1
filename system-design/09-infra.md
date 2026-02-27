# Module 9: Infrastructure & Deployment

## Overview

GoAlong runs on a lean, budget-friendly infra stack designed for an MVP that needs to scale from 0 to a few thousand users. Every service is either free-tier or pay-per-use. No idle costs.

### Infrastructure Map

```
┌──────────────────────────────────────────────────────────────────┐
│                           GCP Project                            │
│                                                                  │
│  ┌──────────────┐   ┌──────────────────┐   ┌─────────────────┐  │
│  │  Cloud Run    │   │  Cloud Build      │   │ Secret Manager  │  │
│  │  (FastAPI)    │   │  (CI/CD)          │   │ (Env Vars)      │  │
│  │              │   │                    │   │                 │  │
│  │  min: 0      │   │  Trigger on push  │   │ DB URLs         │  │
│  │  max: 4      │   │  to main branch   │   │ API keys        │  │
│  │  256MB-1GB   │   │                    │   │ Supabase keys   │  │
│  └──────┬───────┘   └────────────────────┘   └─────────────────┘  │
│         │                                                        │
│  ┌──────┴───────────────────────────┐                            │
│  │  Compute Engine (e2-micro)       │                            │
│  │  Self-hosted OSRM                │                            │
│  │  (Routing + Distance)            │                            │
│  │  Always-on, ~$6/month            │                            │
│  └──────────────────────────────────┘                            │
└──────────────────────────────────────────────────────────────────┘
         │                    │                      │
         ▼                    ▼                      ▼
┌─────────────────┐  ┌────────────────┐   ┌──────────────────┐
│  Supabase       │  │  MongoDB Atlas │   │  Firebase         │
│  (Free Tier)    │  │  (M0 Free)     │   │  (FCM)            │
│                 │  │                │   │                    │
│  • Auth (OTP)   │  │  • Chat msgs   │   │  Push Notifications│
│  • PostgreSQL   │  │    only         │   │                    │
│  • Storage      │  │                │   │                    │
└─────────────────┘  └────────────────┘   └──────────────────┘
```

---

## GCP Cloud Run — App Hosting

### Why Cloud Run
- **Scale to zero** — no traffic = no cost
- **Container-based** — standard Docker deployment
- **Managed HTTPS** — free SSL certificate
- **Custom domain** — supported out of the box
- **Cost** — Free tier: 2 million requests/month, 360,000 GB-seconds

### Configuration

| Setting              | Value                          | Reason                              |
|----------------------|--------------------------------|-------------------------------------|
| Min instances        | 0                              | Scale to zero when no traffic       |
| Max instances        | 4                              | Prevent runaway costs               |
| Memory               | 512MB (start), up to 1GB       | FastAPI + SQLAlchemy is lightweight  |
| CPU                  | 1 vCPU                         | Sufficient for MVP                  |
| Concurrency          | 80                             | Default, handles well               |
| Request timeout      | 300s                           | Long enough for OSRM calls          |
| CPU allocation       | CPU only during requests       | Saves cost (implications for WS)    |
| Region               | asia-south1 (Mumbai)           | Closest to Indian users             |

### WebSocket Constraint on Cloud Run
Cloud Run has a **request timeout** that applies to WebSocket connections. When `CPU is allocated only during requests`, idle WebSocket connections will be killed after the timeout.

**Solution (already implemented in 06-chat.md):**
- Client sends periodic pings (every 25 seconds)
- Server responds with pongs
- This keeps the connection alive
- If disconnected, client auto-reconnects + FCM handles offline delivery

---

## Dockerfile

```dockerfile
# Dockerfile

FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Run with uvicorn
# - 0.0.0.0 required for Cloud Run
# - PORT env var is set by Cloud Run automatically
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080", "--workers", "1"]
```

### Things To Note:
- **Single worker.** Cloud Run handles scaling by adding instances, not workers. Multiple workers in one container = wasted memory.
- **Port 8080.** Cloud Run injects `PORT=8080` by default. Uvicorn must bind to it.
- **No `--reload`.** That's for development only.
- **`python:3.11-slim`** not `alpine`. Alpine has musl libc issues with some Python packages (e.g., psycopg2).

---

## Cloud Build — CI/CD Pipeline

```yaml
# cloudbuild.yaml

steps:
  # Step 1: Build the Docker image
  - name: 'gcr.io/cloud-builders/docker'
    args:
      - 'build'
      - '-t'
      - 'asia-south1-docker.pkg.dev/$PROJECT_ID/goalong/api:$COMMIT_SHA'
      - '-t'
      - 'asia-south1-docker.pkg.dev/$PROJECT_ID/goalong/api:latest'
      - '.'

  # Step 2: Push to Artifact Registry
  - name: 'gcr.io/cloud-builders/docker'
    args:
      - 'push'
      - 'asia-south1-docker.pkg.dev/$PROJECT_ID/goalong/api:$COMMIT_SHA'

  - name: 'gcr.io/cloud-builders/docker'
    args:
      - 'push'
      - 'asia-south1-docker.pkg.dev/$PROJECT_ID/goalong/api:latest'

  # Step 3: Deploy to Cloud Run
  - name: 'gcr.io/google.com/cloudsdktool/cloud-sdk'
    entrypoint: gcloud
    args:
      - 'run'
      - 'deploy'
      - 'goalong-api'
      - '--image'
      - 'asia-south1-docker.pkg.dev/$PROJECT_ID/goalong/api:$COMMIT_SHA'
      - '--region'
      - 'asia-south1'
      - '--platform'
      - 'managed'
      - '--min-instances'
      - '0'
      - '--max-instances'
      - '4'
      - '--memory'
      - '512Mi'
      - '--allow-unauthenticated'
      - '--set-secrets'
      - 'DATABASE_URL=DATABASE_URL:latest,SUPABASE_URL=SUPABASE_URL:latest,SUPABASE_SERVICE_ROLE_KEY=SUPABASE_SERVICE_ROLE_KEY:latest,SUPABASE_JWT_SECRET=SUPABASE_JWT_SECRET:latest,MONGODB_URL=MONGODB_URL:latest,ADMIN_PASSWORD=ADMIN_PASSWORD:latest,SESSION_SECRET_KEY=SESSION_SECRET_KEY:latest,FCM_SERVICE_ACCOUNT=FCM_SERVICE_ACCOUNT:latest'

  # Step 4: Run Alembic migrations
  - name: 'asia-south1-docker.pkg.dev/$PROJECT_ID/goalong/api:$COMMIT_SHA'
    entrypoint: 'alembic'
    args: ['upgrade', 'head']
    secretEnv: ['DATABASE_URL']

availableSecrets:
  secretManager:
    - versionName: projects/$PROJECT_ID/secrets/DATABASE_URL/versions/latest
      env: 'DATABASE_URL'

options:
  logging: CLOUD_LOGGING_ONLY

images:
  - 'asia-south1-docker.pkg.dev/$PROJECT_ID/goalong/api:$COMMIT_SHA'
  - 'asia-south1-docker.pkg.dev/$PROJECT_ID/goalong/api:latest'
```

### Cloud Build Trigger Setup

```
1. Go to GCP Console → Cloud Build → Triggers
2. Create trigger:
   - Name: deploy-goalong-api
   - Event: Push to branch
   - Source: Connect your GitHub repo
   - Branch: ^main$
   - Configuration: Cloud Build config file
   - File: cloudbuild.yaml
3. Enable required APIs:
   - Cloud Build API
   - Cloud Run API
   - Artifact Registry API
   - Secret Manager API
```

---

## GCP Secret Manager

All sensitive configuration is stored in Secret Manager, NOT in environment variables or `.env` files.

### Secrets to Create

| Secret Name                  | Value                                      |
|------------------------------|--------------------------------------------|
| `DATABASE_URL`               | `postgresql+asyncpg://<user>:<pass>@<host>/<db>`   |
| `SUPABASE_URL`               | `https://<project-ref>.supabase.co`                 |
| `SUPABASE_SERVICE_ROLE_KEY`  | `<your-service-role-key>`                  |
| `SUPABASE_JWT_SECRET`        | `<your-jwt-secret>`                        |
| `MONGODB_URL`                | `mongodb+srv://<user>:<pass>@<cluster>.mongodb.net/goalong` |
| `ADMIN_PASSWORD`             | Strong random password for admin panel     |
| `SESSION_SECRET_KEY`         | Random 32+ char string for session signing |
| `FCM_SERVICE_ACCOUNT`        | Firebase service account JSON (base64'd)   |

### Creating Secrets

```bash
# Create each secret
echo -n "postgresql+asyncpg://<user>:<pass>@<host>:5432/goalong" | \
  gcloud secrets create DATABASE_URL --data-file=-

# Grant Cloud Run access
gcloud secrets add-iam-policy-binding DATABASE_URL \
  --member="serviceAccount:YOUR_PROJECT_NUMBER-compute@developer.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"
```

---

## Supabase Setup

### Project Creation
```
1. Go to supabase.com → Create new project
2. Region: South Asia (Mumbai) — ap-south-1
3. Database password: Generate a strong one
4. Pricing: Free tier (sufficient for MVP)
```

### Free Tier Limits

| Resource           | Limit              | Sufficient for MVP? |
|--------------------|--------------------|--------------------|
| Database           | 500 MB             | Yes                |
| Auth users         | 50,000 MAU         | Yes                |
| Storage            | 1 GB               | Yes (compress images) |
| Edge Functions     | Not used           | n/a                |
| Bandwidth          | 2 GB/month         | Monitor closely    |

### Auth Configuration
```
1. Supabase Dashboard → Authentication → Providers
2. Enable Phone (OTP):
   - Provider: Twilio (or MessageBird)
   - Enter Twilio SID, Auth Token, Sender number
   - OTP expiry: 60 seconds
   - OTP length: 6 digits
3. Enable Email:
   - For admin or password recovery
4. URL Configuration:
   - Site URL: your app's deep link scheme
   - Redirect URLs: Add your Flutter app scheme
```

### SMS Provider Cost Note
Supabase free tier includes 30 OTP messages/month. After that, you need a Twilio account:
- Twilio SMS to India: ~₹0.35/SMS
- Budget: 1000 users * 2 logins/month = 2000 SMS = ~₹700/month

### Storage Buckets
```sql
-- Create buckets via Supabase Dashboard → Storage

-- 1. Profile photos (public read)
-- Bucket: profile-photos
-- Public: Yes
-- Max file size: 2MB
-- Allowed types: image/jpeg, image/png, image/webp

-- 2. Driver documents (private)
-- Bucket: driver-documents
-- Public: No (requires signed URL)
-- Max file size: 5MB
-- Allowed types: image/jpeg, image/png, application/pdf

-- 3. Toll proofs (private)
-- Bucket: toll-proofs
-- Public: No
-- Max file size: 5MB
-- Allowed types: image/jpeg, image/png
```

### RLS Policy — OFF
```
GoAlong uses Supabase as a dumb database layer.
ALL access control is handled by FastAPI using the service_role_key.
RLS is disabled on all tables via Supabase Dashboard → Table Editor → Disable RLS.
```

---

## MongoDB Atlas Setup

### Cluster Creation
```
1. Go to mongodb.com/atlas → Create cluster
2. Tier: M0 Shared (Free Forever)
3. Cloud Provider: GCP
4. Region: Mumbai (asia-south1)
5. Cluster name: goalong-chat
```

### M0 Free Tier Limits

| Resource              | Limit      | Sufficient? |
|-----------------------|-----------|-------------|
| Storage               | 512 MB    | Yes         |
| Shared RAM            | Shared    | Yes for MVP |
| Connections           | 500       | Yes         |
| Collections           | Unlimited | Yes (only 1)|

### Network Access
```
1. Atlas → Network Access → Add IP Address
2. For Cloud Run: Add 0.0.0.0/0 (allow all)
   — Cloud Run has dynamic IPs, can't whitelist
   — Security via username/password auth, not IP
3. For development: Add your local IP
```

### Database User
```
1. Atlas → Database Access → Add Database User
2. Username: goalong_app
3. Password: Generate strong password
4. Role: readWriteAnyDatabase (or scope to specific DB)
```

### Collection Index
```javascript
// Create index on chat_messages collection for fast queries
// Run in MongoDB Atlas → Collections → goalong → chat_messages

db.chat_messages.createIndex(
  { "booking_id": 1, "created_at": 1 },
  { name: "booking_timeline" }
)

db.chat_messages.createIndex(
  { "created_at": 1 },
  { expireAfterSeconds: 7776000, name: "auto_delete_90_days" }
  // Auto-delete messages after 90 days to stay within 512MB
)
```

---

## OSRM Self-Hosting on GCP

### Why Self-Host
- Google Maps API: ~₹700/1000 requests (gets expensive fast)
- OSRM: Free, open-source, uses OpenStreetMap data
- Self-hosted on an `e2-micro` VM: ~$6/month

### Setup Script

```bash
#!/bin/bash
# Run on a GCP Compute Engine e2-micro instance (Ubuntu 22.04)

# Install Docker
sudo apt-get update
sudo apt-get install -y docker.io
sudo systemctl enable docker
sudo systemctl start docker

# Download India OSM data (filtered extract is ~500MB)
mkdir -p /opt/osrm
cd /opt/osrm

# Use Geofabrik's India extract
wget https://download.geofabrik.de/asia/india-latest.osm.pbf

# Pre-process the data (takes ~15-30 minutes on e2-micro)
sudo docker run -t -v /opt/osrm:/data osrm/osrm-backend \
  osrm-extract -p /opt/car.lua /data/india-latest.osm.pbf

sudo docker run -t -v /opt/osrm:/data osrm/osrm-backend \
  osrm-partition /data/india-latest.osrm

sudo docker run -t -v /opt/osrm:/data osrm/osrm-backend \
  osrm-customize /data/india-latest.osrm

# Run OSRM server
sudo docker run -d --restart=always \
  --name osrm \
  -p 5000:5000 \
  -v /opt/osrm:/data \
  osrm/osrm-backend \
  osrm-routed --algorithm mld /data/india-latest.osrm

# OSRM is now running at http://<VM_INTERNAL_IP>:5000
```

### GCP VM Configuration

| Setting          | Value                               |
|------------------|-------------------------------------|
| Machine type     | e2-micro (2 vCPU, 1 GB memory)     |
| Image            | Ubuntu 22.04 LTS                    |
| Disk             | 20 GB SSD (for OSM data + OSRM)    |
| Region           | asia-south1 (same as Cloud Run)     |
| Network          | Default VPC (internal IP access)    |
| Firewall         | Allow port 5000 from Cloud Run only |
| Static IP        | Internal only — no external access  |

### Accessing OSRM from Cloud Run
Cloud Run and Compute Engine in the same GCP project and region can communicate via **internal IP** through the VPC connector.

```bash
# Create a VPC connector for Cloud Run
gcloud compute networks vpc-access connectors create goalong-connector \
  --region=asia-south1 \
  --network=default \
  --range=10.8.0.0/28

# Update Cloud Run service to use the connector
gcloud run services update goalong-api \
  --vpc-connector=goalong-connector \
  --region=asia-south1
```

Then set `OSRM_BASE_URL=http://<VM_INTERNAL_IP>:5000` in the environment.

### Data Freshness
OSM data updates weekly. For an MVP, update monthly:
```bash
# Monthly cron job on the VM
# Re-download and re-process India data
0 3 1 * * /opt/osrm/update-osrm.sh
```

---

## Environment Variables Summary

### Local Development (.env)

```env
# Database (Supabase PostgreSQL — use connection pooler URL)
DATABASE_URL=postgresql+asyncpg://<user>:<password>@<pooler-host>:6543/postgres

# Supabase
SUPABASE_URL=https://<project-ref>.supabase.co
SUPABASE_SERVICE_ROLE_KEY=<your-service-role-key>
SUPABASE_JWT_SECRET=<your-jwt-secret>

# MongoDB
MONGODB_URL=mongodb+srv://<user>:<password>@<cluster>.mongodb.net/goalong

# OSRM
OSRM_BASE_URL=http://router.project-osrm.org  # Public demo for dev; self-hosted for prod

# Admin
ADMIN_USERNAME=admin
ADMIN_PASSWORD=dev-password-change-in-prod
SESSION_SECRET_KEY=local-dev-session-key-32-chars-min

# FCM
GOOGLE_APPLICATION_CREDENTIALS=path/to/firebase-service-account.json

# App
ENV=development
LOG_LEVEL=DEBUG
```

### Production (GCP Secret Manager → Cloud Run)
All values above are stored as secrets and injected into Cloud Run via `--set-secrets` flag in cloudbuild.yaml. No `.env` file exists in production.

---

## Monitoring & Logging

### Cloud Logging (Built-in)
Cloud Run automatically sends stdout/stderr to Cloud Logging. Structure your FastAPI logs:

```python
# core/logging.py

import logging
import json
import sys

class CloudRunFormatter(logging.Formatter):
    """Format logs as JSON for Cloud Logging's structured logging."""
    def format(self, record):
        log_entry = {
            "severity": record.levelname,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
        }
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_entry)


def setup_logging():
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(CloudRunFormatter())

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    root_logger.addHandler(handler)

    # Suppress noisy loggers
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
```

### Health Check Endpoint
```python
# routers/health.py

@router.get("/health")
async def health_check(db: AsyncSession = Depends(get_db)):
    """Used by Cloud Run for liveness probes."""
    try:
        await db.execute(text("SELECT 1"))
        return {"status": "healthy", "db": "connected"}
    except Exception:
        return JSONResponse(
            status_code=503,
            content={"status": "unhealthy", "db": "disconnected"}
        )
```

### Error Tracking
For Phase 1, Cloud Logging is sufficient. Phase 2 can add Sentry:
```
pip install sentry-sdk[fastapi]
```

---

## Alembic — Database Migrations

```bash
# Initialize Alembic (one-time)
alembic init alembic

# alembic.ini — set sqlalchemy.url to sync URL for migrations
# (Alembic doesn't support async URLs natively)
sqlalchemy.url = postgresql://<user>:<password>@<host>:5432/postgres
```

```python
# alembic/env.py — import all models so Alembic can detect them

from app.models.user import User
from app.models.driver import Driver
from app.models.driver_document import DriverDocument
from app.models.ride import Ride
from app.models.booking import Booking
from app.models.wallet import Wallet
from app.models.wallet_transaction import WalletTransaction
from app.models.platform_config import PlatformConfig

target_metadata = Base.metadata
```

```bash
# Create a migration
alembic revision --autogenerate -m "add_wallet_tables"

# Apply migrations
alembic upgrade head

# Rollback one migration
alembic downgrade -1
```

### Things To Note:
- **Run migrations before deploying the new app version.** The cloudbuild.yaml runs `alembic upgrade head` as a step before the new Cloud Run revision starts receiving traffic.
- **Use `--autogenerate` carefully.** Always review the generated migration file.
- **Alembic uses sync driver** (`postgresql://` not `postgresql+asyncpg://`). This is expected — migration scripts run synchronously.

---

## Estimated Monthly Cost

| Service                     | Cost              | Notes                         |
|-----------------------------|--------------------|-------------------------------|
| GCP Cloud Run               | $0                | Free tier: 2M requests/month  |
| GCP Compute Engine (OSRM)   | ~$6              | e2-micro, always running      |
| GCP Cloud Build              | $0               | Free tier: 120 build-min/day  |
| GCP Secret Manager           | $0               | Free tier: 10K access/month   |
| GCP VPC Connector            | ~$7              | Required for OSRM access      |
| Supabase (Free)              | $0               | Auth + DB + Storage           |
| MongoDB Atlas (M0)           | $0               | 512MB free tier               |
| Firebase (FCM)               | $0               | FCM is free unlimited         |
| Twilio SMS (OTP)             | ~₹700 (~$8)     | ~2000 SMS/month               |
| Domain                       | ~$10/year        | Annual cost                   |
| **Total**                    | **~$21/month**   | Everything else is free tier  |

---

## Pre-Launch Checklist

```
□ GCP Project created, billing enabled
□ Artifact Registry repo created (asia-south1)
□ Cloud Build trigger connected to GitHub repo
□ Secret Manager secrets created
□ Cloud Run service deployed and accessible
□ VPC connector created for OSRM access
□ Supabase project created (Mumbai region)
□ Supabase Auth configured (Phone OTP + Email)
□ Supabase Storage buckets created (profile-photos, driver-documents, toll-proofs)
□ MongoDB Atlas cluster created (Mumbai region)
□ MongoDB chat_messages index created
□ OSRM VM provisioned and running
□ OSRM India data extracted and server started
□ Alembic migrations run on production DB
□ platform_config seed data inserted
□ Admin credentials set and tested
□ Health check endpoint responding
□ Cloud Logging receiving structured logs
□ Custom domain configured (optional for MVP)
□ Flutter app pointing to production API URL
□ FCM configured and test notification sent
```
