"""Award drill-down services for CET applicability workflows."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime
from typing import Iterable, Mapping, Sequence

import pandas as pd

from sbir_cet_classifier.features.gaps import GapAnalytics, GapInsight


@dataclass(frozen=True)
class AwardsFilters:
    fiscal_year_start: int
    fiscal_year_end: int
    agencies: tuple[str, ...] = ()
    phases: tuple[str, ...] = ()
    cet_areas: tuple[str, ...] = ()
    location_states: tuple[str, ...] = ()
    page: int = 1
    page_size: int = 25


@dataclass(frozen=True)
class Pagination:
    page: int
    page_size: int
    total_pages: int
    total_records: int

    def as_dict(self) -> dict:
        return {
            "page": self.page,
            "pageSize": self.page_size,
            "totalPages": self.total_pages,
            "totalRecords": self.total_records,
        }


@dataclass(frozen=True)
class CetRef:
    cet_id: str
    name: str
    taxonomy_version: str | None

    def as_dict(self) -> dict:
        return {
            "cetId": self.cet_id,
            "name": self.name,
            "taxonomyVersion": self.taxonomy_version,
        }


@dataclass(frozen=True)
class AwardListItem:
    award_id: str
    title: str
    agency: str
    phase: str
    score: int
    classification: str
    data_incomplete: bool
    primary_cet: CetRef
    supporting_cet: list[CetRef]
    evidence: list[dict]

    def as_dict(self) -> dict:
        return {
            "awardId": self.award_id,
            "title": self.title,
            "agency": self.agency,
            "phase": self.phase,
            "score": self.score,
            "classification": self.classification,
            "dataIncomplete": self.data_incomplete,
            "primaryCet": self.primary_cet.as_dict(),
            "supportingCet": [ref.as_dict() for ref in self.supporting_cet],
            "evidence": self.evidence,
        }


@dataclass(frozen=True)
class AwardListResponse:
    pagination: Pagination
    awards: list[AwardListItem]

    def as_dict(self) -> dict:
        return {
            "pagination": self.pagination.as_dict(),
            "awards": [award.as_dict() for award in self.awards],
        }


@dataclass(frozen=True)
class ReviewQueueSnapshot:
    queue_id: str
    award_id: str
    reason: str
    status: str
    opened_at: datetime
    due_by: date
    assigned_to: str | None
    resolved_at: datetime | None
    resolution_notes: str | None

    def as_dict(self) -> dict:
        return {
            "queueId": self.queue_id,
            "awardId": self.award_id,
            "reason": self.reason,
            "status": self.status,
            "openedAt": self.opened_at.isoformat(),
            "dueBy": self.due_by.isoformat(),
            "assignedTo": self.assigned_to,
            "resolvedAt": self.resolved_at.isoformat() if self.resolved_at else None,
            "resolutionNotes": self.resolution_notes,
        }


@dataclass(frozen=True)
class AwardCore:
    award_id: str
    title: str
    abstract: str | None
    keywords: list[str]
    agency: str
    phase: str
    obligated_usd: float
    award_date: date | None
    taxonomy_version: str | None
    data_incomplete: bool

    def as_dict(self) -> dict:
        return {
            "awardId": self.award_id,
            "title": self.title,
            "abstract": self.abstract,
            "keywords": self.keywords,
            "agency": self.agency,
            "phase": self.phase,
            "obligatedUsd": round(self.obligated_usd, 2),
            "awardDate": self.award_date.isoformat() if self.award_date else None,
            "taxonomyVersion": self.taxonomy_version,
            "dataIncomplete": self.data_incomplete,
        }


@dataclass(frozen=True)
class AssessmentRecord:
    assessment_id: str
    assessed_at: datetime | None
    score: int
    classification: str
    primary_cet: CetRef
    supporting_cet: list[CetRef]
    evidence: list[dict]
    generation_method: str
    reviewer_notes: str | None

    def as_dict(self) -> dict:
        return {
            "assessmentId": self.assessment_id,
            "assessedAt": self.assessed_at.isoformat() if self.assessed_at else None,
            "score": self.score,
            "classification": self.classification,
            "primaryCet": self.primary_cet.as_dict(),
            "supportingCet": [ref.as_dict() for ref in self.supporting_cet],
            "evidence": self.evidence,
            "generationMethod": self.generation_method,
            "reviewerNotes": self.reviewer_notes,
        }


@dataclass(frozen=True)
class AwardDetail:
    award: AwardCore
    assessments: list[AssessmentRecord]
    review_queue: ReviewQueueSnapshot | None

    def as_dict(self) -> dict:
        return {
            "award": self.award.as_dict(),
            "assessments": [assessment.as_dict() for assessment in self.assessments],
            "reviewQueue": self.review_queue.as_dict() if self.review_queue else None,
        }


@dataclass(frozen=True)
class CetSummary:
    cet_id: str
    name: str
    awards: int
    obligated_usd: float
    share: float
    top_award_id: str | None
    applicability_breakdown: dict[str, int]

    def as_dict(self) -> dict:
        return {
            "cetId": self.cet_id,
            "name": self.name,
            "awards": self.awards,
            "obligatedUsd": round(self.obligated_usd, 2),
            "share": round(self.share, 2),
            "topAwardId": self.top_award_id,
            "applicabilityBreakdown": self.applicability_breakdown,
        }


@dataclass(frozen=True)
class CetDetail:
    cet: CetRef
    summary: CetSummary
    representative_awards: list[AwardListItem]
    gaps: list[GapInsight]

    def as_dict(self) -> dict:
        return {
            "cet": self.cet.as_dict(),
            "summary": self.summary.as_dict(),
            "representativeAwards": [award.as_dict() for award in self.representative_awards],
            "gaps": [gap.as_dict() for gap in self.gaps],
        }


class AwardsService:
    """Provides drill-down information for CET-aligned awards."""

    def __init__(
        self,
        awards: pd.DataFrame,
        assessments: pd.DataFrame,
        taxonomy: pd.DataFrame,
        review_queue: pd.DataFrame,
        *,
        target_shares: Mapping[str, float] | None = None,
    ) -> None:
        self._awards = awards.copy()
        if "fiscal_year" not in self._awards.columns and "award_date" in self._awards.columns:
            self._awards["fiscal_year"] = pd.to_datetime(
                self._awards["award_date"], errors="coerce"
            ).dt.year
        if "award_date" in self._awards.columns:
            self._awards["award_date"] = pd.to_datetime(
                self._awards["award_date"], errors="coerce"
            ).dt.date
        else:
            self._awards["award_date"] = pd.Series([None] * len(self._awards))
        if "keywords" in self._awards.columns:
            self._awards["keywords"] = self._awards["keywords"].apply(self._normalise_keywords)
        else:
            self._awards["keywords"] = [[] for _ in range(len(self._awards))]

        self._assessments = assessments.copy()
        if not self._assessments.empty and "assessed_at" in self._assessments.columns:
            self._assessments["assessed_at"] = pd.to_datetime(
                self._assessments["assessed_at"], errors="coerce", utc=True
            )

        self._taxonomy = taxonomy.copy()
        self._taxonomy_map = self._taxonomy.set_index("cet_id")["name"].to_dict()

        self._review_queue = review_queue.copy()
        if not self._review_queue.empty:
            for column in ("opened_at", "resolved_at"):
                if column in self._review_queue.columns:
                    self._review_queue[column] = pd.to_datetime(
                        self._review_queue[column], errors="coerce", utc=True
                    )
            if "due_by" in self._review_queue.columns:
                self._review_queue["due_by"] = pd.to_datetime(
                    self._review_queue["due_by"], errors="coerce"
                ).dt.date

        self._gap_analytics = GapAnalytics(target_shares or {})

    @classmethod
    def from_records(
        cls,
        *,
        awards: Sequence[dict],
        assessments: Iterable[dict],
        taxonomy: Sequence[dict],
        review_queue: Iterable[dict],
        target_shares: Mapping[str, float] | None = None,
    ) -> "AwardsService":
        awards_df = pd.DataFrame(list(awards)) if awards else pd.DataFrame()
        assessments_df = pd.DataFrame(list(assessments)) if assessments else pd.DataFrame()
        taxonomy_df = pd.DataFrame(list(taxonomy)) if taxonomy else pd.DataFrame()
        review_queue_df = pd.DataFrame(list(review_queue)) if review_queue else pd.DataFrame()
        return cls(
            awards=awards_df,
            assessments=assessments_df,
            taxonomy=taxonomy_df,
            review_queue=review_queue_df,
            target_shares=target_shares,
        )

    # --------------------------------------------------------------------- helpers
    @staticmethod
    def _normalise_keywords(value) -> list[str]:
        if value is None:
            return []
        if isinstance(value, str):
            return [token.strip() for token in value.split(";") if token.strip()]
        return [str(token).strip() for token in value if str(token).strip()]

    def _latest_assessments(self) -> pd.DataFrame:
        if self._assessments.empty:
            return self._assessments
        ordered = self._assessments.sort_values("assessed_at")
        return ordered.drop_duplicates("award_id", keep="last")

    def _review_queue_map(self) -> dict[str, ReviewQueueSnapshot]:
        if self._review_queue.empty:
            return {}
        snapshots: dict[str, ReviewQueueSnapshot] = {}
        now = datetime.now(tz=UTC)
        today = now.date()
        for _, row in self._review_queue.iterrows():
            status = row.get("status")
            due_by = row.get("due_by")
            if status in {"resolved"}:
                continue
            if due_by and status in {"pending", "in_review"} and due_by < today:
                status = "escalated"
            opened_at = row.get("opened_at")
            resolved_at = row.get("resolved_at")
            snapshot = ReviewQueueSnapshot(
                queue_id=str(row.get("queue_id")),
                award_id=row.get("award_id"),
                reason=row.get("reason"),
                status=status,
                opened_at=opened_at.to_pydatetime() if pd.notna(opened_at) else now,
                due_by=due_by or today,
                assigned_to=row.get("assigned_to"),
                resolved_at=resolved_at.to_pydatetime() if pd.notna(resolved_at) else None,
                resolution_notes=row.get("resolution_notes"),
            )
            snapshots[snapshot.award_id] = snapshot
        return snapshots

    def _apply_filters(self, filters: AwardsFilters) -> pd.DataFrame:
        df = self._awards.copy()
        df = df[(df["fiscal_year"] >= filters.fiscal_year_start) & (df["fiscal_year"] <= filters.fiscal_year_end)]
        if filters.agencies:
            df = df[df["agency"].isin(filters.agencies)]
        if filters.phases:
            df = df[df["phase"].isin(filters.phases)]
        if filters.location_states:
            df = df[df["firm_state"].isin(filters.location_states)]

        latest = self._latest_assessments()
        merged = df.merge(
            latest,
            on="award_id",
            how="left",
            suffixes=("", "_assessment"),
        )
        if filters.cet_areas:
            merged = merged[merged["primary_cet_id"].isin(filters.cet_areas)]
        if "score" in merged.columns:
            merged["score"] = pd.to_numeric(merged["score"], errors="coerce").fillna(-1)
        else:
            merged["score"] = -1
        review_map = self._review_queue_map()
        merged["review_queue"] = merged["award_id"].map(review_map)
        merged["data_incomplete"] = merged.apply(self._compute_data_incomplete, axis=1)
        return merged

    @staticmethod
    def _compute_data_incomplete(row) -> bool:
        abstract = row.get("abstract")
        keywords = row.get("keywords") or []
        has_text = bool(abstract and abstract.strip()) and bool(keywords)
        queue: ReviewQueueSnapshot | None = row.get("review_queue")
        queue_pending = queue is not None and queue.status in {"pending", "in_review", "escalated"}
        return (not has_text) or queue_pending

    def _build_cet_ref(self, cet_id: str | None, taxonomy_version: str | None) -> CetRef:
        if cet_id is None:
            return CetRef(cet_id="", name="", taxonomy_version=taxonomy_version)
        name = self._taxonomy_map.get(cet_id, cet_id)
        return CetRef(cet_id=cet_id, name=name, taxonomy_version=taxonomy_version)

    def _build_supporting_refs(self, supporting_ids: Iterable[str], taxonomy_version: str | None) -> list[CetRef]:
        return [self._build_cet_ref(cet_id, taxonomy_version) for cet_id in supporting_ids]

    def _build_award_item(self, row) -> AwardListItem:
        primary_ref = self._build_cet_ref(row.get("primary_cet_id"), row.get("taxonomy_version"))
        supporting = self._build_supporting_refs(row.get("supporting_cet_ids") or [], row.get("taxonomy_version"))
        evidence = row.get("evidence_statements") or []
        return AwardListItem(
            award_id=row["award_id"],
            title=row.get("title", row["award_id"]),
            agency=row.get("agency", ""),
            phase=row.get("phase", ""),
            score=int(round(row.get("score", 0))),
            classification=row.get("classification", "Low"),
            data_incomplete=bool(row.get("data_incomplete")),
            primary_cet=primary_ref,
            supporting_cet=supporting,
            evidence=evidence,
        )

    def _build_award_core(self, row) -> AwardCore:
        return AwardCore(
            award_id=row["award_id"],
            title=row.get("title", row["award_id"]),
            abstract=row.get("abstract"),
            keywords=row.get("keywords") or [],
            agency=row.get("agency", ""),
            phase=row.get("phase", ""),
            obligated_usd=float(row.get("award_amount", 0.0) or 0.0),
            award_date=row.get("award_date"),
            taxonomy_version=row.get("taxonomy_version"),
            data_incomplete=bool(row.get("data_incomplete")),
        )

    def _build_assessment_records(self, award_id: str) -> list[AssessmentRecord]:
        subset = self._assessments[self._assessments["award_id"] == award_id]
        if subset.empty:
            return []
        subset = subset.sort_values("assessed_at", ascending=False)
        records: list[AssessmentRecord] = []
        for _, row in subset.iterrows():
            taxonomy_version = row.get("taxonomy_version")
            primary_ref = self._build_cet_ref(row.get("primary_cet_id"), taxonomy_version)
            supporting_refs = self._build_supporting_refs(row.get("supporting_cet_ids") or [], taxonomy_version)
            assessed_at = row.get("assessed_at")
            assessed_dt = assessed_at.to_pydatetime().astimezone(UTC) if pd.notna(assessed_at) else None
            records.append(
                AssessmentRecord(
                    assessment_id=row.get("assessment_id"),
                    assessed_at=assessed_dt,
                    score=int(row.get("score", 0)),
                    classification=row.get("classification", "Low"),
                    primary_cet=primary_ref,
                    supporting_cet=supporting_refs,
                    evidence=row.get("evidence_statements") or [],
                    generation_method=row.get("generation_method", "automated"),
                    reviewer_notes=row.get("reviewer_notes"),
                )
            )
        return records

    # ---------------------------------------------------------------- public API
    def list_awards(self, filters: AwardsFilters) -> AwardListResponse:
        filtered = self._apply_filters(filters)
        if filtered.empty:
            pagination = Pagination(page=filters.page, page_size=filters.page_size, total_pages=0, total_records=0)
            return AwardListResponse(pagination=pagination, awards=[])

        total_records = len(filtered)
        total_pages = max(1, (total_records + filters.page_size - 1) // filters.page_size)
        start = (filters.page - 1) * filters.page_size
        end = start + filters.page_size
        sorted_frame = filtered.sort_values(
            by=["score", "award_amount", "award_date"],
            ascending=[False, False, False],
            na_position="last",
        )
        page_frame = sorted_frame.iloc[start:end]
        items = [self._build_award_item(row) for _, row in page_frame.iterrows()]
        pagination = Pagination(
            page=filters.page,
            page_size=filters.page_size,
            total_pages=total_pages,
            total_records=total_records,
        )
        return AwardListResponse(pagination=pagination, awards=items)

    def get_award_detail(self, award_id: str) -> AwardDetail:
        filtered = self._awards[self._awards["award_id"] == award_id]
        if filtered.empty:
            raise KeyError(award_id)

        latest = self._apply_filters(
            AwardsFilters(
                fiscal_year_start=int(filtered["fiscal_year"].min()),
                fiscal_year_end=int(filtered["fiscal_year"].max()),
                page=1,
                page_size=10,
            )
        )
        row = latest[latest["award_id"] == award_id]
        if row.empty:
            row = filtered
            row["data_incomplete"] = True
            row["taxonomy_version"] = None
        record = row.iloc[0]
        award = self._build_award_core(record)
        assessments = self._build_assessment_records(award_id)
        review_queue_map = self._review_queue_map()
        detail = AwardDetail(
            award=award,
            assessments=assessments,
            review_queue=review_queue_map.get(award_id),
        )
        return detail

    def get_cet_detail(self, cet_id: str, filters: AwardsFilters) -> CetDetail:
        filtered = self._apply_filters(filters)
        if filtered.empty:
            raise KeyError(cet_id)

        total_awards = len(filtered)
        taxonomy_version = filtered["taxonomy_version"].mode().iat[0] if "taxonomy_version" in filtered else None
        centroid = filtered[filtered["primary_cet_id"] == cet_id]
        if centroid.empty:
            raise KeyError(cet_id)

        awards_count = len(centroid)
        obligated_usd = float(centroid.get("award_amount", 0).sum())
        share = (awards_count / total_awards) * 100 if total_awards else 0.0
        breakdown = centroid["classification"].value_counts().to_dict()
        for band in ("High", "Medium", "Low"):
            breakdown.setdefault(band.lower(), breakdown.get(band.lower(), 0))
        breakdown = {
            "high": int(centroid[centroid["classification"] == "High"].shape[0]),
            "medium": int(centroid[centroid["classification"] == "Medium"].shape[0]),
            "low": int(centroid[centroid["classification"] == "Low"].shape[0]),
        }

        sorted_centroid = centroid.sort_values(
            by=["score", "award_amount", "award_date"],
            ascending=[False, False, False],
            na_position="last",
        )
        top_award_id = sorted_centroid.iloc[0]["award_id"] if not sorted_centroid.empty else None
        representative_awards = [
            self._build_award_item(row) for _, row in sorted_centroid.head(3).iterrows()
        ]

        pending_reviews = int(sorted_centroid["data_incomplete"].sum())
        gaps: list[GapInsight] = [
            self._gap_analytics.share_gap(cet_id=cet_id, share_percent=share),
        ]
        manual_gap = self._gap_analytics.manual_review_gap(cet_id=cet_id, pending_reviews=pending_reviews)
        if manual_gap:
            gaps.append(manual_gap)

        summary = CetSummary(
            cet_id=cet_id,
            name=self._taxonomy_map.get(cet_id, cet_id),
            awards=awards_count,
            obligated_usd=obligated_usd,
            share=share,
            top_award_id=top_award_id,
            applicability_breakdown=breakdown,
        )
        detail = CetDetail(
            cet=CetRef(cet_id=cet_id, name=self._taxonomy_map.get(cet_id, cet_id), taxonomy_version=taxonomy_version),
            summary=summary,
            representative_awards=representative_awards,
            gaps=gaps,
        )
        return detail


__all__ = [
    "AwardsFilters",
    "AwardsService",
    "AwardListResponse",
    "AwardListItem",
    "AwardDetail",
    "CetDetail",
]
