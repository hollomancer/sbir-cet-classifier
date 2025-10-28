"""
Public exports for sbir_cet_classifier.models

This module re-exports the canonical model and scoring primitives so callers
can import from a single location:

    from sbir_cet_classifier.models import (
        MultiSourceTextVectorizer,
        CETRelevanceScorer,
        RuleBasedScorer,
        ApplicabilityModel,
        EnhancedCETClassifier,
        SolicitationEnhancedScorer,
        ...
    )

Keep this file small and only export stable, canonical types. Avoid re-exporting
experimental or archived modules (those should live under docs/archive/ or an
experimental/ namespace).
"""

from .vectorizers import MultiSourceTextVectorizer
from .cet_relevance_scorer import CETRelevanceScorer
from .rules_scorer import RuleBasedScorer
from .applicability import (
    ApplicabilityModel,
    TrainingExample,
    ApplicabilityScore,
    band_for_score,
    build_enriched_text,
    prepare_award_text_for_classification,
)
from .enhanced_scoring import EnhancedCETClassifier, SolicitationEnhancedScorer

__all__ = [
    # Vectorizers & relevance
    "MultiSourceTextVectorizer",
    "CETRelevanceScorer",
    # Rule-based scoring
    "RuleBasedScorer",
    # ML applicability model
    "ApplicabilityModel",
    "TrainingExample",
    "ApplicabilityScore",
    "band_for_score",
    "build_enriched_text",
    "prepare_award_text_for_classification",
    # Convenience enhanced scoring helpers
    "EnhancedCETClassifier",
    "SolicitationEnhancedScorer",
]
