# PEP - Persona Generator Backend

A scalable, Docker-based backend API for automatically generating personas from unstructured data using LLM and vector database technology.

## Features

- **Document Processing**: Upload and process context documents and interview transcripts
- **Vector Database Integration**: Store and query document embeddings using ChromaDB
- **LLM-Powered Analysis**: Process documents and generate insights using OpenAI
- **Multi-Step Persona Generation**: 
  1. Create persona sets with basic demographics
  2. Expand personas into detailed profiles
  3. Generate AI images for personas
- **Prompt Completion**: Complete prompts using context from processed documents
- **RESTful API**: Well-structured FastAPI endpoints

## Architecture

- **FastAPI**: Modern, fast web framework for building APIs
- **PostgreSQL**: Relational database for storing personas and documents
- **ChromaDB**: Vector database for semantic search and embeddings
- **OpenAI**: LLM service for document processing and persona generation
- **Docker**: Containerized deployment for easy scaling

## Project Structure

```
pep-be/
├── app/
│   ├── api/
│   │   └── v1/
│   │       ├── endpoints/      # API endpoints
│   │       └── router.py       # Route definitions
│   ├── core/
│   │   ├── config.py          # Application configuration
│   │   ├── database.py        # Database setup
│   │   ├── vector_db.py       # Vector DB client
│   │   └── llm_service.py     # LLM service
│   ├── models/                # SQLAlchemy models
│   ├── schemas/               # Pydantic schemas
│   ├── services/              # Business logic
│   └── utils/                 # Utility functions
├── docker-compose.yml         # Docker services
├── Dockerfile                # API container
└── requirements.txt          # Python dependencies
```

## Prerequisites

- Docker and Docker Compose
- OpenAI API key

## Setup

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd pep-be
   ```

2. **Create environment file**
   ```bash
   # Copy the example file (or create manually)
   cp env.example .env
   # Or on Windows PowerShell:
   Copy-Item env.example .env
   ```

3. **Configure environment variables**
   Edit `.env` and set your OpenAI API key:
   ```
   OPENAI_API_KEY=your_openai_api_key_here
   ```

4. **Start services**
   ```bash
   docker-compose up -d
   ```

   This will start:
   - PostgreSQL database (port 5432)
   - ChromaDB vector database (port 8000)
   - FastAPI application (port 8080)

5. **Verify installation**
   ```bash
   curl http://localhost:8080/health
   ```

## API Endpoints

### Document Processing

**POST `/api/v1/documents/process`**
- Upload and process a document (context or interview)
- Body: multipart/form-data with `file` and `document_type`
- Returns: Document processing result

**GET `/api/v1/documents`**
- Get all documents (optional `document_type` query parameter)
- Returns: List of documents

**GET `/api/v1/documents/{document_id}`**
- Get a specific document
- Returns: Document details

### Persona Generation

**POST `/api/v1/personas/generate-set`**
- Step 1: Generate initial persona set with basic demographics
- Body: `{"num_personas": 3}`
- Returns: Persona set with basic personas

**POST `/api/v1/personas/{persona_set_id}/expand`**
- Step 2: Expand all personas into full profiles
- Returns: List of expanded personas

**POST `/api/v1/personas/{persona_set_id}/generate-images`**
- Step 3: Generate images for all personas
- Returns: List of personas with image URLs

**POST `/api/v1/personas/{persona_set_id}/save`**
- Save/update a persona set
- Body: Optional `name` and `description`
- Returns: Saved persona set

**GET `/api/v1/personas/sets`**
- Get all persona sets
- Returns: List of persona sets

**GET `/api/v1/personas/sets/{persona_set_id}`**
- Get a specific persona set
- Returns: Persona set with all personas

### Prompt Completion

**POST `/api/v1/prompts/complete`**
- Complete a prompt using context from documents
- Body: `{"prompt": "your prompt", "max_tokens": 1000}`
- Returns: Completed text with context information

## Usage Example

1. **Process context documents**
   ```bash
   curl -X POST "http://localhost:8080/api/v1/documents/process" \
     -F "file=@context.txt" \
     -F "document_type=context"
   ```

2. **Process interview documents**
   ```bash
   curl -X POST "http://localhost:8080/api/v1/documents/process" \
     -F "file=@interview.txt" \
     -F "document_type=interview"
   ```

3. **Generate persona set**
   ```bash
   curl -X POST "http://localhost:8080/api/v1/personas/generate-set" \
     -H "Content-Type: application/json" \
     -d '{"num_personas": 3}'
   ```

4. **Expand personas**
   ```bash
   curl -X POST "http://localhost:8080/api/v1/personas/1/expand"
   ```

5. **Generate images**
   ```bash
   curl -X POST "http://localhost:8080/api/v1/personas/1/generate-images"
   ```

6. **Save persona set**
   ```bash
   curl -X POST "http://localhost:8080/api/v1/personas/1/save?name=My%20Persona%20Set"
   ```

## Development

### Running Locally (without Docker)

1. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

2. **Set up environment**
   ```bash
   export DATABASE_URL="postgresql://pep_user:pep_password@localhost:5432/pep_db"
   export OPENAI_API_KEY="your_key"
   ```

3. **Run database migrations** (if using Alembic)
   ```bash
   alembic upgrade head
   ```

4. **Start the server**
   ```bash
   uvicorn app.main:app --reload --port 8080
   ```

### Database Migrations

The application uses SQLAlchemy with async support. For production, consider setting up Alembic for migrations:

```bash
alembic init alembic
alembic revision --autogenerate -m "Initial migration"
alembic upgrade head
```

## Configuration

Key configuration options in `.env`:

- `DATABASE_URL`: PostgreSQL connection string
- `CHROMA_HOST` / `CHROMA_PORT`: ChromaDB connection
- `OPENAI_API_KEY`: OpenAI API key (required)
- `OPENAI_MODEL`: LLM model (default: gpt-4-turbo-preview)
- `OPENAI_EMBEDDING_MODEL`: Embedding model (default: text-embedding-3-large)
- `MAX_UPLOAD_SIZE`: Maximum file upload size (default: 10MB)
- `ALLOWED_EXTENSIONS`: Allowed file extensions

## Scaling and Enhancement

The architecture is designed for scalability:

- **Horizontal Scaling**: API can be scaled by running multiple containers
- **Database**: PostgreSQL can be configured with read replicas
- **Vector DB**: ChromaDB supports clustering for larger datasets
- **Caching**: Add Redis for caching frequently accessed data
- **Queue System**: Add Celery for async task processing (image generation, etc.)
- **File Storage**: Use S3 or similar for document storage
- **Monitoring**: Add Prometheus/Grafana for metrics
- **Logging**: Structured logging with structlog

## File Format Support

Currently supports:
- `.txt` - Plain text files
- `.md` - Markdown files
- `.pdf` - PDF files (requires `pypdf` package)
- `.docx` - Word documents (requires `python-docx` package)

To add PDF/DOCX support:
```bash
pip install pypdf python-docx
```

## API Documentation

Once the server is running, visit:
- Swagger UI: http://localhost:8080/docs
- ReDoc: http://localhost:8080/redoc

## License

[Your License Here]

## Contributing

[Contributing Guidelines Here]

