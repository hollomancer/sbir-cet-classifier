from __future__ import annotations

from sbir_cet_classifier.models.applicability import (
    ApplicabilityModel,
    TrainingExample,
    band_for_score,
)


def test_band_for_score_thresholds():
    assert band_for_score(85) == "High"
    assert band_for_score(55) == "Medium"
    assert band_for_score(10) == "Low"


def test_model_trains_and_predicts():
    examples = [
        TrainingExample(
            award_id="AF123",
            text="hypersonic propulsion for high-speed flight",
            primary_cet_id="hypersonics",
        ),
        TrainingExample(
            award_id="NAV456",
            text="quantum sensing underwater communications",
            primary_cet_id="quantum_sensing",
        ),
        TrainingExample(
            award_id="AF789",
            text="next-generation hypersonic thermal protection",
            primary_cet_id="hypersonics",
        ),
    ]

    model = ApplicabilityModel().fit(examples)

    result = model.predict("AF999", "thermal protection for hypersonic vehicles")
    assert result.primary_cet_id == "hypersonics"
    assert result.classification in {"High", "Medium", "Low"}
    assert len(result.supporting_ranked) <= 3

    batch = model.batch_predict([
        ("AF999", "thermal protection for hypersonic vehicles"),
        ("NAV999", "quantum sensors for underwater navigation"),
    ])
    assert {score.award_id for score in batch} == {"AF999", "NAV999"}
