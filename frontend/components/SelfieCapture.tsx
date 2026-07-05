"use client";

import { useCallback, useEffect, useRef, useState } from "react";

type Props = {
  onCapture: (blob: Blob) => void;
  onCancel: () => void;
};

export default function SelfieCapture({ onCapture, onCancel }: Props) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    navigator.mediaDevices
      .getUserMedia({ video: { facingMode: "user", width: { ideal: 1280 } } })
      .then((stream) => {
        if (cancelled) {
          stream.getTracks().forEach((t) => t.stop());
          return;
        }
        streamRef.current = stream;
        if (videoRef.current) videoRef.current.srcObject = stream;
      })
      .catch(() => setError("Camera unavailable — you can upload a photo instead."));
    return () => {
      cancelled = true;
      streamRef.current?.getTracks().forEach((t) => t.stop());
    };
  }, []);

  const snap = useCallback(() => {
    const video = videoRef.current;
    if (!video) return;
    const canvas = document.createElement("canvas");
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    canvas.getContext("2d")!.drawImage(video, 0, 0);
    canvas.toBlob((blob) => blob && onCapture(blob), "image/jpeg", 0.92);
  }, [onCapture]);

  if (error) {
    return (
      <div className="card bg-coral p-4">
        <p className="font-bold">{error}</p>
        <button className="btn mt-3 bg-white" onClick={onCancel}>Back</button>
      </div>
    );
  }

  return (
    <div className="card overflow-hidden bg-ink">
      <video ref={videoRef} autoPlay playsInline muted className="w-full -scale-x-100" />
      <div className="flex gap-3 bg-white p-3">
        <button className="btn flex-1 bg-lime" onClick={snap}>Take selfie</button>
        <button className="btn bg-white" onClick={onCancel}>Cancel</button>
      </div>
    </div>
  );
}
