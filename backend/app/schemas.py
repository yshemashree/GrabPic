import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class EventCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    date: str | None = None
    description: str | None = None


class EventOut(BaseModel):
    id: uuid.UUID
    name: str
    code: str
    date: str | None
    description: str | None
    created_at: datetime

    class Config:
        from_attributes = True


class PhotoOut(BaseModel):
    id: uuid.UUID
    filename: str
    status: str
    face_count: int
    taken_at: datetime | None
    uploaded_at: datetime
    thumb_url: str | None = None


class UploadAccepted(BaseModel):
    accepted: int
    rejected: list[str]
    photo_ids: list[uuid.UUID]


class EventStatus(BaseModel):
    total_photos: int
    processed: int
    pending: int
    failed: int
    skipped: int
    duplicates: int
    faces_detected: int
    unique_people: int | None


class MatchOut(BaseModel):
    result_id: uuid.UUID
    photo_id: uuid.UUID
    photo_url: str
    thumb_url: str | None
    face_crop_url: str | None
    score: float
    tier: str
    bbox: dict
    taken_at: datetime | None


class SearchOut(BaseModel):
    search_id: uuid.UUID
    matches: list[MatchOut]
    confident_count: int
    borderline_count: int


class FeedbackIn(BaseModel):
    photo_id: uuid.UUID
    accepted: bool
