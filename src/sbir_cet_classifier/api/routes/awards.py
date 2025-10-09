"""API routes for award drill-down endpoints."""

from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query, status

from sbir_cet_classifier.features.awards import AwardsFilters, AwardsService

router = APIRouter(prefix="/applicability", tags=["awards"])

_awards_service: AwardsService | None = None


def configure_awards_service(service: AwardsService) -> None:
    """Configure the global awards service."""
    global _awards_service
    _awards_service = service


def get_awards_service() -> AwardsService:
    """Get the configured awards service or raise error."""
    if _awards_service is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Awards service not configured",
        )
    return _awards_service


@router.get("/awards")
def list_awards(
    fiscal_year_start: int = Query(...),
    fiscal_year_end: int = Query(...),
    agencies: Optional[List[str]] = Query(default=None),
    phases: Optional[List[str]] = Query(default=None),
    cet_areas: Optional[List[str]] = Query(default=None, alias="cetAreas"),
    location_state: Optional[str] = Query(default=None, alias="locationState"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=10, le=200, alias="pageSize"),
) -> dict:
    """List awards with applicability details."""
    service = get_awards_service()

    filters = AwardsFilters(
        fiscal_year_start=fiscal_year_start,
        fiscal_year_end=fiscal_year_end,
        agencies=tuple(agencies or []),
        phases=tuple(phases or []),
        cet_areas=tuple(cet_areas or []),
        location_states=tuple([location_state]) if location_state else (),
        page=page,
        page_size=page_size,
    )

    response = service.list_awards(filters)
    return response.as_dict()


@router.get("/awards/{award_id}")
def get_award_detail(award_id: str) -> dict:
    """Get detailed award information with assessment history."""
    service = get_awards_service()

    try:
        detail = service.get_award_detail(award_id)
        return detail.as_dict()
    except KeyError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Award not found: {award_id}",
        )


@router.get("/cet/{cet_id}")
def get_cet_detail(
    cet_id: str,
    fiscal_year_start: int = Query(...),
    fiscal_year_end: int = Query(...),
    agencies: Optional[List[str]] = Query(default=None),
    phases: Optional[List[str]] = Query(default=None),
) -> dict:
    """Get CET area detail with gap analytics."""
    service = get_awards_service()

    filters = AwardsFilters(
        fiscal_year_start=fiscal_year_start,
        fiscal_year_end=fiscal_year_end,
        agencies=tuple(agencies or []),
        phases=tuple(phases or []),
        page=1,
        page_size=10,
    )

    try:
        detail = service.get_cet_detail(cet_id, filters)
        return detail.as_dict()
    except KeyError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"CET area not found: {cet_id}",
        )


__all__ = [
    "router",
    "configure_awards_service",
    "get_awards_service",
]
