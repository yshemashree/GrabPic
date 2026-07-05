import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


def _uuid() -> uuid.UUID:
    return uuid.uuid4()


class PhotoStatus(str, enum.Enum):
    pending = "pending"
    processing = "processing"
    done = "done"
    failed = "failed"
    skipped_blurry = "skipped_blurry"
    duplicate = "duplicate"


class Event(Base):
    __tablename__ = "events"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String(200))
    code: Mapped[str] = mapped_column(String(12), unique=True, index=True)
    date: Mapped[str | None] = mapped_column(String(40), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    photos: Mapped[list["Photo"]] = relationship(back_populates="event")


class Photo(Base):
    __tablename__ = "photos"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    event_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("events.id"), index=True)
    filename: Mapped[str] = mapped_column(String(300))
    object_key: Mapped[str] = mapped_column(String(500))
    thumb_key: Mapped[str | None] = mapped_column(String(500), nullable=True)
    status: Mapped[PhotoStatus] = mapped_column(
        Enum(PhotoStatus), default=PhotoStatus.pending, index=True
    )
    face_count: Mapped[int] = mapped_column(Integer, default=0)
    phash: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    blur_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    taken_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    camera: Mapped[str | None] = mapped_column(String(200), nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    event: Mapped[Event] = relationship(back_populates="photos")
    faces: Mapped[list["Face"]] = relationship(back_populates="photo")


class Face(Base):
    __tablename__ = "faces"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    photo_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("photos.id"), index=True)
    event_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("events.id"), index=True)
    bbox: Mapped[dict] = mapped_column(JSON)
    crop_key: Mapped[str | None] = mapped_column(String(500), nullable=True)
    cluster_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)

    photo: Mapped[Photo] = relationship(back_populates="faces")


class Search(Base):
    __tablename__ = "searches"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    event_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("events.id"), index=True)
    selfie_key: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    results: Mapped[list["SearchResult"]] = relationship(back_populates="search")


class SearchResult(Base):
    __tablename__ = "search_results"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    search_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("searches.id"), index=True)
    photo_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("photos.id"))
    face_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("faces.id"), nullable=True)
    score: Mapped[float] = mapped_column(Float)
    tier: Mapped[str] = mapped_column(String(20))  # confident | borderline
    confirmed: Mapped[bool | None] = mapped_column(Boolean, nullable=True)

    search: Mapped[Search] = relationship(back_populates="results")


class Feedback(Base):
    __tablename__ = "feedback"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    search_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("searches.id"), index=True)
    photo_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("photos.id"))
    accepted: Mapped[bool] = mapped_column(Boolean)
    score_at_time: Mapped[float] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
