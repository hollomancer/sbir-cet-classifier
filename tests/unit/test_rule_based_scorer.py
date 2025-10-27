import pytest

from src.sbir_cet_classifier.models.rules_scorer import RuleBasedScorer


@pytest.fixture
def scorer():
    return RuleBasedScorer()


def test_agency_priors_boost_applied(scorer):
    # Department of Defense has hypersonics: 15 in agency_priors
    text = ""
    scores = scorer.score_text(text, agency="Department of Defense")
    assert "hypersonics" in scores
    assert scores["hypersonics"] >= 15.0


def test_branch_priors_boost_applied(scorer):
    # Air Force has hypersonics: 20 in branch_priors
    text = ""
    scores = scorer.score_text(text, branch="Air Force")
    assert "hypersonics" in scores
    assert scores["hypersonics"] >= 20.0


def test_keyword_core_contributes_for_quantum(scorer):
    # "quantum computing" and "quantum algorithm" are core phrases for quantum_computing
    text = "This project develops quantum computing and a novel quantum algorithm."
    scores = scorer.score_text(text)
    qc = scores.get("quantum_computing", 0.0)
    cy = scores.get("cybersecurity", 0.0)
    assert qc > 0.0
    # Should be larger than an unrelated CET like cybersecurity
    assert qc >= cy


def test_negative_keyword_penalizes_ai(scorer):
    # "ai-powered diagnostic" is a negative phrase for artificial_intelligence
    # With no positives present for AI, the score should clamp to 0
    text = "An ai-powered diagnostic platform for process optimization."
    scores = scorer.score_text(text)
    ai = scores.get("artificial_intelligence", 0.0)
    assert ai == 0.0


def test_context_rule_boost_for_medical_devices(scorer):
    # Context rule: medical_devices has a rule requiring ["ai", "diagnostic"] with +20 boost
    text = "This AI diagnostic platform improves clinical workflows."
    scores = scorer.score_text(text)
    md = scores.get("medical_devices", 0.0)
    assert md >= 20.0


def test_priors_and_keywords_additive_for_quantum(scorer):
    # Department of Energy has quantum_computing prior 15; text adds keyword points
    text = "We propose quantum computing techniques for simulation."
    scores = scorer.score_text(text, agency="Department of Energy")
    qc = scores.get("quantum_computing", 0.0)
    # Should exceed prior-only value due to keyword contributions
    assert qc > 15.0
