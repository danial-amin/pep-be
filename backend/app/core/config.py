"""
Application configuration settings.
"""
from pydantic_settings import BaseSettings
from pydantic import field_validator
from typing import List, Optional, Union
import json


class Settings(BaseSettings):
    """Application settings."""
    
    # Database
    DATABASE_URL: str
    POSTGRES_USER: str = "pep_user"
    POSTGRES_PASSWORD: str = "pep_password"
    POSTGRES_DB: str = "pep_db"
    
    # Vector Database - Pinecone (recommended)
    PINECONE_API_KEY: Optional[str] = None
    PINECONE_ENVIRONMENT: Optional[str] = None  # e.g., "us-east-1-aws" or "gcp-starter"
    PINECONE_INDEX_NAME: str = "pep-documents"
    
    # Vector Database - ChromaDB (optional, for local development)
    VECTOR_DB_TYPE: str = "pinecone"  # "pinecone" or "chroma"
    CHROMA_HOST: str = "localhost"
    CHROMA_PORT: int = 8000
    
    # OpenAI
    OPENAI_API_KEY: str
    OPENAI_MODEL: str = "gpt-4o-mini"
    OPENAI_EMBEDDING_MODEL: str = "text-embedding-3-large"

    # Cohere (for reranking)
    COHERE_API_KEY: Optional[str] = None
    COHERE_RERANK_MODEL: str = "rerank-english-v3.0"
    USE_COHERE_RERANKING: bool = True  # Enable/disable Cohere reranking
    
    # Image Generation
    IMAGE_GENERATION_SERVICE: str = "openai"
    
    # Application (e.g. "development" | "deployment" | "production"; only "development" enables DB query logging)
    ENVIRONMENT: str = "development"
    LOG_LEVEL: str = "INFO"
    CORS_ORIGINS: Union[str, List[str]] = ["*"]

    # Persona simulation: max output tokens per persona message (API max_tokens).
    # Clamped in PersonaSimulationService to 100–150 per turn. Override via env in that band.
    SIMULATION_MAX_OUTPUT_TOKENS: int = 128
    
    @field_validator('CORS_ORIGINS', mode='before')
    @classmethod
    def parse_cors_origins(cls, v):
        """Parse CORS_ORIGINS from various formats."""
        if isinstance(v, list):
            return v
        if isinstance(v, str):
            # Handle empty string
            if not v or v.strip() == "":
                return ["*"]
            # Try to parse as JSON first
            try:
                parsed = json.loads(v)
                if isinstance(parsed, list):
                    return parsed
            except (json.JSONDecodeError, ValueError):
                pass
            # Handle comma-separated string
            if "," in v:
                return [origin.strip() for origin in v.split(",") if origin.strip()]
            # Single string value
            return [v.strip()]
        return ["*"]
    
    # File Upload (use absolute path on Railway e.g. /data/uploads when using a Volume)
    UPLOAD_DIR: str = "uploads"
    MAX_UPLOAD_SIZE: int = 100 * 1024 * 1024  # 100MB
    ALLOWED_EXTENSIONS: List[str] = [".pdf", ".docx", ".txt", ".md", ".csv"]

    # Storage: "local" (Volume/filesystem) or "s3" (Railway Storage Buckets)
    STORAGE_TYPE: str = "local"

    # S3 / Railway Storage Buckets (required when STORAGE_TYPE=s3)
    S3_ACCESS_KEY_ID: Optional[str] = None
    S3_SECRET_ACCESS_KEY: Optional[str] = None
    S3_BUCKET: Optional[str] = None
    S3_ENDPOINT: Optional[str] = None  # e.g. https://storage.railway.app
    S3_REGION: Optional[str] = "auto"

    # Redis (required for document processing queue)
    REDIS_URL: str = "redis://localhost:6379/0"

    # Static files root (mount at /static). Use volume path e.g. /data/static to retain persona images across deploys.
    STATIC_DIR: str = "/app/static"
    # Persona images subdir under STATIC_DIR (so full path = STATIC_DIR + /images/personas)
    PERSONA_IMAGES_DIR: str = "/app/static/images/personas"
    
    # Document Processing
    MAX_TOKENS_PER_CHUNK: int = 20000  # Max tokens per processing chunk (leaving room for prompt)
    CHUNK_OVERLAP_TOKENS: int = 500  # Overlap between chunks
    PROCESSING_DELAY_SECONDS: float = 2.0  # Delay between chunk processing to avoid rate limits
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()

