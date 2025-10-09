"""API routes for export endpoints."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel

from sbir_cet_classifier.features.exporter import ExportFormat, ExportOrchestrator
from sbir_cet_classifier.features.summary import SummaryFilters

router = APIRouter(prefix="/exports", tags=["exports"])


class ExportRequest(BaseModel):
    """Request body for creating an export."""

    fiscal_year_start: int
    fiscal_year_end: int
    agencies: list[str] = []
    phases: list[str] = []
    cet_areas: list[str] = []
    location_states: list[str] = []
    format: str = "csv"
    include_review_queue: bool = False


@router.post("")
def create_export(request: ExportRequest) -> dict:
    """Create a new export job."""
    filters = SummaryFilters(
        fiscal_year_start=request.fiscal_year_start,
        fiscal_year_end=request.fiscal_year_end,
        agencies=tuple(request.agencies),
        phases=tuple(request.phases),
        cet_areas=tuple(request.cet_areas),
        location_states=tuple(request.location_states),
    )

    try:
        export_format = ExportFormat(request.format.lower())
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid format: {request.format}. Must be 'csv' or 'parquet'",
        )

    orchestrator = ExportOrchestrator()

    # In production, this would load actual data from storage
    # For now, return a stub job
    import pandas as pd

    awards_df = pd.DataFrame()
    assessments_df = pd.DataFrame()
    taxonomy_df = pd.DataFrame()

    job = orchestrator.create_export(
        filters=filters,
        format=export_format,
        awards_df=awards_df,
        assessments_df=assessments_df,
        taxonomy_df=taxonomy_df,
        include_review_queue=request.include_review_queue,
    )

    return job.to_dict()


@router.get("")
def get_export_status(job_id: str = Query(..., alias="jobId")) -> dict:
    """Get the status of an export job."""
    orchestrator = ExportOrchestrator()

    try:
        job = orchestrator.get_job_status(job_id)
        return job.to_dict()
    except KeyError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Export job not found: {job_id}",
        )


__all__ = ["router"]
