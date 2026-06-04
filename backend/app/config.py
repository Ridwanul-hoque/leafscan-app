from __future__ import annotations

from functools import lru_cache
from typing import Annotated, List

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration pulled from environment / .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # `NoDecode` keeps pydantic-settings from JSON-parsing this env value
    # before our validator runs, so a plain comma-separated string works.
    cors_origins: Annotated[List[str], NoDecode] = Field(
        default_factory=lambda: [
            "http://localhost:3000",
            "http://127.0.0.1:3000",
        ]
    )
    model_path: str = "models/hybrid_effnet_mobilenet_distill_final.weights.h5"
    class_labels_path: str = "app/data/class_labels.json"
    max_upload_bytes: int = 8 * 1024 * 1024  # 8 MB
    low_confidence_threshold: float = 0.50
    leaf_gate_model_path: str = "models/leaf_gate.weights.h5"
    leaf_gate_threshold: float = 0.85

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _split_csv(cls, value):
        if isinstance(value, str):
            return [v.strip() for v in value.split(",") if v.strip()]
        return value


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
