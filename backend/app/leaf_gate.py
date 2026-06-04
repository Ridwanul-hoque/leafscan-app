"""CNN leaf gate (MobileNetV2 leaf vs not-leaf) before disease inference."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

import cv2
import numpy as np

if TYPE_CHECKING:
    from .config import Settings

logger = logging.getLogger(__name__)

_gate: "CnnLeafGate | None" = None

# Fast scene veto — catches CNN false positives (e.g. car + overcast sky/road).
_GRAY_MAX = 0.62
_MIN_PLANT_WHEN_GRAY = 0.12
_BLUE_MAX = 0.28
_SKIN_MAX = 0.18
_MIN_PLANT_ABSOLUTE = 0.03


def _plant_fraction(bgr: np.ndarray) -> float:
    h, w = bgr.shape[:2]
    if h == 0 or w == 0:
        return 0.0
    total = float(h * w)
    hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
    mask_green = cv2.inRange(hsv, (15, 20, 20), (95, 255, 255))
    mask_yellow = cv2.inRange(hsv, (8, 20, 20), (45, 255, 255))
    plant_mask = cv2.bitwise_or(mask_green, mask_yellow)
    plant_cov = float(np.count_nonzero(plant_mask)) / total
    rgb_f = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0
    r, g, b = rgb_f[..., 0], rgb_f[..., 1], rgb_f[..., 2]
    exg = 2.0 * g - r - b
    exg_cov = float(np.count_nonzero(exg > 0.02)) / total
    return max(plant_cov, exg_cov)


def _scene_veto_reason(bgr: np.ndarray) -> str | None:
    """Obvious non-leaf scenes the demo CNN may still label as leaf."""
    h, w = bgr.shape[:2]
    if h == 0 or w == 0:
        return "empty_image"
    total = float(h * w)
    hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)

    blue_cov = float(np.count_nonzero(cv2.inRange(hsv, (90, 30, 40), (130, 255, 255)))) / total
    gray_cov = float(np.count_nonzero(cv2.inRange(hsv, (0, 0, 40), (180, 50, 230)))) / total
    skin_cov = float(np.count_nonzero(cv2.inRange(hsv, (0, 20, 70), (25, 160, 255)))) / total
    plant_cov = _plant_fraction(bgr)

    if blue_cov >= _BLUE_MAX:
        return "too_much_sky"
    if gray_cov >= _GRAY_MAX and plant_cov < _MIN_PLANT_WHEN_GRAY:
        return "mostly_gray_scene"
    if skin_cov >= _SKIN_MAX:
        return "skin_detected"
    if plant_cov < _MIN_PLANT_ABSOLUTE:
        return "no_plant_pixels"
    return None


@dataclass(frozen=True)
class LeafGateResult:
    is_leaf: bool
    score: float  # P(leaf), 0–1
    reason: str | None = None


class CnnLeafGate:
    """MobileNetV2 binary classifier; softmax index 1 = leaf."""

    name = "model"

    def __init__(self, model_path: str, threshold: float) -> None:
        from tensorflow.keras.applications.mobilenet_v2 import preprocess_input

        from .leaf_gate_model import LEAF_CLASS_INDEX, build_leaf_gate_mobilenet

        weights_file = Path(model_path)
        if not weights_file.is_file():
            raise FileNotFoundError(
                f"Leaf gate weights not found at {weights_file.resolve()}. "
                "Run: python scripts/train_leaf_gate.py --demo"
            )

        self._threshold = threshold
        self._preprocess_input = preprocess_input
        self._leaf_index = LEAF_CLASS_INDEX

        logger.info("Building leaf gate MobileNetV2...")
        self._model = build_leaf_gate_mobilenet()
        logger.info("Loading leaf gate weights from %s", weights_file)
        self._model.load_weights(str(weights_file))

        logger.info("Warming up leaf gate...")
        warmup = self._preprocess_input(np.zeros((1, 224, 224, 3), dtype=np.float32))
        self._model.predict(warmup, verbose=0)
        logger.info("CnnLeafGate ready.")

    def is_plant_leaf(self, rgb: np.ndarray) -> LeafGateResult:
        if rgb.dtype != np.uint8:
            rgb = np.clip(rgb, 0, 255).astype(np.uint8)
        bgr = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)

        veto = _scene_veto_reason(bgr)
        if veto is not None:
            return LeafGateResult(is_leaf=False, score=0.0, reason=veto)

        resized = cv2.resize(rgb, (224, 224), interpolation=cv2.INTER_AREA)
        batch = self._preprocess_input(resized.astype(np.float32))[None, ...]
        probs = self._model.predict(batch, verbose=0)[0]
        score = float(probs[self._leaf_index])
        is_leaf = score >= self._threshold

        # CNN can overfit demo data; block high-confidence leaf on plant-poor scenes.
        if is_leaf and _plant_fraction(bgr) < 0.06:
            return LeafGateResult(is_leaf=False, score=score, reason="low_plant_coverage")

        reason = None if is_leaf else "below_threshold"
        return LeafGateResult(is_leaf=is_leaf, score=score, reason=reason)


def build_leaf_gate(settings: "Settings") -> CnnLeafGate:
    """Load the CNN leaf gate (required at startup)."""
    return CnnLeafGate(
        model_path=settings.leaf_gate_model_path,
        threshold=settings.leaf_gate_threshold,
    )


def get_leaf_gate() -> CnnLeafGate:
    global _gate
    if _gate is None:
        from .config import get_settings

        _gate = build_leaf_gate(get_settings())
    return _gate


def set_leaf_gate(gate: CnnLeafGate) -> None:
    global _gate
    _gate = gate


def reset_leaf_gate() -> None:
    global _gate
    _gate = None
