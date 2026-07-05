from functools import lru_cache

import httpx

from .config import get_settings


@lru_cache
def _client() -> httpx.Client:
    s = get_settings()
    return httpx.Client(
        base_url=f"{s.supabase_url}/storage/v1",
        headers={
            "Authorization": f"Bearer {s.supabase_service_key}",
            "apikey": s.supabase_service_key,
        },
        timeout=30.0,
    )


def ensure_bucket() -> None:
    s = get_settings()
    c = _client()
    resp = c.get(f"/bucket/{s.supabase_bucket}")
    if resp.status_code == 200:
        return
    c.post("/bucket", json={"id": s.supabase_bucket, "name": s.supabase_bucket, "public": True})


def put_bytes(key: str, data: bytes, content_type: str = "application/octet-stream") -> None:
    s = get_settings()
    resp = _client().post(
        f"/object/{s.supabase_bucket}/{key}",
        content=data,
        headers={"Content-Type": content_type, "x-upsert": "true"},
    )
    resp.raise_for_status()


def get_bytes(key: str) -> bytes:
    s = get_settings()
    resp = _client().get(f"/object/{s.supabase_bucket}/{key}")
    resp.raise_for_status()
    return resp.content


def presigned_url(key: str, expires_minutes: int = 60) -> str:
    # Bucket is public, so a plain public URL works without signing.
    s = get_settings()
    return f"{s.supabase_url}/storage/v1/object/public/{s.supabase_bucket}/{key}"
