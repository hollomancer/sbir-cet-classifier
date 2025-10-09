"""API router for SBIR CET classifier endpoints."""

from __future__ import annotations

from typing import List, Optional, Tuple

from fastapi import APIRouter, Depends, HTTPException, Query, status

from sbir_cet_classifier.features.summary import SummaryFilters, SummaryService, empty_service

router = APIRouter()

_summary_service: SummaryService | None = empty_service()


def configure_summary_service(service: SummaryService) -> None:
    """Configure the global summary service used by API routes."""

    global _summary_service
    _summary_service = service


def get_summary_service() -> SummaryService:
    if _summary_service is None:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Summary service not configured")
    return _summary_service


def _tuple(values: Optional[List[str]]) -> Tuple[str, ...]:
    return tuple(values or [])


@router.get("/health")
def healthcheck() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/applicability/summary")
def get_summary(
    fiscal_year_start: int,
    fiscal_year_end: int,
    agency: Optional[List[str]] = Query(default=None),
    phases: Optional[List[str]] = Query(default=None),
    cet_area: Optional[List[str]] = Query(default=None),
    location_state: Optional[List[str]] = Query(default=None),
    service: SummaryService = Depends(get_summary_service),
) -> dict:
    filters = SummaryFilters(
        fiscal_year_start=fiscal_year_start,
        fiscal_year_end=fiscal_year_end,
        agencies=_tuple(agency),
        phases=_tuple(phases),
        cet_areas=_tuple(cet_area),
        location_states=_tuple(location_state),
    )
    return service.summarize(filters).as_dict()


@router.get("/applicability/awards")
def list_awards() -> dict[str, str]:
    raise HTTPException(status.HTTP_501_NOT_IMPLEMENTED, "Awards listing not yet implemented")


@router.get("/applicability/awards/{award_id}")
def get_award(award_id: str) -> dict[str, str]:
    raise HTTPException(status.HTTP_501_NOT_IMPLEMENTED, "Award detail not yet implemented")


@router.get("/applicability/cet/{cet_id}")
def get_cet_area(cet_id: str) -> dict[str, str]:
    raise HTTPException(status.HTTP_501_NOT_IMPLEMENTED, "CET detail not yet implemented")


@router.get("/applicability/review-queue")
def get_review_queue() -> dict[str, str]:
    raise HTTPException(status.HTTP_501_NOT_IMPLEMENTED, "Review queue not yet implemented")


@router.post("/refresh")
def trigger_refresh() -> dict[str, str]:
    raise HTTPException(status.HTTP_501_NOT_IMPLEMENTED, "Refresh trigger not yet implemented")


@router.post("/exports")
def create_export() -> dict[str, str]:
    raise HTTPException(status.HTTP_501_NOT_IMPLEMENTED, "Export not yet implemented")


@router.get("/exports")
def get_export_status() -> dict[str, str]:
    raise HTTPException(status.HTTP_501_NOT_IMPLEMENTED, "Export status not yet implemented")
