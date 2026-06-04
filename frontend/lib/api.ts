export interface PredictionResponse {
  label: string;
  confidence: number;
  severity: "mild" | "moderate" | "severe" | "unknown";
  symptoms: string[];
  treatment: string[];
  low_confidence_warning: boolean;
  warning_message: string | null;
}

export type ValidationErrorCode = "not_a_leaf";

export class ApiError extends Error {
  status: number;
  code?: ValidationErrorCode | string;

  constructor(
    message: string,
    status: number,
    code?: ValidationErrorCode | string,
  ) {
    super(message);
    this.status = status;
    this.code = code;
  }
}

function parseErrorDetail(detail: unknown): { message: string; code?: string } {
  if (typeof detail === "string") {
    return { message: detail };
  }
  if (
    detail &&
    typeof detail === "object" &&
    "message" in detail &&
    typeof (detail as { message: unknown }).message === "string"
  ) {
    const obj = detail as { message: string; code?: string };
    return { message: obj.message, code: obj.code };
  }
  return { message: "Prediction failed." };
}

function isLocalApiHost(hostname: string): boolean {
  return hostname === "localhost" || hostname === "127.0.0.1";
}

export function getApiBase(): string {
  const envUrl = process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "");

  if (typeof window === "undefined") {
    return "http://127.0.0.1:8000";
  }

  // Production: explicit remote API URL (e.g. Render/Railway).
  if (envUrl) {
    try {
      const parsed = new URL(envUrl);
      if (!isLocalApiHost(parsed.hostname)) {
        return envUrl;
      }
    } catch {
      /* use local proxy below */
    }
  }

  // Local dev: same-origin /api proxy → backend on this PC (works from phone).
  return `${window.location.origin}/api`;
}

export async function predictImage(file: File): Promise<PredictionResponse> {
  const form = new FormData();
  form.append("image", file);

  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 90_000);

  let res: Response;
  try {
    res = await fetch(`${getApiBase()}/predict`, {
      method: "POST",
      body: form,
      signal: controller.signal,
    });
  } catch (err) {
    if (err instanceof DOMException && err.name === "AbortError") {
      throw new ApiError(
        "Analysis timed out. Move closer to Wi-Fi, use a smaller photo, or retry.",
        0,
      );
    }
    const base = getApiBase();
    throw new ApiError(
      `Could not reach the prediction service (tried ${base}). Is the backend running on this PC? Start it with: uvicorn app.main:app --reload --port 8000`,
      0,
    );
  } finally {
    clearTimeout(timeout);
  }

  if (!res.ok) {
    let message = `Prediction failed (HTTP ${res.status})`;
    let code: string | undefined;
    try {
      const body = (await res.json()) as { detail?: unknown };
      if (body?.detail !== undefined) {
        const parsed = parseErrorDetail(body.detail);
        message = parsed.message;
        code = parsed.code;
      }
    } catch {
      /* ignore parse errors */
    }
    throw new ApiError(message, res.status, code);
  }

  return (await res.json()) as PredictionResponse;
}

export async function checkHealth(): Promise<boolean> {
  try {
    const res = await fetch(`${getApiBase()}/health`, { method: "GET" });
    return res.ok;
  } catch {
    return false;
  }
}
