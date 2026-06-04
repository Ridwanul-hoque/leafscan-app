# LeafScan — AI Plant Disease Detection

Cross-platform web app (desktop + mobile browsers, installable as a PWA) that detects plant leaf diseases from a photo upload or a live camera capture, powered by a hybrid deep-learning model. The repo contains two services: a Next.js frontend and a FastAPI backend.

> **Status:** MVP; the backend runs a CNN leaf gate plus the hybrid MobileNetV2 disease student. The API does not start without leaf-gate weights, disease weights, and a non-empty class list.

**Full workflow** (startup, upload path, CNN gate, disease model, UI): see [docs/WORKFLOW.md](docs/WORKFLOW.md).

---

## Repository layout

```
.
├── frontend/          # Next.js 14 (App Router) + TypeScript + Tailwind + Framer Motion
├── backend/           # FastAPI + CNN leaf gate + hybrid disease predictor
├── docs/              # WORKFLOW.md — end-to-end architecture and request flow
├── .env.example       # reference env values for both services
└── README.md
```

---

## Prerequisites

| Tool         | Version              | Notes                                                                   |
| ------------ | -------------------- | ----------------------------------------------------------------------- |
| Node.js      | 20 LTS (≥ 18.17)     | https://nodejs.org/ — installer adds `node` and `npm` to PATH           |
| Python       | 3.11 (required for hybrid model) | https://www.python.org/downloads/release/python-3119/ or `winget install Python.Python.3.11`. TensorFlow has no 3.13/3.14 wheels yet. |
| Git          | any                  | Optional, recommended                                                   |
| Docker       | any recent version   | Optional, for the backend container                                     |

After installing, open a **new** terminal and verify:

```powershell
node --version
npm --version
python --version
```

---

## Quick start (local)

Open two terminals, one per service.

From the repo root:

```powershell
cd .
```

### 1. Backend (FastAPI) — terminal 1

```powershell
cd .\backend
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

> The first `pip install` pulls TensorFlow (~375 MB) and OpenCV; expect 3-5 minutes on a decent connection. Subsequent installs are cached.

- API root: http://localhost:8000
- Interactive docs: http://localhost:8000/docs
- Health: http://localhost:8000/health

### 2. Frontend (Next.js) — terminal 2

```powershell
cd .\frontend
copy .env.local.example .env.local
npm install
npm run dev
```

Then open http://localhost:3000.

Or use the helper script from the repo root (opens two terminals):

```powershell
cd .
.\start-dev.ps1
```

### Test on a phone

1. Find your laptop's LAN IP (`ipconfig` → `IPv4 Address`, e.g. `192.168.1.192`).
2. On the phone (same Wi-Fi), open `http://<laptop-lan-ip>:3000`.
3. Keep the backend running on your PC — the phone talks to **port 3000 only**. Next.js proxies `/api/*` to `localhost:8000` on the laptop, so you do **not** need to open port 8000 in Windows Firewall for phone testing.

Use **Upload image** on the phone (live camera over plain HTTP on a LAN IP is blocked by most mobile browsers).

**Quick check from the phone browser:** open `http://<laptop-lan-ip>:3000/api/health` — you should see JSON with `"model_loaded": true`.

---

## Running tests (backend)

```powershell
cd .\backend
.\.venv\Scripts\Activate.ps1
pytest -q
```

Covers: `/health`, valid-image success path (skipped without hybrid artifacts), hybrid determinism per image, 415 on wrong content type, 400 on corrupt bytes. Preprocessing tests always run.

---

## Environment variables

### Frontend — `frontend/.env.local`

| Var                    | Example                  | Purpose                        |
| ---------------------- | ------------------------ | ------------------------------ |
| `NEXT_PUBLIC_API_URL`  | `http://localhost:8000`  | Base URL the frontend calls    |

### Backend — `backend/.env`

| Var                  | Example                                                          | Purpose                                                                                |
| -------------------- | ---------------------------------------------------------------- | -------------------------------------------------------------------------------------- |
| `CORS_ORIGINS`       | `http://localhost:3000,http://127.0.0.1:3000`                    | Comma-separated browser origins allowed to call the API                                |
| `MODEL_PATH`         | `models/hybrid_effnet_mobilenet_distill_final.weights.h5`        | Trained MobileNetV2 student weights (required)                                         |
| `CLASS_LABELS_PATH`  | `app/data/class_labels.json`                                     | JSON array, ordered by softmax index. See `app/data/class_labels.README.md`             |
| `LOW_CONFIDENCE_THRESHOLD` | `0.50`                                                     | Below this, result page shows a warning (does not block the scan)                      |
| `LEAF_GATE_MODEL_PATH` | `models/leaf_gate.weights.h5`                                  | CNN leaf gate weights (required — train via `scripts/train_leaf_gate.py`)            |
| `LEAF_GATE_THRESHOLD` | `0.85`                                                          | Min P(leaf) to accept upload before disease model runs                                 |

---

## Running on another PC

Share/copy the full project folder **including model artifacts**:

- `backend/models/hybrid_effnet_mobilenet_distill_final.weights.h5`
- `backend/models/leaf_gate.weights.h5`
- `backend/app/data/class_labels.json`

Then on the new PC (from repo root):

```powershell
.\setup-dev.ps1
.\start-dev.ps1
```

Notes:

- Do **not** copy `.venv` or `node_modules` between machines; recreate them with `setup-dev.ps1`.
- `setup-dev.ps1` checks Python 3.11, Node/npm, installs deps, creates env files, and verifies required artifacts.
- Verify startup with `http://localhost:3000/api/health` (expect `"model_loaded": true` and `"leaf_gate": "model"`).

---

## Architecture

See [docs/WORKFLOW.md](docs/WORKFLOW.md) for diagrams (system overview, dev startup, user journey, and `POST /predict` pipeline).

```
Browser (PC or phone)
   │   upload | camera capture
   ▼
Next.js frontend  ──POST /predict (multipart)──▶  FastAPI backend
   ▲                                                   │
   │  JSON: label, confidence, severity, symptoms,     │
   │         treatment, low_confidence_warning,        │
   │         warning_message                           ▼
   └────────── result dashboard ◀──────────────  Predictor interface
                                                  └─ HybridModelPredictor
                                                       ├─ OpenCV preprocessing
                                                       ├─ MobileNetV2 student
                                                       └─ class_labels.json
                                                          │
                                                 diseases.json (symptoms + treatment)
```

Key files:

- Frontend
  - Landing: `frontend/app/page.tsx`
  - Detection: `frontend/app/detect/page.tsx`
  - Result: `frontend/app/result/page.tsx`
  - API client: `frontend/lib/api.ts`
  - Session store (pass data to result page): `frontend/lib/scanStore.ts`
  - Components: `frontend/components/{UploadCard,CameraCard,ConfidenceMeter,Navbar}.tsx`
  - PWA: `frontend/public/manifest.json` + metadata in `frontend/app/layout.tsx`
- Backend
  - App: `backend/app/main.py`
  - Predictor: `backend/app/predictor.py`
  - Hybrid model architecture: `backend/app/model.py`
  - OpenCV preprocessing pipeline: `backend/app/preprocessing.py`
  - Leaf gate: `backend/app/leaf_gate.py`, `backend/app/leaf_gate_model.py`
  - Class label list: `backend/app/data/class_labels.json` (+ `class_labels.README.md`)
  - Disease info (curated + auto-generated): `backend/app/data/diseases.json`, `backend/app/diseases.py`
  - Config: `backend/app/config.py`
  - Schemas: `backend/app/schemas.py`
  - Tests: `backend/tests/`

---

## Hybrid validation (no model retrain)

Before running inference, a **CNN leaf gate** (MobileNetV2, leaf vs not-leaf) checks whether the upload looks like a plant leaf photo. This runs on top of the frozen disease classifier.

| Situation | What happens |
| --------- | ------------ |
| **No leaf at all** (car, sky, face, gray desk) | Detect page shows **No leaf detected** (HTTP 422, code `not_a_leaf`) |
| **Leaf photo, confidence ≥ 50%** | Normal result page with diagnosis |
| **Leaf photo, confidence < 50%** | Result page still shows diagnosis, plus an amber **low-confidence warning** |

Flow:

```
Upload → plant-leaf check → [fail] → "No leaf detected"
                ↓ pass
         Run hybrid model
                ↓
         confidence < 50%? → warning banner on result page
                ↓ else
         normal result
```

### CNN leaf gate

- Implementation: `backend/app/leaf_gate.py` (224×224 MobileNetV2 binary classifier)
- Weights: `models/leaf_gate.weights.h5` (required at startup)
- `GET /health` reports `"leaf_gate": "model"`

Train or refresh weights (from `backend/` with venv active):

```powershell
python scripts/train_leaf_gate.py --demo
# or: python scripts/train_leaf_gate.py --data-dir path/to/leaf_and_not_leaf
```

Restart uvicorn after updating weights.

Other notes:

- Low-confidence warning: `low_confidence_warning` and `warning_message` in the `/predict` JSON response
- Threshold: `LOW_CONFIDENCE_THRESHOLD=0.50` (warning only — does not reject)
- Phone testing: frontend proxies `/api/*` → backend on the laptop, so only port **3000** needs to be reachable from the phone

Supported crops: **maize, potato, and tomato** leaves only (22 disease classes from training).

**Limitations:** Gate accuracy depends on your training data (demo weights use synthetic data only). It does not block overconfident wrong disease labels — use the low-confidence warning for that.

---

## Hybrid model setup

The backend loads the student model on startup. Complete these steps before running uvicorn (the process exits if setup is invalid).

1. **Confirm Python 3.11**. TensorFlow 2.19 has no 3.13/3.14 wheels:
   ```powershell
   py -3.11 --version    # should print 3.11.x
   ```
   If missing: `winget install Python.Python.3.11` (one-time, user scope).
2. **Recreate the venv** so it uses 3.11 and pulls TF + OpenCV from `requirements.txt`:
   ```powershell
   cd "l:\BracU\Thesis App\backend"
   if (Test-Path .venv) { Remove-Item -Recurse -Force .venv }
   py -3.11 -m venv .venv
   .\.venv\Scripts\Activate.ps1
   pip install -r requirements.txt    # pulls TF (~375 MB)
   ```
3. **Drop the trained weights** at the expected paths:
   ```
   backend/models/hybrid_effnet_mobilenet_distill_final.weights.h5
   backend/models/leaf_gate.weights.h5
   ```
   Train the leaf gate if missing: `python scripts/train_leaf_gate.py --demo`
   Git-ignored by default. See `backend/models/README.md` for cloud-hosting alternatives.
4. **Paste your class list** into `backend/app/data/class_labels.json` (see `class_labels.README.md` for the exact one-liner to run inside the notebook). Confirm `MODEL_PATH` / `CLASS_LABELS_PATH` in `backend/.env` if you use non-default paths. Restart uvicorn. On startup you should see:
   ```
   Building MobileNetV2 student (num_classes=N)...
   Loading weights from models/hybrid_effnet_mobilenet_distill_final.weights.h5
   Warming up the model...
   HybridModelPredictor ready.
   ```
   And `GET /health` returns `{"predictor":"hybrid","model_loaded":true,"leaf_gate":"model"}`.

### Failure modes

If weights are missing, `class_labels.json` is empty/invalid, or the label count does not match the trained dense layer, startup raises `PredictorError` and uvicorn will not serve requests until you fix configuration and files.

### What's running under the hood

- `backend/app/model.py` rebuilds the exact student architecture from your notebook (Rescaling [-1, 1] → MobileNetV2 alpha=1.0 → GAP → BN → Dropout → Dense softmax).
- `backend/app/preprocessing.py` is a verbatim port of the OpenCV pipeline (gray-world WB → CLAHE → HSV leaf mask → lesion saliency → lesion-aware crop → resize to 256×256). The model was trained with `FAST_MODE=False`, and inference uses the same setting.
- `HybridModelPredictor` runs a one-shot zero-tensor warmup in its constructor so the first user request isn't slow.

---

## Cloud deployment (ready when you are)

The services are intentionally decoupled so you can deploy them independently.

### Frontend → Vercel

```powershell
cd frontend
# Install Vercel CLI once:  npm i -g vercel
vercel
```

Set the env var `NEXT_PUBLIC_API_URL` in the Vercel project settings to your deployed backend URL.

### Backend → Render / Railway / Fly.io

The provided `backend/Dockerfile`:

- Uses `python:3.11-slim`, installs Pillow system deps, runs as a non-root user.
- Binds to `$PORT` (set by the hosting platform) or falls back to `8000`.

Render example (`render.yaml` not required):

- New → Web Service → point at this repo, set **root directory** `backend`, **Runtime** Docker.
- Add env vars: `CORS_ORIGINS=https://<your-vercel-domain>`, plus `MODEL_PATH` / `CLASS_LABELS_PATH` (or bake weights into the image — see `backend/models/README.md`).

Build and run the image locally to smoke-test:

```powershell
cd "l:\BracU\Thesis App\backend"
docker build -t leafscan-api .
docker run --rm -p 8000:8000 --env-file .env leafscan-api
```

---

## MVP scope vs deferred features

**Done:**

- Landing page with upload + camera CTAs and animated demo card
- Detection screen: drag-and-drop upload + live camera capture with `getUserMedia` (flip camera, retake)
- Result dashboard: animated confidence meter, severity chip, symptoms, numbered treatment steps, low-confidence warning banner
- FastAPI `/predict` + `/health` with pluggable predictor, CORS, size/type validation
- **Hybrid validation** — CNN leaf gate rejects non-leaf uploads; warn when disease confidence is below 50%
- **Hybrid model** — MobileNetV2 student loader, verbatim OpenCV preprocessing pipeline (no stub predictor; valid artifacts required at startup)
- PWA manifest + icons
- Dockerfile (Python 3.11 + libgl + libjpeg) with env-driven config
- Backend test suite: preprocessing tests always run; API and hybrid integration tests skip when `models/*.weights.h5` or `class_labels.json` are missing

**Deferred (each a clean additive pass):**

- Curated symptom/treatment text for every Crop___Disease class (placeholders auto-generated for now)
- Scan history + MongoDB Atlas
- Auth
- Dark/Light mode toggle (currently dark-only)
- Bangla / English i18n
- Grad-CAM heatmap overlay
- Severity percentage scoring
- Geolocation outbreak map
- Farmer chatbot

---

## Troubleshooting

- **"No leaf detected"** on the detect page — the upload has no recognizable plant leaf (car, sky, face, desk, etc.). Use a close-up maize, potato, or tomato leaf that fills most of the frame.
- **Low-confidence warning on result page** — the model ran but confidence is below 50%. Retake with better lighting and a sharper close-up; the diagnosis is shown but may be unreliable.
- **"Could not reach the prediction service"** — the backend isn't running on your PC, or the frontend wasn't restarted after config changes. On the phone, open `http://<lan-ip>:3000/api/health`; if that fails, restart `npm run dev` on the PC and confirm uvicorn is running.
- **Wrong or random-looking classes** — confirm `/health` shows `{"predictor":"hybrid","model_loaded":true}` and that `class_labels.json` order matches the softmax indices from training (see `class_labels.README.md`).
- **Stale server / port conflicts** — an old uvicorn may still be bound to port `8000`. Stop all listeners on that port, or run backend on a clean port (example `8001`) and point frontend `NEXT_PUBLIC_API_URL` at it:
  - backend: `uvicorn app.main:app --reload --host 0.0.0.0 --port 8001`
  - frontend `.env.local`: `NEXT_PUBLIC_API_URL=http://localhost:8001`
  - restart `npm run dev`
- **CORS errors** — add your frontend origin to `CORS_ORIGINS` in `backend/.env` and restart uvicorn.
- **Camera permission denied** — your browser or OS blocked the site. On Chrome click the lock icon → Site settings → Camera → Allow. On iOS Safari, camera only works over HTTPS (or `localhost`).
- **`npm install` is slow** — `tailwindcss`, `next`, and `framer-motion` are the heaviest deps; subsequent installs are fast thanks to the `node_modules` cache.
