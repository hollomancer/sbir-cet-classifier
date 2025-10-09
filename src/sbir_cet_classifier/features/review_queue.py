"""Repository for managing manual review queue items."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Iterable, Iterator
from uuid import UUID, uuid4

from sbir_cet_classifier.common.config import AppConfig, load_config
from sbir_cet_classifier.common.schemas import ReviewQueueItem

QUEUE_FILENAME = "review_queue.jsonl"


@dataclass
class QueueRepository:
    storage_path: Path

    def __post_init__(self) -> None:
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.storage_path.exists():
            self.storage_path.write_text("")

    @classmethod
    def from_config(cls, config: AppConfig | None = None) -> "QueueRepository":
        app_config = config or load_config()
        return cls(app_config.storage.artifacts / QUEUE_FILENAME)

    def _load_items(self) -> list[ReviewQueueItem]:
        items: list[ReviewQueueItem] = []
        with self.storage_path.open("r", encoding="utf-8") as fh:
            for line in fh:
                if line.strip():
                    payload = json.loads(line)
                    items.append(ReviewQueueItem(**payload))
        return items

    def _write_items(self, items: Iterable[ReviewQueueItem]) -> None:
        with self.storage_path.open("w", encoding="utf-8") as fh:
            for item in items:
                fh.write(json.dumps(item.model_dump(), default=str))
                fh.write("\n")

    def all(self) -> list[ReviewQueueItem]:
        return self._load_items()

    def enqueue(
        self,
        award_id: str,
        reason: ReviewQueueItem.reason.__value_type__,
        *,
        due_by: date,
        assigned_to: str | None = None,
    ) -> ReviewQueueItem:
        item = ReviewQueueItem(
            queue_id=uuid4(),
            award_id=award_id,
            reason=reason,
            status="pending",
            assigned_to=assigned_to,
            opened_at=datetime.utcnow(),
            due_by=due_by,
        )
        items = self._load_items()
        items.append(item)
        self._write_items(items)
        return item

    def update_status(
        self,
        queue_id: UUID,
        *,
        status: ReviewQueueItem.status.__value_type__,
        resolution_notes: str | None = None,
    ) -> ReviewQueueItem:
        items = self._load_items()
        updated: list[ReviewQueueItem] = []
        target: ReviewQueueItem | None = None
        for item in items:
            if item.queue_id == queue_id:
                target = item.model_copy(update={
                    "status": status,
                    "resolution_notes": resolution_notes or item.resolution_notes,
                    "resolved_at": datetime.utcnow() if status in {"resolved", "escalated"} else item.resolved_at,
                })
                updated.append(target)
            else:
                updated.append(item)
        if target is None:
            raise KeyError(f"Queue item {queue_id} not found")
        self._write_items(updated)
        return target

    def overdue(self, reference: date | None = None) -> list[ReviewQueueItem]:
        ref = reference or date.today()
        return [
            item
            for item in self._load_items()
            if item.due_by < ref and item.status not in {"resolved"}
        ]

    def pending(self) -> Iterator[ReviewQueueItem]:
        return (item for item in self._load_items() if item.status == "pending")


__all__ = ["QueueRepository", "QUEUE_FILENAME"]
