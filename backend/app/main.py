from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI, File, HTTPException, Request, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware

from .config import Settings, get_settings
from .leaf_gate import build_leaf_gate, set_leaf_gate
from .predictor import (
    Predictor,
    PredictorError,
    PredictorValidationError,
    build_predictor,
)
from .schemas import HealthResponse, PredictionResponse

logger = logging.getLogger("leafscan")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    leaf_gate = build_leaf_gate(settings)
    set_leaf_gate(leaf_gate)
    logger.info("Leaf gate initialized: mode=%s", leaf_gate.name)

    predictor = build_predictor(
        settings.model_path,
        settings.class_labels_path,
    )
    app.state.predictor = predictor
    app.state.leaf_gate = leaf_gate
    logger.info(
        "Predictor initialized: name=%s model_loaded=%s",
        predictor.name,
        predictor.model_loaded,
    )
    yield


app = FastAPI(
    title="LeafScan API",
    version="0.1.0",
    description="Plant disease detection backend for the LeafScan web app.",
    lifespan=lifespan,
)


_settings: Settings = get_settings()
# Allow LAN dev origins (phone on same Wi-Fi) without editing CORS_ORIGINS each time.
_LAN_ORIGIN_REGEX = (
    r"https?://("
    r"localhost|127\.0\.0\.1"
    r"|192\.168\.\d{1,3}\.\d{1,3}"
    r"|10\.\d{1,3}\.\d{1,3}\.\d{1,3}"
    r"|172\.(1[6-9]|2\d|3[01])\.\d{1,3}\.\d{1,3}"
    r")(:\d+)?"
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=_settings.cors_origins,
    allow_origin_regex=_LAN_ORIGIN_REGEX,
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)


def _predictor(request: Request) -> Predictor:
    pred = getattr(request.app.state, "predictor", None)
    if pred is None:
        raise HTTPException(status_code=503, detail="Predictor is not ready yet.")
    return pred


@app.get("/health", response_model=HealthResponse, tags=["meta"])
async def health(request: Request) -> HealthResponse:
    pred = _predictor(request)
    gate = getattr(request.app.state, "leaf_gate", None)
    return HealthResponse(
        predictor=pred.name,
        model_loaded=pred.model_loaded,
        leaf_gate=gate.name if gate is not None else "unknown",
    )


@app.get("/", tags=["meta"])
async def root() -> dict:
    return {
        "name": "LeafScan API",
        "docs": "/docs",
        "endpoints": ["/health", "/predict"],
    }


_ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp"}


@app.post("/predict", response_model=PredictionResponse, tags=["inference"])
async def predict(
    request: Request,
    image: UploadFile = File(..., description="Leaf image (JPEG, PNG, or WEBP)."),
) -> PredictionResponse:
    settings = get_settings()

    if image.content_type not in _ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Unsupported content type: {image.content_type or 'unknown'}. Use JPEG, PNG, or WEBP.",
        )

    payload = await image.read()
    if len(payload) > settings.max_upload_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Image larger than {settings.max_upload_bytes // (1024 * 1024)} MB.",
        )

    pred = _predictor(request)
    try:
        return pred.predict(payload)
    except PredictorValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={"code": exc.code, "message": str(exc)},
        ) from exc
    except PredictorError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except NotImplementedError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception:  # noqa: BLE001 — surface as 500 with a generic message
        logger.exception("Prediction failed")
        raise HTTPException(status_code=500, detail="Internal prediction error.")
