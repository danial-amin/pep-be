# Root Dockerfile - builds the backend API
# This Dockerfile is intentionally robust to two common build contexts:
# - repo root (./backend/app, ./backend/alembic, ...)
# - backend/ folder (./app, ./alembic, ...)
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy build context (repo root OR backend/) then normalize paths
COPY . /build

# Copy app code into /app/app (supports both contexts)
RUN set -eux; \
    if [ -d /build/backend/app ]; then \
      cp -r /build/backend/app /app/app; \
    elif [ -d /build/app ]; then \
      cp -r /build/app /app/app; \
    else \
      echo "Could not find app directory (expected /build/backend/app or /build/app)"; \
      ls -la /build; \
      exit 1; \
    fi

# Install python requirements
RUN pip install -r /app/app/requirements.txt
RUN pip install pinecone-client==3.0.0 aiohttp==3.9.1 scikit-learn==1.3.2 numpy==1.26.2

# Copy default personas (supports both contexts)
RUN set -eux; \
    if [ -d /build/backend/default_personas ]; then \
      mkdir -p /app/default_personas; \
      cp -r /build/backend/default_personas/. /app/default_personas/; \
    elif [ -d /build/default_personas ]; then \
      mkdir -p /app/default_personas; \
      cp -r /build/default_personas/. /app/default_personas/; \
    else \
      echo "No default_personas directory found (continuing)"; \
    fi

# Copy Alembic configuration and migrations (supports both contexts)
RUN set -eux; \
    if [ -f /build/backend/alembic.ini ]; then \
      cp /build/backend/alembic.ini /app/alembic.ini; \
    elif [ -f /build/alembic.ini ]; then \
      cp /build/alembic.ini /app/alembic.ini; \
    else \
      echo "No alembic.ini found (continuing)"; \
    fi; \
    if [ -d /build/backend/alembic ]; then \
      cp -r /build/backend/alembic /app/alembic; \
    elif [ -d /build/alembic ]; then \
      cp -r /build/alembic /app/alembic; \
    else \
      echo "No alembic migrations found (continuing)"; \
    fi

# Create uploads and static directories
RUN mkdir -p /app/uploads /app/static/images/personas

EXPOSE 8080

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080}"]
