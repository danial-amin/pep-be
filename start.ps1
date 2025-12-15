# PowerShell start script for PEP Backend

Write-Host "Starting PEP Backend services..." -ForegroundColor Green

# Check if .env exists
if (-not (Test-Path .env)) {
    Write-Host "Warning: .env file not found. Creating from env.example..." -ForegroundColor Yellow
    if (Test-Path env.example) {
        Copy-Item env.example .env
        Write-Host "Please edit .env and add your OPENAI_API_KEY" -ForegroundColor Yellow
    } else {
        Write-Host "Error: env.example not found. Please create .env manually." -ForegroundColor Red
        Write-Host "Required variables: OPENAI_API_KEY, DATABASE_URL, CHROMA_HOST, CHROMA_PORT" -ForegroundColor Yellow
        exit 1
    }
}

# Start Docker services
Write-Host "Starting Docker services..." -ForegroundColor Green
docker-compose up -d

Write-Host "Waiting for services to be ready..." -ForegroundColor Yellow
Start-Sleep -Seconds 10

# Check health
Write-Host "Checking API health..." -ForegroundColor Green
try {
    $response = Invoke-WebRequest -Uri "http://localhost:8080/health" -UseBasicParsing
    Write-Host "API is healthy!" -ForegroundColor Green
} catch {
    Write-Host "API not ready yet. Check logs with: docker-compose logs api" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "Services started!" -ForegroundColor Green
Write-Host "API available at: http://localhost:8080" -ForegroundColor Cyan
Write-Host "API docs at: http://localhost:8080/docs" -ForegroundColor Cyan
Write-Host ""
Write-Host "To view logs: docker-compose logs -f" -ForegroundColor Yellow
Write-Host "To stop: docker-compose down" -ForegroundColor Yellow

