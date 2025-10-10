"""YAML configuration loader with validation."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field


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


class PhaseKeywordsConfig(BaseModel):
    """Phase-specific keywords."""
    phase_i: list[str]
    phase_ii: list[str]


class EnrichmentConfig(BaseModel):
    """Complete enrichment configuration."""
    version: str
    description: str
    topic_domains: dict[str, TopicDomainConfig]
    agency_focus: dict[str, str]
    phase_keywords: PhaseKeywordsConfig


@lru_cache(maxsize=1)
def load_classification_config(path: Path | None = None) -> ClassificationConfig:
    """Load classification configuration from YAML.
    
    Args:
        path: Path to classification.yaml (defaults to config/classification.yaml)
        
    Returns:
        Validated classification configuration
    """
    if path is None:
        path = Path(__file__).parent.parent.parent.parent / "config" / "classification.yaml"
    
    with open(path) as f:
        data = yaml.safe_load(f)
    
    return ClassificationConfig(**data)


@lru_cache(maxsize=1)
def load_enrichment_config(path: Path | None = None) -> EnrichmentConfig:
    """Load enrichment configuration from YAML.
    
    Args:
        path: Path to enrichment.yaml (defaults to config/enrichment.yaml)
        
    Returns:
        Validated enrichment configuration
    """
    if path is None:
        path = Path(__file__).parent.parent.parent.parent / "config" / "enrichment.yaml"
    
    with open(path) as f:
        data = yaml.safe_load(f)
    
    return EnrichmentConfig(**data)
