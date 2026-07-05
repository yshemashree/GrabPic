"use client";

import { useEffect, useRef } from "react";

type Props = {
  label?: string;
  onDone?: () => void;
  durationMs?: number;
};

function buildFaceNodes(): [number, number][] {
  const pts: [number, number][] = [];
  for (let i = 0; i <= 16; i++) {
    const t = i / 16;
    const ang = Math.PI * 0.15 + t * Math.PI * 0.7;
    pts.push([0.5 + Math.cos(ang + Math.PI / 2) * 0.3, 0.3 + Math.sin(ang) * 0.42 + 0.18]);
  }
  for (let i = 0; i < 5; i++) pts.push([0.32 + i * 0.02, 0.36 - Math.sin((i / 4) * Math.PI) * 0.03]);
  for (let i = 0; i < 5; i++) pts.push([0.56 + i * 0.02, 0.36 - Math.sin((i / 4) * Math.PI) * 0.03]);
  for (let i = 0; i < 6; i++) {
    const ang = (i / 6) * Math.PI * 2;
    pts.push([0.38 + Math.cos(ang) * 0.045, 0.44 + Math.sin(ang) * 0.025]);
    pts.push([0.62 + Math.cos(ang) * 0.045, 0.44 + Math.sin(ang) * 0.025]);
  }
  pts.push([0.5, 0.42], [0.5, 0.48], [0.5, 0.54], [0.46, 0.58], [0.5, 0.59], [0.54, 0.58]);
  for (let i = 0; i < 10; i++) {
    const t = i / 9;
    pts.push([0.38 + t * 0.24, 0.7 + Math.sin(t * Math.PI) * 0.035]);
  }
  return pts;
}

const FACE_NODES = buildFaceNodes();
const LINKS: [number, number][] = [
  ...Array.from({ length: 16 }, (_, i): [number, number] => [i, i + 1]),
  ...Array.from({ length: 4 }, (_, i): [number, number] => [17 + i, 18 + i]),
  ...Array.from({ length: 4 }, (_, i): [number, number] => [22 + i, 23 + i]),
  ...Array.from({ length: 5 }, (_, i): [number, number] => [39 + i, 40 + i]),
  ...Array.from({ length: 9 }, (_, i): [number, number] => [45 + i, 46 + i]),
];

export default function FaceScanOverlay({ label = "Analyzing face", onDone, durationMs = 2400 }: Props) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const labelRef = useRef<HTMLDivElement>(null);
  const readoutRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    const wrap = canvas?.parentElement;
    if (!canvas || !wrap) return;
    const ctx = canvas.getContext("2d")!;
    const dpr = Math.min(window.devicePixelRatio || 1, 2);

    const resize = () => {
      const rect = wrap.getBoundingClientRect();
      canvas.width = rect.width * dpr;
      canvas.height = rect.height * dpr;
    };
    resize();
    window.addEventListener("resize", resize);

    const jitter = FACE_NODES.map(() => Math.random() * Math.PI * 2);
    const start = performance.now();
    let raf = 0;
    let stopped = false;

    function frame(now: number) {
      if (!canvas) return;
      const elapsed = now - start;
      const t = Math.min(elapsed / durationMs, 1);
      const w = canvas.width,
        h = canvas.height;
      ctx.clearRect(0, 0, w, h);

      ctx.strokeStyle = "rgba(57,255,106,0.08)";
      ctx.lineWidth = 1;
      const gap = 24 * dpr;
      for (let x = 0; x < w; x += gap) {
        ctx.beginPath();
        ctx.moveTo(x, 0);
        ctx.lineTo(x, h);
        ctx.stroke();
      }
      for (let y = 0; y < h; y += gap) {
        ctx.beginPath();
        ctx.moveTo(0, y);
        ctx.lineTo(w, y);
        ctx.stroke();
      }

      const cx = w * 0.5,
        cy = h * 0.52;
      const fw = Math.min(w * 0.55, h * 0.62),
        fh = fw * 1.15;
      const px = (nx: number, ny: number): [number, number] => [cx + (nx - 0.5) * fw, cy + (ny - 0.5) * fh];

      ctx.strokeStyle = "rgba(57,255,106,0.55)";
      ctx.lineWidth = 1.2 * dpr;
      LINKS.forEach(([a, b]) => {
        if (!FACE_NODES[a] || !FACE_NODES[b]) return;
        const [ax, ay] = px(...FACE_NODES[a]);
        const [bx, by] = px(...FACE_NODES[b]);
        ctx.beginPath();
        ctx.moveTo(ax, ay);
        ctx.lineTo(bx, by);
        ctx.stroke();
      });

      FACE_NODES.forEach((n, i) => {
        const [x, y] = px(n[0], n[1]);
        const twinkle = 0.6 + 0.4 * Math.sin(elapsed / 200 + jitter[i]);
        const r = 2.2 * dpr * twinkle;
        ctx.beginPath();
        ctx.fillStyle = `rgba(57,255,106,${0.7 * twinkle + 0.3})`;
        ctx.shadowColor = "#39ff6a";
        ctx.shadowBlur = 8 * dpr;
        ctx.arc(x, y, r, 0, Math.PI * 2);
        ctx.fill();
      });
      ctx.shadowBlur = 0;

      const sweepT = (elapsed % 900) / 900;
      const beamY = h * 0.12 + sweepT * h * 0.76;
      const grad = ctx.createLinearGradient(0, beamY - 18, 0, beamY + 18);
      grad.addColorStop(0, "rgba(57,255,106,0)");
      grad.addColorStop(0.5, "rgba(57,255,106,0.35)");
      grad.addColorStop(1, "rgba(57,255,106,0)");
      ctx.fillStyle = grad;
      ctx.fillRect(0, beamY - 18, w, 36);
      ctx.strokeStyle = "rgba(120,255,170,0.9)";
      ctx.lineWidth = 1.5 * dpr;
      ctx.beginPath();
      ctx.moveTo(0, beamY);
      ctx.lineTo(w, beamY);
      ctx.stroke();

      const lock = Math.min(t / 0.3, 1);
      ctx.strokeStyle = "rgba(57,255,106,0.9)";
      ctx.lineWidth = 2 * dpr;
      const bx0 = cx - (fw / 2) * (1.15 - 0.15 * lock),
        bx1 = cx + (fw / 2) * (1.15 - 0.15 * lock);
      const by0 = cy - (fh / 2) * (1.15 - 0.15 * lock),
        by1 = cy + (fh / 2) * (1.15 - 0.15 * lock);
      const cl = 14 * dpr;
      (
        [
          [bx0, by0, 1, 1],
          [bx1, by0, -1, 1],
          [bx0, by1, 1, -1],
          [bx1, by1, -1, -1],
        ] as [number, number, number, number][]
      ).forEach(([x, y, dx, dy]) => {
        ctx.beginPath();
        ctx.moveTo(x, y + cl * dy);
        ctx.lineTo(x, y);
        ctx.lineTo(x + cl * dx, y);
        ctx.stroke();
      });

      const pct = Math.floor(t * 100);
      if (readoutRef.current) {
        readoutRef.current.textContent =
          `LANDMARKS: ${FACE_NODES.length}   VECTOR: 512-D\n` +
          `MATCH CONFIDENCE: ${Math.min(99, Math.floor(t * 97 + Math.random() * 3))}%\n` +
          `PROGRESS: ${pct}%`;
      }
      if (labelRef.current) labelRef.current.textContent = pct < 100 ? label.toUpperCase() : "MATCH FOUND";

      if (t < 1 && !stopped) {
        raf = requestAnimationFrame(frame);
      } else if (!stopped) {
        onDone?.();
      }
    }
    raf = requestAnimationFrame(frame);

    return () => {
      stopped = true;
      cancelAnimationFrame(raf);
      window.removeEventListener("resize", resize);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div className="relative h-[360px] w-full overflow-hidden border-brutal border-ink bg-black shadow-brutal">
      <canvas ref={canvasRef} className="absolute inset-0 h-full w-full" />
      <div className="pointer-events-none absolute inset-0 font-mono text-[#39ff6a]" style={{ textShadow: "0 0 6px #39ff6a" }}>
        <Corner className="left-4 top-4 border-l-[3px] border-t-[3px]" />
        <Corner className="right-4 top-4 border-r-[3px] border-t-[3px]" />
        <Corner className="bottom-4 left-4 border-b-[3px] border-l-[3px]" />
        <Corner className="bottom-4 right-4 border-b-[3px] border-r-[3px]" />
        <div ref={labelRef} className="absolute left-1/2 top-4 -translate-x-1/2 text-sm font-bold tracking-widest">
          {label.toUpperCase()}
        </div>
        <div
          ref={readoutRef}
          className="absolute bottom-4 left-1/2 -translate-x-1/2 whitespace-pre text-center text-xs leading-relaxed"
        />
      </div>
    </div>
  );
}

function Corner({ className }: { className: string }) {
  return <div className={`absolute h-7 w-7 border-[#39ff6a] ${className}`} />;
}
