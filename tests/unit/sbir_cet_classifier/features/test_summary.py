from __future__ import annotations

from datetime import datetime

import pandas as pd

from sbir_cet_classifier.features.summary import SummaryFilters, SummaryService
from sbir_cet_classifier.common.schemas import ApplicabilityAssessment, EvidenceStatement


def _create_service():
    awards = pd.DataFrame(
        [
            {
                "award_id": "AF123",
                "agency": "AF",
                "phase": "I",
                "firm_state": "OH",
                "award_amount": 150000,
                "award_date": "2023-06-01",
                "fiscal_year": 2023,
            },
            {
                "award_id": "NAV456",
                "agency": "NAVY",
                "phase": "II",
                "firm_state": "CA",
                "award_amount": 900000,
                "award_date": "2023-09-15",
                "fiscal_year": 2023,
            },
            {
                "award_id": "AF789",
                "agency": "AF",
                "phase": "II",
                "firm_state": "OH",
                "award_amount": 350000,
                "award_date": "2024-01-10",
                "fiscal_year": 2024,
            },
        ]
    )

    assessments = pd.DataFrame(
        [
            {
                "assessment_id": "1",
                "award_id": "AF123",
                "taxonomy_version": "NSTC-2025Q1",
                "score": 88,
                "classification": "High",
                "primary_cet_id": "hypersonics",
                "supporting_cet_ids": ["thermal"],
                "evidence_statements": [
                    EvidenceStatement(
                        excerpt="Hypersonic propulsion research",
                        source_location="abstract",
                        rationale_tag="performance",
                    ).model_dump()
                ],
                "generation_method": "automated",
                "assessed_at": datetime(2024, 1, 2),
            },
            {
                "assessment_id": "2",
                "award_id": "NAV456",
                "taxonomy_version": "NSTC-2025Q1",
                "score": 62,
                "classification": "Medium",
                "primary_cet_id": "quantum_sensing",
                "supporting_cet_ids": [],
                "evidence_statements": [],
                "generation_method": "manual_review",
                "assessed_at": datetime(2024, 1, 3),
            },
        ]
    )

    taxonomy = pd.DataFrame(
        [
            {"cet_id": "hypersonics", "name": "Hypersonics"},
            {"cet_id": "quantum_sensing", "name": "Quantum Sensing"},
        ]
    )

    return SummaryService(awards, assessments, taxonomy)


def test_summarize_filters_and_aggregates():
    service = _create_service()
    filters = SummaryFilters(fiscal_year_start=2023, fiscal_year_end=2023, agencies=("AF", "NAVY"))
    response = service.summarize(filters).as_dict()

    assert response["totals"]["awards"] == 2
    assert response["totals"]["percent_classified"] == 100.0
    summaries = response["cet_summaries"]
    assert len(summaries) == 2

    hypersonics = next(item for item in summaries if item["cet_id"] == "hypersonics")
    assert hypersonics["awards"] == 1
    assert hypersonics["classification_breakdown"]["High"] == 1
    assert hypersonics["share_of_awards"] == 50.0
    assert hypersonics["top_award"]["award_id"] == "AF123"


def test_empty_summary_when_no_awards():
    service = _create_service()
    filters = SummaryFilters(fiscal_year_start=2025, fiscal_year_end=2025)
    response = service.summarize(filters).as_dict()
    assert response["totals"]["awards"] == 0
    assert response["cet_summaries"] == []
