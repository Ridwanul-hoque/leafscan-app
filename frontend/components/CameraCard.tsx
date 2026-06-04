"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { motion } from "framer-motion";
import { Camera, CameraOff, RotateCcw, Zap } from "lucide-react";

import { motionInitial } from "@/lib/motion";

interface CameraCardProps {
  onCapture: (file: File) => void;
  disabled?: boolean;
  autoStart?: boolean;
}

export default function CameraCard({
  onCapture,
  disabled,
  autoStart,
}: CameraCardProps) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const [active, setActive] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [facing, setFacing] = useState<"environment" | "user">("environment");
  const [captured, setCaptured] = useState<string | null>(null);
  const [starting, setStarting] = useState(false);

  const stop = useCallback(() => {
    streamRef.current?.getTracks().forEach((t) => t.stop());
    streamRef.current = null;
    if (videoRef.current) videoRef.current.srcObject = null;
    setActive(false);
  }, []);

  const start = useCallback(
    async (mode: "environment" | "user" = facing) => {
      setError(null);
      setCaptured(null);
      setStarting(true);
      try {
        if (!navigator.mediaDevices?.getUserMedia) {
          throw new Error("Camera API not available in this browser.");
        }
        if (
          typeof window !== "undefined" &&
          window.location.protocol === "http:" &&
          window.location.hostname !== "localhost" &&
          window.location.hostname !== "127.0.0.1"
        ) {
          throw new Error(
            "Camera requires HTTPS on mobile. Use Upload image instead, or open the site via localhost on this device.",
          );
        }
        stop();
        const stream = await navigator.mediaDevices.getUserMedia({
          video: {
            facingMode: { ideal: mode },
            width: { ideal: 1280 },
            height: { ideal: 720 },
          },
          audio: false,
        });
        streamRef.current = stream;
        if (videoRef.current) {
          videoRef.current.srcObject = stream;
          await videoRef.current.play().catch(() => undefined);
        }
        setActive(true);
      } catch (err: unknown) {
        const msg =
          err instanceof Error ? err.message : "Could not access camera.";
        if (msg.toLowerCase().includes("permission") || msg.includes("NotAllowedError")) {
          setError(
            "Camera permission denied. Allow access in your browser settings, or upload an image instead.",
          );
        } else if (msg.includes("NotFoundError")) {
          setError("No camera detected on this device.");
        } else {
          setError(msg);
        }
        setActive(false);
      } finally {
        setStarting(false);
      }
    },
    [facing, stop],
  );

  useEffect(() => {
    if (autoStart) void start();
    return () => stop();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const capture = useCallback(() => {
    const video = videoRef.current;
    if (!video || !video.videoWidth) return;
    const canvas = document.createElement("canvas");
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
    canvas.toBlob(
      (blob) => {
        if (!blob) return;
        const url = URL.createObjectURL(blob);
        setCaptured(url);
        const file = new File([blob], `leaf-${Date.now()}.jpg`, {
          type: "image/jpeg",
        });
        onCapture(file);
        stop();
      },
      "image/jpeg",
      0.92,
    );
  }, [onCapture, stop]);

  const flip = useCallback(() => {
    const next = facing === "environment" ? "user" : "environment";
    setFacing(next);
    if (active) void start(next);
  }, [facing, active, start]);

  const retake = useCallback(() => {
    if (captured) URL.revokeObjectURL(captured);
    setCaptured(null);
    void start();
  }, [captured, start]);

  return (
    <motion.div
      initial={motionInitial}
      className="glass-card flex h-full flex-col p-5 sm:p-6"
    >
      <div className="flex items-center gap-3">
        <span className="grid h-10 w-10 place-items-center rounded-xl bg-leaf-500/15 ring-1 ring-leaf-400/30">
          <Camera className="h-5 w-5 text-leaf-300" />
        </span>
        <div>
          <h2 className="text-lg font-semibold">Use camera</h2>
          <p className="text-sm text-leaf-100/60">
            Capture a leaf directly from your device.
          </p>
        </div>
      </div>

      <div className="relative mt-5 flex min-h-[240px] flex-1 items-center justify-center overflow-hidden rounded-2xl border border-white/10 bg-black/40">
        {captured ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={captured}
            alt="Captured leaf"
            className="max-h-full w-full object-contain"
          />
        ) : (
          <>
            <video
              ref={videoRef}
              playsInline
              muted
              className={`h-full w-full object-cover ${
                active ? "opacity-100" : "opacity-0"
              } transition`}
            />
            {!active && (
              <div className="absolute inset-0 flex flex-col items-center justify-center p-6 text-center">
                <CameraOff className="h-8 w-8 text-leaf-100/50" />
                <p className="mt-3 text-sm text-leaf-100/70">
                  {starting ? "Starting camera..." : "Camera is off."}
                </p>
              </div>
            )}
            {active && (
              <div className="pointer-events-none absolute inset-4 rounded-xl border-2 border-leaf-300/40" />
            )}
          </>
        )}
      </div>

      {error && (
        <p className="mt-3 text-sm text-red-300">{error}</p>
      )}

      <div className="mt-4 flex flex-wrap gap-2">
        {!active && !captured && (
          <button
            type="button"
            onClick={() => void start()}
            disabled={disabled || starting}
            className="btn-primary w-full sm:w-auto"
          >
            <Camera className="h-4 w-4" />
            {starting ? "Starting..." : "Start camera"}
          </button>
        )}
        {active && !captured && (
          <>
            <button
              type="button"
              onClick={capture}
              disabled={disabled}
              className="btn-primary w-full sm:w-auto"
            >
              <Zap className="h-4 w-4" />
              Capture
            </button>
            <button type="button" onClick={flip} className="btn-ghost">
              <RotateCcw className="h-4 w-4" />
              Flip
            </button>
            <button type="button" onClick={stop} className="btn-ghost">
              Stop
            </button>
          </>
        )}
        {captured && (
          <button type="button" onClick={retake} className="btn-ghost">
            <RotateCcw className="h-4 w-4" />
            Retake
          </button>
        )}
      </div>
    </motion.div>
  );
}
