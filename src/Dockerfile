# =============================================================================
# Dockerfile — Production Container for GCP Cloud Run
# =============================================================================
# See: system-design/09-infra.md §1 for the Dockerfile spec
# See: system-design/09-infra.md §3 for Cloud Run configuration
#
# TODO: Build the production Docker image:
#
#   FROM python:3.11-slim
#
#   WORKDIR /app
#
#   # Install system dependencies (if any, e.g., for asyncpg)
#   RUN apt-get update && apt-get install -y --no-install-recommends \
#       && rm -rf /var/lib/apt/lists/*
#
#   # Copy and install Python dependencies first (Docker layer caching)
#   COPY requirements.txt .
#   RUN pip install --no-cache-dir -r requirements.txt
#
#   # Copy application code
#   COPY . .
#
#   # Run Alembic migrations on startup, then start Uvicorn
#   # Cloud Run injects PORT env var (default 8080)
#   CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080} --workers 1"]
#
# IMPORTANT:
#   - Single worker (--workers 1) because Cloud Run handles scaling via instances
#   - Cloud Run sets PORT=8080 by default
#   - Alembic upgrade runs before app start to ensure schema is current
#   - Use python:3.11-slim (not alpine — asyncpg needs glibc)
#
# Build & push:
#   docker build -t goalong-api .
#   docker tag goalong-api asia-south1-docker.pkg.dev/{project}/goalong/api:latest
#   docker push asia-south1-docker.pkg.dev/{project}/goalong/api:latest
#
# work by adolf.
