"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";

export default function Landing() {
  const router = useRouter();
  const [code, setCode] = useState("");

  return (
    <main className="mx-auto max-w-5xl px-4 py-10">
      <header className="mb-14 flex items-center justify-between">
        <span className="tag bg-amber text-2xl">GrabPic</span>
        <Link href="/organizer" className="btn bg-candy">
          I&apos;m an organizer
        </Link>
      </header>

      <section className="card bg-amber p-8 md:p-14">
        <h1 className="text-4xl md:text-6xl font-black leading-tight">
          Upload a selfie.
          <br />
          Find every photo of you.
        </h1>
        <p className="mt-4 max-w-xl text-lg font-medium">
          No more &quot;can you send me the ones with me in them?&quot; — GrabPic scans every
          event photo and hands you yours in seconds.
        </p>
        <form
          className="mt-8 flex flex-col gap-3 sm:flex-row"
          onSubmit={(e) => {
            e.preventDefault();
            if (code.trim()) router.push(`/e/${code.trim().toLowerCase()}`);
          }}
        >
          <input
            className="input sm:max-w-xs"
            placeholder="Event code, e.g. x7k2p9"
            value={code}
            onChange={(e) => setCode(e.target.value)}
          />
          <button type="submit" className="btn bg-lime">
            Find my photos
          </button>
        </form>
      </section>

      <section className="mt-14 grid gap-6 md:grid-cols-3">
        {[
          { n: "1", bg: "bg-coral", t: "Organizer uploads everything", d: "All 500 wedding photos, straight from the camera. We index every face automatically." },
          { n: "2", bg: "bg-sky", t: "You take one selfie", d: "Any time after the event. No account, no pre-registration, just your face." },
          { n: "3", bg: "bg-lime", t: "Get your photos", d: "Every match ranked by confidence. Confirm the borderline ones, download the lot as a zip." },
        ].map((s) => (
          <div key={s.n} className={`card ${s.bg} p-6`}>
            <span className="tag bg-white">{s.n}</span>
            <h3 className="mt-3 text-xl font-black">{s.t}</h3>
            <p className="mt-2 font-medium">{s.d}</p>
          </div>
        ))}
      </section>

      <footer className="mt-14 text-sm font-medium">
        Built with FastAPI, InsightFace and Qdrant. Faces stay on your server.
      </footer>
    </main>
  );
}
