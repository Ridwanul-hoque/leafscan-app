"""Hybrid model architecture.

This is the MobileNetV2 student that was trained via knowledge distillation
from an EfficientNetV2-S teacher in the Kaggle notebook
``fork-of-hybrid-efficientnet-mobilenet-distillation.ipynb`` (lines 569-584).

Inference-time only: ``weights=None`` so we don't fetch ImageNet weights
during cold start. The trained weights (``hybrid_effnet_mobilenet_distill_final
.weights.h5``) are loaded by :class:`HybridModelPredictor`.
"""

from __future__ import annotations

from typing import Tuple

# Keep TF import lazy when the module is imported by tooling that doesn't need
# it (linters, OpenAPI dump). Importing at module level is fine for runtime.
from tensorflow.keras import layers, models
from tensorflow.keras.applications import MobileNetV2


def build_student_mobilenet(
    input_shape: Tuple[int, int, int] = (256, 256, 3),
    num_classes: int = 38,
    alpha: float = 1.0,
    dropout: float = 0.4,
):
    """Construct the student MobileNetV2 architecture.

    Mirrors the notebook exactly (Rescaling to [-1, 1], MobileNetV2 backbone,
    GAP -> BN -> Dropout -> Dense softmax). Use ``num_classes`` derived from
    the saved class list, not a hard-coded constant.
    """
    inputs = layers.Input(shape=input_shape)
    x = layers.Rescaling(1.0 / 127.5, offset=-1)(inputs)
    backbone = MobileNetV2(
        include_top=False,
        weights=None,
        input_shape=input_shape,
        alpha=alpha,
    )
    x = backbone(x, training=False)
    x = layers.GlobalAveragePooling2D()(x)
    x = layers.BatchNormalization()(x)
    x = layers.Dropout(dropout)(x)
    outputs = layers.Dense(num_classes, activation="softmax", dtype="float32")(x)
    model = models.Model(inputs=inputs, outputs=outputs, name="student_mobilenetv2")
    model._backbone_name = backbone.name  # type: ignore[attr-defined]
    return model
