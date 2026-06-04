# models/

Drop trained weight files here. They are git-ignored by default
(see `backend/.gitignore`).

## Expected files

### Disease model (required)

```
hybrid_effnet_mobilenet_distill_final.weights.h5
```

### Leaf gate (required)

```
leaf_gate.weights.h5
```

Train with `python scripts/train_leaf_gate.py --demo` (synthetic) or
`--data-dir` pointing at `leaf/` and `not_leaf/` folders. Configure via
`LEAF_GATE_MODEL_PATH` in `backend/.env`. The API will not start without this file.

## Shared package checklist (another PC)

If you share this project to another machine, include all three required files:

1. `backend/models/hybrid_effnet_mobilenet_distill_final.weights.h5`
2. `backend/models/leaf_gate.weights.h5`
3. `backend/app/data/class_labels.json`

Then run from repo root on that machine:

```powershell
.\setup-dev.ps1
.\start-dev.ps1
```

Do not copy `.venv` or `node_modules` from another PC; recreate them locally.

## Disease model details

This is the **MobileNetV2 student** produced by the Kaggle notebook
[`fork-of-hybrid-efficientnet-mobilenet-distillation.ipynb`](../../fork-of-hybrid-efficientnet-mobilenet-distillation.ipynb)
(line 211 saves it via `model.save_weights(FINAL_MODEL_PATH)`).

The path is configurable via `MODEL_PATH` in `backend/.env`. The default
matches the file name above.

## How the file is consumed

1. `HybridModelPredictor.__init__` reads `class_labels.json` to find
   `num_classes`.
2. Calls `build_student_mobilenet(num_classes=N)` to recreate the exact
   architecture used during training (Rescaling -> MobileNetV2 -> GAP ->
   BN -> Dropout -> Dense softmax).
3. Calls `model.load_weights("models/...weights.h5")`.
4. Runs a single zero-tensor warmup so the first user request is fast.

## Why .weights.h5, not .keras?

The notebook saves *partial weights* (Keras 3 format), not a full SavedModel
or `.keras` archive. Loading partial weights requires recreating the same
architecture first, which we do in `app/model.py`.

## Cloud deployment

If you containerize via `Dockerfile`, you have two options:

1. **Bake the weights into the image** — uncomment the
   `COPY models ./models` line in `backend/Dockerfile`. Best for Render /
   Railway where ephemeral filesystem is fine and image size isn't billed
   per GB.
2. **Mount at runtime** — leave the COPY commented and provide the file via
   a mounted volume / object-storage download in the platform's start
   command. Best for Fly.io volumes or S3-backed setups.
