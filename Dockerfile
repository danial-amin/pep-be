FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install -r requirements.txt

# Copy application code
COPY ./app /app/app

# Copy default personas directory (supports multiple persona set files)
# This handles the directory structure: default_personas/*.json
COPY default_personas/ /app/default_personas/

# Copy Alembic configuration and migrations
COPY alembic.ini /app/alembic.ini
COPY alembic /app/alembic

# Create uploads and static directories
RUN mkdir -p /app/uploads /app/static/images/personas

# Expose port (Railway will provide PORT env var)
EXPOSE 8080

# Run the application
# Railway provides PORT env var, fallback to 8080 for local development
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080}"]

