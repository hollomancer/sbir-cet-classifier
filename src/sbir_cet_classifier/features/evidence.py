"""Utilities for generating evidence snippets supporting CET classifications."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from functools import lru_cache
from typing import Literal

import spacy

from sbir_cet_classifier.common.config import load_config

SourceLocation = Literal["abstract", "keywords", "solicitation", "reviewer_notes"]


@dataclass(frozen=True)
class EvidenceSnippet:
    excerpt: str
    source_location: SourceLocation
    rationale_tag: str


def _truncate_to_word_limit(text: str, *, limit: int = 50) -> str:
    words = text.split()
    if len(words) <= limit:
        return text.strip()
    return " ".join(words[:limit]).strip()


@lru_cache(maxsize=1)
def _get_nlp() -> spacy.language.Language:
    model_name = load_config().spacy_model
    try:
        nlp = spacy.load(model_name)
    except OSError:  # pragma: no cover - executed when model missing
        nlp = spacy.blank("en")
    if not nlp.has_pipe("senter") and not nlp.has_pipe("parser"):
        nlp.add_pipe("sentencizer")
    return nlp


def extract_evidence_sentences(text: str, keywords: Iterable[str]) -> list[str]:
    """Return sentences containing any of the supplied keywords."""

    if not text:
        return []
    doc = _get_nlp()(text)
    lowered = [keyword.lower() for keyword in keywords]
    sentences: list[str] = []
    for sent in doc.sents:
        sentence_text = sent.text.strip()
        if any(keyword in sentence_text.lower() for keyword in lowered):
            sentences.append(sentence_text)
    return sentences


def build_evidence_snippet(
    *,
    text: str,
    keywords: Iterable[str],
    source_location: SourceLocation,
    rationale_tag: str,
    fallback: str = "",
) -> EvidenceSnippet:
    """Construct an :class:`EvidenceSnippet` within the 50-word limit."""

    candidates = extract_evidence_sentences(text, keywords)
    excerpt = candidates[0] if candidates else fallback or text[:280]
    excerpt = _truncate_to_word_limit(excerpt)
    return EvidenceSnippet(excerpt=excerpt, source_location=source_location, rationale_tag=rationale_tag)


__all__ = ["EvidenceSnippet", "SourceLocation", "build_evidence_snippet", "extract_evidence_sentences"]
