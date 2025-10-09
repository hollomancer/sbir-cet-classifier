from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from sbir_cet_classifier.api import router as router_module


class StubAwardsService:
    def __init__(self) -> None:
        self.list_response = {
            "pagination": {
                "page": 1,
                "pageSize": 25,
                "totalPages": 1,
                "totalRecords": 2,
            },
            "awards": [
                {
                    "awardId": "AF123",
                    "title": "Hypersonic Flight Control",
                    "agency": "AF",
                    "phase": "I",
                    "score": 88,
                    "classification": "High",
                    "dataIncomplete": False,
                    "primaryCet": {
                        "cetId": "hypersonics",
                        "name": "Hypersonics",
                        "taxonomyVersion": "NSTC-2025Q1",
                    },
                    "supportingCet": [
                        {
                            "cetId": "thermal_protection",
                            "name": "Thermal Protection",
                            "taxonomyVersion": "NSTC-2025Q1",
                        }
                    ],
                    "evidence": [
                        {
                            "excerpt": "Hypersonic propulsion research",
                            "sourceLocation": "abstract",
                            "rationaleTag": "performance",
                        }
                    ],
                },
                {
                    "awardId": "NAV456",
                    "title": "Quantum Navigation Suite",
                    "agency": "NAVY",
                    "phase": "II",
                    "score": 62,
                    "classification": "Medium",
                    "dataIncomplete": True,
                    "primaryCet": {
                        "cetId": "quantum_sensing",
                        "name": "Quantum Sensing",
                        "taxonomyVersion": "NSTC-2025Q1",
                    },
                    "supportingCet": [],
                    "evidence": [],
                },
            ],
        }
        assessment_id = str(uuid4())
        self.detail_response = {
            "award": {
                "awardId": "AF123",
                "title": "Hypersonic Flight Control",
                "abstract": "Propulsion advances for hypersonic flight control surfaces.",
                "keywords": ["hypersonic", "propulsion"],
                "agency": "AF",
                "phase": "I",
                "obligatedUsd": 150000,
                "awardDate": "2023-06-01",
                "taxonomyVersion": "NSTC-2025Q1",
                "dataIncomplete": False,
            },
            "assessments": [
                {
                    "assessmentId": assessment_id,
                    "assessedAt": datetime(2024, 1, 2, tzinfo=timezone.utc).isoformat(),
                    "score": 88,
                    "classification": "High",
                    "primaryCet": {
                        "cetId": "hypersonics",
                        "name": "Hypersonics",
                        "taxonomyVersion": "NSTC-2025Q1",
                    },
                    "supportingCet": [
                        {
                            "cetId": "thermal_protection",
                            "name": "Thermal Protection",
                            "taxonomyVersion": "NSTC-2025Q1",
                        }
                    ],
                    "evidence": [
                        {
                            "excerpt": "Hypersonic propulsion research",
                            "sourceLocation": "abstract",
                            "rationaleTag": "performance",
                        }
                    ],
                    "generationMethod": "automated",
                    "reviewerNotes": None,
                }
            ],
            "reviewQueue": None,
        }
        self.cet_response = {
            "cet": {
                "cetId": "hypersonics",
                "name": "Hypersonics",
                "taxonomyVersion": "NSTC-2025Q1",
            },
            "summary": {
                "cetId": "hypersonics",
                "name": "Hypersonics",
                "awards": 1,
                "obligatedUsd": 150000.0,
                "share": 66.67,
                "topAwardId": "AF123",
                "applicabilityBreakdown": {"high": 1, "medium": 0, "low": 0},
            },
            "representativeAwards": self.list_response["awards"][:1],
            "gaps": [
                {
                    "metric": "share_vs_target",
                    "currentValue": 66.67,
                    "targetValue": 80.0,
                    "narrative": "Hypersonics coverage trails the 80% target for this filter set.",
                }
            ],
        }

    # The router under test will call these methods; we return static payloads
    def list_awards(self, filters) -> dict:
        self.last_filters = filters
        return self.list_response

    def get_award_detail(self, award_id: str) -> dict:
        if award_id != "AF123":
            raise KeyError(award_id)
        return self.detail_response

    def get_cet_detail(self, cet_id: str, filters) -> dict:
        if cet_id != "hypersonics":
            raise KeyError(cet_id)
        return self.cet_response


@pytest.fixture()
def api_client(monkeypatch):
    stub_service = StubAwardsService()
    monkeypatch.setattr(
        router_module,
        "_awards_service",
        stub_service,
        raising=False,
    )
    app = FastAPI()
    app.include_router(router_module.router, prefix="/api")
    client = TestClient(app)
    return client, stub_service


def test_list_awards_returns_paginated_payload(api_client):
    client, _ = api_client

    response = client.get(
        "/api/applicability/awards",
        params={
            "fiscal_year_start": 2023,
            "fiscal_year_end": 2023,
            "agencies": ["AF", "NAVY"],
            "page": 1,
            "page_size": 25,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["pagination"]["totalRecords"] == 2
    first_award = payload["awards"][0]
    assert first_award["awardId"] == "AF123"
    assert first_award["primaryCet"]["cetId"] == "hypersonics"
    assert first_award["supportingCet"][0]["name"] == "Thermal Protection"
    assert first_award["evidence"][0]["sourceLocation"] == "abstract"
    assert first_award["dataIncomplete"] is False


def test_get_award_detail_returns_assessments(api_client):
    client, _ = api_client

    response = client.get("/api/applicability/awards/AF123")

    assert response.status_code == 200
    payload = response.json()
    assert payload["award"]["awardId"] == "AF123"
    assert payload["award"]["taxonomyVersion"] == "NSTC-2025Q1"
    assert payload["assessments"][0]["classification"] == "High"
    assert payload["assessments"][0]["supportingCet"][0]["cetId"] == "thermal_protection"
    assert payload["reviewQueue"] is None


def test_get_cet_detail_returns_gap_payload(api_client):
    client, _ = api_client

    response = client.get(
        "/api/applicability/cet/hypersonics",
        params={
            "fiscal_year_start": 2023,
            "fiscal_year_end": 2023,
            "agencies": ["AF"],
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["cet"]["cetId"] == "hypersonics"
    assert payload["summary"]["share"] == pytest.approx(66.67, rel=1e-3)
    assert payload["representativeAwards"][0]["awardId"] == "AF123"
    assert payload["gaps"][0]["metric"] == "share_vs_target"


def test_get_award_detail_missing_award_returns_404(api_client):
    client, _ = api_client

    response = client.get("/api/applicability/awards/UNKNOWN")

    assert response.status_code == 404
