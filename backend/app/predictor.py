"""Predictor layer: trained MobileNetV2 student (hybrid distillation model).

Loads weights from disk, runs the same OpenCV preprocessing as training, and
returns a fully-populated :class:`PredictionResponse`.
"""

from __future__ import annotations

import io
import json
import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import List

from PIL import Image, UnidentifiedImageError

from .config import get_settings
from .diseases import get_disease
from .schemas import PredictionResponse

logger = logging.getLogger(__name__)

_NOT_A_LEAF_MSG = (
    "No plant leaf detected. Upload a close-up of a maize, potato, or tomato leaf."
)
_LOW_CONFIDENCE_MSG = (
    "Confidence is below 50%. This diagnosis may be unreliable — retake with a "
    "clearer, well-lit leaf photo."
)


class PredictorError(ValueError):
    """Raised when input is not a processable image, or the predictor cannot start."""


class PredictorValidationError(PredictorError):
    """Raised when the upload fails app-layer leaf/confidence validation."""

    def __init__(self, message: str, code: str = "validation_failed") -> None:
        super().__init__(message)
        self.code = code


class Predictor(ABC):
    """Abstract predictor."""

    name: str = "base"
    model_loaded: bool = False

    @abstractmethod
    def predict(self, image_bytes: bytes) -> PredictionResponse:  # pragma: no cover
        raise NotImplementedError


def _open_image(image_bytes: bytes) -> Image.Image:
    if not image_bytes:
        raise PredictorError("Empty image payload.")
    try:
        img = Image.open(io.BytesIO(image_bytes))
        img.verify()
    except (UnidentifiedImageError, OSError) as exc:
        raise PredictorError("File is not a valid image.") from exc
    return Image.open(io.BytesIO(image_bytes)).convert("RGB")


def _normalize_class_key(class_key: str) -> str:
    """Map ``"Tomato___Early_blight"`` -> ``"tomato_early_blight"``.

    Used to look up symptom/treatment info in ``diseases.json``.
    """
    return class_key.lower().replace("___", "_")


class HybridModelPredictor(Predictor):
    """MobileNetV2 student trained via EfficientNetV2-S distillation."""

    name = "hybrid"

    def __init__(self, model_path: str, class_labels_path: str) -> None:
        labels_file = Path(class_labels_path)
        if not labels_file.exists():
            raise PredictorError(
                f"Class labels file not found at {class_labels_path}. "
                "Create it and paste your sorted class list."
            )
        try:
            self._labels: List[str] = json.loads(labels_file.read_text("utf-8"))
        except json.JSONDecodeError as exc:
            raise PredictorError(
                f"{class_labels_path} is not valid JSON: {exc}"
            ) from exc

        if not isinstance(self._labels, list) or not all(
            isinstance(x, str) for x in self._labels
        ):
            raise PredictorError(
                f"{class_labels_path} must be a JSON array of strings."
            )
        if not self._labels:
            raise PredictorError(
                f"{class_labels_path} is empty. Paste the sorted class list "
                "from your Kaggle notebook. "
                "See app/data/class_labels.README.md for instructions."
            )

        weights_file = Path(model_path)
        if not weights_file.exists():
            raise PredictorError(
                f"Model weights not found at {model_path}. "
                "Place hybrid_effnet_mobilenet_distill_final.weights.h5 there."
            )

        # Lazy heavy imports — keep module import cheap for tooling.
        import numpy as np  # noqa: F401  (used in warmup below)

        from .model import build_student_mobilenet

        logger.info(
            "Building MobileNetV2 student (num_classes=%d)...", len(self._labels)
        )
        self._model = build_student_mobilenet(num_classes=len(self._labels))
        logger.info("Loading weights from %s", weights_file)
        self._model.load_weights(str(weights_file))

        # Warmup: first predict() incurs graph compile + kernel autotune.
        # Doing it here makes the first user request fast.
        logger.info("Warming up the model...")
        warmup = np.zeros((1, 256, 256, 3), dtype="float32")
        self._model.predict(warmup, verbose=0)
        logger.info("HybridModelPredictor ready.")
        self.model_loaded = True

    def predict(self, image_bytes: bytes) -> PredictionResponse:
        import numpy as np

        from .preprocessing import prepare_for_model_with_metrics

        settings = get_settings()
        try:
            prepared = prepare_for_model_with_metrics(image_bytes)
        except (UnidentifiedImageError, OSError) as exc:
            raise PredictorError("File is not a valid image.") from exc

        if not prepared.is_plant_leaf:
            raise PredictorValidationError(_NOT_A_LEAF_MSG, code="not_a_leaf")

        probs = self._model.predict(prepared.tensor, verbose=0)[0]
        idx = int(np.argmax(probs))
        confidence = float(probs[idx])

        low_confidence_warning = confidence < settings.low_confidence_threshold

        if idx >= len(self._labels):
            raise PredictorError(
                f"Model produced index {idx} but only {len(self._labels)} class labels are configured."
            )
        class_key = self._labels[idx]
        info = get_disease(_normalize_class_key(class_key))

        return PredictionResponse(
            label=info["label"],
            confidence=round(confidence, 4),
            severity=info.get("severity", "unknown"),
            symptoms=list(info.get("symptoms", [])),
            treatment=list(info.get("treatment", [])),
            low_confidence_warning=low_confidence_warning,
            warning_message=_LOW_CONFIDENCE_MSG if low_confidence_warning else None,
        )


def build_predictor(model_path: str, class_labels_path: str) -> HybridModelPredictor:
    """Load the hybrid student model. Raises :class:`PredictorError` if misconfigured."""
    if not model_path or not class_labels_path:
        raise PredictorError("MODEL_PATH and CLASS_LABELS_PATH must be set.")
    return HybridModelPredictor(model_path, class_labels_path)
