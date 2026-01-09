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
    OPENAI_MODEL: str = "gpt-4-turbo-preview"
    OPENAI_EMBEDDING_MODEL: str = "text-embedding-3-large"
    
    # Image Generation
    IMAGE_GENERATION_SERVICE: str = "openai"
    
    # Application
    ENVIRONMENT: str = "development"
    LOG_LEVEL: str = "INFO"
    CORS_ORIGINS: Union[str, List[str]] = ["*"]
    
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
    
    # File Upload
    MAX_UPLOAD_SIZE: int = 10 * 1024 * 1024  # 10MB
    ALLOWED_EXTENSIONS: List[str] = [".pdf", ".docx", ".txt", ".md"]
    
    # Document Processing
    MAX_TOKENS_PER_CHUNK: int = 20000  # Max tokens per processing chunk (leaving room for prompt)
    CHUNK_OVERLAP_TOKENS: int = 500  # Overlap between chunks
    PROCESSING_DELAY_SECONDS: float = 2.0  # Delay between chunk processing to avoid rate limits
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()

