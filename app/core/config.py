from functools import lru_cache
from typing import Literal

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "rag-interview-backend"
    app_env: Literal["development", "staging", "production"] = "development"
    debug: bool = False
    api_v1_prefix: str = "/api/v1"

    openai_api_key: str = ""
    openai_base_url: str = "https://api.openai.com/v1"
    llm_model: str = "gpt-4o-mini"
    embedding_model: str = "text-embedding-3-small"
    embedding_dimension: int = 1536

    qdrant_url: str = "http://localhost:6333"
    qdrant_api_key: str | None = None
    qdrant_collection: str = "documents"

    database_url: str = "postgresql+asyncpg://rag:rag@localhost:5432/rag"

    redis_url: str = "redis://localhost:6379/0"
    chat_memory_ttl_seconds: int = 86400

    booking_encryption_key: str = ""

    max_upload_bytes: int = 10 * 1024 * 1024
    chunk_size: int = 800
    chunk_overlap: int = 120
    sentence_window_size: int = 5
    sentence_window_overlap: int = 1
    retrieval_top_k: int = 5

    @field_validator("qdrant_api_key", mode="before")
    @classmethod
    def empty_api_key_to_none(cls, value: object) -> object:
        if value == "":
            return None
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()
