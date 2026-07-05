import io
import uuid
import zipfile

from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile
from fastapi.responses import StreamingResponse
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .. import storage, vector
from ..config import get_settings
from ..db import get_db
from ..logging_conf import get_logger
from ..models import Event, Face, Feedback, Photo, Search, SearchResult
from ..schemas import FeedbackIn, MatchOut, SearchOut

router = APIRouter(prefix="/events/{event_id}", tags=["search"])
log = get_logger("api.search")
limiter = Limiter(key_func=get_remote_address)

ALLOWED_TYPES = {"image/jpeg", "image/png", "image/webp"}


@router.post("/search", response_model=SearchOut)
@limiter.limit(get_settings().search_rate_limit)
async def search_selfie(
    request: Request,
    event_id: uuid.UUID,
    selfie: UploadFile,
    db: AsyncSession = Depends(get_db),
):
    from ..services import faces as face_svc

    settings = get_settings()
    event = await db.get(Event, event_id)
    if event is None:
        raise HTTPException(404, "Event not found")
    if selfie.content_type not in ALLOWED_TYPES:
        raise HTTPException(415, "Please upload a JPEG, PNG or WebP image")
    data = await selfie.read()
    if len(data) > settings.max_upload_mb * 1024 * 1024:
        raise HTTPException(413, f"Selfie exceeds {settings.max_upload_mb} MB")

    img = face_svc.decode_image(data)
    if img is None:
        raise HTTPException(422, "Could not read that image — try a different photo")

    detected = face_svc.detect_faces(img)
    if len(detected) == 0:
        raise HTTPException(422, "No face found in your selfie. Face the camera in good light and try again.")
    if len(detected) > 1:
        raise HTTPException(422, "More than one face found. Please use a selfie with only you in it.")

    embedding = detected[0]["embedding"]
    hits = vector.search_faces(str(event_id), embedding, limit=50)

    # Keep best hit per photo, drop below borderline threshold
    best_per_photo: dict[str, tuple] = {}
    for h in hits:
        if h.score < settings.borderline_threshold:
            continue
        pid = h.payload["photo_id"]
        if pid not in best_per_photo or h.score > best_per_photo[pid][0]:
            best_per_photo[pid] = (h.score, h.payload)

    search = Search(event_id=event_id)
    db.add(search)
    await db.flush()
    selfie_key = f"selfies/{event_id}/{search.id}.jpg"
    storage.put_bytes(selfie_key, data, selfie.content_type)
    search.selfie_key = selfie_key

    matches: list[MatchOut] = []
    for pid, (score, payload) in sorted(best_per_photo.items(), key=lambda kv: -kv[1][0]):
        photo = await db.get(Photo, uuid.UUID(pid))
        if photo is None:
            continue
        face = await db.get(Face, uuid.UUID(payload["face_id"]))
        tier = "confident" if score >= settings.confident_threshold else "borderline"
        result = SearchResult(
            search_id=search.id, photo_id=photo.id,
            face_id=face.id if face else None, score=score, tier=tier,
        )
        db.add(result)
        await db.flush()
        matches.append(
            MatchOut(
                result_id=result.id,
                photo_id=photo.id,
                photo_url=storage.presigned_url(photo.object_key),
                thumb_url=storage.presigned_url(photo.thumb_key) if photo.thumb_key else None,
                face_crop_url=storage.presigned_url(face.crop_key) if face and face.crop_key else None,
                score=round(score, 4),
                tier=tier,
                bbox=payload.get("bbox", {}),
                taken_at=photo.taken_at,
            )
        )
    await db.commit()
    log.info("search_done", event_id=str(event_id), search_id=str(search.id), matches=len(matches))
    return SearchOut(
        search_id=search.id,
        matches=matches,
        confident_count=sum(1 for m in matches if m.tier == "confident"),
        borderline_count=sum(1 for m in matches if m.tier == "borderline"),
    )


@router.post("/search/{search_id}/feedback", status_code=201)
async def submit_feedback(
    event_id: uuid.UUID,
    search_id: uuid.UUID,
    body: FeedbackIn,
    db: AsyncSession = Depends(get_db),
):
    row = await db.execute(
        select(SearchResult).where(
            SearchResult.search_id == search_id, SearchResult.photo_id == body.photo_id
        )
    )
    result = row.scalar_one_or_none()
    if result is None:
        raise HTTPException(404, "That photo isn't part of this search")
    result.confirmed = body.accepted
    db.add(
        Feedback(
            search_id=search_id, photo_id=body.photo_id,
            accepted=body.accepted, score_at_time=result.score,
        )
    )
    await db.commit()
    return {"ok": True}


@router.get("/photos/{photo_id}/download")
async def download_photo(event_id: uuid.UUID, photo_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    photo = await db.get(Photo, photo_id)
    if photo is None or photo.event_id != event_id:
        raise HTTPException(404, "Photo not found")
    data = storage.get_bytes(photo.object_key)
    return StreamingResponse(
        io.BytesIO(data),
        media_type="image/jpeg",
        headers={"Content-Disposition": f'attachment; filename="{photo.filename}"'},
    )


@router.post("/search/{search_id}/download-all")
async def download_all(event_id: uuid.UUID, search_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """Zip every confident match plus any borderline match the guest confirmed."""
    rows = await db.execute(select(SearchResult).where(SearchResult.search_id == search_id))
    results = rows.scalars().all()
    if not results:
        raise HTTPException(404, "Search not found or has no results")

    keep = [
        r for r in results
        if r.confirmed is True or (r.tier == "confident" and r.confirmed is not False)
    ]
    if not keep:
        raise HTTPException(400, "No confirmed matches to download")

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for r in keep:
            photo = await db.get(Photo, r.photo_id)
            if photo is None:
                continue
            zf.writestr(photo.filename, storage.get_bytes(photo.object_key))
    buf.seek(0)
    return StreamingResponse(
        buf,
        media_type="application/zip",
        headers={"Content-Disposition": 'attachment; filename="grabpic-photos.zip"'},
    )
