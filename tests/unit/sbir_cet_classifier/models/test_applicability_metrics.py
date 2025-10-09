from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from sbir_cet_classifier.common.config import AppConfig, StoragePaths
from sbir_cet_classifier.common.schemas import ApplicabilityAssessment, EvidenceStatement
from sbir_cet_classifier.models.applicability_metrics import compute_metrics, write_metrics


def _build_assessment(method: str) -> ApplicabilityAssessment:
    return ApplicabilityAssessment(
        assessment_id=uuid4(),
        award_id="AF123",
        taxonomy_version="NSTC-2025Q1",
        score=85,
        classification="High",
        primary_cet_id="hypersonics",
        supporting_cet_ids=["quantum_sensing"],
        evidence_statements=[
            EvidenceStatement(
                excerpt="Hypersonic propulsion research",
                source_location="abstract",
                rationale_tag="performance",
            )
        ],
        generation_method=method,
        assessed_at=datetime.utcnow(),
        reviewer_notes=None,
    )


def _config(tmp_path):
    storage = StoragePaths(
        raw=tmp_path / "raw",
        processed=tmp_path / "processed",
        artifacts=tmp_path / "artifacts",
    )
    for path in (storage.raw, storage.processed, storage.artifacts):
        path.mkdir(parents=True, exist_ok=True)
    return AppConfig(storage=storage)


def test_compute_and_write_metrics(tmp_path):
    assessments = [_build_assessment("automated"), _build_assessment("manual_review")]
    metrics = compute_metrics(2023, assessments)
    assert metrics.total_awards == 2
    assert metrics.automated == 1
    assert metrics.percentage_automated == 50.0

    config = _config(tmp_path)
    path = write_metrics(metrics, config=config)
    assert path.exists()
    contents = path.read_text()
    assert "percentage_automated" in contents
