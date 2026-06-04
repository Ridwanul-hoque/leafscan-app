"use client";

import type { PredictionResponse } from "./api";

const STORAGE_KEY = "leafscan:last-scan";

export interface StoredScan {
  prediction: PredictionResponse;
  imageDataUrl: string;
  createdAt: string;
}

export function saveScan(scan: StoredScan): void {
  if (typeof window === "undefined") return;
  try {
    window.sessionStorage.setItem(STORAGE_KEY, JSON.stringify(scan));
  } catch {
    /* quota / private mode */
  }
}

export function loadScan(): StoredScan | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = window.sessionStorage.getItem(STORAGE_KEY);
    if (!raw) return null;
    return JSON.parse(raw) as StoredScan;
  } catch {
    return null;
  }
}

export function clearScan(): void {
  if (typeof window === "undefined") return;
  window.sessionStorage.removeItem(STORAGE_KEY);
}

export function fileToDataUrl(file: File | Blob): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result));
    reader.onerror = () => reject(reader.error ?? new Error("Read failed"));
    reader.readAsDataURL(file);
  });
}
