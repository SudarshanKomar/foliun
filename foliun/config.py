from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    api_key: str = Field(default="dev-api-key", alias="API_KEY")
    database_url: str = Field(default="postgresql+psycopg2://foliun:foliun@localhost:5432/foliun", alias="DATABASE_URL")
    redis_url: str = Field(default="redis://localhost:6379/0", alias="REDIS_URL")
    storage_dir: Path = Field(default=Path("./storage/documents"), alias="STORAGE_DIR")
    cors_origins: str = Field(default="*", alias="CORS_ORIGINS")
    ollama_base_url: str = Field(default="http://localhost:11434", alias="OLLAMA_BASE_URL")
    ollama_model: str = Field(default="gemma4:2b", alias="OLLAMA_MODEL")
    openai_api_key: str | None = Field(default=None, alias="OPENAI_API_KEY")
    embedding_model_name: str = "BAAI/bge-base-en-v1.5"
    embedding_dimensions: int = 768
    embedding_batch_size: int = 32
    reranker_model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"
    chunk_size_tokens: int = 512
    chunk_overlap_tokens: int = 102
    max_upload_bytes: int = 50 * 1024 * 1024
    retrieval_top_per_query: int = 20
    retrieval_rrf_k: int = 60
    retrieval_rerank_candidates: int = 30
    retrieval_top_k: int = 10
    relevance_threshold: float = 0.5
    context_budget_tokens: int = 4000
    hnsw_ef_search: int = 40
    sse_timeout_seconds: int = 120
    load_models_at_startup: bool = Field(default=True, alias="LOAD_MODELS_AT_STARTUP")

    model_config = SettingsConfigDict(env_file=".env", populate_by_name=True)

    @property
    def cors_origin_list(self) -> list[str]:
        """Return configured CORS origins as a list."""

        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    """Return cached application settings."""

    return Settings()
