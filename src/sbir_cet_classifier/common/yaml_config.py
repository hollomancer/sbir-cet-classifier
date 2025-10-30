"""YAML configuration loader with validation."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import yaml
from pydantic import BaseModel, Field


class CategoryConfig(BaseModel):
    """CET category configuration."""

    id: str
    name: str
    definition: str
    parent: str | None = None
    keywords: list[str] = Field(default_factory=list)


class TaxonomyConfig(BaseModel):
    """CET taxonomy configuration."""

    version: str
    effective_date: str
    description: str
    categories: list[CategoryConfig]


class VectorizerConfig(BaseModel):
    """TF-IDF vectorizer configuration."""

    ngram_range: tuple[int, int]
    max_features: int
    min_df: int
    max_df: float


class FeatureSelectionConfig(BaseModel):
    """Feature selection configuration."""

    enabled: bool
    method: str
    k: int


class ClassifierConfig(BaseModel):
    """Logistic regression classifier configuration."""

    max_iter: int
    solver: str
    n_jobs: int
    class_weight: str


class CalibrationConfig(BaseModel):
    """Calibration configuration."""

    enabled: bool
    method: str
    cv: int
    min_samples_per_class: int


class BandConfig(BaseModel):
    """Classification band configuration."""

    min: int
    max: int
    label: str


class ScoringConfig(BaseModel):
    """Scoring configuration."""

    bands: dict[str, BandConfig]
    max_supporting: int


class ClassificationConfig(BaseModel):
    """Complete classification configuration."""

    version: str
    description: str
    vectorizer: VectorizerConfig
    feature_selection: FeatureSelectionConfig
    classifier: ClassifierConfig
    calibration: CalibrationConfig
    scoring: ScoringConfig
    stop_words: list[str]


class TopicDomainConfig(BaseModel):
    """Topic domain configuration."""

    name: str
    keywords: list[str]


class NIHMatcherConfig(BaseModel):
    """NIH matcher configuration."""

    amount_tolerance_min: float = Field(ge=0.0, le=1.0)
    amount_tolerance_max: float = Field(ge=1.0, le=2.0)
    similarity_threshold: float = Field(ge=0.0, le=1.0)
    org_suffixes: list[str]
    exact_match_limit: int = Field(ge=1)
    fuzzy_match_limit: int = Field(ge=1)
    similarity_match_limit: int = Field(ge=1)


class PhaseKeywordsConfig(BaseModel):
    """Phase-specific keywords."""

    phase_i: list[str]
    phase_ii: list[str]


class EnrichmentConfig(BaseModel):
    """Complete enrichment configuration."""

    version: str
    description: str
    nih_matcher: NIHMatcherConfig
    topic_domains: dict[str, TopicDomainConfig]
    agency_focus: dict[str, str]
    phase_keywords: PhaseKeywordsConfig


def load_taxonomy_config(path: Path | None = None) -> TaxonomyConfig:
    """Load taxonomy configuration from YAML.

    Args:
        path: Path to taxonomy.yaml (defaults to SBIR_CONFIG_DIR/taxonomy.yaml if set,
              otherwise config/taxonomy.yaml)

    Returns:
        Validated taxonomy configuration
    """
    # For backward compatibility, if a specific path is provided, use direct loading
    if path is not None:
        import os
        resolved = Path(path).resolve()
        key = str(resolved)

        cache = getattr(load_taxonomy_config, "_cache", {})
        if key in cache:
            return cache[key]

        with resolved.open() as f:
            data = yaml.safe_load(f)

        cfg = TaxonomyConfig(**data)
        cache[key] = cfg
        setattr(load_taxonomy_config, "_cache", cache)
        return cfg
    
    # Use centralized configuration manager for default loading
    from .configuration_manager import get_config_manager
    config_manager = get_config_manager()
    return config_manager.get_taxonomy_config()


def load_classification_config(path: Path | None = None) -> ClassificationConfig:
    """Load classification configuration from YAML.

    Args:
        path: Path to classification.yaml (defaults to SBIR_CONFIG_DIR/classification.yaml if set,
              otherwise config/classification.yaml)

    Returns:
        Validated classification configuration
    """
    # For backward compatibility, if a specific path is provided, use direct loading
    if path is not None:
        import os
        resolved = Path(path).resolve()
        key = str(resolved)

        cache = getattr(load_classification_config, "_cache", {})
        if key in cache:
            return cache[key]

        with resolved.open() as f:
            data = yaml.safe_load(f)

        cfg = ClassificationConfig(**data)
        cache[key] = cfg
        setattr(load_classification_config, "_cache", cache)
        return cfg
    
    # Use centralized configuration manager for default loading
    from .configuration_manager import get_config_manager
    config_manager = get_config_manager()
    return config_manager.get_classification_config()


def load_enrichment_config(path: Path | None = None) -> EnrichmentConfig:
    """Load enrichment configuration from YAML.

    Args:
        path: Path to enrichment.yaml (defaults to SBIR_CONFIG_DIR/enrichment.yaml if set,
              otherwise config/enrichment.yaml)

    Returns:
        Validated enrichment configuration
    """
    # For backward compatibility, if a specific path is provided, use direct loading
    if path is not None:
        import os
        resolved = Path(path).resolve()
        key = str(resolved)

        cache = getattr(load_enrichment_config, "_cache", {})
        if key in cache:
            return cache[key]

        with resolved.open() as f:
            data = yaml.safe_load(f)

        cfg = EnrichmentConfig(**data)
        cache[key] = cfg
        setattr(load_enrichment_config, "_cache", cache)
        return cfg
    
    # Use centralized configuration manager for default loading
    from .configuration_manager import get_config_manager
    config_manager = get_config_manager()
    return config_manager.get_enrichment_config()
