import hashlib
import json
from pathlib import Path
from typing import Literal

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from .constants import MAX_FILE_SIZE, MAX_TOTAL_SIZE, ALLOWED_TYPES

PROJECT_ROOT = Path(__file__).resolve().parents[1]

class Settings(BaseSettings):
    # Required settings
    GROQ_API_KEY: str
    GROQ_MODEL: str = Field(default="openai/gpt-oss-20b", min_length=1)
    GROQ_MAX_TOKENS: int = Field(default=1024, gt=0)
    # Accepted for compatibility with existing .env files; no longer used.
    GEMINI_API_KEY: str | None = None

    # Public tunnels are optional; local usage does not require the share service.
    GRADIO_SHARE: bool = False

    # Optional settings with defaults
    MAX_FILE_SIZE: int = MAX_FILE_SIZE
    MAX_TOTAL_SIZE: int = MAX_TOTAL_SIZE
    ALLOWED_TYPES: list = ALLOWED_TYPES

    # Database settings
    CHROMA_DB_PATH: str = str(PROJECT_ROOT / "chroma_db_local")
    CHROMA_COLLECTION_NAME: str = "documents"

    # Retrieval settings
    VECTOR_SEARCH_K: int = 10
    HYBRID_RETRIEVER_WEIGHTS: list = [0.4, 0.6]

    # Local, multilingual embeddings. BGE-M3 offers a larger context window.
    EMBEDDING_MODEL: Literal[
        "intfloat/multilingual-e5-small", "BAAI/bge-m3"
    ] = "intfloat/multilingual-e5-small"
    EMBEDDING_DEVICE: str = "cpu"
    EMBEDDING_BATCH_SIZE: int = Field(default=16, gt=0)
    MODEL_CACHE_DIR: str = str(PROJECT_ROOT / ".cache" / "models")
    CHUNK_SIZE_TOKENS: int = Field(default=448, gt=0)
    CHUNK_OVERLAP_TOKENS: int = Field(default=64, ge=0)

    @model_validator(mode="after")
    def validate_chunk_limits(self):
        limit = 512 if self.EMBEDDING_MODEL == "intfloat/multilingual-e5-small" else 8192
        if self.CHUNK_OVERLAP_TOKENS >= self.CHUNK_SIZE_TOKENS:
            raise ValueError("CHUNK_OVERLAP_TOKENS must be less than CHUNK_SIZE_TOKENS")
        # Reserve room for special tokens and the E5 retrieval prefix.
        if self.CHUNK_SIZE_TOKENS > limit - 16:
            raise ValueError(f"CHUNK_SIZE_TOKENS must not exceed {limit - 16} for this model")
        return self

    @property
    def embedding_fingerprint(self) -> str:
        configuration = {
            "model": self.EMBEDDING_MODEL,
            "chunk_size": self.CHUNK_SIZE_TOKENS,
            "overlap": self.CHUNK_OVERLAP_TOKENS,
            "format": "local-embeddings-v1",
        }
        return hashlib.sha256(json.dumps(configuration, sort_keys=True).encode()).hexdigest()[:16]

    @property
    def embedding_collection_name(self) -> str:
        return f"{self.CHROMA_COLLECTION_NAME}-{self.embedding_fingerprint}"

    # Logging settings
    LOG_LEVEL: str = "INFO"

    # New cache settings with type annotations
    CACHE_DIR: str = str(PROJECT_ROOT / "document_cache_local")
    CACHE_EXPIRE_DAYS: int = 7

    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        hide_input_in_errors=True,
    )

settings = Settings()
