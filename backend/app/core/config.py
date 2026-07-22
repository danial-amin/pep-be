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
    
    # Image Generation (DALL·E retired May 2026 — use GPT Image models)
    IMAGE_GENERATION_SERVICE: str = "openai"
    OPENAI_IMAGE_MODEL: str = "gpt-image-1"  # gpt-image-1 | gpt-image-1-mini | gpt-image-1.5 | gpt-image-2
    OPENAI_IMAGE_QUALITY: str = "medium"  # low | medium | high | auto
    OPENAI_IMAGE_SIZE: str = "1024x1024"
    
    # Application (e.g. "development" | "deployment" | "production"; only "development" enables DB query logging)
    ENVIRONMENT: str = "development"
    LOG_LEVEL: str = "INFO"
    CORS_ORIGINS: Union[str, List[str]] = ["*"]

    # Persona simulation: max output tokens per persona message (API max_tokens).
    # Clamped in PersonaSimulationService to 100–150 per turn. Override via env in that band.
    SIMULATION_MAX_OUTPUT_TOKENS: int = 128

    # Controlled 1:1 persona chat
    PERSONA_CHAT_REFUSAL_THRESHOLD: float = 0.55  # Min RAG score to hard-refuse factual questions (strict mode)
    PERSONA_CHAT_TEMPERATURE: float = 0.35
    PERSONA_CHAT_MAX_OUTPUT_TOKENS: int = 400

    # Auth (invite-only)
    SECRET_KEY: str = "change-me-in-production-pep-secret"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days
    INVITE_EXPIRE_DAYS: int = 14
    # Bootstrap first admin when users table is empty
    ADMIN_EMAIL: Optional[str] = None
    ADMIN_PASSWORD: Optional[str] = None
    ADMIN_NAME: str = "Admin"    
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

    @field_validator("ALLOWED_EXTENSIONS", mode="before")
    @classmethod
    def parse_allowed_extensions(cls, v):
        """Allow env var ALLOWED_EXTENSIONS as JSON or comma-separated string."""
        if isinstance(v, list):
            return [str(x).strip() for x in v if str(x).strip()]
        if isinstance(v, str):
            s = v.strip()
            if not s:
                return [".pdf", ".docx", ".txt", ".md", ".csv"]
            # JSON list
            try:
                parsed = json.loads(s)
                if isinstance(parsed, list):
                    return [str(x).strip() for x in parsed if str(x).strip()]
            except Exception:
                pass
            # Comma-separated
            if "," in s:
                return [p.strip() for p in s.split(",") if p.strip()]
            return [s]
        return [".pdf", ".docx", ".txt", ".md", ".csv"]

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
    
    # Simulation LLM-as-judge evaluation
    JUDGE_MODELS: Union[str, List[str]] = '["gpt-4o","gpt-4o-mini","gpt-4.1-mini"]'
    JUDGE_PASS_COUNT: int = 1
    JUDGE_TEMPERATURE: float = 0.0

    @field_validator("JUDGE_MODELS", mode="before")
    @classmethod
    def parse_judge_models(cls, v):
        if isinstance(v, list):
            return v
        if isinstance(v, str):
            s = v.strip()
            if not s:
                return ["gpt-4o", "gpt-4o-mini", "gpt-4.1-mini"]
            try:
                parsed = json.loads(s)
                if isinstance(parsed, list):
                    return [str(m).strip() for m in parsed if str(m).strip()]
            except (json.JSONDecodeError, ValueError):
                pass
            if "," in s:
                return [m.strip() for m in s.split(",") if m.strip()]
            return [s]
        return ["gpt-4o", "gpt-4o-mini", "gpt-4.1-mini"]

    def judge_models_list(self) -> List[str]:
        models = self.JUDGE_MODELS
        if isinstance(models, str):
            return [models]
        return list(models)

    # Document Processing
    MAX_TOKENS_PER_CHUNK: int = 20000  # Max tokens per processing chunk (leaving room for prompt)
    CHUNK_OVERLAP_TOKENS: int = 500  # Overlap between chunks
    PROCESSING_DELAY_SECONDS: float = 2.0  # Delay between chunk processing to avoid rate limits
    # If true, run expensive chat-completions summarization during ingestion.
    # Default false: ingestion should be parse+chunk+embed only.
    DOCUMENT_SUMMARIZE_ON_INGEST: bool = False
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()

