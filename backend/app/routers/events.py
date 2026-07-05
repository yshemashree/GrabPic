import secrets
import string
import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, UploadFile
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from .. import storage
from ..config import get_settings
from ..db import get_db
from ..logging_conf import get_logger
from ..models import Event, Face, Photo, PhotoStatus
from ..schemas import EventCreate, EventOut, EventStatus, PhotoOut, UploadAccepted

router = APIRouter(prefix="/events", tags=["events"])
log = get_logger("api.events")

ALLOWED_TYPES = {"image/jpeg", "image/png", "image/webp"}


def _code() -> str:
    alphabet = string.ascii_lowercase + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(6))


async def _get_event(event_id: uuid.UUID, db: AsyncSession) -> Event:
    event = await db.get(Event, event_id)
    if event is None:
        raise HTTPException(404, "Event not found")
    return event


@router.post("", response_model=EventOut, status_code=201)
async def create_event(body: EventCreate, db: AsyncSession = Depends(get_db)):
    event = Event(name=body.name, date=body.date, description=body.description, code=_code())
    db.add(event)
    await db.commit()
    log.info("event_created", event_id=str(event.id), code=event.code)
    return event


@router.get("", response_model=list[EventOut])
async def list_events(db: AsyncSession = Depends(get_db)):
    rows = await db.execute(select(Event).order_by(Event.created_at.desc()))
    return rows.scalars().all()


@router.get("/by-code/{code}", response_model=EventOut)
async def event_by_code(code: str, db: AsyncSession = Depends(get_db)):
    row = await db.execute(select(Event).where(Event.code == code.lower()))
    event = row.scalar_one_or_none()
    if event is None:
        raise HTTPException(404, "No event with that code")
    return event


@router.get("/{event_id}", response_model=EventOut)
async def get_event(event_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    return await _get_event(event_id, db)


@router.post("/{event_id}/photos", response_model=UploadAccepted, status_code=202)
async def upload_photos(
    event_id: uuid.UUID,
    files: list[UploadFile],
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """Store originals in Supabase Storage immediately, queue indexing, return 202."""
    from worker.tasks import process_photo

    event = await _get_event(event_id, db)
    settings = get_settings()
    max_bytes = settings.max_upload_mb * 1024 * 1024

    accepted_ids: list[uuid.UUID] = []
    rejected: list[str] = []

    for f in files:
        if f.content_type not in ALLOWED_TYPES:
            rejected.append(f"{f.filename}: unsupported type {f.content_type}")
            continue
        data = await f.read()
        if len(data) > max_bytes:
            rejected.append(f"{f.filename}: exceeds {settings.max_upload_mb} MB")
            continue
        if len(data) == 0:
            rejected.append(f"{f.filename}: empty file")
            continue

        photo = Photo(event_id=event.id, filename=f.filename or "upload.jpg", object_key="")
        db.add(photo)
        await db.flush()
        key = f"originals/{event.id}/{photo.id}/{photo.filename}"
        photo.object_key = key
        storage.put_bytes(key, data, f.content_type)
        accepted_ids.append(photo.id)

    await db.commit()
    for pid in accepted_ids:
        background_tasks.add_task(process_photo, str(pid))
    log.info("photos_uploaded", event_id=str(event_id), accepted=len(accepted_ids), rejected=len(rejected))
    return UploadAccepted(accepted=len(accepted_ids), rejected=rejected, photo_ids=accepted_ids)


@router.get("/{event_id}/status", response_model=EventStatus)
async def event_status(event_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    await _get_event(event_id, db)
    counts = dict(
        (await db.execute(
            select(Photo.status, func.count()).where(Photo.event_id == event_id).group_by(Photo.status)
        )).all()
    )
    faces_total = (await db.execute(
        select(func.count()).select_from(Face).where(Face.event_id == event_id)
    )).scalar_one()
    people = (await db.execute(
        select(func.count(func.distinct(Face.cluster_id))).where(
            Face.event_id == event_id, Face.cluster_id.is_not(None)
        )
    )).scalar_one()

    def n(s: PhotoStatus) -> int:
        return counts.get(s, 0)

    return EventStatus(
        total_photos=sum(counts.values()),
        processed=n(PhotoStatus.done),
        pending=n(PhotoStatus.pending) + n(PhotoStatus.processing),
        failed=n(PhotoStatus.failed),
        skipped=n(PhotoStatus.skipped_blurry),
        duplicates=n(PhotoStatus.duplicate),
        faces_detected=faces_total,
        unique_people=people or None,
    )


@router.get("/{event_id}/photos", response_model=list[PhotoOut])
async def list_photos(event_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    await _get_event(event_id, db)
    rows = await db.execute(
        select(Photo).where(Photo.event_id == event_id).order_by(Photo.taken_at.asc().nulls_last(), Photo.uploaded_at.asc())
    )
    out = []
    for p in rows.scalars():
        out.append(
            PhotoOut(
                id=p.id,
                filename=p.filename,
                status=p.status.value,
                face_count=p.face_count,
                taken_at=p.taken_at,
                uploaded_at=p.uploaded_at,
                thumb_url=storage.presigned_url(p.thumb_key) if p.thumb_key else None,
            )
        )
    return out


@router.post("/{event_id}/reprocess", status_code=202)
async def reprocess_failed(
    event_id: uuid.UUID, background_tasks: BackgroundTasks, db: AsyncSession = Depends(get_db)
):
    """Requeue every failed photo (dead-letter recovery)."""
    from worker.tasks import process_photo

    await _get_event(event_id, db)
    rows = await db.execute(
        select(Photo.id).where(Photo.event_id == event_id, Photo.status == PhotoStatus.failed)
    )
    ids = [str(i) for i in rows.scalars()]
    for pid in ids:
        background_tasks.add_task(process_photo, pid)
    return {"requeued": len(ids)}


@router.post("/{event_id}/cluster", status_code=202)
async def trigger_clustering(
    event_id: uuid.UUID, background_tasks: BackgroundTasks, db: AsyncSession = Depends(get_db)
):
    from worker.tasks import cluster_event

    await _get_event(event_id, db)
    background_tasks.add_task(cluster_event, str(event_id))
    return {"queued": True}
