import io
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from app.config import get_settings
from app.leaf_gate import build_leaf_gate, reset_leaf_gate, set_leaf_gate
from app.main import app
from app.predictor import build_predictor

from hybrid_requirements import hybrid_artifacts_ready, leaf_gate_artifacts_ready


@pytest.fixture(scope="session", autouse=True)
def _reset_settings_cache():
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture(autouse=True)
def _init_leaf_gate():
    """Load CNN leaf gate for tests that call prepare_for_model / get_leaf_gate."""
    if not leaf_gate_artifacts_ready():
        yield
        return
    settings = get_settings()
    gate = build_leaf_gate(settings)
    set_leaf_gate(gate)
    yield
    reset_leaf_gate()


@pytest.fixture()
def client():
    if not hybrid_artifacts_ready():
        pytest.skip(
            "Hybrid + leaf gate weights and class_labels.json required for API tests."
        )
    settings = get_settings()
    gate = build_leaf_gate(settings)
    set_leaf_gate(gate)
    app.state.leaf_gate = gate
    app.state.predictor = build_predictor(
        settings.model_path,
        settings.class_labels_path,
    )
    with TestClient(app) as c:
        yield c


@pytest.fixture()
def sample_leaf_bytes() -> bytes:
    """Leaf-like PNG that passes the CNN leaf gate in tests."""
    import numpy as np

    h = w = 320
    arr = np.full((h, w, 3), 16, dtype=np.uint8)
    yy, xx = np.mgrid[0:h, 0:w]
    cx, cy, r = w // 2, h // 2, int(0.42 * w)
    disc = (xx - cx) ** 2 + (yy - cy) ** 2 <= r * r
    arr[disc] = (40, 160, 60)
    buf = io.BytesIO()
    Image.fromarray(arr).save(buf, format="PNG")
    return buf.getvalue()


@pytest.fixture()
def non_leaf_bytes() -> bytes:
    """Uniform gray image — HSV leaf mask should find almost no plant tissue."""
    img = Image.new("RGB", (128, 128), color=(80, 80, 80))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


@pytest.fixture()
def car_bytes() -> bytes:
    """Red car on gray background — must not pass the leaf gate."""
    import numpy as np

    car = np.full((400, 600, 3), 90, dtype=np.uint8)
    car[100:250, 150:450] = (180, 40, 35)
    img = Image.fromarray(car)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


@pytest.fixture()
def fixtures_dir() -> Path:
    return Path(__file__).parent / "fixtures"
