"use client";

import { motion, useMotionValue, useTransform, animate } from "framer-motion";
import { useEffect, useState } from "react";

interface ConfidenceMeterProps {
  value: number; // 0..1
  size?: number;
  label?: string;
}

export default function ConfidenceMeter({
  value,
  size = 180,
  label = "Confidence",
}: ConfidenceMeterProps) {
  const clamped = Math.max(0, Math.min(1, value));
  const stroke = 14;
  const radius = (size - stroke) / 2;
  const circumference = 2 * Math.PI * radius;

  const progress = useMotionValue(0);
  const dashOffset = useTransform(
    progress,
    (p) => circumference - circumference * p,
  );
  const [display, setDisplay] = useState(0);

  useEffect(() => {
    const controls = animate(progress, clamped, {
      duration: 1.1,
      ease: "easeOut",
      onUpdate: (v) => setDisplay(v),
    });
    return () => controls.stop();
  }, [clamped, progress]);

  const tone =
    clamped >= 0.9
      ? "text-leaf-300"
      : clamped >= 0.7
        ? "text-amber-300"
        : "text-red-300";

  const stopStart = clamped >= 0.9 ? "#56c97b" : clamped >= 0.7 ? "#fbbf24" : "#f87171";
  const stopEnd = clamped >= 0.9 ? "#bfefca" : clamped >= 0.7 ? "#fde68a" : "#fecaca";

  return (
    <div
      className="relative grid place-items-center"
      style={{ width: size, height: size }}
      role="img"
      aria-label={`${label} ${(clamped * 100).toFixed(1)} percent`}
    >
      <svg width={size} height={size} className="-rotate-90">
        <defs>
          <linearGradient id="meterGrad" x1="0" x2="1" y1="0" y2="1">
            <stop offset="0%" stopColor={stopStart} />
            <stop offset="100%" stopColor={stopEnd} />
          </linearGradient>
        </defs>
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke="rgba(255,255,255,0.08)"
          strokeWidth={stroke}
        />
        <motion.circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke="url(#meterGrad)"
          strokeWidth={stroke}
          strokeLinecap="round"
          strokeDasharray={circumference}
          style={{ strokeDashoffset: dashOffset }}
        />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span className={`text-4xl font-semibold tabular-nums ${tone}`}>
          {(display * 100).toFixed(1)}
          <span className="text-lg">%</span>
        </span>
        <span className="mt-1 text-xs uppercase tracking-wider text-leaf-100/60">
          {label}
        </span>
      </div>
    </div>
  );
}
