from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/postgres"
    sync_database_url: str = "postgresql+psycopg2://postgres:postgres@localhost:5432/postgres"

    qdrant_url: str = "http://localhost:6333"
    qdrant_api_key: str = ""

    supabase_url: str = ""
    supabase_service_key: str = ""
    supabase_bucket: str = "grabpic"

    confident_threshold: float = 0.5
    borderline_threshold: float = 0.35

    blur_threshold: float = 60.0
    phash_distance: int = 4
    max_upload_mb: int = 25

    search_rate_limit: str = "10/minute"
    cors_origins: str = "http://localhost:3000"

    class Config:
        env_file = ".env"
        extra = "ignore"


@lru_cache
def get_settings() -> Settings:
    return Settings()
