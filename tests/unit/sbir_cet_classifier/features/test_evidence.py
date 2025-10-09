from __future__ import annotations

from sbir_cet_classifier.features.evidence import (
    EvidenceSnippet,
    build_evidence_snippet,
    extract_evidence_sentences,
)


def test_extract_evidence_sentences_returns_keyword_matches():
    text = "Hypersonic propulsion research improves thermal protection. Quantum sensors enable navigation."
    sentences = extract_evidence_sentences(text, ["hypersonic", "quantum"])
    assert len(sentences) == 2
    assert sentences[0].startswith("Hypersonic propulsion")


def test_build_evidence_snippet_truncates_to_50_words():
    text = " ".join(["word"] * 100)
    snippet = build_evidence_snippet(
        text=text,
        keywords=["word"],
        source_location="abstract",
        rationale_tag="performance",
    )
    assert isinstance(snippet, EvidenceSnippet)
    assert len(snippet.excerpt.split()) <= 50
