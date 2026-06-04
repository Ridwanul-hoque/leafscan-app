"""Shared checks for pytest (importable module; not collected as tests)."""

from __future__ import annotations

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent
HYBRID_WEIGHTS = REPO_ROOT / "models" / "hybrid_effnet_mobilenet_distill_final.weights.h5"
HYBRID_LABELS = REPO_ROOT / "app" / "data" / "class_labels.json"
LEAF_GATE_WEIGHTS = REPO_ROOT / "models" / "leaf_gate.weights.h5"


def leaf_gate_artifacts_ready() -> bool:
    return LEAF_GATE_WEIGHTS.is_file()


def hybrid_artifacts_ready() -> bool:
    if not HYBRID_WEIGHTS.exists() or not leaf_gate_artifacts_ready():
        return False
    try:
        data = json.loads(HYBRID_LABELS.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    return isinstance(data, list) and bool(data) and all(isinstance(x, str) for x in data)
