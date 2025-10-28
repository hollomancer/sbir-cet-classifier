"""Batch processing pipeline for solicitation enrichment."""

import asyncio
from typing import List, Dict, Any, Optional, Callable, Tuple
from datetime import datetime
from dataclasses import dataclass

from .models import Solicitation
from .solicitation_service import SolicitationService


@dataclass
class BatchProcessingResults:
    """Results from batch processing operation."""

    successful: List[str]
    failed: List[Tuple[str, str]]  # (id, error_message)
    skipped: List[str]
    total_processed: int
    processing_time: float

    @property
    def success_rate(self) -> float:
        """Calculate success rate."""
        if self.total_processed == 0:
            return 0.0
        return len(self.successful) / self.total_processed

    def get_summary(self) -> str:
        """Get human-readable summary."""
        return (
            f"Batch processing completed: "
            f"{len(self.successful)} successful, "
            f"{len(self.failed)} failed, "
            f"{len(self.skipped)} skipped, "
            f"{self.total_processed} total processed "
            f"in {self.processing_time:.1f}s"
        )


class SolicitationBatchProcessor:
    """Batch processor for solicitation enrichment."""

    def __init__(self, sam_client, storage=None, batch_size: int = 10, max_concurrent: int = 3):
        """Initialize batch processor."""
        self.sam_client = sam_client
        self.storage = storage
        self.batch_size = batch_size
        self.max_concurrent = max_concurrent
        self.solicitation_service = SolicitationService(sam_client)

    async def process_batch(
        self,
        awards: List[Dict[str, Any]],
        skip_existing: bool = False,
        save_to_storage: bool = False,
        max_retries: int = 0,
        progress_callback: Optional[Callable[[int, int, str], None]] = None,
    ) -> BatchProcessingResults:
        """Process a batch of awards for solicitation enrichment."""
        start_time = datetime.now()

        successful = []
        failed = []
        skipped = []
        all_solicitations = []

        # Process in chunks to respect batch size
        for i in range(0, len(awards), self.batch_size):
            batch = awards[i : i + self.batch_size]

            # Process batch with concurrency control
            batch_results = await self._process_batch_chunk(
                batch, skip_existing, max_retries, progress_callback, i, len(awards)
            )

            successful.extend(batch_results["successful"])
            failed.extend(batch_results["failed"])
            skipped.extend(batch_results["skipped"])
            all_solicitations.extend(batch_results["solicitations"])

        # Save to storage if requested
        if save_to_storage and self.storage and all_solicitations:
            try:
                self.storage.save_solicitations(all_solicitations)
            except Exception as e:
                # Log error but don't fail the entire batch
                pass

        processing_time = (datetime.now() - start_time).total_seconds()

        return BatchProcessingResults(
            successful=successful,
            failed=failed,
            skipped=skipped,
            total_processed=len(awards),
            processing_time=processing_time,
        )

    async def _process_batch_chunk(
        self,
        batch: List[Dict[str, Any]],
        skip_existing: bool,
        max_retries: int,
        progress_callback: Optional[Callable],
        batch_start_idx: int,
        total_awards: int,
    ) -> Dict[str, List]:
        """Process a single batch chunk with concurrency control."""
        semaphore = asyncio.Semaphore(self.max_concurrent)

        async def process_single_award(
            award: Dict[str, Any],
        ) -> Tuple[str, Optional[str], Optional[Solicitation]]:
            """Process a single award."""
            async with semaphore:
                solicitation_number = award.get("solicitation_number")
                if not solicitation_number:
                    return "failed", "No solicitation number", None

                # Check if already exists
                if skip_existing and self.storage:
                    existing = self.storage.find_solicitation_by_id(solicitation_number)
                    if existing:
                        return "skipped", None, None

                # Process with retries
                for attempt in range(max_retries + 1):
                    try:
                        solicitation = await self.solicitation_service.get_solicitation_by_number(
                            solicitation_number
                        )
                        if solicitation:
                            return "successful", None, solicitation
                        else:
                            return "failed", "Solicitation not found", None

                    except Exception as e:
                        if attempt < max_retries:
                            await asyncio.sleep(2**attempt)  # Exponential backoff
                            continue
                        else:
                            return "failed", str(e), None

        # Process all awards in the batch concurrently
        tasks = [process_single_award(award) for award in batch]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Categorize results
        successful = []
        failed = []
        skipped = []
        solicitations_to_save = []

        for i, result in enumerate(results):
            if isinstance(result, Exception):
                failed.append((batch[i].get("award_id", f"unknown_{i}"), str(result)))
            else:
                status, error, solicitation = result
                award_id = batch[i].get("award_id", f"unknown_{i}")

                if status == "successful":
                    successful.append(award_id)
                    if solicitation:
                        solicitations_to_save.append(solicitation)
                elif status == "failed":
                    failed.append((award_id, error))
                elif status == "skipped":
                    skipped.append(award_id)

            # Update progress
            if progress_callback:
                current_progress = batch_start_idx + i + 1
                progress_callback(current_progress, total_awards, "processing")

        return {
            "successful": successful,
            "failed": failed,
            "skipped": skipped,
            "solicitations": solicitations_to_save,
        }


class BatchEnrichmentPipeline:
    """Complete pipeline for batch enrichment of awards with solicitation data."""

    def __init__(self, sam_client, storage_manager):
        """Initialize pipeline with dependencies."""
        self.sam_client = sam_client
        self.storage_manager = storage_manager
        self.batch_processor = SolicitationBatchProcessor(sam_client, storage_manager)

    async def enrich_awards_with_solicitations(
        self, awards: List[Dict[str, Any]], batch_size: int = 50, max_concurrent: int = 5
    ) -> Dict[str, Any]:
        """Enrich awards with solicitation data."""
        # Configure batch processor
        self.batch_processor.batch_size = batch_size
        self.batch_processor.max_concurrent = max_concurrent

        # Process batch
        results = await self.batch_processor.process_batch(
            awards, skip_existing=True, save_to_storage=True, max_retries=2
        )

        return {
            "results": results,
            "summary": results.get_summary(),
            "success_rate": results.success_rate,
            "total_processed": results.total_processed,
        }

    def get_enrichment_status(self, award_ids: List[str]) -> Dict[str, str]:
        """Get enrichment status for specific awards."""
        status_map = {}

        for award_id in award_ids:
            # This would need to be implemented based on storage structure
            # For now, return placeholder
            status_map[award_id] = "unknown"

        return status_map

    async def retry_failed_enrichments(
        self, failed_awards: List[Dict[str, Any]]
    ) -> BatchProcessingResults:
        """Retry enrichment for previously failed awards."""
        return await self.batch_processor.process_batch(
            failed_awards, skip_existing=False, save_to_storage=True, max_retries=3
        )
