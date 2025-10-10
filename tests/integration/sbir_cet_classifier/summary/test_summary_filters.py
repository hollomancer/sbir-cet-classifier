from __future__ import annotations

import json
from datetime import datetime
from uuid import uuid4

from typer.testing import CliRunner

from sbir_cet_classifier.api.router import configure_summary_service
from sbir_cet_classifier.cli.app import app
from sbir_cet_classifier.common.schemas import ApplicabilityAssessment, EvidenceStatement
from sbir_cet_classifier.features.summary import SummaryService

runner = CliRunner()


def _configure_service() -> None:
    awards = [
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
        ),
        ApplicabilityAssessment(
            assessment_id=str(uuid4()),
            award_id="NAV456",
            taxonomy_version="NSTC-2025Q1",
            score=62,
            classification="Medium",
            primary_cet_id="quantum_sensing",
            supporting_cet_ids=[],
            evidence_statements=[],
            generation_method="manual_review",
            assessed_at=datetime(2024, 1, 3),
            reviewer_notes=None,
        ),
    ]
    taxonomy = [
        {"cet_id": "hypersonics", "name": "Hypersonics"},
        {"cet_id": "quantum_sensing", "name": "Quantum Sensing"},
    ]
    service = SummaryService.from_records(awards, assessments, taxonomy)
    configure_summary_service(service)


def test_cli_summary_matches_api_filters(tmp_path):
    _configure_service()

    result = runner.invoke(
        app,
        [
            "summary",
            "2023",
            "2023",
            "--agency",
            "AF",
        ],
    )
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["filters"]["agencies"] == ["AF"]
    assert payload["totals"]["awards"] == 1
    assert payload["cet_summaries"][0]["cet_id"] == "hypersonics"
