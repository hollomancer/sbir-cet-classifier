"""Applicability scoring pipeline for CET alignment."""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass

import numpy as np
from sklearn.calibration import CalibratedClassifierCV
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.feature_selection import SelectKBest, chi2
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import LabelEncoder
from sklearn.utils.class_weight import compute_class_weight

from sbir_cet_classifier.common.yaml_config import load_classification_config

# Load configuration from YAML
_config = load_classification_config()


@dataclass(frozen=True)
class TrainingExample:
    """Single labelled example for applicability training."""

    award_id: str
    text: str
    primary_cet_id: str


@dataclass(frozen=True)
class ApplicabilityScore:
    award_id: str
    primary_cet_id: str
    primary_score: float
    supporting_ranked: list[tuple[str, float]]
    classification: str


def band_for_score(score: float) -> str:
    """Determine classification band for a score using YAML config."""
    for band_name, band_config in _config.scoring.bands.items():
        if band_config.min <= score <= band_config.max:
            return band_config.label
    return "Low"  # Default fallback


class ApplicabilityModel:
    """Wrapper around TF-IDF + calibrated logistic regression with optimizations.

    When calibration is enabled, the same base estimator instance is passed to
    CalibratedClassifierCV (instead of instantiating a new one).
    """

    def __init__(self) -> None:
        # Load config from YAML
        vec_cfg = _config.vectorizer
        self._vectorizer = TfidfVectorizer(
            ngram_range=tuple(vec_cfg.ngram_range),
            max_features=vec_cfg.max_features,
            stop_words=_config.stop_words,
            min_df=vec_cfg.min_df,
            max_df=vec_cfg.max_df,
        )
        # Feature selection
        fs_cfg = _config.feature_selection
        self._feature_selector = SelectKBest(chi2, k=fs_cfg.k) if fs_cfg.enabled else None
        self._classifier: LogisticRegression | CalibratedClassifierCV | None = None
        self._label_encoder = LabelEncoder()
        self._is_fitted = False
        self._is_calibrated = False

    def fit(self, examples: Sequence[TrainingExample]) -> ApplicabilityModel:
        texts = [example.text for example in examples]
        cet_labels = [example.primary_cet_id for example in examples]
        y = self._label_encoder.fit_transform(cet_labels)

        # TF-IDF vectorization
        # Adjust vectorizer thresholds for small training sets to avoid min_df/max_df conflicts
        n_docs = max(1, len(texts))
        min_df_cfg = _config.vectorizer.min_df
        max_df_cfg = _config.vectorizer.max_df
        # Ensure min_df does not exceed number of documents
        adjusted_min_df = min(min_df_cfg, n_docs)
        # Ensure max_df corresponds to at least adjusted_min_df documents
        if max_df_cfg <= 1.0:
            min_fraction = adjusted_min_df / n_docs
            adjusted_max_df = min(1.0, max(max_df_cfg, min_fraction))
        else:
            adjusted_max_df = float(max(max_df_cfg, float(adjusted_min_df)))
        self._vectorizer.set_params(min_df=adjusted_min_df, max_df=adjusted_max_df)
        try:
            X = self._vectorizer.fit_transform(texts)
        except ValueError as e:
            msg = str(e)
            if "After pruning, no terms remain" in msg or "empty vocabulary" in msg:
                # Fallback for tiny datasets: relax pruning thresholds
                self._vectorizer.set_params(min_df=1, max_df=1.0)
                X = self._vectorizer.fit_transform(texts)
            else:
                raise

        # Feature selection (if enabled)
        if self._feature_selector:
            X_selected = self._feature_selector.fit_transform(X, y)
        else:
            X_selected = X

        # Compute class weights for imbalanced data
        classes = np.unique(y)
        clf_cfg = _config.classifier
        if clf_cfg.class_weight == "balanced":
            class_weights = compute_class_weight("balanced", classes=classes, y=y)
            class_weight_dict = dict(zip(classes, class_weights, strict=False))
        else:
            class_weight_dict = None

        # Train base classifier
        base_classifier = LogisticRegression(
            max_iter=clf_cfg.max_iter,
            class_weight=class_weight_dict,
            solver=clf_cfg.solver,
            n_jobs=clf_cfg.n_jobs,
        )
        # Calibrate if enabled and enough samples per class
        cal_cfg = _config.calibration
        class_counts = np.bincount(y)
        if (
            cal_cfg.enabled
            and class_counts.size >= 2
            and class_counts.min() >= cal_cfg.min_samples_per_class
        ):
            # Reuse the same base estimator instance for calibration to avoid redundant instantiation
            calibrated = CalibratedClassifierCV(
                estimator=base_classifier,
                cv=cal_cfg.cv,
            )
            calibrated.fit(X_selected, y)
            self._classifier = calibrated
            self._is_calibrated = True
        else:
            # Fit the base classifier directly when calibration is disabled or not applicable
            base_classifier.fit(X_selected, y)
            self._classifier = base_classifier
            self._is_calibrated = False
        self._is_fitted = True
        return self

    def predict(self, award_id: str, text: str) -> ApplicabilityScore:
        if not self._is_fitted:
            raise RuntimeError("Model must be fitted before prediction")
        if self._classifier is None:  # pragma: no cover - defensive
            raise RuntimeError("Classifier unavailable; call fit first")

        # Apply same transformations as training
        X = self._vectorizer.transform([text])
        if self._feature_selector:
            X_selected = self._feature_selector.transform(X)
        else:
            X_selected = X

        probs = self._classifier.predict_proba(X_selected)[0]  # type: ignore[call-arg]
        labels = self._label_encoder.inverse_transform(np.arange(len(probs)))
        ranked = sorted(zip(labels, probs, strict=False), key=lambda pair: pair[1], reverse=True)
        primary_cet_id, probability = ranked[0]
        score = float(probability * 100)
        max_supporting = _config.scoring.max_supporting
        supporting = [(cet, float(p * 100)) for cet, p in ranked[1 : max_supporting + 1]]
        return ApplicabilityScore(
            award_id=award_id,
            primary_cet_id=primary_cet_id,
            primary_score=score,
            supporting_ranked=supporting,
            classification=band_for_score(score),
        )

    def batch_predict(self, records: Iterable[tuple[str, str]]) -> list[ApplicabilityScore]:
        if not self._is_fitted:
            raise RuntimeError("Model must be fitted before prediction")
        if self._classifier is None:  # pragma: no cover - defensive
            raise RuntimeError("Classifier unavailable; call fit first")
        award_ids, texts = zip(*records, strict=False)
        X = self._vectorizer.transform(texts)
        if self._feature_selector:
            X_selected = self._feature_selector.transform(X)
        else:
            X_selected = X
        probs = self._classifier.predict_proba(X_selected)  # type: ignore[call-arg]
        labels = self._label_encoder.inverse_transform(np.arange(probs.shape[1]))
        results: list[ApplicabilityScore] = []
        max_supporting = _config.scoring.max_supporting
        for award_id, prob_vector in zip(award_ids, probs, strict=False):
            ranked = sorted(
                zip(labels, prob_vector, strict=False), key=lambda pair: pair[1], reverse=True
            )
            primary_cet_id, probability = ranked[0]
            score = float(probability * 100)
            supporting = [(cet, float(p * 100)) for cet, p in ranked[1 : max_supporting + 1]]
            results.append(
                ApplicabilityScore(
                    award_id=award_id,
                    primary_cet_id=primary_cet_id,
                    primary_score=score,
                    supporting_ranked=supporting,
                    classification=band_for_score(score),
                )
            )
        return results

    def export_bundle(self) -> dict:
        if not self._is_fitted:
            raise RuntimeError("Model must be fitted before export")
        if self._classifier is None:  # pragma: no cover - defensive
            raise RuntimeError("Classifier unavailable; call fit first")
        return {
            "vectorizer": self._vectorizer,
            "classifier": self._classifier,
            "label_encoder": self._label_encoder,
            "calibrated": self._is_calibrated,
        }


def build_enriched_text(
    *,
    award_text: str,
    solicitation_description: str | None = None,
    solicitation_keywords: list[str] | None = None,
) -> str:
    """Build enriched text combining award and solicitation data.

    Combines award text (typically abstract + keywords) with solicitation
    description and technical keywords for enhanced TF-IDF classification.
    Falls back gracefully to award-only text when solicitation data unavailable.

    Args:
        award_text: Award abstract and keywords text
        solicitation_description: Optional solicitation description from API
        solicitation_keywords: Optional solicitation technical keywords from API

    Returns:
        Combined text for TF-IDF feature extraction

    Example:
        >>> award_text = "AI-powered robotics for manufacturing"
        >>> sol_desc = "SBIR Phase I: Advanced Manufacturing Technologies"
        >>> sol_keywords = ["AI", "robotics", "manufacturing"]
        >>> enriched = build_enriched_text(
        ...     award_text=award_text,
        ...     solicitation_description=sol_desc,
        ...     solicitation_keywords=sol_keywords
        ... )
        >>> print(enriched)
        AI-powered robotics for manufacturing SBIR Phase I: Advanced Manufacturing Technologies AI robotics manufacturing

    Note:
        Per FR-008 and T036, solicitation enrichment enhances classification
        quality by including program-level technical context. When solicitation
        data is missing or enrichment fails, falls back to award-only features.
    """
    text_parts = [award_text]

    if solicitation_description:
        text_parts.append(solicitation_description.strip())

    if solicitation_keywords:
        # Join keywords with spaces for TF-IDF
        keywords_text = " ".join(kw.strip() for kw in solicitation_keywords if kw)
        if keywords_text:
            text_parts.append(keywords_text)

    return " ".join(text_parts)


def prepare_award_text_for_classification(
    *,
    abstract: str | None = None,
    keywords: list[str] | None = None,
) -> str:
    """Prepare award text for classification from abstract and keywords.

    Args:
        abstract: Award abstract text
        keywords: Award keywords list

    Returns:
        Combined award text string

    Example:
        >>> text = prepare_award_text_for_classification(
        ...     abstract="Research on AI algorithms",
        ...     keywords=["AI", "machine learning", "algorithms"]
        ... )
        >>> print(text)
        Research on AI algorithms AI machine learning algorithms
    """
    text_parts = []

    if abstract:
        text_parts.append(abstract.strip())

    if keywords:
        keywords_text = " ".join(kw.strip() for kw in keywords if kw)
        if keywords_text:
            text_parts.append(keywords_text)

    return " ".join(text_parts) if text_parts else ""


__all__ = [
    "ApplicabilityModel",
    "ApplicabilityScore",
    "TrainingExample",
    "band_for_score",
    "build_enriched_text",
    "prepare_award_text_for_classification",
]
