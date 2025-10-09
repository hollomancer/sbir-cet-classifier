from __future__ import annotations

from datetime import date, timedelta

from sbir_cet_classifier.common.config import AppConfig, StoragePaths
from sbir_cet_classifier.features.review_queue import QueueRepository


def _config(tmp_path):
    storage = StoragePaths(
        raw=tmp_path / "raw",
        processed=tmp_path / "processed",
        artifacts=tmp_path / "artifacts",
    )
    for path in (storage.raw, storage.processed, storage.artifacts):
        path.mkdir(parents=True, exist_ok=True)
    return AppConfig(storage=storage)


def test_enqueue_and_overdue(tmp_path):
    repo = QueueRepository.from_config(_config(tmp_path))
    item = repo.enqueue(
        award_id="AF123",
        reason="missing_text",
        due_by=date.today(),
    )

    assert item.status == "pending"
    assert list(repo.pending())

    overdue = repo.overdue(reference=date.today() + timedelta(days=1))
    assert {entry.queue_id for entry in overdue} == {item.queue_id}


def test_update_status(tmp_path):
    repo = QueueRepository.from_config(_config(tmp_path))
    item = repo.enqueue(
        award_id="AF123",
        reason="low_confidence",
        due_by=date.today() + timedelta(days=5),
    )

    updated = repo.update_status(item.queue_id, status="in_review")
    assert updated.status == "in_review"

    resolved = repo.update_status(item.queue_id, status="resolved", resolution_notes="Reviewed")
    assert resolved.status == "resolved"
    assert resolved.resolution_notes == "Reviewed"
