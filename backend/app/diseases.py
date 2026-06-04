"""Disease info database.

Combines two sources at startup:

1. ``app/data/diseases.json`` — hand-curated entries (current MVP has ~10).
2. ``app/data/class_labels.json`` — the full ordered class list from the
   trained model. For any class key that doesn't have a curated entry, we
   synthesize an English placeholder so the API never returns empty
   symptoms/treatment arrays.

Lookup is by normalized key, e.g. ``"tomato_early_blight"``. The hybrid
predictor lowercases and replaces ``___`` with ``_`` before calling
:func:`get_disease`.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List

DATA_DIR = Path(__file__).parent / "data"
DISEASES_FILE = DATA_DIR / "diseases.json"
CLASS_LABELS_FILE = DATA_DIR / "class_labels.json"


def _normalize(class_key: str) -> str:
    return class_key.lower().replace("___", "_")


def _placeholder(class_key: str) -> Dict[str, Any]:
    """Generate a generic English entry for an uncurated class.

    Detects ``"healthy"`` in the key for a friendlier message; otherwise
    returns a neutral diagnosis with safe, non-prescriptive guidance.
    """
    raw = class_key
    crop, _, disease = raw.partition("___") if "___" in raw else (raw, "", "")
    crop_label = crop.replace("_", " ").strip().title() if crop else ""
    disease_label = disease.replace("_", " ").strip().title() if disease else ""

    is_healthy = "healthy" in raw.lower()

    if is_healthy:
        if crop_label:
            label = f"{crop_label} — Healthy"
        else:
            label = "Healthy plant"
        return {
            "key": _normalize(raw),
            "label": label,
            "severity": "mild",
            "symptoms": [
                "No visible lesions or discoloration on the leaf.",
                "Foliage shows normal color and venation.",
            ],
            "treatment": [
                "Maintain regular watering and balanced fertilization.",
                "Continue weekly scouting for early signs of disease.",
                "Practice crop rotation and good field hygiene.",
            ],
        }

    if crop_label and disease_label:
        label = f"{crop_label} — {disease_label}"
    elif crop_label:
        label = crop_label
    else:
        label = raw.replace("_", " ").title()

    return {
        "key": _normalize(raw),
        "label": label,
        "severity": "unknown",
        "symptoms": [
            f"Symptoms consistent with {disease_label or 'this condition'} on {crop_label or 'the plant'}.",
            "Detailed symptom notes have not been curated for this class yet.",
        ],
        "treatment": [
            "Consult a local agricultural extension officer for a definitive diagnosis.",
            "Isolate affected plants and remove severely diseased foliage to slow spread.",
            "Apply an appropriate broad-spectrum fungicide or bactericide per local guidelines.",
        ],
    }


@lru_cache(maxsize=1)
def load_diseases() -> Dict[str, Dict[str, Any]]:
    """Load curated entries and merge in auto-generated placeholders."""
    db: Dict[str, Dict[str, Any]] = {}

    raw_curated: List[Dict[str, Any]] = json.loads(
        DISEASES_FILE.read_text(encoding="utf-8")
    )
    for entry in raw_curated:
        key = _normalize(entry["key"])
        entry = dict(entry)
        entry["key"] = key
        db[key] = entry

    if CLASS_LABELS_FILE.exists():
        try:
            class_labels = json.loads(CLASS_LABELS_FILE.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            class_labels = []
        if isinstance(class_labels, list):
            for class_key in class_labels:
                if not isinstance(class_key, str):
                    continue
                norm = _normalize(class_key)
                if norm not in db:
                    db[norm] = _placeholder(class_key)

    if "unknown" not in db:
        db["unknown"] = {
            "key": "unknown",
            "label": "Unknown class",
            "severity": "unknown",
            "symptoms": ["The system has no detailed notes for this class yet."],
            "treatment": [
                "Consult a local agricultural extension officer for a definitive diagnosis.",
                "Isolate the plant to prevent potential spread while investigating.",
            ],
        }

    return db


def get_disease(key: str) -> Dict[str, Any]:
    db = load_diseases()
    norm = _normalize(key)
    return db.get(norm) or db["unknown"]


def all_keys() -> List[str]:
    return [k for k in load_diseases().keys() if k != "unknown"]
