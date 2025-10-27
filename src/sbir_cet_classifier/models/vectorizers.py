"""Canonical multi-source TF-IDF vectorizer.

This module provides a reusable, well-documented MultiSourceTextVectorizer that
combines multiple text sources (e.g., abstract, keywords, solicitation text) into a
single sparse feature matrix. It uses separate TfidfVectorizer instances per source,
applies per-source weights post-vectorization, and horizontally stacks the results.

Key properties:
- Deterministic feature name prefixes: abstract_, keywords_, solicitation_
- Configurable source weights that must sum to 1.0 across active sources
- Per-source max_features allocation (even split across active sources)
- Standard fit/transform/fit_transform API

Example:
    >>> from sbir_cet_classifier.models.vectorizers import MultiSourceTextVectorizer
    >>> docs = [
    ...     {"abstract": "Quantum computing for cryptography",
    ...      "keywords": "quantum, cryptography",
    ...      "solicitation_text": "Advanced quantum algorithms"},
    ...     {"abstract": "AI for autonomous vehicles",
    ...      "keywords": "AI, autonomous, navigation",
    ...      "solicitation_text": "Intelligent transportation systems"},
    ... ]
    >>> vec = MultiSourceTextVectorizer(abstract_weight=0.5, keywords_weight=0.2, solicitation_weight=0.3)
    >>> X = vec.fit_transform(docs)
    >>> X.shape[0] == 2
    True
    >>> names = vec.get_feature_names_out()
    >>> any(n.startswith("abstract_") for n in names) and any(n.startswith("keywords_") for n in names)
    True
"""

from __future__ import annotations

from typing import Any, Dict, Iterable, List, Mapping, Tuple

from scipy.sparse import csr_matrix, hstack  # type: ignore[import-untyped]
from sklearn.feature_extraction.text import TfidfVectorizer  # type: ignore[import-untyped]


Document = Mapping[str, str]


class MultiSourceTextVectorizer:
    """Combine multiple text sources with TF-IDF and configurable weights.

    This class fits one TfidfVectorizer per source (abstract, keywords, solicitation_text),
    then applies per-source weights and horizontally stacks the results into a single
    sparse matrix suitable for downstream models.

    Parameters:
        abstract_weight: Weight for the 'abstract' source (0.0–1.0)
        keywords_weight: Weight for the 'keywords' source (0.0–1.0)
        solicitation_weight: Weight for the 'solicitation_text' source (0.0–1.0)
        include_solicitation: If False, the solicitation source is ignored and its weight is unused
        max_features: Global feature budget to be split evenly across active sources
        ngram_range: N-gram range for each TfidfVectorizer
        **tfidf_params: Additional sklearn TfidfVectorizer parameters (e.g., min_df, max_df, stop_words)

    Notes:
        - Active sources must have weights that sum to 1.0 (checked with a tolerance).
        - max_features is split evenly across active sources (with remainder distributed to the first sources).
        - Feature names are prefixed with the source name to avoid collisions.
    """

    def __init__(
        self,
        *,
        abstract_weight: float = 0.5,
        keywords_weight: float = 0.2,
        solicitation_weight: float = 0.3,
        include_solicitation: bool = True,
        max_features: int = 10_000,
        ngram_range: Tuple[int, int] = (1, 2),
        **tfidf_params: Any,
    ) -> None:
        # Determine active sources and validate weights
        if include_solicitation:
            active_weights = {
                "abstract": float(abstract_weight),
                "keywords": float(keywords_weight),
                "solicitation": float(solicitation_weight),
            }
        else:
            active_weights = {
                "abstract": float(abstract_weight),
                "keywords": float(keywords_weight),
            }

        weight_sum = sum(active_weights.values())
        if abs(weight_sum - 1.0) > 1e-6:
            raise ValueError(f"Weights must sum to 1.0 across active sources; got {weight_sum:.6f}")

        if max_features <= 0:
            raise ValueError("max_features must be a positive integer")

        self._weights: Dict[str, float] = active_weights
        self._ngram_range = tuple(ngram_range)
        self._max_features = int(max_features)

        # Allocate per-source feature budgets (even split across active sources)
        self._per_source_features = self._allocate_per_source_features(
            self._max_features, list(self._weights.keys())
        )

        # Initialize individual vectorizers per source
        base_params: Dict[str, Any] = dict(
            ngram_range=self._ngram_range,
            **tfidf_params,
        )

        self.abstract_vectorizer: TfidfVectorizer | None = (
            TfidfVectorizer(
                max_features=self._per_source_features.get("abstract", 0), **base_params
            )
            if "abstract" in self._weights
            else None
        )

        self.keywords_vectorizer: TfidfVectorizer | None = (
            TfidfVectorizer(
                max_features=self._per_source_features.get("keywords", 0), **base_params
            )
            if "keywords" in self._weights
            else None
        )

        self.solicitation_vectorizer: TfidfVectorizer | None = (
            TfidfVectorizer(
                max_features=self._per_source_features.get("solicitation", 0), **base_params
            )
            if "solicitation" in self._weights
            else None
        )

        self.is_fitted_: bool = False
        self._feature_names_: List[str] = []
        self._vocabulary_: Dict[str, int] = {}

    @staticmethod
    def _allocate_per_source_features(total: int, sources: List[str]) -> Dict[str, int]:
        """Evenly split a global feature budget across active sources.

        Remainder (if any) is distributed to the first k sources.
        """
        if not sources:
            return {}
        n = len(sources)
        base = total // n
        remainder = total % n
        allocation: Dict[str, int] = {}
        for idx, src in enumerate(sources):
            allocation[src] = base + (1 if idx < remainder else 0)
        return allocation

    def fit(self, documents: Iterable[Document]) -> "MultiSourceTextVectorizer":
        """Fit per-source vectorizers on the provided documents."""
        abs_texts, kw_texts, sol_texts = self._split_documents(documents)

        if self.abstract_vectorizer is not None:
            self.abstract_vectorizer.fit(abs_texts)
        if self.keywords_vectorizer is not None:
            self.keywords_vectorizer.fit(kw_texts)
        if self.solicitation_vectorizer is not None:
            self.solicitation_vectorizer.fit(sol_texts)

        # Rebuild combined feature names/vocabulary
        self._rebuild_feature_space()
        self.is_fitted_ = True
        return self

    def transform(self, documents: Iterable[Document]) -> csr_matrix:
        """Transform documents to a weighted, horizontally stacked sparse matrix."""
        if not self.is_fitted_:
            raise ValueError("Vectorizer must be fitted before transform")

        abs_texts, kw_texts, sol_texts = self._split_documents(documents)

        mats: List[csr_matrix] = []

        if self.abstract_vectorizer is not None:
            X_abs = self.abstract_vectorizer.transform(abs_texts) * self._weights["abstract"]
            mats.append(X_abs)

        if self.keywords_vectorizer is not None:
            X_kw = self.keywords_vectorizer.transform(kw_texts) * self._weights["keywords"]
            mats.append(X_kw)

        if self.solicitation_vectorizer is not None:
            X_sol = (
                self.solicitation_vectorizer.transform(sol_texts) * self._weights["solicitation"]
            )
            mats.append(X_sol)

        if not mats:
            # Should not happen due to validation in __init__
            raise RuntimeError("No active sources available to transform")

        return hstack(mats, format="csr")

    def fit_transform(self, documents: Iterable[Document]) -> csr_matrix:
        """Fit and transform in one step."""
        return self.fit(documents).transform(documents)

    def get_feature_names_out(self) -> List[str]:
        """Return combined, prefixed feature names (post-fit)."""
        if not self.is_fitted_:
            raise ValueError("Vectorizer must be fitted before getting feature names")
        return list(self._feature_names_)

    # Internal helpers

    def _split_documents(
        self, documents: Iterable[Document]
    ) -> Tuple[List[str], List[str], List[str]]:
        """Split document mappings into source-specific text lists."""
        abs_texts: List[str] = []
        kw_texts: List[str] = []
        sol_texts: List[str] = []
        for doc in documents:
            # Use .get for robustness; coerce to string and strip
            abs_texts.append(str(doc.get("abstract", "") or "").strip())
            kw_texts.append(str(doc.get("keywords", "") or "").strip())
            sol_texts.append(str(doc.get("solicitation_text", "") or "").strip())
        return abs_texts, kw_texts, sol_texts

    def _rebuild_feature_space(self) -> None:
        """Build combined feature names and vocabulary from per-source vectorizers."""
        names: List[str] = []

        if self.abstract_vectorizer is not None:
            names.extend(f"abstract_{n}" for n in self.abstract_vectorizer.get_feature_names_out())

        if self.keywords_vectorizer is not None:
            names.extend(f"keywords_{n}" for n in self.keywords_vectorizer.get_feature_names_out())

        if self.solicitation_vectorizer is not None:
            names.extend(
                f"solicitation_{n}" for n in self.solicitation_vectorizer.get_feature_names_out()
            )

        self._feature_names_ = names
        self._vocabulary_ = {name: i for i, name in enumerate(self._feature_names_)}


__all__ = ["MultiSourceTextVectorizer"]
