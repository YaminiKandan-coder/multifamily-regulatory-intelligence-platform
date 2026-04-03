from __future__ import annotations
from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    # LLM API keys
    ANTHROPIC_API_KEY: Optional[str] = None
    OPENAI_API_KEY: Optional[str] = None
    GOOGLE_API_KEY: Optional[str] = None

    # Provider selection
    CHAT_PROVIDER: str = "auto"
    EMBED_PROVIDER: str = "gemini"

    # Supabase
    SUPABASE_URL: Optional[str] = None
    SUPABASE_KEY: Optional[str] = None

    # SMTP / email alerts
    SMTP_EMAIL: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587

    # RAG parameters
    RAG_HYBRID_ENABLED: bool = True
    RAG_HYBRID_VECTOR_WEIGHT: float = 0.6
    RAG_RETRIEVAL_TOP_N: int = 15
    RAG_RERANK_TOP_K: int = 5
    RAG_LLM_RERANK_ENABLED: bool = False
    RAG_USE_LEGAL_CHUNKING: bool = True

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"

    # ── validation helpers ──────────────────────────────────────────────────
    @property
    def has_anthropic_key(self) -> bool:
        return bool(self.ANTHROPIC_API_KEY and self.ANTHROPIC_API_KEY != "your_key_here")

    @property
    def has_openai_key(self) -> bool:
        return bool(self.OPENAI_API_KEY and self.OPENAI_API_KEY != "your_key_here")

    @property
    def has_google_key(self) -> bool:
        return bool(self.GOOGLE_API_KEY and self.GOOGLE_API_KEY != "your_key_here")


# RAG constants
CHUNK_SIZE = 800
CHUNK_OVERLAP = 200
CONTEXT_LIMIT = 4000
EMBEDDING_DIM_SMALL = 1536
EMBEDDING_DIM_LARGE = 3072

LEGAL_DISCLAIMER = "This is for informational purposes only and is not legal advice."

settings = Settings()
