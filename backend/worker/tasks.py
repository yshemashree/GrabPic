"""Celery tasks: photo indexing pipeline + per-event face clustering.

Pipeline per photo:
  quality gate (blur) -> near-duplicate gate (pHash) -> face detection ->
  embeddings -> Qdrant upsert -> thumbnails/crops -> Postgres metadata.

Tasks are idempotent: re-running a photo re-derives everything and upserts,
so retries after a crash never corrupt state.
"""
from datetime import datetime

from sqlalchemy import select

from app import storage, vector
from app.config import get_settings
from app.logging_conf import get_logger
from app.models import Face, Photo, PhotoStatus
from app.services import clustering, faces, quality
from worker.celery_app import celery_app
from worker.db_sync import SyncSession

log = get_logger("worker")
settings = get_settings()


@celery_app.task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=5,
    retry_backoff_max=120,
    max_retries=3,
)
def process_photo(self, photo_id: str) -> str:
    with SyncSession() as db:
        photo = db.get(Photo, photo_id)
        if photo is None:
            return "missing"
        photo.status = PhotoStatus.processing
        db.commit()

        try:
            data = storage.get_bytes(photo.object_key)
            img = faces.decode_image(data)
            if img is None:
                raise ValueError("could not decode image")

            # EXIF (GPS never read)
            taken_at, camera = quality.extract_exif(data)
            photo.taken_at, photo.camera = taken_at, camera

            # Quality gate: blur
            b = quality.blur_score(img)
            photo.blur_score = b
            if b < settings.blur_threshold:
                photo.status = PhotoStatus.skipped_blurry
                photo.processed_at = datetime.utcnow()
                db.commit()
                log.info("photo_skipped_blurry", photo_id=photo_id, blur=b)
                return "blurry"

            # Near-duplicate gate: pHash against already-processed photos in event
            ph = quality.phash(data)
            photo.phash = ph
            existing = db.execute(
                select(Photo.phash).where(
                    Photo.event_id == photo.event_id,
                    Photo.id != photo.id,
                    Photo.status == PhotoStatus.done,
                    Photo.phash.is_not(None),
                )
            ).scalars()
            for other in existing:
                if quality.phash_distance(ph, other) <= settings.phash_distance:
                    photo.status = PhotoStatus.duplicate
                    photo.processed_at = datetime.utcnow()
                    db.commit()
                    log.info("photo_skipped_duplicate", photo_id=photo_id)
                    return "duplicate"

            # Thumbnail
            thumb_key = f"thumbs/{photo.event_id}/{photo.id}.jpg"
            storage.put_bytes(thumb_key, quality.make_thumbnail(data), "image/jpeg")
            photo.thumb_key = thumb_key

            # Detect + embed every face
            detected = faces.detect_faces(img)
            # Idempotency: clear any faces from a previous partial run
            for old in db.execute(select(Face).where(Face.photo_id == photo.id)).scalars():
                db.delete(old)
            db.flush()

            for d in detected:
                face = Face(photo_id=photo.id, event_id=photo.event_id, bbox=d["bbox"])
                db.add(face)
                db.flush()
                crop_key = f"crops/{photo.event_id}/{face.id}.jpg"
                storage.put_bytes(crop_key, faces.crop_face(img, d["bbox"]), "image/jpeg")
                face.crop_key = crop_key
                vector.upsert_face(
                    str(face.id),
                    d["embedding"],
                    payload={
                        "event_id": str(photo.event_id),
                        "photo_id": str(photo.id),
                        "face_id": str(face.id),
                        "bbox": d["bbox"],
                        "det_score": d["det_score"],
                    },
                )

            photo.face_count = len(detected)
            photo.status = PhotoStatus.done
            photo.processed_at = datetime.utcnow()
            photo.error = None
            db.commit()
            log.info("photo_indexed", photo_id=photo_id, faces=len(detected), blur=b)
            return "done"

        except Exception as exc:
            db.rollback()
            photo = db.get(Photo, photo_id)
            if photo is not None:
                photo.error = str(exc)[:2000]
                # Mark failed only when retries are exhausted (dead-letter state)
                if self.request.retries >= self.max_retries:
                    photo.status = PhotoStatus.failed
                    photo.processed_at = datetime.utcnow()
                db.commit()
            log.error("photo_failed", photo_id=photo_id, error=str(exc), retry=self.request.retries)
            raise


@celery_app.task
def cluster_event(event_id: str) -> int:
    """Re-cluster all faces of an event so the dashboard can show unique-people count."""
    points = vector.all_event_faces(event_id)
    if not points:
        return 0
    ids = [str(p.id) for p in points]
    vecs = [p.vector for p in points]
    assignment = clustering.cluster_embeddings(ids, vecs)
    with SyncSession() as db:
        for fid, cid in assignment.items():
            face = db.get(Face, fid)
            if face is not None:
                face.cluster_id = cid
        db.commit()
    n = len(set(assignment.values()))
    log.info("event_clustered", event_id=event_id, faces=len(ids), people=n)
    return n
