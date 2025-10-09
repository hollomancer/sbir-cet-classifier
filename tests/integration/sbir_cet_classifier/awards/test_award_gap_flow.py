from __future__ import annotations

import json
from datetime import datetime, timezone
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from typer.testing import CliRunner

from sbir_cet_classifier.api.router import router as api_router
from sbir_cet_classifier.cli.app import app as cli_app


def _build_awards_service():
    from sbir_cet_classifier.features.awards import AwardsService

    awards = [
        {
            "award_id": "AF123",
            "title": "Hypersonic Flight Control",
            "abstract": "Propulsion advances for hypersonic flight control surfaces.",
            "keywords": ["hypersonic", "propulsion"],
            "agency": "AF",
            "phase": "I",
            "award_amount": 150000,
            "award_date": "2023-06-01",
            "firm_state": "OH",
            "fiscal_year": 2023,
        },
        {
            "award_id": "NAV456",
            "title": "Quantum Navigation Suite",
            "abstract": None,
            "keywords": [],
            "agency": "NAVY",
            "phase": "II",
            "award_amount": 900000,
            "award_date": "2023-09-15",
            "firm_state": "CA",
            "fiscal_year": 2023,
        },
        {
            "award_id": "AF789",
            "title": "Thermal Protection Composites",
            "abstract": "Advanced TPS materials.",
            "keywords": ["thermal", "protection"],
            "agency": "AF",
            "phase": "II",
            "award_amount": 450000,
            "award_date": "2024-01-12",
            "firm_state": "VA",
            "fiscal_year": 2024,
        },
    ]
    assessments = [
        {
            "assessment_id": str(uuid4()),
            "award_id": "AF123",
            "taxonomy_version": "NSTC-2025Q1",
            "score": 88,
            "classification": "High",
            "primary_cet_id": "hypersonics",
            "supporting_cet_ids": ["thermal_protection"],
            "evidence_statements": [
                {
                    "excerpt": "Hypersonic propulsion research",
                    "source_location": "abstract",
                    "rationale_tag": "performance",
                }
            ],
            "generation_method": "automated",
            "assessed_at": datetime(2024, 1, 2, tzinfo=timezone.utc),
            "reviewer_notes": None,
        },
        {
            "assessment_id": str(uuid4()),
            "award_id": "NAV456",
            "taxonomy_version": "NSTC-2025Q1",
            "score": 61,
            "classification": "Medium",
            "primary_cet_id": "quantum_sensing",
            "supporting_cet_ids": [],
            "evidence_statements": [],
            "generation_method": "manual_review",
            "assessed_at": datetime(2024, 2, 4, tzinfo=timezone.utc),
            "reviewer_notes": "Awaiting abstract from vendor.",
        },
        {
            "assessment_id": str(uuid4()),
            "award_id": "AF789",
            "taxonomy_version": "NSTC-2025Q1",
            "score": 72,
            "classification": "High",
            "primary_cet_id": "thermal_protection",
            "supporting_cet_ids": ["hypersonics"],
            "evidence_statements": [],
            "generation_method": "automated",
            "assessed_at": datetime(2024, 3, 9, tzinfo=timezone.utc),
            "reviewer_notes": None,
        },
    ]
    taxonomy = [
        {"cet_id": "hypersonics", "name": "Hypersonics"},
        {"cet_id": "thermal_protection", "name": "Thermal Protection"},
        {"cet_id": "quantum_sensing", "name": "Quantum Sensing"},
    ]
    review_queue = [
        {
            "queue_id": str(uuid4()),
            "award_id": "NAV456",
            "reason": "missing_text",
            "status": "pending",
            "assigned_to": None,
            "opened_at": datetime(2024, 2, 5, tzinfo=timezone.utc),
            "due_by": datetime(2024, 3, 31, tzinfo=timezone.utc).date(),
            "resolved_at": None,
            "resolution_notes": None,
        }
    ]
    target_shares = {
        "hypersonics": 0.8,
        "quantum_sensing": 0.6,
        "thermal_protection": 0.4,
    }
    return AwardsService.from_records(
        awards=awards,
        assessments=assessments,
        taxonomy=taxonomy,
        review_queue=review_queue,
        target_shares=target_shares,
    )


@pytest.fixture()
def integration_context(monkeypatch):
    service = _build_awards_service()
    monkeypatch.setattr(
        api_router,
        "_awards_service",
        service,
        raising=False,
    )
    app = FastAPI()
    app.include_router(api_router.router, prefix="/api")
    client = TestClient(app)
    runner = CliRunner()
    return client, runner


def test_cli_and_api_award_list_align(integration_context):
    client, runner = integration_context

    cli_result = runner.invoke(
        cli_app,
        [
            "awards",
            "list",
            "--fiscal-year-start",
            "2023",
            "--fiscal-year-end",
            "2024",
            "--agency",
            "AF",
            "--agency",
            "NAVY",
            "--page",
            "1",
            "--page-size",
            "10",
        ],
    )

    assert cli_result.exit_code == 0
    cli_payload = json.loads(cli_result.stdout)
    assert any(award["dataIncomplete"] for award in cli_payload["awards"])

    api_response = client.get(
        "/api/applicability/awards",
        params={
            "fiscal_year_start": 2023,
            "fiscal_year_end": 2024,
            "agencies": ["AF", "NAVY"],
            "page": 1,
            "page_size": 10,
        },
    )

    assert api_response.status_code == 200
    api_payload = api_response.json()
    assert {award["awardId"] for award in api_payload["awards"]} == {
        award["awardId"] for award in cli_payload["awards"]
    }


def test_award_detail_and_cet_gap_flow(integration_context):
    client, runner = integration_context

    detail_result = runner.invoke(cli_app, ["awards", "show", "--award-id", "NAV456"])
    assert detail_result.exit_code == 0
    detail_payload = json.loads(detail_result.stdout)
    assert detail_payload["award"]["dataIncomplete"] is True
    assert detail_payload["reviewQueue"]["status"] == "pending"

    cet_response = client.get(
        "/api/applicability/cet/hypersonics",
        params={
            "fiscal_year_start": 2023,
            "fiscal_year_end": 2024,
            "agencies": ["AF", "NAVY"],
        },
    )

    assert cet_response.status_code == 200
    cet_payload = cet_response.json()
    assert cet_payload["summary"]["cetId"] == "hypersonics"
    assert cet_payload["gaps"][0]["metric"] == "share_vs_target"
    assert cet_payload["representativeAwards"][0]["awardId"] in {"AF123", "AF789"}
