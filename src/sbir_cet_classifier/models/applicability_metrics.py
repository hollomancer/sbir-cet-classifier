"""Utilities for computing classification coverage metrics."""

from __future__ import annotations

import json
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from sbir_cet_classifier.common.config import AppConfig, load_config
from sbir_cet_classifier.common.schemas import ApplicabilityAssessment

COVERAGE_FILENAME = "coverage.json"


@dataclass(frozen=True)
class CoverageMetrics:
    fiscal_year: int
    total_awards: int
    automated: int
    manual: int
    percentage_automated: float
    generated_at: datetime

    def as_dict(self) -> dict:
        return {
            "fiscal_year": self.fiscal_year,
            "total_awards": self.total_awards,
            "automated": self.automated,
            "manual": self.manual,
            "percentage_automated": self.percentage_automated,
            "generated_at": self.generated_at.isoformat(),
        }


def compute_metrics(
    fiscal_year: int,
    assessments: Iterable[ApplicabilityAssessment],
) -> CoverageMetrics:
    assessments = list(assessments)
    total = len(assessments)
    automated = sum(1 for assessment in assessments if assessment.generation_method == "automated")
    manual = total - automated
    percentage = (automated / total * 100) if total else 0.0
    return CoverageMetrics(
        fiscal_year=fiscal_year,
        total_awards=total,
        automated=automated,
        manual=manual,
        percentage_automated=round(percentage, 2),
        generated_at=datetime.now(UTC),
    )


def write_metrics(metrics: CoverageMetrics, *, config: AppConfig | None = None) -> Path:
    app_config = config or load_config()
    output_path = app_config.storage.artifacts / COVERAGE_FILENAME
    output_path.parent.mkdir(parents=True, exist_ok=True)
    existing: list[dict] = []
    if output_path.exists():
        existing = json.loads(output_path.read_text())
    existing = [entry for entry in existing if entry.get("fiscal_year") != metrics.fiscal_year]
    existing.append(metrics.as_dict())
    output_path.write_text(json.dumps(existing, indent=2))
    return output_path


__all__ = ["COVERAGE_FILENAME", "CoverageMetrics", "compute_metrics", "write_metrics"]
