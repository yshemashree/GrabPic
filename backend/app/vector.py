from functools import lru_cache

from qdrant_client import QdrantClient
from qdrant_client.http import models as qm

from .config import get_settings

COLLECTION = "faces"
DIM = 512


@lru_cache
def client() -> QdrantClient:
    s = get_settings()
    return QdrantClient(url=s.qdrant_url, api_key=s.qdrant_api_key or None)


def ensure_collection() -> None:
    c = client()
    if not c.collection_exists(COLLECTION):
        c.create_collection(
            collection_name=COLLECTION,
            vectors_config=qm.VectorParams(size=DIM, distance=qm.Distance.COSINE),
        )
        c.create_payload_index(
            collection_name=COLLECTION,
            field_name="event_id",
            field_schema=qm.PayloadSchemaType.KEYWORD,
        )


def upsert_face(face_id: str, embedding: list[float], payload: dict) -> None:
    client().upsert(
        collection_name=COLLECTION,
        points=[qm.PointStruct(id=face_id, vector=embedding, payload=payload)],
    )


def search_faces(event_id: str, embedding: list[float], limit: int = 50):
    return client().search(
        collection_name=COLLECTION,
        query_vector=embedding,
        limit=limit,
        query_filter=qm.Filter(
            must=[qm.FieldCondition(key="event_id", match=qm.MatchValue(value=event_id))]
        ),
    )


def all_event_faces(event_id: str):
    """Scroll all face vectors for an event (used by clustering)."""
    points, offset = [], None
    while True:
        batch, offset = client().scroll(
            collection_name=COLLECTION,
            scroll_filter=qm.Filter(
                must=[qm.FieldCondition(key="event_id", match=qm.MatchValue(value=event_id))]
            ),
            limit=256,
            offset=offset,
            with_vectors=True,
        )
        points.extend(batch)
        if offset is None:
            break
    return points
