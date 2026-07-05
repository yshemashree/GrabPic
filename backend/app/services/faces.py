"""Face detection + embedding via InsightFace (buffalo_l, ArcFace embeddings)."""
import threading

import cv2
import numpy as np

_lock = threading.Lock()
_app = None


def get_app():
    global _app
    with _lock:
        if _app is None:
            from insightface.app import FaceAnalysis

            app = FaceAnalysis(name="buffalo_l", providers=["CPUExecutionProvider"])
            app.prepare(ctx_id=-1, det_size=(640, 640))
            _app = app
    return _app


def decode_image(data: bytes) -> np.ndarray | None:
    arr = np.frombuffer(data, dtype=np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    return img


def detect_faces(img: np.ndarray):
    """Returns list of dicts: {bbox: {x,y,w,h}, embedding: list[float], det_score: float}."""
    faces = get_app().get(img)
    out = []
    for f in faces:
        x1, y1, x2, y2 = [int(v) for v in f.bbox]
        emb = f.normed_embedding
        out.append(
            {
                "bbox": {"x": max(x1, 0), "y": max(y1, 0), "w": x2 - x1, "h": y2 - y1},
                "embedding": emb.astype(float).tolist(),
                "det_score": float(f.det_score),
            }
        )
    return out


def crop_face(img: np.ndarray, bbox: dict, margin: float = 0.25) -> bytes:
    h, w = img.shape[:2]
    mx, my = int(bbox["w"] * margin), int(bbox["h"] * margin)
    x1 = max(bbox["x"] - mx, 0)
    y1 = max(bbox["y"] - my, 0)
    x2 = min(bbox["x"] + bbox["w"] + mx, w)
    y2 = min(bbox["y"] + bbox["h"] + my, h)
    crop = img[y1:y2, x1:x2]
    ok, buf = cv2.imencode(".jpg", crop, [cv2.IMWRITE_JPEG_QUALITY, 88])
    return buf.tobytes()
