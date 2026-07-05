# GrabPic

Upload 500 event photos. Walk away. Come back to folders already sorted by face. No more "can you send me the ones with me in them?"

Organizers bulk-upload event photos; every face is detected (SCRFD via InsightFace), embedded (ArcFace `buffalo_l`, 512-dim), and indexed in Qdrant. Guests upload one selfie any time later and get back every photo they appear in, ranked by cosine similarity.

## Architecture

```
frontend (Next.js 14) ──► api (FastAPI) ──► Postgres (Supabase)  (metadata, searches, feedback)
                              │        ──► Qdrant Cloud          (face embeddings, per-event filter)
                              │        ──► Supabase Storage      (originals, thumbs, face crops, selfies)
                              └──► indexing runs inline as a FastAPI BackgroundTask
                                   (blur gate → pHash dedupe → detect → embed → index → thumbnail → cluster)
```

No Docker, no self-hosted database — everything runs against free managed cloud services plus your local Python/Node processes.

## Quick start

1. **Create the free cloud services** (one-time):
   - [Supabase](https://supabase.com) → new project → grab the Project URL, `service_role` key (Settings → API), and the Postgres connection string (Settings → Database)
   - In Supabase → Storage, create a public bucket named `grabpic`
   - [Qdrant Cloud](https://cloud.qdrant.io) → create a free cluster → grab the Cluster URL and an API key

2. **Configure**
   ```bash
   cp .env.example .env
   # fill in DATABASE_URL, SYNC_DATABASE_URL, QDRANT_URL, QDRANT_API_KEY,
   # SUPABASE_URL, SUPABASE_SERVICE_KEY
   ```

3. **Backend**
   ```bash
   cd backend
   python3 -m venv venv && source venv/bin/activate
   pip install -r requirements.txt
   uvicorn app.main:app --reload
   ```
   First run downloads the InsightFace model (~300 MB).

4. **Frontend** (separate terminal)
   ```bash
   cd frontend
   npm install
   NEXT_PUBLIC_API_URL=http://localhost:8000 npm run dev
   ```

- API + Swagger UI: http://localhost:8000/docs
- Frontend: http://localhost:3000

Tables are created automatically on API startup (SQLAlchemy `create_all`) — no separate migration step for now.

## Seed a test event (no frontend needed)

Everything is testable from Swagger UI at `/docs`, or with curl:

```bash
# Create an event — note the returned id and guest code
curl -X POST localhost:8000/events -H 'Content-Type: application/json' \
  -d '{"name": "Test wedding", "date": "2026-08-14"}'

# Bulk upload photos (returns 202; indexing runs in the background)
curl -X POST "localhost:8000/events/<EVENT_ID>/photos" \
  -F "files=@photo1.jpg" -F "files=@photo2.jpg"

# Watch indexing progress
curl "localhost:8000/events/<EVENT_ID>/status"

# Search with a selfie
curl -X POST "localhost:8000/events/<EVENT_ID>/search" -F "selfie=@me.jpg"

# Guest page in the browser
open http://localhost:3000/e/<GUEST_CODE>
```

## How matching works

- Selfie must contain exactly one face (0 or >1 returns a clear 422).
- Top-50 nearest faces in the event, best hit per photo.
- Cosine ≥ `CONFIDENT_THRESHOLD` (0.5) → shown as confident; ≥ `BORDERLINE_THRESHOLD` (0.35) → shown as "is this you?" with confirm/reject; below → dropped. Tune both in `.env`.
- Confirm/reject is stored (`feedback` table) as labeled data for future re-ranking.
- "Download all" zips confident matches plus confirmed borderline ones, minus rejections.

## Pipeline details

Each uploaded photo goes through, inline as a background task:
1. **Blur gate** — Laplacian variance below `BLUR_THRESHOLD` → skipped.
2. **Duplicate gate** — pHash within `PHASH_DISTANCE` of an already-indexed photo in the same event → skipped.
3. **EXIF** — capture time and camera extracted for the timeline; GPS is never read.
4. **Detect + embed** — every face gets a bounding box, a cropped face chip in Supabase Storage, and a 512-dim embedding in Qdrant.
5. **Thumbnail** — 640px JPEG for fast galleries.

Failed photos land in a `failed` state visible on the dashboard with a one-click requeue (`POST /events/{id}/reprocess`). `POST /events/{id}/cluster` groups all faces into unique people for the "N unique people found" stat.

## Repo layout

```
backend/
  app/            FastAPI app (routers, models, schemas, services)
  worker/         indexing/clustering task functions, run via BackgroundTasks
frontend/
  app/            Next.js App Router pages (landing, organizer, guest gallery)
  components/     SelfieCapture (getUserMedia), FaceScanOverlay (scan animation)
```
