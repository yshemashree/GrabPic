export const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export type EventInfo = {
  id: string;
  name: string;
  code: string;
  date: string | null;
  description: string | null;
};

export type EventStatus = {
  total_photos: number;
  processed: number;
  pending: number;
  failed: number;
  skipped: number;
  duplicates: number;
  faces_detected: number;
  unique_people: number | null;
};

export type Match = {
  result_id: string;
  photo_id: string;
  photo_url: string;
  thumb_url: string | null;
  face_crop_url: string | null;
  score: number;
  tier: "confident" | "borderline";
  taken_at: string | null;
};

export type SearchResponse = {
  search_id: string;
  matches: Match[];
  confident_count: number;
  borderline_count: number;
};

async function ok<T>(res: Response): Promise<T> {
  if (!res.ok) {
    let msg = `Request failed (${res.status})`;
    try {
      const body = await res.json();
      if (body.detail) msg = typeof body.detail === "string" ? body.detail : msg;
    } catch {}
    throw new Error(msg);
  }
  return res.json();
}

export const api = {
  createEvent: (body: { name: string; date?: string; description?: string }) =>
    fetch(`${API}/events`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }).then((r) => ok<EventInfo>(r)),

  listEvents: () => fetch(`${API}/events`).then((r) => ok<EventInfo[]>(r)),

  eventByCode: (code: string) =>
    fetch(`${API}/events/by-code/${code}`).then((r) => ok<EventInfo>(r)),

  eventStatus: (id: string) =>
    fetch(`${API}/events/${id}/status`).then((r) => ok<EventStatus>(r)),

  uploadPhotos: (id: string, files: File[]) => {
    const fd = new FormData();
    files.forEach((f) => fd.append("files", f));
    return fetch(`${API}/events/${id}/photos`, { method: "POST", body: fd }).then((r) =>
      ok<{ accepted: number; rejected: string[] }>(r)
    );
  },

  search: (id: string, selfie: Blob, filename = "selfie.jpg") => {
    const fd = new FormData();
    fd.append("selfie", selfie, filename);
    return fetch(`${API}/events/${id}/search`, { method: "POST", body: fd }).then((r) =>
      ok<SearchResponse>(r)
    );
  },

  feedback: (eventId: string, searchId: string, photoId: string, accepted: boolean) =>
    fetch(`${API}/events/${eventId}/search/${searchId}/feedback`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ photo_id: photoId, accepted }),
    }).then((r) => ok<{ ok: boolean }>(r)),

  downloadAllUrl: (eventId: string, searchId: string) =>
    `${API}/events/${eventId}/search/${searchId}/download-all`,
};
