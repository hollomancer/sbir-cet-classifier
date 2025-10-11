"""Logging configuration for SAM.gov enrichment operations."""

import logging
from datetime import datetime
from pathlib import Path
from typing import Any

from ...common.config import load_config
from ...common.json_log import JsonLogManager


def setup_enrichment_logging() -> logging.Logger:
    """Set up structured logging for enrichment operations."""
    logger = logging.getLogger("sbir_cet_classifier.enrichment")
    
    if not logger.handlers:
        # Create console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        
        # Create formatter
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        console_handler.setFormatter(formatter)
        
        logger.addHandler(console_handler)
        logger.setLevel(logging.INFO)
    
    return logger


class EnrichmentLogger:
    """Structured logger for enrichment operations."""
    
    def __init__(self):
        self.config = load_config()
        self.logger = setup_enrichment_logging()
        self.json_log = JsonLogManager(
            self.config.artifacts_dir / "enrichment_runs.json",
            "enrichment_runs"
        )
    
    def log_enrichment_start(self, award_ids: list[str], enrichment_types: list[str]) -> str:
        """Log the start of an enrichment operation."""
        run_id = f"enrich_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        entry = {
            "run_id": run_id,
            "timestamp": datetime.now().isoformat(),
            "status": "started",
            "award_count": len(award_ids),
            "enrichment_types": enrichment_types,
            "sample_award_ids": award_ids[:5]  # Log first 5 for debugging
        }
        
        self.json_log.append(entry)
        self.logger.info(f"Started enrichment run {run_id} for {len(award_ids)} awards")
        
        return run_id
    
    def log_enrichment_progress(self, run_id: str, completed: int, total: int, 
                              failed: int = 0) -> None:
        """Log progress of an enrichment operation."""
        progress_pct = (completed / total * 100) if total > 0 else 0
        
        self.logger.info(
            f"Enrichment {run_id}: {completed}/{total} completed "
            f"({progress_pct:.1f}%), {failed} failed"
        )
    
    def log_enrichment_complete(self, run_id: str, results: dict[str, Any]) -> None:
        """Log completion of an enrichment operation."""
        entry = {
            "run_id": run_id,
            "timestamp": datetime.now().isoformat(),
            "status": "completed",
            "results": results
        }
        
        self.json_log.append(entry)
        self.logger.info(f"Completed enrichment run {run_id}: {results}")
    
    def log_enrichment_error(self, run_id: str, error: str, context: dict[str, Any]) -> None:
        """Log an error during enrichment operation."""
        entry = {
            "run_id": run_id,
            "timestamp": datetime.now().isoformat(),
            "status": "error",
            "error": error,
            "context": context
        }
        
        self.json_log.append(entry)
        self.logger.error(f"Enrichment {run_id} failed: {error}")


# Global logger instance
enrichment_logger = EnrichmentLogger()
