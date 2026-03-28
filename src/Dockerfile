FROM python:3.11-slim

# Install system dependencies for 'shapely' and common python build tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgeos-dev \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

ENV PORT=8080

# CRITICAL: Entry point must match folder structure inside /app
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT}"]