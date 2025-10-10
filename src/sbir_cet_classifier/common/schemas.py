"""Pydantic domain schemas shared across the application."""

from __future__ import annotations

from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, ValidationError, field_validator, model_validator


class Award(BaseModel):
    """Canonical SBIR award record used throughout the pipeline."""

    award_id: str = Field(min_length=1)
    agency: str = Field(min_length=1, max_length=32)
    sub_agency: str | None = Field(default=None, max_length=64)
    topic_code: str = Field(min_length=1, max_length=64)
    abstract: str | None = None
    keywords: list[str] = Field(default_factory=list)
    phase: Literal["I", "II", "III", "Other"]
    firm_name: str = Field(min_length=1)
    firm_city: str = Field(min_length=1)
    firm_state: str = Field(min_length=2, max_length=2)
    award_amount: float = Field(ge=0)
    award_date: date
    is_export_controlled: bool = False
    source_version: str = Field(min_length=1)
    ingested_at: datetime
    program: str | None = None
    solicitation_id: str | None = None
    solicitation_year: int | None = None

    @field_validator("keywords", mode="before")
    @classmethod
    def _normalise_keywords(cls, value: list[str] | str | None) -> list[str]:
        if value is None:
            return []
        if isinstance(value, str):
            tokens = [token.strip() for token in value.split(";")]
        else:
            tokens = [token.strip() for token in value]
        return [token for token in tokens if token]


class CETArea(BaseModel):
    """Critical or emerging technology taxonomy entry."""

    cet_id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    definition: str
    parent_cet_id: str | None = None
    version: str = Field(min_length=1)
    effective_date: date
    retired_date: date | None = None
    status: Literal["active", "retired"] = "active"

    @model_validator(mode="after")
    def _validate_dates(self) -> "CETArea":
        if self.retired_date and self.retired_date < self.effective_date:
            raise ValidationError("retired_date must be >= effective_date")
        return self


class EvidenceStatement(BaseModel):
    """Summarised rationale for CET alignment."""

    excerpt: str = Field(min_length=1)
    source_location: Literal["abstract", "keywords", "solicitation", "reviewer_notes"]
    rationale_tag: str = Field(min_length=1)

    @field_validator("excerpt")
    @classmethod
    def _limit_word_count(cls, value: str) -> str:
        word_count = len(value.split())
        if word_count > 50:
            raise ValueError("Evidence excerpts must be 50 words or fewer")
        return value


class ApplicabilityAssessment(BaseModel):
    """Model output linking an SBIR award to CET areas."""

    assessment_id: UUID
    award_id: str
    taxonomy_version: str
    score: int = Field(ge=0, le=100)
    classification: Literal["High", "Medium", "Low"]
    primary_cet_id: str
    supporting_cet_ids: list[str] = Field(default_factory=list)
    evidence_statements: list[EvidenceStatement] = Field(default_factory=list, max_length=3)
    generation_method: Literal["automated", "manual_review"]
    assessed_at: datetime
    reviewer_notes: str | None = None

    @model_validator(mode="after")
    def _validate_supporting(self) -> "ApplicabilityAssessment":
        if self.primary_cet_id in self.supporting_cet_ids:
            raise ValueError("supporting_cet_ids cannot include the primary_cet_id")
        if len(set(self.supporting_cet_ids)) != len(self.supporting_cet_ids):
            raise ValueError("supporting_cet_ids must be unique")
        if len(self.supporting_cet_ids) > 3:
            raise ValueError("supporting_cet_ids cannot exceed three entries")
        return self


class ReviewQueueItem(BaseModel):
    """Represents an award awaiting manual review or escalation."""

    queue_id: UUID
    award_id: str
    reason: Literal["missing_text", "low_confidence", "controlled_data", "conflict"]
    status: Literal["pending", "in_review", "resolved", "escalated"] = "pending"
    assigned_to: str | None = None
    opened_at: datetime
    due_by: date
    resolved_at: datetime | None = None
    resolution_notes: str | None = None

    @model_validator(mode="after")
    def _validate_dates(self) -> "ReviewQueueItem":
        if self.resolved_at and self.resolved_at.date() < self.opened_at.date():
            raise ValueError("resolved_at cannot precede opened_at")
        return self


__all__ = [
    "ApplicabilityAssessment",
    "Award",
    "CETArea",
    "EvidenceStatement",
    "ReviewQueueItem",
]
