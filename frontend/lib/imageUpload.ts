const ALLOWED_TYPES = new Set(["image/jpeg", "image/png", "image/webp"]);
const ALLOWED_EXT = new Set([
  "jpg",
  "jpeg",
  "png",
  "webp",
  "heic",
  "heif",
]);
const MAX_BYTES = 8 * 1024 * 1024;
/** Resize/compress before upload so Wi-Fi + server inference stay fast on phones. */
const UPLOAD_MAX_EDGE = 1280;
const UPLOAD_QUALITY = 0.85;
/** Phone gallery JPEGs are often 2–5 MB even when under the 8 MB cap. */
const UPLOAD_SIZE_THRESHOLD = 350 * 1024;
const PREVIEW_MAX_EDGE = 640;
const PREVIEW_QUALITY = 0.78;

export class ImageUploadError extends Error {
  constructor(
    public code:
      | "unsupported_format"
      | "decode_failed"
      | "too_large"
      | "compression_failed",
    message: string,
  ) {
    super(message);
  }
}

export function isLikelyImageFile(file: File): boolean {
  if (ALLOWED_TYPES.has(file.type)) return true;
  if (file.type.startsWith("image/")) return true;
  if (file.type === "" || file.type === "application/octet-stream") {
    const ext = file.name.split(".").pop()?.toLowerCase();
    return ext ? ALLOWED_EXT.has(ext) : true;
  }
  return false;
}

async function fileToJpeg(
  file: File,
  quality = UPLOAD_QUALITY,
  maxEdge = UPLOAD_MAX_EDGE,
): Promise<File | null> {
  const canvas = document.createElement("canvas");
  const ctx = canvas.getContext("2d");
  if (!ctx) return null;

  const drawAndEncode = async (srcW: number, srcH: number, draw: () => void) => {
    const scale = Math.min(1, maxEdge / Math.max(srcW, srcH));
    const width = Math.max(1, Math.round(srcW * scale));
    const height = Math.max(1, Math.round(srcH * scale));
    canvas.width = width;
    canvas.height = height;
    draw();
    const blob = await new Promise<Blob | null>((resolve) => {
      canvas.toBlob(resolve, "image/jpeg", quality);
    });
    return blob;
  };

  if (typeof createImageBitmap === "function") {
    try {
      const bitmap = await createImageBitmap(file);
      const blob = await drawAndEncode(bitmap.width, bitmap.height, () => {
        ctx.drawImage(bitmap, 0, 0, canvas.width, canvas.height);
      });
      bitmap.close();
      if (blob) {
        const baseName = file.name.replace(/\.[^.]+$/, "") || "photo";
        return new File([blob], `${baseName}.jpg`, { type: "image/jpeg" });
      }
    } catch {
      // Fallback to FileReader + HTMLImageElement for mobile browsers.
    }
  }

  try {
    const dataUrl = await new Promise<string>((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = () => resolve(String(reader.result));
      reader.onerror = () => reject(reader.error ?? new Error("Read failed"));
      reader.readAsDataURL(file);
    });

    const img = await new Promise<HTMLImageElement>((resolve, reject) => {
      const el = new Image();
      el.onload = () => resolve(el);
      el.onerror = () => reject(new Error("Decode failed"));
      el.src = dataUrl;
    });

    const blob = await drawAndEncode(img.naturalWidth, img.naturalHeight, () => {
      ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
    });
    if (!blob) return null;

    const baseName = file.name.replace(/\.[^.]+$/, "") || "photo";
    return new File([blob], `${baseName}.jpg`, { type: "image/jpeg" });
  } catch {
    return null;
  }
}

/** Decode phone gallery picks and shrink large photos before preview + API upload. */
export async function normalizeImageForUpload(file: File): Promise<File> {
  if (!isLikelyImageFile(file)) {
    throw new ImageUploadError(
      "unsupported_format",
      "Unsupported format. Use JPG, PNG, or WEBP.",
    );
  }

  const needsConvert =
    !ALLOWED_TYPES.has(file.type) ||
    file.size > UPLOAD_SIZE_THRESHOLD ||
    file.type === "image/heic" ||
    file.type === "image/heif";

  if (!needsConvert) return file;

  const converted = await fileToJpeg(file, UPLOAD_QUALITY, UPLOAD_MAX_EDGE);
  if (!converted) {
    if (ALLOWED_TYPES.has(file.type) && file.size <= MAX_BYTES) {
      return file;
    }
    throw new ImageUploadError(
      "decode_failed",
      "Could not read this photo. On iPhone, try Settings → Camera → Formats → Most Compatible, or pick a JPG/PNG from your gallery.",
    );
  }

  if (converted.size > MAX_BYTES) {
    const smaller = await fileToJpeg(converted, 0.72, 1024);
    if (smaller && smaller.size <= MAX_BYTES) return smaller;
    throw new ImageUploadError(
      "too_large",
      "Image is larger than 8 MB even after compression.",
    );
  }

  return converted;
}

/** Small JPEG data URL for the result page — avoids encoding multi-MB files on phones. */
export async function fileToPreviewDataUrl(file: File | Blob): Promise<string> {
  const asFile =
    file instanceof File
      ? file
      : new File([file], "preview.jpg", { type: file.type || "image/jpeg" });

  const thumb = await fileToJpeg(asFile, PREVIEW_QUALITY, PREVIEW_MAX_EDGE);
  const blob = thumb ?? asFile;
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result));
    reader.onerror = () => reject(reader.error ?? new Error("Read failed"));
    reader.readAsDataURL(blob);
  });
}
