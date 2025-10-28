"""
Backward-compatibility shim for older / experimental enhanced vectorizers.

This module is intentionally lightweight: it emits a clear deprecation warning on
import and exposes small compatibility wrappers that delegate to the canonical,
supported `MultiSourceTextVectorizer` in
`sbir_cet_classifier.models.vectorizers`.

Goals:
- Warn users who import this module that the implementations are deprecated.
- Provide thin wrappers with the old class names so existing imports don't
  break immediately (but surface deprecation notices on construction/use).
- Point to the canonical implementation and provide a simple migration path.

Note:
- The original, experimental implementations have been archived in
  `docs/archive/enhanced_vectorization.py` (kept for reference).
- Prefer importing:
    from sbir_cet_classifier.models.vectorizers import MultiSourceTextVectorizer
"""

from __future__ import annotations

import logging
import warnings
from typing import Dict, List, Optional, Set, Tuple

from scipy.sparse import csr_matrix  # type: ignore[import-untyped]

# Import the canonical vectorizer (the single source of truth for multi-source TF-IDF)
from sbir_cet_classifier.models.vectorizers import MultiSourceTextVectorizer

logger = logging.getLogger(__name__)

# Emit an import-time deprecation warning so users see this immediately.
warning_msg = (
    "sbir_cet_classifier.models.enhanced_vectorization is deprecated and has been "
    "archived. Use the canonical MultiSourceTextVectorizer in "
    "`sbir_cet_classifier.models.vectorizers` instead. See docs/archive/enhanced_vectorization.py "
    "for the archived experimental implementations and migration notes."
)
# Use warnings.warn so it surfaces in user code/tests; also log once.
warnings.warn(warning_msg, DeprecationWarning, stacklevel=2)
logger.warning(warning_msg)


class WeightedTextCombiner:
    """
    Lightweight compatibility shim for the older WeightedTextCombiner.

    Behavior:
    - Accepts a `weights` mapping of source -> weight and a `normalize_weights` flag.
    - `combine_texts(text_sources)` returns a combined string where each source's
      text is repeated in proportion to its weight (naive but deterministic).
    - Construction emits a deprecation warning and points to the canonical vectorizer
      approach (which prefers separate vectorizers per source with explicit weighting).
    """

    def __init__(self, weights: Dict[str, float], normalize_weights: bool = False):
        warnings.warn(
            "WeightedTextCombiner is deprecated. Prefer MultiSourceTextVectorizer with per-source weights.",
            DeprecationWarning,
            stacklevel=2,
        )
        self.weights = dict(weights)
        if normalize_weights:
            total = sum(self.weights.values())
            if total > 0:
                self.weights = {k: v / total for k, v in self.weights.items()}

    def combine_texts(self, text_sources: Dict[str, str]) -> str:
        parts: List[str] = []
        for source, weight in self.weights.items():
            text = (text_sources.get(source) or "").strip()
            if not text or weight <= 0:
                continue
            # Scale weight to a modest repetition count for simple boosting
            repetitions = max(1, int(round(weight * 10)))
            parts.extend([text] * repetitions)
        return " ".join(parts)


class CETAwareTfidfVectorizer:
    """
    Deprecated compatibility wrapper: previously boosted CET keywords inside a single TF-IDF.

    This shim:
    - Emits a deprecation warning on instantiation.
    - Delegates to the canonical `MultiSourceTextVectorizer` with `include_solicitation=False`.
    - Attempts to preserve a minimal API surface: `fit`, `transform`, `fit_transform`,
      `get_feature_names_out`. Other advanced, experimental behaviors (e.g., internal
      CET boosting heuristics) are not reimplemented here — prefer explicit scoring
      via `RuleBasedScorer` or engineered features upstream.
    """

    def __init__(
        self,
        cet_keywords_boost: float = 2.0,
        technical_terms_boost: float = 1.5,
        custom_cet_vocabulary: Optional[List[str]] = None,
        max_features: int = 10000,
        ngram_range: Tuple[int, int] = (1, 2),
        **tfidf_params,
    ):
        warnings.warn(
            "CETAwareTfidfVectorizer is deprecated. Use MultiSourceTextVectorizer "
            "and combine canonical CET signals via RuleBasedScorer or explicit features.",
            DeprecationWarning,
            stacklevel=2,
        )
        # Map to a reasonable default delegate: abstract + keywords (no solicitation)
        self._delegate = MultiSourceTextVectorizer(
            abstract_weight=0.7,
            keywords_weight=0.3,
            solicitation_weight=0.0,
            include_solicitation=False,
            max_features=max_features,
            ngram_range=ngram_range,
            **tfidf_params,
        )
        # Keep references to parameters for informational purposes
        self.cet_keywords_boost = cet_keywords_boost
        self.technical_terms_boost = technical_terms_boost
        self.custom_cet_vocabulary = list(custom_cet_vocabulary or [])

    def fit(self, documents: List[str]):
        """
        Fit delegate on a list of text documents.

        Historically this class accepted plain strings. To preserve compatibility,
        we convert the list of strings into the expected dict shape for the delegate.
        """
        wrapped = [{"abstract": d, "keywords": ""} for d in documents]
        self._delegate.fit(wrapped)
        return self

    def transform(self, documents: List[str]) -> csr_matrix:
        wrapped = [{"abstract": d, "keywords": ""} for d in documents]
        return self._delegate.transform(wrapped)

    def fit_transform(self, documents: List[str]) -> csr_matrix:
        self.fit(documents)
        return self.transform(documents)

    def get_feature_names_out(self) -> List[str]:
        return self._delegate.get_feature_names_out()

    def get_cet_keywords(self) -> Set[str]:
        """
        Return the configured CET keyword set if provided; otherwise empty set.

        Note: canonical CET keywords live in configuration (config/classification.yaml)
        and are surfaced via classification_config helpers.
        """
        return set(k.lower() for k in (self.custom_cet_vocabulary or []))


class SolicitationEnhancedTfidfVectorizer:
    """
    Deprecated wrapper for a solicitation-aware TF-IDF vectorizer.

    Shim behavior:
    - Emits a deprecation warning on instantiation.
    - Delegates to `MultiSourceTextVectorizer` with `include_solicitation=True`.
    - Maintains a minimal API compatible with the original class: `fit`, `transform`,
      `fit_transform`, `get_feature_names_out`.
    """

    def __init__(
        self,
        abstract_weight: float = 0.5,
        keywords_weight: float = 0.2,
        solicitation_weight: float = 0.3,
        max_features: int = 10_000,
        ngram_range: Tuple[int, int] = (1, 2),
        **tfidf_params,
    ):
        warnings.warn(
            "SolicitationEnhancedTfidfVectorizer is deprecated. Use MultiSourceTextVectorizer "
            "with `include_solicitation=True` instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        self._delegate = MultiSourceTextVectorizer(
            abstract_weight=abstract_weight,
            keywords_weight=keywords_weight,
            solicitation_weight=solicitation_weight,
            include_solicitation=True,
            max_features=max_features,
            ngram_range=ngram_range,
            **tfidf_params,
        )

    def fit(self, documents: List[Dict[str, str]]):
        """
        Fit expects the older dict shape with keys: 'abstract', 'keywords', 'solicitation_text'.
        It forwards them to the canonical vectorizer.
        """
        self._delegate.fit(documents)
        return self

    def transform(self, documents: List[Dict[str, str]]) -> csr_matrix:
        return self._delegate.transform(documents)

    def fit_transform(self, documents: List[Dict[str, str]]) -> csr_matrix:
        self.fit(documents)
        return self.transform(documents)

    def get_feature_names_out(self) -> List[str]:
        return self._delegate.get_feature_names_out()


__all__ = [
    "WeightedTextCombiner",
    "CETAwareTfidfVectorizer",
    "SolicitationEnhancedTfidfVectorizer",
    # Note: consumers should prefer `sbir_cet_classifier.models.vectorizers.MultiSourceTextVectorizer`
]
