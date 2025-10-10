"""API router for SBIR CET classifier endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status

from sbir_cet_classifier.api.routes import awards as awards_routes
from sbir_cet_classifier.api.routes import exports as exports_routes
from sbir_cet_classifier.features.awards import AwardsService
from sbir_cet_classifier.features.summary import SummaryFilters, SummaryService, empty_service

router = APIRouter()
router.include_router(awards_routes.router)
router.include_router(exports_routes.router)

_summary_service: SummaryService | None = empty_service()
_awards_service: AwardsService | None = None


def configure_summary_service(service: SummaryService) -> None:
    """Configure the global summary service used by API routes."""

    global _summary_service
    _summary_service = service


def get_summary_service() -> SummaryService:
    if _summary_service is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Summary service not configured",
        )
    return _summary_service


def configure_awards_service(service: AwardsService) -> None:
    """Configure the global awards service used by API routes."""
    global _awards_service
    _awards_service = service
    awards_routes.configure_awards_service(service)


def get_awards_service() -> AwardsService:
    if _awards_service is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Awards service not configured",
        )
    return _awards_service


def _tuple(values: list[str] | None) -> tuple[str, ...]:
    return tuple(values or [])


@router.get("/health")
def healthcheck() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/applicability/summary")
def get_summary(
    fiscal_year_start: int,
    fiscal_year_end: int,
    agency: list[str] | None = Query(default=None),
    phases: list[str] | None = Query(default=None),
    cet_area: list[str] | None = Query(default=None),
    location_state: list[str] | None = Query(default=None),
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




@router.get("/applicability/review-queue")
def get_review_queue() -> dict[str, str]:
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Review queue not yet implemented",
    )


@router.post("/refresh")
def trigger_refresh() -> dict[str, str]:
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Refresh trigger not yet implemented",
    )
