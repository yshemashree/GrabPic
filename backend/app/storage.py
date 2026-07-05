import io
from datetime import timedelta
from functools import lru_cache

from minio import Minio

from .config import get_settings


@lru_cache
def _client(public: bool = False) -> Minio:
    s = get_settings()
    endpoint = s.minio_public_endpoint if public else s.minio_endpoint
    return Minio(
        endpoint,
        access_key=s.minio_access_key,
        secret_key=s.minio_secret_key,
        secure=s.minio_secure,
    )


def ensure_bucket() -> None:
    s = get_settings()
    c = _client()
    if not c.bucket_exists(s.minio_bucket):
        c.make_bucket(s.minio_bucket)


def put_bytes(key: str, data: bytes, content_type: str = "application/octet-stream") -> None:
    s = get_settings()
    _client().put_object(
        s.minio_bucket, key, io.BytesIO(data), length=len(data), content_type=content_type
    )


def get_bytes(key: str) -> bytes:
    s = get_settings()
    resp = _client().get_object(s.minio_bucket, key)
    try:
        return resp.read()
    finally:
        resp.close()
        resp.release_conn()


def presigned_url(key: str, expires_minutes: int = 60) -> str:
    s = get_settings()
    # Sign with the public endpoint so browsers outside the compose network can use it.
    return _client(public=True).presigned_get_object(
        s.minio_bucket, key, expires=timedelta(minutes=expires_minutes)
    )
