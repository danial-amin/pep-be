# Root Dockerfile - builds the backend API
# Use this when building from repo root (e.g. Railway without Root Directory, or `docker build .`)
# For docker-compose, the backend and frontend use their own Dockerfiles in backend/ and frontend/
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY ./backend/app /app/app
RUN pip install -r /app/app/requirements.txt
RUN pip install pinecone-client==3.0.0 aiohttp==3.9.1 scikit-learn==1.3.2 numpy==1.26.2

# Copy default personas directory
COPY ./backend/default_personas/ /app/default_personas/

# Copy Alembic configuration and migrations
COPY ./backend/alembic.ini /app/alembic.ini
COPY ./backend/alembic /app/alembic

# Create uploads and static directories
RUN mkdir -p /app/uploads /app/static/images/personas

EXPOSE 8080

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080}"]
