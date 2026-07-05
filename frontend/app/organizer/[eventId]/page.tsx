"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { useCallback } from "react";
import { useDropzone } from "react-dropzone";
import { API, api } from "@/lib/api";

export default function EventDashboard({ params }: { params: { eventId: string } }) {
  const { eventId } = params;
  const qc = useQueryClient();

  const status = useQuery({
    queryKey: ["status", eventId],
    queryFn: () => api.eventStatus(eventId),
    refetchInterval: (q) => ((q.state.data?.pending ?? 0) > 0 ? 2000 : 10000),
  });

  const photos = useQuery({
    queryKey: ["photos", eventId],
    queryFn: () =>
      fetch(`${API}/events/${eventId}/photos`).then((r) => r.json()) as Promise<
        { id: string; filename: string; status: string; face_count: number; thumb_url: string | null }[]
      >,
    refetchInterval: (q) => (status.data && status.data.pending > 0 ? 3000 : false),
  });

  const upload = useMutation({
    mutationFn: (files: File[]) => api.uploadPhotos(eventId, files),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["status", eventId] });
      qc.invalidateQueries({ queryKey: ["photos", eventId] });
    },
  });

  const onDrop = useCallback((accepted: File[]) => {
    if (accepted.length) upload.mutate(accepted);
  }, [upload]);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: { "image/jpeg": [], "image/png": [], "image/webp": [] },
  });

  const s = status.data;
  const pct = s && s.total_photos > 0 ? Math.round(((s.total_photos - s.pending) / s.total_photos) * 100) : 0;

  return (
    <main className="mx-auto max-w-5xl px-4 py-10">
      <header className="mb-8 flex items-center justify-between">
        <Link href="/organizer" className="tag bg-amber text-xl">← GrabPic</Link>
        <button className="btn bg-coral text-sm" onClick={() => fetch(`${API}/events/${eventId}/cluster`, { method: "POST" })}>
          Re-cluster people
        </button>
      </header>

      <section {...getRootProps()} className={`card cursor-pointer p-10 text-center ${isDragActive ? "bg-lime" : "bg-candy"}`}>
        <input {...getInputProps()} />
        <p className="text-2xl font-black">{isDragActive ? "Drop them!" : "Drag photos here, or click to pick"}</p>
        <p className="mt-2 font-medium">JPEG, PNG or WebP · up to 25 MB each · uploads never wait on processing</p>
        {upload.isPending && <p className="mt-3 font-bold">Uploading…</p>}
        {upload.data && upload.data.rejected.length > 0 && (
          <ul className="mt-3 text-left font-medium text-coral">
            {upload.data.rejected.map((r) => <li key={r}>⚠ {r}</li>)}
          </ul>
        )}
      </section>

      {s && (
        <section className="mt-8 card p-6">
          <div className="flex items-center justify-between">
            <h2 className="text-xl font-black">Indexing progress</h2>
            <span className="tag bg-amber">{pct}%</span>
          </div>
          <div className="mt-3 h-8 border-brutal border-ink bg-white">
            <div className="h-full bg-lime transition-all" style={{ width: `${pct}%` }} />
          </div>
          <div className="mt-4 flex flex-wrap gap-2">
            <span className="tag bg-lime">{s.processed} processed</span>
            <span className="tag bg-amber">{s.pending} pending</span>
            <span className="tag bg-sky">{s.faces_detected} faces</span>
            {s.unique_people != null && <span className="tag bg-candy">{s.unique_people} unique people</span>}
            {s.duplicates > 0 && <span className="tag bg-white">{s.duplicates} duplicates skipped</span>}
            {s.skipped > 0 && <span className="tag bg-white">{s.skipped} too blurry</span>}
            {s.failed > 0 && (
              <button
                className="tag bg-coral cursor-pointer"
                onClick={() => fetch(`${API}/events/${eventId}/reprocess`, { method: "POST" })}
              >
                {s.failed} failed — retry
              </button>
            )}
          </div>
        </section>
      )}

      <section className="mt-8 grid grid-cols-2 gap-4 sm:grid-cols-3 md:grid-cols-4">
        {photos.data?.map((p) => (
          <figure key={p.id} className="card overflow-hidden">
            {p.thumb_url ? (
              // eslint-disable-next-line @next/next/no-img-element
              <img src={p.thumb_url} alt={p.filename} className="aspect-square w-full object-cover" />
            ) : (
              <div className="flex aspect-square items-center justify-center bg-paper font-bold">
                {p.status === "pending" || p.status === "processing" ? "indexing…" : p.status}
              </div>
            )}
            <figcaption className="flex items-center justify-between p-2 text-sm font-bold">
              <span className="truncate">{p.filename}</span>
              <span className="tag bg-sky text-xs">{p.face_count} 👤</span>
            </figcaption>
          </figure>
        ))}
      </section>
    </main>
  );
}
