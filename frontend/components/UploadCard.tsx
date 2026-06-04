"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { Loader2, UploadCloud, ImagePlus, X } from "lucide-react";

import {
  ImageUploadError,
  isLikelyImageFile,
  normalizeImageForUpload,
} from "@/lib/imageUpload";

interface UploadCardProps {
  onFileSelected: (file: File) => void;
  onFileCleared?: () => void;
  disabled?: boolean;
}

const MAX_BYTES = 8 * 1024 * 1024;

export default function UploadCard({
  onFileSelected,
  onFileCleared,
  disabled,
}: UploadCardProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const previewRef = useRef<string | null>(null);
  const [dragging, setDragging] = useState(false);
  const [processing, setProcessing] = useState(false);
  const [preview, setPreview] = useState<string | null>(null);
  const [fileName, setFileName] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const revokePreview = useCallback(() => {
    if (previewRef.current) {
      URL.revokeObjectURL(previewRef.current);
      previewRef.current = null;
    }
  }, []);

  useEffect(() => {
    return () => revokePreview();
  }, [revokePreview]);

  const processFile = useCallback(
    async (file: File) => {
      setError(null);
      if (!isLikelyImageFile(file)) {
        setError("Unsupported format. Use JPG, PNG, or WEBP.");
        return;
      }

      // Show immediate feedback while conversion/compression runs on slower phones.
      revokePreview();
      const pendingUrl = URL.createObjectURL(file);
      previewRef.current = pendingUrl;
      setPreview(pendingUrl);
      setFileName(file.name);

      setProcessing(true);
      try {
        const normalized = await normalizeImageForUpload(file);
        if (normalized.size > MAX_BYTES) {
          revokePreview();
          setPreview(null);
          setFileName(null);
          setError("Image is larger than 8 MB.");
          return;
        }

        if (normalized !== file) {
          revokePreview();
          const url = URL.createObjectURL(normalized);
          previewRef.current = url;
          setPreview(url);
          setFileName(normalized.name);
        }
        onFileSelected(normalized);
      } catch (err) {
        revokePreview();
        setPreview(null);
        setFileName(null);
        const msg =
          err instanceof ImageUploadError
            ? err.message
            : err instanceof Error
            ? err.message
            : "Could not load this image. Try another photo.";
        setError(msg);
      } finally {
        setProcessing(false);
      }
    },
    [onFileSelected, revokePreview],
  );

  const onInputChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0];
      if (file) void processFile(file);
      e.target.value = "";
    },
    [processFile],
  );

  const onDrop = useCallback(
    (e: React.DragEvent<HTMLDivElement>) => {
      e.preventDefault();
      setDragging(false);
      if (disabled || processing) return;
      const file = e.dataTransfer.files?.[0];
      if (file) void processFile(file);
    },
    [disabled, processing, processFile],
  );

  const clear = (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    revokePreview();
    setPreview(null);
    setFileName(null);
    setError(null);
    onFileCleared?.();
    if (inputRef.current) inputRef.current.value = "";
  };

  const openPicker = useCallback(() => {
    if (disabled || processing) return;
    inputRef.current?.click();
  }, [disabled, processing]);

  const busy = disabled || processing;

  return (
    <div className="glass-card flex h-full flex-col p-5 sm:p-6">
      <div className="flex items-center gap-3">
        <span className="grid h-10 w-10 place-items-center rounded-xl bg-leaf-500/15 ring-1 ring-leaf-400/30">
          <UploadCloud className="h-5 w-5 text-leaf-300" />
        </span>
        <div>
          <h2 className="text-lg font-semibold">Upload image</h2>
          <p className="text-sm text-leaf-100/60">
            Tap the dashed area to pick a photo from your gallery.
          </p>
        </div>
      </div>

      <input
        ref={inputRef}
        type="file"
        accept="image/jpeg,image/png,image/webp,.jpg,.jpeg,.png,.webp"
        disabled={busy}
        className="sr-only"
        onChange={onInputChange}
      />

      <div
        onDragOver={(e) => {
          e.preventDefault();
          if (!busy) setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={onDrop}
        className={`relative mt-5 flex min-h-[240px] flex-1 flex-col items-center justify-center overflow-hidden rounded-2xl border-2 border-dashed p-6 text-center transition ${
          dragging
            ? "border-leaf-400/60 bg-leaf-500/10"
            : "border-white/10 bg-white/[0.02]"
        } ${busy && !processing ? "opacity-60" : ""}`}
      >
        {processing ? (
          <div className="flex flex-col items-center gap-3">
            <Loader2 className="h-8 w-8 animate-spin text-leaf-300" />
            <p className="text-sm text-leaf-100/70">Loading photo...</p>
          </div>
        ) : preview ? (
          <div className="relative w-full">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src={preview}
              alt="Leaf preview"
              className="mx-auto max-h-64 w-auto rounded-xl object-contain"
            />
            <button
              type="button"
              onClick={clear}
              className="absolute right-0 top-0 z-30 grid h-11 w-11 touch-manipulation place-items-center rounded-full bg-black/60 text-white backdrop-blur transition hover:bg-black/80"
              aria-label="Remove image"
            >
              <X className="h-4 w-4" />
            </button>
            <p className="mt-3 truncate text-sm text-leaf-100/70">{fileName}</p>
            <button
              type="button"
              onClick={openPicker}
              disabled={busy}
              className="btn-ghost mt-3 w-full touch-manipulation sm:w-auto"
            >
              <ImagePlus className="h-4 w-4" />
              Choose a different photo
            </button>
          </div>
        ) : (
          <div className="flex flex-col items-center">
            <ImagePlus className="h-8 w-8 text-leaf-300" />
            <p className="mt-3 text-sm text-leaf-100/60">
              Pick a photo from your gallery
            </p>
            <p className="mt-1 text-xs text-leaf-100/50">
              JPG, PNG, or WEBP up to 8 MB
            </p>
            <button
              type="button"
              onClick={openPicker}
              disabled={busy}
              className="btn-primary mt-5 w-full touch-manipulation sm:w-auto"
            >
              <UploadCloud className="h-4 w-4" />
              Choose photo
            </button>
          </div>
        )}
      </div>

      {error && <p className="mt-3 text-sm text-red-300">{error}</p>}
    </div>
  );
}
