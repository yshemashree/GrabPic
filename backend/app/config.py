from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://grabpic:grabpic@localhost:5432/grabpic"
    sync_database_url: str = "postgresql+psycopg2://grabpic:grabpic@localhost:5432/grabpic"
    redis_url: str = "redis://localhost:6379/0"
    qdrant_url: str = "http://localhost:6333"

    minio_endpoint: str = "localhost:9000"
    minio_public_endpoint: str = "localhost:9000"
    minio_access_key: str = "grabpic"
    minio_secret_key: str = "grabpic-secret"
    minio_bucket: str = "grabpic"
    minio_secure: bool = False

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
