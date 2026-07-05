"use client";

import { useMutation, useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { useRef, useState } from "react";
import SelfieCapture from "@/components/SelfieCapture";
import { api, Match, SearchResponse } from "@/lib/api";

export default function GuestGallery({ params }: { params: { code: string } }) {
  const { code } = params;
  const [camera, setCamera] = useState(false);
  const [results, setResults] = useState<SearchResponse | null>(null);
  const [decided, setDecided] = useState<Record<string, boolean>>({});
  const fileRef = useRef<HTMLInputElement>(null);

  const event = useQuery({ queryKey: ["event", code], queryFn: () => api.eventByCode(code) });

  const search = useMutation({
    mutationFn: (blob: Blob) => api.search(event.data!.id, blob),
    onSuccess: (data) => { setResults(data); setDecided({}); setCamera(false); },
  });

  const feedback = useMutation({
    mutationFn: ({ photoId, accepted }: { photoId: string; accepted: boolean }) =>
      api.feedback(event.data!.id, results!.search_id, photoId, accepted),
  });

  const decide = (m: Match, accepted: boolean) => {
    setDecided((d) => ({ ...d, [m.photo_id]: accepted }));
    feedback.mutate({ photoId: m.photo_id, accepted });
  };

  if (event.isLoading) return <Center><p className="tag bg-amber text-xl">Loading event…</p></Center>;
  if (event.isError)
    return (
      <Center>
        <div className="card bg-coral p-6 text-center">
          <p className="text-xl font-black">No event with code “{code}”</p>
          <Link href="/" className="btn mt-4 bg-white">Try another code</Link>
        </div>
      </Center>
    );

  const kept = results?.matches.filter((m) => decided[m.photo_id] !== false) ?? [];

  return (
    <main className="mx-auto max-w-3xl px-3 py-6">
      <header className="mb-6 flex items-center justify-between">
        <Link href="/" className="tag bg-amber text-xl">GrabPic</Link>
        <span className="tag bg-sky">{event.data!.name}</span>
      </header>

      {!results && (
        <section className="card bg-amber p-6 text-center">
          <h1 className="text-2xl font-black sm:text-3xl">Find your photos</h1>
          <p className="mt-2 font-medium">One selfie is all it takes. Only you in the frame, good light.</p>

          {camera ? (
            <div className="mt-5"><SelfieCapture onCapture={(b) => search.mutate(b)} onCancel={() => setCamera(false)} /></div>
          ) : (
            <div className="mt-5 flex flex-col gap-3 sm:flex-row sm:justify-center">
              <button className="btn bg-lime" onClick={() => setCamera(true)}>📷 Take a selfie</button>
              <button className="btn bg-white" onClick={() => fileRef.current?.click()}>Upload a photo</button>
              <input
                ref={fileRef} type="file" accept="image/jpeg,image/png,image/webp" hidden
                onChange={(e) => e.target.files?.[0] && search.mutate(e.target.files[0])}
              />
            </div>
          )}

          {search.isPending && (
            <p className="mt-5 animate-pulse text-lg font-black">Searching every face at the event…</p>
          )}
          {search.isError && (
            <p className="mt-5 border-brutal border-ink bg-coral p-3 font-bold">{(search.error as Error).message}</p>
          )}
        </section>
      )}

      {results && (
        <>
          <section className="card bg-lime p-4">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <p className="font-black">
                {results.matches.length === 0
                  ? "No matches found — try a clearer selfie?"
                  : `Found you in ${results.confident_count} photo${results.confident_count === 1 ? "" : "s"}${results.borderline_count ? ` + ${results.borderline_count} maybe` : ""}`}
              </p>
              <div className="flex gap-2">
                <button className="btn bg-white text-sm" onClick={() => setResults(null)}>New search</button>
                {kept.length > 0 && (
                  <button
                    className="btn bg-amber text-sm"
                    onClick={async () => {
                      const res = await fetch(api.downloadAllUrl(event.data!.id, results.search_id), { method: "POST" });
                      if (!res.ok) return alert("Nothing confirmed to download yet");
                      const blob = await res.blob();
                      const a = document.createElement("a");
                      a.href = URL.createObjectURL(blob);
                      a.download = "grabpic-photos.zip";
                      a.click();
                    }}
                  >
                    ⬇ Download all
                  </button>
                )}
              </div>
            </div>
          </section>

          <section className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-3">
            {results.matches.map((m) => {
              const verdict = decided[m.photo_id];
              const rejected = verdict === false;
              return (
                <figure key={m.result_id} className={`card overflow-hidden ${rejected ? "opacity-40" : ""}`}>
                  <a href={m.photo_url} target="_blank" rel="noreferrer">
                    {/* eslint-disable-next-line @next/next/no-img-element */}
                    <img src={m.thumb_url ?? m.photo_url} alt="matched photo" className="aspect-square w-full object-cover" />
                  </a>
                  <figcaption className="p-2">
                    <span className={`tag text-xs ${m.tier === "confident" ? "bg-lime" : "bg-amber"}`}>
                      {m.tier === "confident" ? "confident" : "is this you?"} · {(m.score * 100).toFixed(0)}%
                    </span>
                    {m.tier === "borderline" && verdict === undefined && (
                      <div className="mt-2 flex gap-2">
                        <button className="btn flex-1 bg-lime px-2 py-1 text-sm shadow-brutal-sm" onClick={() => decide(m, true)}>Yes ✓</button>
                        <button className="btn flex-1 bg-coral px-2 py-1 text-sm shadow-brutal-sm" onClick={() => decide(m, false)}>No ✕</button>
                      </div>
                    )}
                    {verdict !== undefined && (
                      <p className="mt-1 text-xs font-bold">{verdict ? "confirmed ✓" : "hidden ✕"}</p>
                    )}
                  </figcaption>
                </figure>
              );
            })}
          </section>
        </>
      )}
    </main>
  );
}

function Center({ children }: { children: React.ReactNode }) {
  return <main className="flex min-h-screen items-center justify-center px-4">{children}</main>;
}
