"""CET summary aggregation service."""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass

import pandas as pd

from sbir_cet_classifier.common.schemas import ApplicabilityAssessment


@dataclass(frozen=True)
class SummaryFilters:
    fiscal_year_start: int
    fiscal_year_end: int
    agencies: tuple[str, ...] = ()
    phases: tuple[str, ...] = ()
    cet_areas: tuple[str, ...] = ()
    location_states: tuple[str, ...] = ()


@dataclass
class SummaryTotals:
    awards: int
    obligated_usd: float
    percent_classified: float

    def as_dict(self) -> dict[str, float | int]:
        return {
            "awards": self.awards,
            "obligated_usd": round(self.obligated_usd, 2),
            "percent_classified": round(self.percent_classified, 2),
        }


@dataclass
class CETSummary:
    cet_id: str
    name: str
    awards: int
    obligated_usd: float
    share_of_awards: float
    share_of_obligated: float
    top_award_id: str | None
    top_award_score: float | None
    classification_breakdown: dict[str, int]

    def as_dict(self) -> dict:
        return {
            "cet_id": self.cet_id,
            "name": self.name,
            "awards": self.awards,
            "obligated_usd": round(self.obligated_usd, 2),
            "share_of_awards": round(self.share_of_awards, 2),
            "share_of_obligated": round(self.share_of_obligated, 2),
            "top_award": {
                "award_id": self.top_award_id,
                "score": round(self.top_award_score, 2) if self.top_award_score is not None else None,
            },
            "classification_breakdown": self.classification_breakdown,
        }


@dataclass
class SummaryResponse:
    taxonomy_version: str | None
    totals: SummaryTotals
    summaries: list[CETSummary]
    filters: SummaryFilters

    def as_dict(self) -> dict:
        return {
            "taxonomy_version": self.taxonomy_version,
            "totals": self.totals.as_dict(),
            "cet_summaries": [summary.as_dict() for summary in self.summaries],
            "filters": {
                "fiscal_year_start": self.filters.fiscal_year_start,
                "fiscal_year_end": self.filters.fiscal_year_end,
                "agencies": list(self.filters.agencies),
                "phases": list(self.filters.phases),
                "cet_areas": list(self.filters.cet_areas),
                "location_states": list(self.filters.location_states),
            },
        }


class SummaryService:
    """Aggregates CET summary metrics for analyst workflows."""

    def __init__(
        self,
        awards: pd.DataFrame,
        assessments: pd.DataFrame,
        taxonomy: pd.DataFrame,
    ) -> None:
        self._awards = awards.copy()
        if "award_amount" in self._awards.columns:
            self._awards["award_amount"] = self._awards["award_amount"].astype(float)
        self._assessments = assessments.copy()
        if "assessed_at" in self._assessments.columns:
            self._assessments["assessed_at"] = pd.to_datetime(
                self._assessments["assessed_at"], errors="coerce"
            )
        self._taxonomy = taxonomy.copy()
        if "fiscal_year" not in self._awards.columns and "award_date" in self._awards.columns:
            self._awards["fiscal_year"] = pd.to_datetime(self._awards["award_date"]).dt.year

    @classmethod
    def from_records(
        cls,
        awards: Sequence[dict],
        assessments: Iterable[ApplicabilityAssessment],
        taxonomy: Sequence[dict],
    ) -> SummaryService:
        award_df = pd.DataFrame(list(awards))
        assessment_df = pd.DataFrame([
            assessment.model_dump()
            for assessment in assessments
        ])
        taxonomy_df = pd.DataFrame(list(taxonomy))
        return cls(award_df, assessment_df, taxonomy_df)

    def _apply_filters(self, filters: SummaryFilters) -> pd.DataFrame:
        df = self._awards.copy()
        df = df[(df["fiscal_year"] >= filters.fiscal_year_start) & (df["fiscal_year"] <= filters.fiscal_year_end)]
        if filters.agencies:
            df = df[df["agency"].isin(filters.agencies)]
        if filters.phases:
            df = df[df["phase"].isin(filters.phases)]
        if filters.location_states:
            df = df[df["firm_state"].isin(filters.location_states)]
        return df

    def summarize(self, filters: SummaryFilters) -> SummaryResponse:
        awards_df = self._apply_filters(filters)
        if awards_df.empty:
            totals = SummaryTotals(awards=0, obligated_usd=0.0, percent_classified=0.0)
            return SummaryResponse(
                taxonomy_version=None,
                totals=totals,
                summaries=[],
                filters=filters,
            )

        assessments_df = self._assessments
        if not assessments_df.empty:
            latest_assessments = assessments_df.sort_values("assessed_at").drop_duplicates("award_id", keep="last")
        else:
            latest_assessments = assessments_df

        merged = awards_df.merge(latest_assessments, on="award_id", how="left", suffixes=("_award", "_assessment"))

        if filters.cet_areas:
            merged = merged[merged["primary_cet_id"].isin(filters.cet_areas)]
        if merged.empty:
            totals = SummaryTotals(awards=0, obligated_usd=0.0, percent_classified=0.0)
            return SummaryResponse(
                taxonomy_version=None,
                totals=totals,
                summaries=[],
                filters=filters,
            )

        total_awards = len(merged)
        total_obligated = merged["award_amount"].sum()
        classified = merged[merged["primary_cet_id"].notna()]
        percent_classified = (len(classified) / total_awards * 100) if total_awards else 0.0

        taxonomy_map = self._taxonomy.set_index("cet_id")["name"].to_dict() if not self._taxonomy.empty else {}
        summaries: list[CETSummary] = []
        taxonomy_version = classified["taxonomy_version"].mode().iat[0] if not classified.empty and "taxonomy_version" in classified else None

        grouped = classified.groupby("primary_cet_id")
        for cet_id, group in grouped:
            awards_count = len(group)
            obligated_sum = group["award_amount"].sum()
            share_awards = (awards_count / total_awards * 100) if total_awards else 0.0
            share_obligated = (obligated_sum / total_obligated * 100) if total_obligated else 0.0

            breakdown = group["classification"].value_counts().to_dict()
            for band in ("High", "Medium", "Low"):
                breakdown.setdefault(band, 0)

            group_sorted = group.sort_values([
                "score",
                "award_amount",
                "award_date",
            ], ascending=[False, False, False])
            top_row = group_sorted.iloc[0]
            summaries.append(
                CETSummary(
                    cet_id=cet_id,
                    name=taxonomy_map.get(cet_id, cet_id),
                    awards=awards_count,
                    obligated_usd=obligated_sum,
                    share_of_awards=share_awards,
                    share_of_obligated=share_obligated,
                    top_award_id=top_row["award_id"],
                    top_award_score=float(top_row["score"]) if pd.notna(top_row.get("score")) else None,
                    classification_breakdown=breakdown,
                )
            )

        summaries.sort(key=lambda summary: summary.awards, reverse=True)
        totals = SummaryTotals(
            awards=total_awards,
            obligated_usd=total_obligated,
            percent_classified=percent_classified,
        )

        return SummaryResponse(
            taxonomy_version=taxonomy_version,
            totals=totals,
            summaries=summaries,
            filters=filters,
        )


def empty_service() -> SummaryService:
    return SummaryService(
        awards=pd.DataFrame(columns=[
            "award_id",
            "agency",
            "phase",
            "firm_state",
            "award_amount",
            "award_date",
            "fiscal_year",
        ]),
        assessments=pd.DataFrame(columns=[
            "award_id",
            "primary_cet_id",
            "score",
            "classification",
            "generation_method",
            "taxonomy_version",
            "assessed_at",
        ]),
        taxonomy=pd.DataFrame(columns=["cet_id", "name"]),
    )


__all__ = [
    "SummaryFilters",
    "SummaryResponse",
    "SummaryService",
    "empty_service",
]
