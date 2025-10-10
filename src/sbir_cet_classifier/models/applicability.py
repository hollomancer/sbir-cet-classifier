"""Applicability scoring pipeline for CET alignment."""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass

import numpy as np
from sklearn.calibration import CalibratedClassifierCV
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import LabelEncoder

CLASSIFICATION_BANDS = {
    "High": (70, 100),
    "Medium": (40, 69),
    "Low": (0, 39),
}


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
    if score >= 70:
        return "High"
    if score >= 40:
        return "Medium"
    return "Low"


class ApplicabilityModel:
    """Wrapper around TF-IDF + calibrated logistic regression."""

    def __init__(self) -> None:
        self._vectorizer = TfidfVectorizer(ngram_range=(1, 2), max_features=20000)
        self._classifier: LogisticRegression | CalibratedClassifierCV | None = None
        self._label_encoder = LabelEncoder()
        self._is_fitted = False
        self._is_calibrated = False

    def fit(self, examples: Sequence[TrainingExample]) -> ApplicabilityModel:
        texts = [example.text for example in examples]
        cet_labels = [example.primary_cet_id for example in examples]
        y = self._label_encoder.fit_transform(cet_labels)
        X = self._vectorizer.fit_transform(texts)
        base_classifier = LogisticRegression(max_iter=500)
        base_classifier.fit(X, y)

        class_counts = np.bincount(y)
        if class_counts.size >= 2 and class_counts.min() >= 3:
            calibrated = CalibratedClassifierCV(
                LogisticRegression(max_iter=500),
                cv=3,
            )
            calibrated.fit(X, y)
            self._classifier = calibrated
            self._is_calibrated = True
        else:
            self._classifier = base_classifier
            self._is_calibrated = False
        self._is_fitted = True
        return self

    def predict(self, award_id: str, text: str) -> ApplicabilityScore:
        if not self._is_fitted:
            raise RuntimeError("Model must be fitted before prediction")
        if self._classifier is None:  # pragma: no cover - defensive
            raise RuntimeError("Classifier unavailable; call fit first")
        X = self._vectorizer.transform([text])
        probs = self._classifier.predict_proba(X)[0]  # type: ignore[call-arg]
        labels = self._label_encoder.inverse_transform(np.arange(len(probs)))
        ranked = sorted(zip(labels, probs, strict=False), key=lambda pair: pair[1], reverse=True)
        primary_cet_id, probability = ranked[0]
        score = float(probability * 100)
        supporting = [(cet, float(p * 100)) for cet, p in ranked[1:4]]
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
        probs = self._classifier.predict_proba(X)  # type: ignore[call-arg]
        labels = self._label_encoder.inverse_transform(np.arange(probs.shape[1]))
        results: list[ApplicabilityScore] = []
        for award_id, prob_vector in zip(award_ids, probs, strict=False):
            ranked = sorted(zip(labels, prob_vector, strict=False), key=lambda pair: pair[1], reverse=True)
            primary_cet_id, probability = ranked[0]
            score = float(probability * 100)
            supporting = [(cet, float(p * 100)) for cet, p in ranked[1:4]]
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
