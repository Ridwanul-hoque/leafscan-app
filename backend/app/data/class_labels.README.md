# class_labels.json

This file maps the **model's output index -> human-readable class key**.
Index 0 in the array == output index 0 in the softmax. **Order matters.**

## How to populate it

In your Kaggle notebook, after the data generators are built, the line

```python
print("Class indices:", class_indices)
```

(notebook line 387) prints something like:

```
{'Apple___Apple_scab': 0, 'Apple___Black_rot': 1, ..., 'Tomato___healthy': 37}
```

Convert that into a sorted-by-value list and paste it as a JSON array into
`class_labels.json`:

```json
[
  "Apple___Apple_scab",
  "Apple___Black_rot",
  "...",
  "Tomato___healthy"
]
```

A quick way to produce it from the notebook:

```python
import json
ordered = [k for k, _ in sorted(class_indices.items(), key=lambda kv: kv[1])]
print(json.dumps(ordered, indent=2))
```

## What happens until you fill it in

`HybridModelPredictor` raises a clear `PredictorError` on startup if the list
is empty or invalid, and the API process will not finish loading until the file
is fixed.

## Format invariants

- Strings only, no nested objects.
- Use the original `Crop___Disease` keys (triple underscore, exactly as in
  the notebook). The predictor lowercases and replaces `___` with `_` to
  look up symptom/treatment info in `diseases.json`.
- Length must equal the model's output dimension. We use it to size
  `Dense(num_classes, ...)` when rebuilding the architecture for weight
  loading.
