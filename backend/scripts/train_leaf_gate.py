#!/usr/bin/env python3
"""Train the binary leaf gate (MobileNetV2, leaf vs not_leaf).

Usage (from backend/ with venv active):

  # Quick synthetic demo (~2 min CPU) — writes models/leaf_gate.weights.h5
  python scripts/train_leaf_gate.py --demo

  # Real data: directories with class subfolders or flat leaf/ not_leaf/
  python scripts/train_leaf_gate.py --data-dir path/to/dataset --epochs 10

Dataset layout (either):
  data_dir/leaf/*.jpg
  data_dir/not_leaf/*.jpg

Or:
  data_dir/train/leaf/ ...
  data_dir/train/not_leaf/ ...
"""

from __future__ import annotations

import argparse
import random
import sys
from pathlib import Path

import numpy as np

# Allow running as ``python scripts/train_leaf_gate.py`` from backend/.
_BACKEND = Path(__file__).resolve().parents[1]
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

from app.leaf_gate_model import LEAF_CLASS_INDEX, build_leaf_gate_mobilenet  # noqa: E402

DEFAULT_OUTPUT = _BACKEND / "models" / "leaf_gate.weights.h5"
IMAGE_SIZE = (224, 224)
BATCH_SIZE = 32


def _synthetic_batch(n: int, rng: random.Random) -> tuple[np.ndarray, np.ndarray]:
    """Generate random leaf-like vs non-leaf RGB patches."""
    import cv2

    xs: list[np.ndarray] = []
    ys: list[int] = []
    for _ in range(n):
        label = rng.randint(0, 1)
        h = w = 256
        if label == LEAF_CLASS_INDEX:
            img = np.full((h, w, 3), 20, dtype=np.uint8)
            yy, xx = np.mgrid[0:h, 0:w]
            cx, cy, r = w // 2, h // 2, rng.randint(80, 110)
            disc = (xx - cx) ** 2 + (yy - cy) ** 2 <= r * r
            img[disc] = (
                rng.randint(30, 60),
                rng.randint(130, 190),
                rng.randint(40, 80),
            )
        else:
            kind = rng.choice(["sky", "gray", "car"])
            if kind == "sky":
                img = np.full((h, w, 3), (135, 180, 220), dtype=np.uint8)
            elif kind == "gray":
                g = rng.randint(60, 120)
                img = np.full((h, w, 3), g, dtype=np.uint8)
            else:
                # Car on road / overcast sky — common false-positive for the gate.
                bg = rng.randint(175, 225)
                img = np.full((h, w, 3), (bg, bg, bg + rng.randint(0, 15)), dtype=np.uint8)
                img[60:200, 70:190] = (180, 40, 35)
        resized = cv2.resize(img, IMAGE_SIZE, interpolation=cv2.INTER_AREA)
        xs.append(resized)
        ys.append(label)
    return np.stack(xs, axis=0), np.array(ys, dtype=np.int32)


def _load_paths(data_dir: Path) -> tuple[list[Path], list[int]]:
    exts = {".jpg", ".jpeg", ".png", ".webp"}
    paths: list[Path] = []
    labels: list[int] = []

    def collect(split: Path, sub: str, label: int) -> None:
        folder = split / sub
        if not folder.is_dir():
            return
        for p in sorted(folder.rglob("*")):
            if p.suffix.lower() in exts:
                paths.append(p)
                labels.append(label)

    for split_name in ("train", ""):
        split = data_dir / split_name if split_name else data_dir
        if split_name and not split.is_dir():
            continue
        collect(split, "leaf", LEAF_CLASS_INDEX)
        collect(split, "not_leaf", 0)
        if paths:
            break

    if not paths:
        raise FileNotFoundError(
            f"No images under {data_dir}/leaf and {data_dir}/not_leaf "
            "(or train/leaf, train/not_leaf)."
        )
    return paths, labels


def _dataset_from_paths(paths: list[Path], labels: list[int], batch_size: int):
    import cv2
    import tensorflow as tf
    from tensorflow.keras.applications.mobilenet_v2 import preprocess_input

    def gen():
        rng = random.Random(42)
        indices = list(range(len(paths)))
        while True:
            rng.shuffle(indices)
            for i in range(0, len(indices), batch_size):
                batch_idx = indices[i : i + batch_size]
                imgs = []
                lbls = []
                for j in batch_idx:
                    bgr = cv2.imread(str(paths[j]))
                    if bgr is None:
                        continue
                    rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
                    rgb = cv2.resize(rgb, IMAGE_SIZE, interpolation=cv2.INTER_AREA)
                    imgs.append(rgb)
                    lbls.append(labels[j])
                if not imgs:
                    continue
                x = preprocess_input(np.stack(imgs, axis=0).astype(np.float32))
                y = tf.keras.utils.to_categorical(lbls, num_classes=2)
                yield x, y

    return (
        tf.data.Dataset.from_generator(
            gen,
            output_signature=(
                tf.TensorSpec(shape=(None, 224, 224, 3), dtype=tf.float32),
                tf.TensorSpec(shape=(None, 2), dtype=tf.float32),
            ),
        )
        .repeat()
    )


def _synthetic_dataset(steps_per_epoch: int, batch_size: int):
    import tensorflow as tf
    from tensorflow.keras.applications.mobilenet_v2 import preprocess_input

    rng = random.Random(42)

    def gen():
        for _ in range(steps_per_epoch):
            x, y = _synthetic_batch(batch_size, rng)
            x = preprocess_input(x.astype(np.float32))
            y_onehot = tf.keras.utils.to_categorical(y, num_classes=2)
            yield x, y_onehot

    return (
        tf.data.Dataset.from_generator(
            gen,
            output_signature=(
                tf.TensorSpec(shape=(None, 224, 224, 3), dtype=tf.float32),
                tf.TensorSpec(shape=(None, 2), dtype=tf.float32),
            ),
        )
        .repeat()
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Train binary leaf gate.")
    parser.add_argument(
        "--data-dir",
        type=Path,
        help="Dataset root with leaf/ and not_leaf/ (or train/...).",
    )
    parser.add_argument(
        "--demo",
        action="store_true",
        help="Train on synthetic leaf vs non-leaf patches (no folders needed).",
    )
    parser.add_argument("--epochs", type=int, default=12)
    parser.add_argument("--steps-per-epoch", type=int, default=60)
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help=f"Output weights path (default: {DEFAULT_OUTPUT}).",
    )
    args = parser.parse_args()

    if not args.demo and args.data_dir is None:
        parser.error("Provide --data-dir or use --demo for synthetic training.")

    import tensorflow as tf

    tf.keras.utils.set_random_seed(42)

    model = build_leaf_gate_mobilenet(backbone_weights="imagenet")
    model.compile(
        optimizer=tf.keras.optimizers.Adam(learning_rate=1e-3),
        loss="categorical_crossentropy",
        metrics=["accuracy"],
    )

    if args.demo:
        print("Training leaf gate on synthetic demo data...")
        train_ds = _synthetic_dataset(args.steps_per_epoch, BATCH_SIZE)
        steps = args.steps_per_epoch
    else:
        paths, labels = _load_paths(args.data_dir)
        print(f"Loaded {len(paths)} images from {args.data_dir}")
        train_ds = _dataset_from_paths(paths, labels, BATCH_SIZE)
        steps = max(1, len(paths) // BATCH_SIZE)

    model.fit(
        train_ds,
        steps_per_epoch=steps,
        epochs=args.epochs,
        verbose=1,
    )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    model.save_weights(str(args.output))
    print(f"Saved leaf gate weights to {args.output}")
    print("Restart uvicorn to load the new leaf gate weights.")


if __name__ == "__main__":
    main()
