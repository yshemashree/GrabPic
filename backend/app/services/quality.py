"""Blur detection, perceptual hashing, thumbnails, EXIF extraction."""
import io
from datetime import datetime

import cv2
import imagehash
import numpy as np
from PIL import ExifTags, Image


def blur_score(img: np.ndarray) -> float:
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    return float(cv2.Laplacian(gray, cv2.CV_64F).var())


def phash(data: bytes) -> str:
    return str(imagehash.phash(Image.open(io.BytesIO(data))))


def phash_distance(a: str, b: str) -> int:
    return imagehash.hex_to_hash(a) - imagehash.hex_to_hash(b)


def make_thumbnail(data: bytes, max_size: int = 640) -> bytes:
    im = Image.open(io.BytesIO(data))
    im = im.convert("RGB")
    im.thumbnail((max_size, max_size))
    out = io.BytesIO()
    im.save(out, format="JPEG", quality=85)
    return out.getvalue()


def extract_exif(data: bytes) -> tuple[datetime | None, str | None]:
    """Return (taken_at, camera). GPS is deliberately not read — privacy."""
    try:
        im = Image.open(io.BytesIO(data))
        exif = im.getexif()
        if not exif:
            return None, None
        tags = {ExifTags.TAGS.get(k, k): v for k, v in exif.items()}
        taken_at = None
        raw = tags.get("DateTimeOriginal") or tags.get("DateTime")
        if raw:
            try:
                taken_at = datetime.strptime(str(raw), "%Y:%m:%d %H:%M:%S")
            except ValueError:
                pass
        make = str(tags.get("Make") or "").strip()
        model = str(tags.get("Model") or "").strip()
        camera = " ".join(p for p in (make, model) if p) or None
        return taken_at, camera
    except Exception:
        return None, None
