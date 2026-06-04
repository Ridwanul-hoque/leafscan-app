from __future__ import annotations

from typing import List, Literal

from pydantic import BaseModel, Field

Severity = Literal["mild", "moderate", "severe", "unknown"]


class PredictionResponse(BaseModel):
    """Shape returned by `POST /predict`. Matches `PredictionResponse` in
    `frontend/lib/api.ts`. Keep the two in sync."""

    label: str = Field(..., description="Human-readable disease name.")
    confidence: float = Field(..., ge=0.0, le=1.0)
    severity: Severity = "unknown"
    symptoms: List[str] = Field(default_factory=list)
    treatment: List[str] = Field(default_factory=list)
    low_confidence_warning: bool = False
    warning_message: str | None = None


class HealthResponse(BaseModel):
    status: Literal["ok"] = "ok"
    predictor: str
    model_loaded: bool
    leaf_gate: str = "model"
