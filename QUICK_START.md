# Quick Start Guide

## Prerequisites
- Docker and Docker Compose installed
- OpenAI API key

## Setup (5 minutes)

1. **Clone and navigate**
   ```bash
   cd pep-be
   ```

2. **Create environment file**
   ```bash
   # On Windows PowerShell
   Copy-Item env.example .env
   
   # On Linux/Mac
   cp env.example .env
   
   # Or create manually - see env.example for template
   ```

3. **Edit `.env` and add your OpenAI API key**
   ```
   OPENAI_API_KEY=sk-your-key-here
   ```

4. **Start services**
   ```bash
   # On Windows PowerShell
   .\start.ps1
   
   # On Linux/Mac
   chmod +x start.sh
   ./start.sh
   
   # Or manually
   docker-compose up -d
   ```

5. **Verify it's working**
   - Open http://localhost:8080/docs in your browser
   - You should see the Swagger API documentation

## Basic Workflow

### 1. Process Documents

**Context Document:**
```bash
curl -X POST "http://localhost:8080/api/v1/documents/process" \
  -F "file=@context.txt" \
  -F "document_type=context"
```

**Interview Document:**
```bash
curl -X POST "http://localhost:8080/api/v1/documents/process" \
  -F "file=@interview.txt" \
  -F "document_type=interview"
```

### 2. Generate Personas (3 Steps)

**Step 1: Create Persona Set**
```bash
curl -X POST "http://localhost:8080/api/v1/personas/generate-set" \
  -H "Content-Type: application/json" \
  -d '{"num_personas": 3}'
```

**Step 2: Expand Personas**
```bash
curl -X POST "http://localhost:8080/api/v1/personas/1/expand"
```

**Step 3: Generate Images**
```bash
curl -X POST "http://localhost:8080/api/v1/personas/1/generate-images"
```

### 3. Save Persona Set**
```bash
curl -X POST "http://localhost:8080/api/v1/personas/1/save?name=My%20Personas"
```

### 4. Complete Prompts**
```bash
curl -X POST "http://localhost:8080/api/v1/prompts/complete" \
  -H "Content-Type: application/json" \
  -d '{"prompt": "What are the main pain points?", "max_tokens": 500}'
```

## Viewing Results

- **API Documentation**: http://localhost:8080/docs
- **All Persona Sets**: http://localhost:8080/api/v1/personas/sets
- **Specific Persona Set**: http://localhost:8080/api/v1/personas/sets/1

## Troubleshooting

**Services won't start:**
```bash
docker-compose logs
```

**Database connection issues:**
- Check that PostgreSQL container is running: `docker-compose ps`
- Wait a few seconds for services to initialize

**API errors:**
- Verify OpenAI API key is set correctly in `.env`
- Check API logs: `docker-compose logs api`

**Reset everything:**
```bash
docker-compose down -v
docker-compose up -d
```

## Next Steps

- Read the full [README.md](README.md) for detailed documentation
- Explore the API at http://localhost:8080/docs
- Check the project structure for customization options

