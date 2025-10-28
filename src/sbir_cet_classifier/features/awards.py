"""Award drill-down services for CET applicability workflows."""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import date, datetime

import pandas as pd

from sbir_cet_classifier.common.datetime_utils import UTC, utc_now
from sbir_cet_classifier.common.serialization import SerializableDataclass
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
class Pagination(SerializableDataclass):
    page: int
    page_size: int
    total_pages: int
    total_records: int


@dataclass(frozen=True)
class CetRef(SerializableDataclass):
    cet_id: str
    name: str
    taxonomy_version: str | None


@dataclass(frozen=True)
class AwardListItem(SerializableDataclass):
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


@dataclass(frozen=True)
class AwardListResponse(SerializableDataclass):
    pagination: Pagination
    awards: list[AwardListItem]


@dataclass(frozen=True)
class ReviewQueueSnapshot(SerializableDataclass):
    queue_id: str
    award_id: str
    reason: str
    status: str
    opened_at: datetime
    due_by: date
    assigned_to: str | None
    resolved_at: datetime | None
    resolution_notes: str | None


@dataclass(frozen=True)
class AwardCore(SerializableDataclass):
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
        """Override to apply custom rounding for USD amounts."""
        result = super().as_dict()
        result["obligatedUsd"] = round(self.obligated_usd, 2)
        return result


@dataclass(frozen=True)
class AssessmentRecord(SerializableDataclass):
    assessment_id: str
    assessed_at: datetime | None
    score: int
    classification: str
    primary_cet: CetRef
    supporting_cet: list[CetRef]
    evidence: list[dict]
    generation_method: str
    reviewer_notes: str | None


@dataclass(frozen=True)
class AwardDetail(SerializableDataclass):
    award: AwardCore
    assessments: list[AssessmentRecord]
    review_queue: ReviewQueueSnapshot | None


@dataclass(frozen=True)
class CetSummary(SerializableDataclass):
    cet_id: str
    name: str
    awards: int
    obligated_usd: float
    share: float
    top_award_id: str | None
    applicability_breakdown: dict[str, int]

    def as_dict(self) -> dict:
        """Override to apply custom rounding for USD amounts and percentages."""
        result = super().as_dict()
        result["obligatedUsd"] = round(self.obligated_usd, 2)
        result["share"] = round(self.share, 2)
        return result


@dataclass(frozen=True)
class CetDetail(SerializableDataclass):
    cet: CetRef
    summary: CetSummary
    representative_awards: list[AwardListItem]
    gaps: list[GapInsight]


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
        # Store references without copying unless necessary
        self._awards = awards
        self._assessments = assessments
        self._taxonomy = taxonomy
        self._review_queue = review_queue

        # Pre-compute commonly used lookups
        self._taxonomy_map = (
            taxonomy.set_index("cet_id")["name"].to_dict() if not taxonomy.empty else {}
        )
        self._gap_analytics = GapAnalytics(target_shares or {})

        # Lazy initialization flags
        self._processed_awards = None
        self._processed_assessments = None
        self._processed_review_queue = None

    @classmethod
    def from_records(
        cls,
        *,
        awards: Sequence[dict],
        assessments: Iterable[dict],
        taxonomy: Sequence[dict],
        review_queue: Iterable[dict],
        target_shares: Mapping[str, float] | None = None,
    ) -> AwardsService:
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
    def _get_processed_awards(self) -> pd.DataFrame:
        """Lazy processing of awards data."""
        if self._processed_awards is None:
            df = self._awards.copy()
            if "fiscal_year" not in df.columns and "award_date" in df.columns:
                df["fiscal_year"] = pd.to_datetime(df["award_date"], errors="coerce").dt.year
            if "award_date" in df.columns:
                df["award_date"] = pd.to_datetime(df["award_date"], errors="coerce").dt.date
            else:
                df["award_date"] = pd.Series([None] * len(df))
            if "keywords" in df.columns:
                df["keywords"] = df["keywords"].apply(self._normalise_keywords)
            else:
                df["keywords"] = [[] for _ in range(len(df))]
            self._processed_awards = df
        return self._processed_awards

    def _get_processed_assessments(self) -> pd.DataFrame:
        """Lazy processing of assessments data."""
        if self._processed_assessments is None:
            df = self._assessments.copy()
            if not df.empty and "assessed_at" in df.columns:
                df["assessed_at"] = pd.to_datetime(df["assessed_at"], errors="coerce", utc=True)
            self._processed_assessments = df
        return self._processed_assessments

    def _get_processed_review_queue(self) -> pd.DataFrame:
        """Lazy processing of review queue data."""
        if self._processed_review_queue is None:
            df = self._review_queue.copy()
            if not df.empty:
                for column in ("opened_at", "resolved_at"):
                    if column in df.columns:
                        df[column] = pd.to_datetime(df[column], errors="coerce", utc=True)
                if "due_by" in df.columns:
                    df["due_by"] = pd.to_datetime(df["due_by"], errors="coerce").dt.date
            self._processed_review_queue = df
        return self._processed_review_queue

    @staticmethod
    def _normalise_keywords(value) -> list[str]:
        if value is None:
            return []
        if isinstance(value, str):
            return [token.strip() for token in value.split(";") if token.strip()]
        return [str(token).strip() for token in value if str(token).strip()]

    def _latest_assessments(self) -> pd.DataFrame:
        assessments = self._get_processed_assessments()
        if assessments.empty:
            return assessments
        return assessments.sort_values("assessed_at").drop_duplicates("award_id", keep="last")

    def _review_queue_map(self) -> dict[str, ReviewQueueSnapshot]:
        review_queue = self._get_processed_review_queue()
        if review_queue.empty:
            return {}

        snapshots: dict[str, ReviewQueueSnapshot] = {}
        now = utc_now()
        today = now.date()

        for _, row in review_queue.iterrows():
            status = row.get("status")
            if status == "resolved":
                continue

            due_by = row.get("due_by")
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
        awards = self._get_processed_awards()

        # Build filter mask efficiently
        mask = (awards["fiscal_year"] >= filters.fiscal_year_start) & (
            awards["fiscal_year"] <= filters.fiscal_year_end
        )

        if filters.agencies:
            mask &= awards["agency"].isin(filters.agencies)
        if filters.phases:
            mask &= awards["phase"].isin(filters.phases)
        if filters.location_states:
            mask &= awards["firm_state"].isin(filters.location_states)

        df = awards[mask].copy()

        latest = self._latest_assessments()
        merged = df.merge(latest, on="award_id", how="left", suffixes=("", "_assessment"))

        if filters.cet_areas:
            merged = merged[merged["primary_cet_id"].isin(filters.cet_areas)]

        # Vectorized score conversion
        merged["score"] = pd.to_numeric(merged.get("score", -1), errors="coerce").fillna(-1)

        # Pre-compute review queue map once
        review_map = self._review_queue_map()
        merged["review_queue"] = merged["award_id"].map(review_map)

        # Vectorized data_incomplete computation
        has_text = (
            merged["abstract"].notna()
            & (merged["abstract"].str.strip() != "")
            & merged["keywords"].notna()
        )
        queue_pending = merged["review_queue"].apply(
            lambda x: isinstance(x, ReviewQueueSnapshot)
            and x.status in {"pending", "in_review", "escalated"}
        )
        merged["data_incomplete"] = ~has_text | queue_pending

        return merged

    @staticmethod
    def _compute_data_incomplete(row) -> bool:
        abstract = row.get("abstract")
        keywords = row.get("keywords") or []
        has_text = bool(abstract and abstract.strip()) and bool(keywords)
        queue: ReviewQueueSnapshot | None = row.get("review_queue")
        # Check if queue is actually a ReviewQueueSnapshot, not NaN (float)
        queue_pending = isinstance(queue, ReviewQueueSnapshot) and queue.status in {
            "pending",
            "in_review",
            "escalated",
        }
        return (not has_text) or queue_pending

    def _build_cet_ref(self, cet_id: str | None, taxonomy_version: str | None) -> CetRef:
        if cet_id is None:
            return CetRef(cet_id="", name="", taxonomy_version=taxonomy_version)
        name = self._taxonomy_map.get(cet_id, cet_id)
        return CetRef(cet_id=cet_id, name=name, taxonomy_version=taxonomy_version)

    def _build_supporting_refs(
        self, supporting_ids: Iterable[str], taxonomy_version: str | None
    ) -> list[CetRef]:
        return [self._build_cet_ref(cet_id, taxonomy_version) for cet_id in supporting_ids]

    def _build_award_item(self, row) -> AwardListItem:
        primary_ref = self._build_cet_ref(row.get("primary_cet_id"), row.get("taxonomy_version"))
        supporting = self._build_supporting_refs(
            row.get("supporting_cet_ids") or [], row.get("taxonomy_version")
        )
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
        assessments = self._get_processed_assessments()
        subset = assessments[assessments["award_id"] == award_id]
        if subset.empty:
            return []
        subset = subset.sort_values("assessed_at", ascending=False)
        records: list[AssessmentRecord] = []
        for _, row in subset.iterrows():
            taxonomy_version = row.get("taxonomy_version")
            primary_ref = self._build_cet_ref(row.get("primary_cet_id"), taxonomy_version)
            supporting_refs = self._build_supporting_refs(
                row.get("supporting_cet_ids") or [], taxonomy_version
            )
            assessed_at = row.get("assessed_at")
            assessed_dt = (
                assessed_at.to_pydatetime().astimezone(UTC) if pd.notna(assessed_at) else None
            )
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
            pagination = Pagination(
                page=filters.page, page_size=filters.page_size, total_pages=0, total_records=0
            )
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
        awards = self._get_processed_awards()
        filtered = awards[awards["award_id"] == award_id]
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
        taxonomy_version = (
            filtered["taxonomy_version"].mode().iat[0] if "taxonomy_version" in filtered else None
        )
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
        manual_gap = self._gap_analytics.manual_review_gap(
            cet_id=cet_id, pending_reviews=pending_reviews
        )
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
            cet=CetRef(
                cet_id=cet_id,
                name=self._taxonomy_map.get(cet_id, cet_id),
                taxonomy_version=taxonomy_version,
            ),
            summary=summary,
            representative_awards=representative_awards,
            gaps=gaps,
        )
        return detail


__all__ = [
    "AwardDetail",
    "AwardListItem",
    "AwardListResponse",
    "AwardsFilters",
    "AwardsService",
    "CetDetail",
]
