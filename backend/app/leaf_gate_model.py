"""CNN leaf vs not-leaf gate (MobileNetV2 backbone).

Separate from the disease-classification student in ``model.py``.
Trained via ``scripts/train_leaf_gate.py``; weights at ``LEAF_GATE_MODEL_PATH``.
Required at API startup.
"""

from __future__ import annotations

from typing import Tuple

from tensorflow.keras import layers, models
from tensorflow.keras.applications import MobileNetV2

LEAF_GATE_INPUT_SHAPE: Tuple[int, int, int] = (224, 224, 3)
LEAF_CLASS_INDEX: int = 1  # softmax index for "leaf" (0 = not_leaf)


def build_leaf_gate_mobilenet(
    input_shape: Tuple[int, int, int] = LEAF_GATE_INPUT_SHAPE,
    alpha: float = 0.35,
    dropout: float = 0.2,
    backbone_weights: str | None = None,
):
    """MobileNetV2 -> GAP -> BN -> Dropout -> 2-class softmax."""
    inputs = layers.Input(shape=input_shape)
    backbone = MobileNetV2(
        include_top=False,
        weights=backbone_weights,
        input_shape=input_shape,
        alpha=alpha,
    )
    x = backbone(inputs, training=False)
    x = layers.GlobalAveragePooling2D()(x)
    x = layers.BatchNormalization()(x)
    x = layers.Dropout(dropout)(x)
    outputs = layers.Dense(2, activation="softmax", dtype="float32")(x)
    return models.Model(inputs=inputs, outputs=outputs, name="leaf_gate_mobilenetv2")
