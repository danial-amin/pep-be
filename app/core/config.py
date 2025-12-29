"""
Application configuration settings.
"""
from pydantic_settings import BaseSettings
from typing import List, Optional


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
    CORS_ORIGINS: List[str] = ["*"]
    
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

