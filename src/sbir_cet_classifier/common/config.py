"""Configuration utilities for SBIR CET processing.

Centralises resolution of storage directories so ingestion, models,
exports, and evaluation share consistent locations. Values can be
customised via environment variables but default to workspace-relative
paths. The loader caches resolved values to avoid repeated filesystem
checks.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

_DEFAULT_RAW = Path("data/raw")
_DEFAULT_PROCESSED = Path("data/processed")
_DEFAULT_ARTIFACTS = Path("artifacts")


@dataclass(frozen=True)
class StoragePaths:
    """Resolved filesystem locations used by the pipeline."""

    raw: Path
    processed: Path
    artifacts: Path


@dataclass(frozen=True)
class AppConfig:
    """Top-level configuration for the CET classifier."""

    storage: StoragePaths
    spacy_model: str = "en_core_web_md"
    timezone: str = "UTC"

    @property
    def data_dir(self) -> Path:
        """Alias for storage.processed for convenience."""
        return self.storage.processed.parent

    @property
    def artifacts_dir(self) -> Path:
        """Alias for storage.artifacts for convenience."""
        return self.storage.artifacts


def _resolve_path(env_var: str, fallback: Path) -> Path:
    """Resolve a path from an environment variable or use the fallback.

    The directory is created if it does not yet exist so downstream code
    can assume the location is writable.
    """

    raw_value = os.getenv(env_var)
    base_path = Path(raw_value).expanduser() if raw_value else fallback
    base_path.mkdir(parents=True, exist_ok=True)
    return base_path.resolve()


@lru_cache(maxsize=1)
def load_config() -> AppConfig:
    """Load and cache the application configuration."""

    storage = StoragePaths(
        raw=_resolve_path("SBIR_RAW_DIR", _DEFAULT_RAW),
        processed=_resolve_path("SBIR_PROCESSED_DIR", _DEFAULT_PROCESSED),
        artifacts=_resolve_path("SBIR_ARTIFACT_DIR", _DEFAULT_ARTIFACTS),
    )
    return AppConfig(storage=storage)


__all__ = ["AppConfig", "StoragePaths", "load_config"]
