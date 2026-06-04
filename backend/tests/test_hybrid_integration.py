"""Integration test for the real hybrid model.

Skipped automatically unless both artifacts are present:

  * ``backend/models/hybrid_effnet_mobilenet_distill_final.weights.h5``
  * ``backend/app/data/class_labels.json`` (non-empty array)

This way the rest of the suite stays fast on machines that don't have the
trained weights downloaded.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from hybrid_requirements import HYBRID_LABELS, HYBRID_WEIGHTS, hybrid_artifacts_ready

from app.config import get_settings
from app.main import app
from app.predictor import HybridModelPredictor, build_predictor

pytestmark = pytest.mark.skipif(
    not hybrid_artifacts_ready(),
    reason="Hybrid model artifacts (weights + class_labels) not present.",
)


def test_hybrid_predictor_loads_and_predicts(sample_leaf_bytes):
    pred = HybridModelPredictor(str(HYBRID_WEIGHTS), str(HYBRID_LABELS))
    assert pred.model_loaded is True

    res = pred.predict(sample_leaf_bytes)
    assert res.label
    assert 0.0 <= res.confidence <= 1.0
    assert res.severity in {"mild", "moderate", "severe", "unknown"}
    assert isinstance(res.symptoms, list)
    assert isinstance(res.treatment, list)


def test_hybrid_endpoint_round_trip(sample_leaf_bytes):
    """End-to-end through the FastAPI app with the hybrid model."""
    get_settings.cache_clear()
    settings = get_settings()
    app.state.predictor = build_predictor(
        settings.model_path,
        settings.class_labels_path,
    )
    try:
        with TestClient(app) as client:
            res = client.post(
                "/predict",
                files={"image": ("leaf.png", sample_leaf_bytes, "image/png")},
            )
            assert res.status_code == 200, res.text
            body = res.json()
            assert app.state.predictor.name == "hybrid"
            assert 0.0 <= body["confidence"] <= 1.0
    finally:
        get_settings.cache_clear()
