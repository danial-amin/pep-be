#!/bin/bash

# Start script for PEP Backend

echo "Starting PEP Backend services..."

# Check if .env exists
if [ ! -f .env ]; then
    echo "Warning: .env file not found. Creating from env.example..."
    if [ -f env.example ]; then
        cp env.example .env
        echo "Please edit .env and add your OPENAI_API_KEY"
    else
        echo "Error: env.example not found. Please create .env manually."
        echo "Required variables: OPENAI_API_KEY, DATABASE_URL, CHROMA_HOST, CHROMA_PORT"
        exit 1
    fi
fi

# Start Docker services
docker-compose up -d

echo "Waiting for services to be ready..."
sleep 10

# Check health
echo "Checking API health..."
curl -f http://localhost:8080/health || echo "API not ready yet. Check logs with: docker-compose logs api"

echo ""
echo "Services started!"
echo "API available at: http://localhost:8080"
echo "API docs at: http://localhost:8080/docs"
echo ""
echo "To view logs: docker-compose logs -f"
echo "To stop: docker-compose down"

