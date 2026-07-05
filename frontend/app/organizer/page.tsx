"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { useState } from "react";
import { api } from "@/lib/api";

export default function OrganizerHome() {
  const qc = useQueryClient();
  const [name, setName] = useState("");
  const [date, setDate] = useState("");
  const [description, setDescription] = useState("");

  const events = useQuery({ queryKey: ["events"], queryFn: api.listEvents });
  const create = useMutation({
    mutationFn: () => api.createEvent({ name, date: date || undefined, description: description || undefined }),
    onSuccess: () => {
      setName(""); setDate(""); setDescription("");
      qc.invalidateQueries({ queryKey: ["events"] });
    },
  });

  return (
    <main className="mx-auto max-w-4xl px-4 py-10">
      <header className="mb-10 flex items-center justify-between">
        <Link href="/" className="tag bg-amber text-2xl">GrabPic</Link>
        <span className="tag bg-candy">Organizer dashboard</span>
      </header>

      <section className="card bg-sky p-6">
        <h2 className="text-2xl font-black">Create an event</h2>
        <form
          className="mt-4 grid gap-3 md:grid-cols-2"
          onSubmit={(e) => { e.preventDefault(); if (name.trim()) create.mutate(); }}
        >
          <input className="input" placeholder="Event name" value={name} onChange={(e) => setName(e.target.value)} />
          <input className="input" placeholder="Date (e.g. 2026-08-14)" value={date} onChange={(e) => setDate(e.target.value)} />
          <input className="input md:col-span-2" placeholder="Description (optional)" value={description} onChange={(e) => setDescription(e.target.value)} />
          <button className="btn bg-lime md:col-span-2" disabled={create.isPending}>
            {create.isPending ? "Creating..." : "Create event"}
          </button>
        </form>
        {create.isError && <p className="mt-2 font-bold text-coral">{(create.error as Error).message}</p>}
      </section>

      <section className="mt-10">
        <h2 className="text-2xl font-black">Your events</h2>
        <div className="mt-4 grid gap-4">
          {events.data?.map((ev) => (
            <Link key={ev.id} href={`/organizer/${ev.id}`} className="card flex items-center justify-between p-5 hover:bg-amber">
              <div>
                <h3 className="text-lg font-black">{ev.name}</h3>
                <p className="font-medium">{ev.date ?? "no date"} · guest code: <span className="tag bg-lime">{ev.code}</span></p>
              </div>
              <span className="font-black">→</span>
            </Link>
          ))}
          {events.data?.length === 0 && <p className="font-medium">No events yet — create one above.</p>}
        </div>
      </section>
    </main>
  );
}
