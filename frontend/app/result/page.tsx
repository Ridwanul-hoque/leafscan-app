"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import {
  ArrowLeft,
  Leaf,
  Stethoscope,
  Sparkles,
  AlertCircle,
} from "lucide-react";

import ConfidenceMeter from "@/components/ConfidenceMeter";
import { motionInitial } from "@/lib/motion";
import { loadScan, type StoredScan } from "@/lib/scanStore";

const severityLabel: Record<string, string> = {
  mild: "Mild",
  moderate: "Moderate",
  severe: "Severe",
  unknown: "Unknown",
};

const severityTone: Record<string, string> = {
  mild: "border-leaf-400/30 bg-leaf-400/10 text-leaf-200",
  moderate: "border-amber-400/30 bg-amber-400/10 text-amber-200",
  severe: "border-red-400/30 bg-red-400/10 text-red-200",
  unknown: "border-white/15 bg-white/5 text-leaf-100/70",
};

export default function ResultPage() {
  const [scan, setScan] = useState<StoredScan | null | undefined>(undefined);

  useEffect(() => {
    setScan(loadScan());
  }, []);

  if (scan === undefined) {
    return (
      <div className="pt-20 text-center text-leaf-100/60">
        Loading result...
      </div>
    );
  }

  if (scan === null) {
    return (
      <div className="mx-auto max-w-xl pt-16 text-center">
        <div className="glass-card p-8">
          <AlertCircle className="mx-auto h-8 w-8 text-amber-300" />
          <h1 className="mt-4 text-2xl font-semibold">No scan found</h1>
          <p className="mt-2 text-sm text-leaf-100/70">
            We could not find a recent scan in this session. Run a new scan to
            see results here.
          </p>
          <Link href="/detect" className="btn-primary mt-6">
            Scan a leaf
          </Link>
        </div>
      </div>
    );
  }

  const { prediction, imageDataUrl, createdAt } = scan;
  const sev = prediction.severity ?? "unknown";
  const showLowConfidenceWarning = prediction.low_confidence_warning;

  return (
    <div className="pt-4 sm:pt-8">
      {showLowConfidenceWarning && (
        <motion.div
          initial={motionInitial}
          className="mb-5 rounded-2xl border border-amber-500/30 bg-amber-500/10 p-4 text-sm text-amber-100"
        >
          <p className="font-medium">Low confidence — diagnosis may be unreliable</p>
          <p className="mt-1 text-amber-100/85">
            {prediction.warning_message ??
              "Retake with brighter light and a clearer close-up of the leaf."}
          </p>
        </motion.div>
      )}

      <motion.div initial={motionInitial} className="mb-6 flex items-center justify-between gap-3">
        <Link
          href="/detect"
          className="inline-flex items-center gap-2 text-sm text-leaf-100/70 hover:text-white"
        >
          <ArrowLeft className="h-4 w-4" />
          New scan
        </Link>
        <span className="text-xs text-leaf-100/50">
          {new Date(createdAt).toLocaleString()}
        </span>
      </motion.div>

      <div className="grid grid-cols-1 gap-5 lg:grid-cols-[1.1fr_1fr]">
        {/* Left: image + meta */}
        <motion.div initial={motionInitial} className="glass-card overflow-hidden">
          <div className="relative bg-black/40">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src={imageDataUrl}
              alt="Scanned leaf"
              className="h-[360px] w-full object-contain sm:h-[460px]"
            />
            <div className="absolute left-4 top-4">
              <span className="chip">
                <Leaf className="h-3.5 w-3.5 text-leaf-300" />
                Scanned leaf
              </span>
            </div>
          </div>
          <div className="p-6">
            <div className="flex flex-wrap items-center gap-2">
              <span
                className={`inline-flex items-center gap-1.5 rounded-full border px-3 py-1 text-xs font-medium ${severityTone[sev] ?? severityTone.unknown}`}
              >
                Severity: {severityLabel[sev] ?? severityLabel.unknown}
              </span>
              <span className="chip">
                <Sparkles className="h-3.5 w-3.5 text-leaf-300" />
                AI diagnosis
              </span>
            </div>
            <h1 className="mt-3 text-3xl font-semibold tracking-tight sm:text-4xl">
              {prediction.label}
            </h1>
          </div>
        </motion.div>

        {/* Right: confidence + info */}
        <motion.div initial={motionInitial} className="flex flex-col gap-5">
          <div className="glass-card flex items-center gap-6 p-6">
            <ConfidenceMeter value={prediction.confidence} />
            <div className="flex-1">
              <h2 className="text-sm uppercase tracking-wider text-leaf-100/60">
                Prediction confidence
              </h2>
              <p className="mt-2 text-sm text-leaf-100/70">
                Our hybrid model scores how sure it is about this diagnosis.
                Anything above 90% is strong; below 50% we recommend capturing
                a clearer, well-lit photo.
              </p>
            </div>
          </div>

          <section className="glass-card p-6">
            <div className="flex items-center gap-2">
              <AlertCircle className="h-5 w-5 text-amber-300" />
              <h2 className="text-lg font-semibold">Symptoms</h2>
            </div>
            {prediction.symptoms?.length ? (
              <ul className="mt-3 space-y-2 text-sm text-leaf-100/80">
                {prediction.symptoms.map((s, i) => (
                  <li key={i} className="flex gap-2">
                    <span className="mt-1 block h-1.5 w-1.5 shrink-0 rounded-full bg-leaf-400" />
                    {s}
                  </li>
                ))}
              </ul>
            ) : (
              <p className="mt-3 text-sm text-leaf-100/60">
                No symptom notes for this class yet.
              </p>
            )}
          </section>

          <section className="glass-card p-6">
            <div className="flex items-center gap-2">
              <Stethoscope className="h-5 w-5 text-leaf-300" />
              <h2 className="text-lg font-semibold">Treatment</h2>
            </div>
            {prediction.treatment?.length ? (
              <ol className="mt-3 space-y-3 text-sm text-leaf-100/80">
                {prediction.treatment.map((t, i) => (
                  <li key={i} className="flex gap-3">
                    <span className="grid h-6 w-6 shrink-0 place-items-center rounded-full bg-leaf-500/20 text-xs font-semibold text-leaf-200 ring-1 ring-leaf-400/30">
                      {i + 1}
                    </span>
                    <span>{t}</span>
                  </li>
                ))}
              </ol>
            ) : (
              <p className="mt-3 text-sm text-leaf-100/60">
                No treatment steps for this class yet.
              </p>
            )}
          </section>
        </motion.div>
      </div>

      <motion.div initial={motionInitial} className="mt-8 flex justify-center">
        <Link href="/detect" className="btn-ghost">
          Scan another leaf
        </Link>
      </motion.div>
    </div>
  );
}
