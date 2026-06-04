"""OpenCV preprocessing pipeline.

Verbatim port of the notebook
``fork-of-hybrid-efficientnet-mobilenet-distillation.ipynb`` lines 71-169.
The model was trained with this exact pipeline (FAST_MODE=False), so any
deviation here will degrade accuracy at inference time.

Pipeline summary (RGB uint8 input -> 256x256x3 RGB uint8 output):

  1. RGB -> BGR
  2. Gray-world white balance
  3. CLAHE on the V channel of HSV (clip=3.0, tiles=8x8)
  4. HSV-based leaf mask (green + red ranges) + morphological cleanup
     + largest connected component
  5. Lesion saliency (LAB-a + ExGR-inverted + Laplacian) -> Otsu threshold
     + morph + size filter
  6. Lesion-aware bounding-box crop with 16 px padding
  7. BGR -> RGB and resize to 256x256 (cv2.INTER_AREA)
"""

from __future__ import annotations

import io
from dataclasses import dataclass
from typing import Tuple

import cv2
import numpy as np
from PIL import Image

TARGET_SIZE: Tuple[int, int] = (256, 256)
FAST_MODE: bool = False  # must match training in the notebook
# OpenCV lesion pipeline is O(pixels); cap input size before heavy ops.
MAX_INPUT_EDGE: int = 1280


# --------------------------------------------------------------------------- #
# Notebook helpers (verbatim)
# --------------------------------------------------------------------------- #


def _to_uint8(img: np.ndarray) -> np.ndarray:
    return np.clip(img, 0, 255).astype(np.uint8)


def gray_world_white_balance(bgr: np.ndarray) -> np.ndarray:
    b, g, r = cv2.split(bgr.astype(np.float32))
    mb, mg, mr = b.mean() + 1e-6, g.mean() + 1e-6, r.mean() + 1e-6
    m = (mb + mg + mr) / 3.0
    b *= m / mb
    g *= m / mg
    r *= m / mr
    return _to_uint8(cv2.merge([b, g, r]))


def clahe_on_v(bgr: np.ndarray, clip: float = 3.0, tiles: int = 8) -> np.ndarray:
    hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
    clahe = cv2.createCLAHE(clipLimit=clip, tileGridSize=(tiles, tiles))
    hsv[..., 2] = clahe.apply(hsv[..., 2])
    return cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)


def leaf_mask_hsv(bgr: np.ndarray) -> np.ndarray:
    hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
    mask_green = cv2.inRange(hsv, (20, 40, 40), (90, 255, 255))
    mask_red1 = cv2.inRange(hsv, (0, 40, 40), (10, 255, 255))
    mask_red2 = cv2.inRange(hsv, (170, 40, 40), (180, 255, 255))
    mask = cv2.bitwise_or(mask_green, cv2.bitwise_or(mask_red1, mask_red2))
    k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, k, iterations=2)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, k, iterations=2)
    num, labels, stats, _ = cv2.connectedComponentsWithStats(mask, 8)
    if num > 1:
        largest = 1 + np.argmax(stats[1:, cv2.CC_STAT_AREA])
        mask = np.where(labels == largest, 255, 0).astype(np.uint8)
    return mask


def compute_indices(bgr: np.ndarray) -> dict:
    rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB).astype(np.float32)
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    eps = 1e-6
    r1, g1, b1 = r / 255.0, g / 255.0, b / 255.0
    exg = 2 * g1 - r1 - b1
    exr = 1.4 * r1 - g1
    exgr = exg - exr
    ndi = (g1 - r1) / (g1 + r1 + eps)
    lab = cv2.cvtColor(_to_uint8(rgb), cv2.COLOR_RGB2LAB).astype(np.float32)
    a = lab[..., 1]

    def norm255(x: np.ndarray) -> np.ndarray:
        x = x - np.nanmin(x)
        d = np.nanmax(x) - np.nanmin(x) + eps
        return _to_uint8(255 * (x / d))

    return {"exgr": norm255(exgr), "ndi": norm255(ndi), "a": norm255(a)}


def lesion_saliency(bgr: np.ndarray, leaf_mask: np.ndarray):
    idx = compute_indices(bgr)
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    lap = cv2.Laplacian(gray, cv2.CV_32F, ksize=3)
    lap_a = _to_uint8(np.abs(lap))
    exgr_inv = _to_uint8(255 - idx["exgr"])
    sal = 0.45 * idx["a"] + 0.30 * exgr_inv + 0.25 * lap_a
    sal = _to_uint8(sal)
    sal = cv2.bitwise_and(sal, sal, mask=leaf_mask)
    _, binm = cv2.threshold(sal, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
    binm = cv2.morphologyEx(binm, cv2.MORPH_OPEN, k, iterations=1)
    binm = cv2.morphologyEx(binm, cv2.MORPH_CLOSE, k, iterations=2)
    num, labels, stats, _ = cv2.connectedComponentsWithStats(binm, 8)
    keep = np.zeros_like(binm)
    h, w = binm.shape
    min_area = max(30, int(0.0005 * h * w))
    for i in range(1, num):
        if stats[i, cv2.CC_STAT_AREA] >= min_area:
            keep[labels == i] = 255
    return keep, sal


def apply_mask(bgr: np.ndarray, mask: np.ndarray) -> np.ndarray:
    return cv2.bitwise_and(bgr, bgr, mask=mask)


def lesion_aware_crop(bgr: np.ndarray, lesion_mask: np.ndarray, pad: int = 16) -> np.ndarray:
    ys, xs = np.where(lesion_mask > 0)
    if len(xs) == 0:
        return bgr
    x1, x2 = xs.min(), xs.max()
    y1, y2 = ys.min(), ys.max()
    x1 = max(0, x1 - pad)
    y1 = max(0, y1 - pad)
    x2 = min(bgr.shape[1] - 1, x2 + pad)
    y2 = min(bgr.shape[0] - 1, y2 + pad)
    return bgr[y1 : y2 + 1, x1 : x2 + 1]


def preprocess_plant_image(img: np.ndarray) -> np.ndarray:
    """RGB uint8 in -> RGB uint8 (TARGET_SIZE) out."""
    if img.dtype != np.uint8:
        img = np.clip(img, 0, 255).astype(np.uint8)
    bgr = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
    wb = gray_world_white_balance(bgr)
    enh = clahe_on_v(wb, clip=3.0, tiles=8)
    if FAST_MODE:
        out_bgr = enh
    else:
        leaf = leaf_mask_hsv(wb)
        plant = apply_mask(enh, leaf)
        lesion_mask, _ = lesion_saliency(plant, leaf)
        out_bgr = lesion_aware_crop(plant, lesion_mask)
    rgb = cv2.cvtColor(out_bgr, cv2.COLOR_BGR2RGB)
    rgb = cv2.resize(rgb, TARGET_SIZE, interpolation=cv2.INTER_AREA)
    return rgb


# --------------------------------------------------------------------------- #
# API integration helper
# --------------------------------------------------------------------------- #


def _downscale_if_needed(rgb: np.ndarray) -> np.ndarray:
    h, w = rgb.shape[:2]
    edge = max(h, w)
    if edge <= MAX_INPUT_EDGE:
        return rgb
    scale = MAX_INPUT_EDGE / edge
    new_w = max(1, int(round(w * scale)))
    new_h = max(1, int(round(h * scale)))
    return cv2.resize(rgb, (new_w, new_h), interpolation=cv2.INTER_AREA)


@dataclass(frozen=True)
class PreprocessResult:
    """Model input tensor plus CNN leaf-gate metrics."""

    tensor: np.ndarray
    leaf_gate_score: float  # P(leaf) from CNN gate
    is_plant_leaf: bool


def prepare_for_model_with_metrics(image_bytes: bytes) -> PreprocessResult:
    """Decode upload bytes -> model tensor and leaf-validation metrics."""
    from .leaf_gate import get_leaf_gate

    pil = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    rgb = np.array(pil, dtype=np.uint8)
    rgb = _downscale_if_needed(rgb)
    gate_result = get_leaf_gate().is_plant_leaf(rgb)
    pre = preprocess_plant_image(rgb)
    return PreprocessResult(
        tensor=pre.astype("float32")[None, ...],
        leaf_gate_score=gate_result.score,
        is_plant_leaf=gate_result.is_leaf,
    )


def prepare_for_model(image_bytes: bytes) -> np.ndarray:
    """Decode arbitrary uploaded image bytes -> ``(1, 256, 256, 3) float32``.

    The model's first layer (``Rescaling(1/127.5, offset=-1)``) handles the
    final [-1, 1] normalization, so this helper returns plain float32 in
    [0, 255].
    """
    return prepare_for_model_with_metrics(image_bytes).tensor
