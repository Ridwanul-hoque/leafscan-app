import pytest
from fastapi.testclient import TestClient


def test_health(client: TestClient):
    res = client.get("/health")
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "ok"
    assert body["predictor"] == "hybrid"
    assert body["leaf_gate"] == "model"


def test_predict_returns_valid_shape(client: TestClient, sample_leaf_bytes: bytes):
    res = client.post(
        "/predict",
        files={"image": ("leaf.png", sample_leaf_bytes, "image/png")},
    )
    assert res.status_code == 200, res.text
    body = res.json()

    assert isinstance(body["label"], str) and body["label"]
    assert 0.0 <= body["confidence"] <= 1.0
    assert body["severity"] in {"mild", "moderate", "severe", "unknown"}
    assert isinstance(body["symptoms"], list)
    assert isinstance(body["treatment"], list)
    assert isinstance(body["low_confidence_warning"], bool)
    assert body["warning_message"] is None or isinstance(body["warning_message"], str)


def test_predict_is_deterministic_per_image(client: TestClient, sample_leaf_bytes: bytes):
    """Identical inputs must map to identical outputs."""
    r1 = client.post(
        "/predict",
        files={"image": ("leaf.png", sample_leaf_bytes, "image/png")},
    ).json()
    r2 = client.post(
        "/predict",
        files={"image": ("leaf.png", sample_leaf_bytes, "image/png")},
    ).json()
    assert r1 == r2


def test_predict_rejects_bad_content_type(client: TestClient):
    res = client.post(
        "/predict",
        files={"image": ("leaf.gif", b"not-really-an-image", "image/gif")},
    )
    assert res.status_code == 415


def test_predict_rejects_invalid_image_bytes(client: TestClient):
    res = client.post(
        "/predict",
        files={"image": ("leaf.png", b"not-a-png", "image/png")},
    )
    assert res.status_code == 400


def test_predict_rejects_car(client: TestClient, car_bytes: bytes):
    res = client.post(
        "/predict",
        files={"image": ("car.png", car_bytes, "image/png")},
    )
    assert res.status_code == 422, res.text
    assert res.json()["detail"]["code"] == "not_a_leaf"


def test_predict_rejects_non_leaf(client: TestClient, non_leaf_bytes: bytes):
    res = client.post(
        "/predict",
        files={"image": ("desk.png", non_leaf_bytes, "image/png")},
    )
    assert res.status_code == 422, res.text
    detail = res.json()["detail"]
    assert detail["code"] == "not_a_leaf"
    assert "No plant leaf detected" in detail["message"]


def test_predict_warns_low_confidence(
    monkeypatch: pytest.MonkeyPatch,
    sample_leaf_bytes: bytes,
):
    from hybrid_requirements import hybrid_artifacts_ready

    if not hybrid_artifacts_ready():
        pytest.skip(
            "Hybrid model weights and non-empty class_labels.json required for API tests."
        )

    from app.config import get_settings
    from app.main import app
    from app.predictor import build_predictor

    monkeypatch.setenv("LOW_CONFIDENCE_THRESHOLD", "0.999")
    get_settings.cache_clear()
    settings = get_settings()
    app.state.predictor = build_predictor(
        settings.model_path,
        settings.class_labels_path,
    )

    with TestClient(app) as client:
        res = client.post(
            "/predict",
            files={"image": ("leaf.png", sample_leaf_bytes, "image/png")},
        )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["low_confidence_warning"] is True
    assert body["warning_message"] is not None
    get_settings.cache_clear()
