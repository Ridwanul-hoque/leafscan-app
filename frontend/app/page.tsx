"use client";

import Link from "next/link";
import { motion } from "framer-motion";
import {
  Camera,
  Upload,
  Sparkles,
  ShieldCheck,
  Zap,
  Leaf,
} from "lucide-react";

import { fadeUpVariants, motionInitial } from "@/lib/motion";

const features = [
  {
    icon: Zap,
    title: "Instant diagnosis",
    body: "Hybrid deep-learning model returns a prediction in under a second on a warm server.",
  },
  {
    icon: ShieldCheck,
    title: "Confidence scored",
    body: "Every prediction ships with a calibrated confidence score so you can trust it.",
  },
  {
    icon: Sparkles,
    title: "Treatment guidance",
    body: "Symptom summary and practical treatment steps — not just a label.",
  },
];

export default function LandingPage() {
  return (
    <div className="relative">
      <section className="relative pt-10 sm:pt-16 lg:pt-24">
        <motion.div
          initial={motionInitial}
          animate="show"
          className="mx-auto max-w-3xl text-center"
        >
          <motion.div variants={fadeUpVariants} custom={0}>
            <span className="chip">
              <Leaf className="h-3.5 w-3.5 text-leaf-300" />
              Plant pathology, powered by AI
            </span>
          </motion.div>

          <motion.h1
            variants={fadeUpVariants}
            custom={1}
            className="mt-6 text-balance text-4xl font-semibold leading-[1.05] tracking-tight sm:text-5xl lg:text-6xl"
          >
            Detect plant diseases{" "}
            <span className="text-leaf-400">instantly</span>
          </motion.h1>

          <motion.p
            variants={fadeUpVariants}
            custom={2}
            className="mx-auto mt-5 max-w-xl text-pretty text-base text-leaf-100/70 sm:text-lg"
          >
            Upload a close-up of a maize, potato, or tomato leaf. Our hybrid
            model identifies the disease, scores its confidence, and recommends
            treatment — right in your browser.
          </motion.p>

          <motion.div
            variants={fadeUpVariants}
            custom={3}
            className="mt-8 flex flex-col items-center justify-center gap-3 sm:flex-row"
          >
            <Link
              href="/detect?mode=upload"
              className="btn-primary relative z-10 w-full touch-manipulation sm:w-auto"
            >
              <Upload className="h-4 w-4" />
              Upload image
            </Link>
            <Link
              href="/detect?mode=camera"
              className="btn-ghost relative z-10 w-full touch-manipulation sm:w-auto"
            >
              <Camera className="h-4 w-4" />
              Open camera
            </Link>
          </motion.div>
        </motion.div>
      </section>

      {/* Features section */}
      <section className="mt-16 grid grid-cols-1 gap-4 sm:mt-24 sm:grid-cols-3">
        {features.map((f) => (
          <div key={f.title} className="glass-card glass-card-hover p-6">
            <f.icon className="h-5 w-5 text-leaf-300" />
            <h3 className="mt-4 text-lg font-semibold">{f.title}</h3>
            <p className="mt-2 text-sm text-leaf-100/70">{f.body}</p>
          </div>
        ))}
      </section>
    </div>
  );
}
