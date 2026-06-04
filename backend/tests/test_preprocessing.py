"""Tests for the OpenCV preprocessing pipeline.

These keep the port honest by checking shape/dtype invariants against
synthetic images. We don't compare exact pixel values since the pipeline is
heavy and platform-specific (cv2 build flags), but the contract — shape,
dtype, and that the output is non-degenerate — is enforced.
"""

import io

import numpy as np
import pytest
from PIL import Image

from hybrid_requirements import leaf_gate_artifacts_ready


def _png_bytes(arr: np.ndarray) -> bytes:
    buf = io.BytesIO()
    Image.fromarray(arr).save(buf, format="PNG")
    return buf.getvalue()


def _leaf_like_rgb(size: int = 320) -> np.ndarray:
    """Deterministic image with a green-dominant centre disc + brown spots
    so the HSV leaf mask actually fires."""
    h = w = size
    arr = np.full((h, w, 3), 16, dtype=np.uint8)  # dark canvas
    yy, xx = np.mgrid[0:h, 0:w]
    cx, cy, r = w // 2, h // 2, int(0.42 * size)
    disc = (xx - cx) ** 2 + (yy - cy) ** 2 <= r * r
    arr[disc] = (40, 160, 60)  # green leaf
    # add a few brown lesion blobs
    for ox, oy, br in [(-30, -10, 12), (20, 25, 14), (5, -40, 9)]:
        blob = (xx - (cx + ox)) ** 2 + (yy - (cy + oy)) ** 2 <= br * br
        arr[blob & disc] = (110, 70, 35)
    return arr


@pytest.fixture()
def leaf_rgb() -> np.ndarray:
    return _leaf_like_rgb()


def test_preprocess_returns_correct_shape_and_dtype(leaf_rgb):
    from app.preprocessing import preprocess_plant_image, TARGET_SIZE

    out = preprocess_plant_image(leaf_rgb)
    assert out.shape == (*TARGET_SIZE, 3)
    assert out.dtype == np.uint8


def test_preprocess_keeps_leaf_pixels(leaf_rgb):
    """A leaf-shaped input should not be entirely masked out."""
    from app.preprocessing import preprocess_plant_image

    out = preprocess_plant_image(leaf_rgb)
    assert out.mean() > 0, "Pipeline produced an all-black output for a leaf image"


def test_prepare_for_model_returns_batch_float(leaf_rgb):
    from app.preprocessing import prepare_for_model

    out = prepare_for_model(_png_bytes(leaf_rgb))
    assert out.shape == (1, 256, 256, 3)
    assert out.dtype == np.float32
    assert 0.0 <= float(out.min()) <= float(out.max()) <= 255.0


def test_prepare_for_model_downscales_large_input():
    from app.preprocessing import MAX_INPUT_EDGE, prepare_for_model

    large = _leaf_like_rgb(size=MAX_INPUT_EDGE * 2)
    out = prepare_for_model(_png_bytes(large))
    assert out.shape == (1, 256, 256, 3)


def test_preprocess_handles_uniform_image():
    """Edge case: the lesion mask might be empty. The pipeline must still
    produce a 256x256x3 uint8 output without raising."""
    from app.preprocessing import preprocess_plant_image

    flat = np.full((128, 128, 3), 50, dtype=np.uint8)
    out = preprocess_plant_image(flat)
    assert out.shape == (256, 256, 3)
    assert out.dtype == np.uint8


@pytest.mark.skipif(not leaf_gate_artifacts_ready(), reason="leaf_gate.weights.h5 missing")
def test_cnn_gate_rejects_red_car():
    from app.leaf_gate import get_leaf_gate

    car = np.full((800, 1200, 3), 90, dtype=np.uint8)
    car[250:500, 350:850] = (180, 40, 35)
    assert not get_leaf_gate().is_plant_leaf(car).is_leaf


@pytest.mark.skipif(not leaf_gate_artifacts_ready(), reason="leaf_gate.weights.h5 missing")
def test_cnn_gate_rejects_sky_photo():
    from app.leaf_gate import get_leaf_gate

    sky = np.full((600, 800, 3), (135, 180, 220), dtype=np.uint8)
    assert not get_leaf_gate().is_plant_leaf(sky).is_leaf


@pytest.mark.skipif(not leaf_gate_artifacts_ready(), reason="leaf_gate.weights.h5 missing")
def test_cnn_gate_accepts_leaf_like(leaf_rgb):
    from app.leaf_gate import get_leaf_gate

    result = get_leaf_gate().is_plant_leaf(leaf_rgb)
    assert result.is_leaf
    assert result.score >= 0.0


@pytest.mark.skipif(not leaf_gate_artifacts_ready(), reason="leaf_gate.weights.h5 missing")
def test_prepare_for_model_with_metrics(leaf_rgb):
    from app.config import get_settings
    from app.leaf_gate import build_leaf_gate, reset_leaf_gate, set_leaf_gate
    from app.preprocessing import prepare_for_model_with_metrics

    reset_leaf_gate()
    set_leaf_gate(build_leaf_gate(get_settings()))

    result = prepare_for_model_with_metrics(_png_bytes(leaf_rgb))
    assert result.is_plant_leaf
    assert 0.0 <= result.leaf_gate_score <= 1.0
    assert result.tensor.shape == (1, 256, 256, 3)
    assert result.tensor.dtype == np.float32
