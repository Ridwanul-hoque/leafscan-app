"""Tests for the CNN leaf gate."""

from pathlib import Path

import numpy as np
import pytest

from app.config import Settings, get_settings
from app.leaf_gate import CnnLeafGate, build_leaf_gate, reset_leaf_gate, set_leaf_gate
from hybrid_requirements import leaf_gate_artifacts_ready


def _leaf_like_rgb(size: int = 320) -> np.ndarray:
    h = w = size
    arr = np.full((h, w, 3), 16, dtype=np.uint8)
    yy, xx = np.mgrid[0:h, 0:w]
    cx, cy, r = w // 2, h // 2, int(0.42 * size)
    disc = (xx - cx) ** 2 + (yy - cy) ** 2 <= r * r
    arr[disc] = (40, 160, 60)
    for ox, oy, br in [(-30, -10, 12), (20, 25, 14), (5, -40, 9)]:
        blob = (xx - (cx + ox)) ** 2 + (yy - (cy + oy)) ** 2 <= br * br
        arr[blob & disc] = (110, 70, 35)
    return arr


@pytest.fixture(scope="module")
def cnn_gate() -> CnnLeafGate:
    if not leaf_gate_artifacts_ready():
        pytest.skip("leaf_gate.weights.h5 required — run scripts/train_leaf_gate.py --demo")
    settings = get_settings()
    return build_leaf_gate(settings)


@pytest.fixture()
def leaf_rgb() -> np.ndarray:
    return _leaf_like_rgb()


def test_build_leaf_gate_missing_weights():
    settings = Settings(
        leaf_gate_model_path="models/does_not_exist_leaf_gate.weights.h5",
    )
    with pytest.raises(FileNotFoundError):
        build_leaf_gate(settings)


def test_cnn_accepts_leaf_like(cnn_gate: CnnLeafGate, leaf_rgb: np.ndarray):
    result = cnn_gate.is_plant_leaf(leaf_rgb)
    assert result.is_leaf
    assert 0.0 <= result.score <= 1.0


def test_cnn_rejects_sky(cnn_gate: CnnLeafGate):
    sky = np.full((600, 800, 3), (135, 180, 220), dtype=np.uint8)
    assert not cnn_gate.is_plant_leaf(sky).is_leaf


def test_cnn_rejects_red_car(cnn_gate: CnnLeafGate):
    car = np.full((800, 1200, 3), 90, dtype=np.uint8)
    car[250:500, 350:850] = (180, 40, 35)
    assert not cnn_gate.is_plant_leaf(car).is_leaf


def test_rejects_car_on_overcast_background(cnn_gate: CnnLeafGate):
    """Real car photos often have pale sky/road — CNN demo weights can false-pass."""
    car = np.full((600, 800, 3), (200, 210, 220), dtype=np.uint8)
    car[200:400, 250:550] = (160, 45, 40)
    result = cnn_gate.is_plant_leaf(car)
    assert not result.is_leaf
    assert result.reason in {"mostly_gray_scene", "below_threshold", "low_plant_coverage"}


def test_cnn_respects_threshold(cnn_gate: CnnLeafGate, leaf_rgb: np.ndarray):
    sky = np.full((400, 400, 3), (135, 180, 220), dtype=np.uint8)
    assert not cnn_gate.is_plant_leaf(sky).is_leaf
    assert cnn_gate.is_plant_leaf(leaf_rgb).is_leaf


def test_prepare_uses_strict_threshold(
    monkeypatch: pytest.MonkeyPatch, leaf_rgb: np.ndarray
):
    from io import BytesIO

    from PIL import Image

    from app.preprocessing import prepare_for_model_with_metrics

    if not leaf_gate_artifacts_ready():
        pytest.skip("leaf_gate.weights.h5 required")

    monkeypatch.setenv("LEAF_GATE_THRESHOLD", "1.01")
    get_settings.cache_clear()
    reset_leaf_gate()
    set_leaf_gate(build_leaf_gate(get_settings()))

    buf = BytesIO()
    Image.fromarray(leaf_rgb).save(buf, format="PNG")
    result = prepare_for_model_with_metrics(buf.getvalue())
    assert not result.is_plant_leaf

    get_settings.cache_clear()
    reset_leaf_gate()
