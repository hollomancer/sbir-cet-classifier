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
class EnrichmentConfig:
    """Configuration for SAM.gov API enrichment."""

    api_key: str
    base_url: str = "https://api.sam.gov/prod/federalregistry/v2"
    rate_limit: int = 100  # requests per minute
    timeout: int = 30  # seconds
    max_retries: int = 3
    batch_size: int = 10
    confidence_threshold: float = 0.7


@dataclass(frozen=True)
class AppConfig:
    """Top-level configuration for the CET classifier."""

    storage: StoragePaths
    enrichment: EnrichmentConfig | None = None
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


def _load_enrichment_config() -> EnrichmentConfig | None:
    """Load enrichment configuration from environment variables."""
    api_key = os.getenv("SBIR_SAM_API_KEY")
    if not api_key:
        return None
    
    return EnrichmentConfig(
        api_key=api_key,
        base_url=os.getenv("SBIR_SAM_API_BASE_URL", "https://api.sam.gov/prod/federalregistry/v2"),
        rate_limit=int(os.getenv("SBIR_SAM_API_RATE_LIMIT", "100")),
        timeout=int(os.getenv("SBIR_SAM_API_TIMEOUT", "30")),
        max_retries=int(os.getenv("SBIR_SAM_API_MAX_RETRIES", "3")),
        batch_size=int(os.getenv("SBIR_SAM_API_BATCH_SIZE", "10")),
        confidence_threshold=float(os.getenv("SBIR_SAM_API_CONFIDENCE_THRESHOLD", "0.7")),
    )


@lru_cache(maxsize=1)
def load_config() -> AppConfig:
    """Load and cache the application configuration."""

    storage = StoragePaths(
        raw=_resolve_path("SBIR_DATA_RAW_DIR", _DEFAULT_RAW),
        processed=_resolve_path("SBIR_DATA_PROCESSED_DIR", _DEFAULT_PROCESSED),
        artifacts=_resolve_path("SBIR_DATA_ARTIFACTS_DIR", _DEFAULT_ARTIFACTS),
    )
    enrichment = _load_enrichment_config()
    return AppConfig(storage=storage, enrichment=enrichment)


__all__ = ["AppConfig", "EnrichmentConfig", "StoragePaths", "load_config"]
