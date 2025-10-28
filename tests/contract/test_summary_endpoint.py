from __future__ import annotations

from datetime import datetime
from sbir_cet_classifier.common.datetime_utils import UTC
from uuid import uuid4

from fastapi import FastAPI
from fastapi.testclient import TestClient

from sbir_cet_classifier.api.router import configure_summary_service, router
from sbir_cet_classifier.common.schemas import ApplicabilityAssessment, EvidenceStatement
from sbir_cet_classifier.features.summary import SummaryService


def _build_service() -> SummaryService:
    awards = [
        {
            "award_id": "AF123",
            "agency": "AF",
            "phase": "I",
            "firm_state": "OH",
            "award_amount": 150000,
            "award_date": "2023-06-01",
            "fiscal_year": 2023,
        }
    ]
    assessments = [
        ApplicabilityAssessment(
            assessment_id=str(uuid4()),
            award_id="AF123",
            taxonomy_version="NSTC-2025Q1",
            score=88,
            classification="High",
            primary_cet_id="hypersonics",
            supporting_cet_ids=[],
            evidence_statements=[
                EvidenceStatement(
                    excerpt="Hypersonic propulsion research",
                    source_location="abstract",
                    rationale_tag="performance",
                )
            ],
            generation_method="automated",
            assessed_at=datetime(2024, 1, 2),
            reviewer_notes=None,
        )
    ]
    taxonomy = [
        {"cet_id": "hypersonics", "name": "Hypersonics"},
    ]
    return SummaryService.from_records(awards, assessments, taxonomy)


def test_get_summary_returns_expected_payload():
    app = FastAPI()
    app.include_router(router, prefix="/api")

    configure_summary_service(_build_service())

    client = TestClient(app)
    response = client.get(
        "/api/applicability/summary",
        params={
            "fiscal_year_start": 2023,
            "fiscal_year_end": 2023,
            "agency": ["AF"],
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["totals"]["awards"] == 1
    assert payload["cet_summaries"][0]["cet_id"] == "hypersonics"
    assert payload["filters"]["agencies"] == ["AF"]
