"use client";

import { Suspense, useCallback, useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { motion } from "framer-motion";
import { Loader2, Sparkles, WifiOff } from "lucide-react";

import UploadCard from "@/components/UploadCard";
import CameraCard from "@/components/CameraCard";
import { ApiError, checkHealth, getApiBase, predictImage } from "@/lib/api";
import { fileToPreviewDataUrl } from "@/lib/imageUpload";
import { motionInitial } from "@/lib/motion";
import { saveScan } from "@/lib/scanStore";

function DetectPageInner() {
  const router = useRouter();
  const params = useSearchParams();
  const mode = params.get("mode");
  const autoStartCamera = mode === "camera";

  const [selected, setSelected] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);
  const [loadingStage, setLoadingStage] = useState<
    "uploading" | "finishing" | null
  >(null);
  const [error, setError] = useState<string | null>(null);
  const [errorCode, setErrorCode] = useState<string | null>(null);
  const [backendOk, setBackendOk] = useState<boolean | null>(null);

  useEffect(() => {
    let cancelled = false;
    void checkHealth().then((ok) => {
      if (!cancelled) setBackendOk(ok);
    });
    return () => {
      cancelled = true;
    };
  }, []);

  const handleFile = useCallback((file: File) => {
    setSelected(file);
    setError(null);
    setErrorCode(null);
  }, []);

  const runPrediction = useCallback(async () => {
    if (!selected || loading) return;
    setLoading(true);
    setLoadingStage("uploading");
    setError(null);
    setErrorCode(null);
    try {
      const prediction = await predictImage(selected);
      setLoadingStage("finishing");
      const imageDataUrl = await fileToPreviewDataUrl(selected);
      saveScan({
        prediction,
        imageDataUrl,
        createdAt: new Date().toISOString(),
      });
      router.push("/result");
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.message);
        setErrorCode(err.code ?? null);
      } else {
        setError(
          err instanceof Error
            ? err.message
            : "Unexpected error during prediction.",
        );
        setErrorCode(null);
      }
    } finally {
      setLoading(false);
      setLoadingStage(null);
    }
  }, [loading, router, selected]);

  return (
    <div className="pb-28 pt-4 sm:pb-8 sm:pt-8">
      <motion.div
        initial={motionInitial}
        animate={{ y: 0 }}
        transition={{ duration: 0.4 }}
        className="mb-8 flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between"
      >
        <div>
          <span className="chip">Detection</span>
          <h1 className="mt-3 text-3xl font-semibold tracking-tight sm:text-4xl">
            Scan a leaf
          </h1>
          <p className="mt-1 max-w-xl text-leaf-100/70">
            Upload a close-up of a{" "}
            <span className="font-medium text-leaf-100">maize, potato, or tomato</span>{" "}
            leaf — fill the frame and use good lighting. Non-leaf photos are
            rejected, and low-confidence scans show a warning on the result page.
          </p>
        </div>

        <div className="hidden flex-col gap-2 sm:flex sm:flex-row sm:items-center">
          <span className="text-sm text-leaf-100/60">
            {selected
              ? "Image ready"
              : "Pick or capture an image to continue"}
          </span>
          <AnalyzeButton
            loading={loading}
            loadingStage={loadingStage}
            disabled={!selected || loading}
            onClick={runPrediction}
          />
        </div>
      </motion.div>

      {backendOk === false && (
        <motion.div
          initial={motionInitial}
          animate={{ y: 0 }}
          className="mb-6 rounded-2xl border border-amber-500/30 bg-amber-500/10 p-4 text-sm text-amber-100"
        >
          <div className="flex items-start gap-3">
            <WifiOff className="mt-0.5 h-4 w-4 shrink-0" />
            <div>
              <p className="font-medium">Backend not reachable</p>
              <p className="mt-1 text-amber-100/80">
                The app calls{" "}
                <span className="font-mono text-xs">{getApiBase()}</span> on
                your PC. Start the backend in a terminal:{" "}
                <span className="font-mono text-xs">
                  uvicorn app.main:app --reload --port 8000
                </span>
              </p>
            </div>
          </div>
        </motion.div>
      )}

      {error && (
        <ValidationErrorBanner code={errorCode} message={error} />
      )}

      <div className="grid grid-cols-1 gap-5 lg:grid-cols-2">
        <UploadCard
          onFileSelected={handleFile}
          onFileCleared={() => setSelected(null)}
          disabled={loading}
        />
        <CameraCard
          onCapture={handleFile}
          disabled={loading}
          autoStart={autoStartCamera}
        />
      </div>

      {/* Sticky analyze bar on phones — primary action stays reachable after upload/capture */}
      <div className="fixed inset-x-0 bottom-0 z-50 border-t border-white/10 bg-canvas/95 p-4 backdrop-blur-xl sm:hidden">
        <p className="mb-2 text-center text-xs text-leaf-100/60">
          {selected
            ? "Image ready — tap Analyze"
            : "Tap Choose photo above, then Analyze"}
        </p>
        <AnalyzeButton
          loading={loading}
          loadingStage={loadingStage}
          disabled={!selected || loading}
          onClick={runPrediction}
          className="w-full"
        />
      </div>
    </div>
  );
}

function ValidationErrorBanner({
  code,
  message,
}: {
  code: string | null;
  message: string;
}) {
  const isNotLeaf = code === "not_a_leaf";

  const title = isNotLeaf
    ? "No leaf detected"
    : "Could not analyze this photo";

  const tip = isNotLeaf
    ? "Upload a close-up of a maize, potato, or tomato leaf. Avoid cars, people, sky, and other objects."
    : "Use a clear close-up of a maize, potato, or tomato leaf on a plain background.";

  return (
    <motion.div
      initial={motionInitial}
      animate={{ y: 0 }}
      className="mb-6 rounded-2xl border border-red-500/30 bg-red-500/10 p-4 text-sm text-red-200"
    >
      <p className="font-medium">{title}</p>
      {!isNotLeaf && <p className="mt-1">{message}</p>}
      <p className="mt-2 text-xs text-red-200/80">{tip}</p>
    </motion.div>
  );
}

function AnalyzeButton({
  loading,
  loadingStage,
  disabled,
  onClick,
  className = "",
}: {
  loading: boolean;
  loadingStage: "uploading" | "finishing" | null;
  disabled: boolean;
  onClick: () => void;
  className?: string;
}) {
  const label =
    loadingStage === "finishing"
      ? "Opening results..."
      : loadingStage === "uploading"
        ? "Analyzing on server..."
        : "Analyzing...";

  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      className={`btn-primary ${className}`.trim()}
    >
      {loading ? (
        <>
          <Loader2 className="h-4 w-4 animate-spin" />
          {label}
        </>
      ) : (
        <>
          <Sparkles className="h-4 w-4" />
          Analyze image
        </>
      )}
    </button>
  );
}

export default function DetectPage() {
  return (
    <Suspense fallback={<DetectFallback />}>
      <DetectPageInner />
    </Suspense>
  );
}

function DetectFallback() {
  return (
    <div className="pt-12 text-center text-leaf-100/60">
      <Loader2 className="mx-auto h-5 w-5 animate-spin" />
      <p className="mt-3 text-sm">Loading scanner...</p>
    </div>
  );
}
