"""Enrichment status tracking system."""

import json
import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any
from collections import defaultdict

from .schemas import EnrichmentStatus, EnrichmentType, StatusState


class EnrichmentStatusTracker:
    """Thread-safe enrichment status tracking system."""
    
    def __init__(self, status_file: Optional[Path] = None):
        """Initialize status tracker.
        
        Args:
            status_file: Path to status file for persistence
        """
        self.status_file = status_file or Path("artifacts/enrichment_status.json")
        self._statuses: Dict[str, EnrichmentStatus] = {}
        self._lock = threading.RLock()
        
        # Ensure directory exists
        self.status_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Load existing statuses if file exists
        if self.status_file.exists():
            self.load()
    
    def create_status(self, award_id: str, enrichment_types: List[EnrichmentType]) -> EnrichmentStatus:
        """Create new enrichment status entry.
        
        Args:
            award_id: Award identifier
            enrichment_types: Types of enrichment to perform
            
        Returns:
            Created enrichment status
        """
        with self._lock:
            status = EnrichmentStatus(
                award_id=award_id,
                enrichment_types=enrichment_types,
                status=StatusState.PENDING,
                confidence_score=0.0,
                last_updated=datetime.now(),
                error_message=None,
                data_sources=[]
            )
            
            self._statuses[award_id] = status
            return status
    
    def update_status(
        self,
        award_id: str,
        status: StatusState,
        confidence_score: Optional[float] = None,
        error_message: Optional[str] = None,
        data_sources: Optional[List[str]] = None
    ) -> Optional[EnrichmentStatus]:
        """Update existing enrichment status.
        
        Args:
            award_id: Award identifier
            status: New status state
            confidence_score: Confidence score (0.0 to 1.0)
            error_message: Error message if failed
            data_sources: Data sources used
            
        Returns:
            Updated enrichment status or None if not found
        """
        with self._lock:
            if award_id not in self._statuses:
                return None
            
            enrichment_status = self._statuses[award_id]
            enrichment_status.status = status
            enrichment_status.last_updated = datetime.now()
            
            if confidence_score is not None:
                enrichment_status.confidence_score = confidence_score
            
            if error_message is not None:
                enrichment_status.error_message = error_message
            
            if data_sources is not None:
                enrichment_status.data_sources = data_sources
            
            return enrichment_status
    
    def get_status(self, award_id: str) -> Optional[EnrichmentStatus]:
        """Get enrichment status for award.
        
        Args:
            award_id: Award identifier
            
        Returns:
            Enrichment status or None if not found
        """
        with self._lock:
            return self._statuses.get(award_id)
    
    def list_statuses(
        self,
        status_filter: Optional[StatusState] = None,
        enrichment_type_filter: Optional[EnrichmentType] = None,
        limit: Optional[int] = None
    ) -> List[EnrichmentStatus]:
        """List enrichment statuses with optional filtering.
        
        Args:
            status_filter: Filter by status state
            enrichment_type_filter: Filter by enrichment type
            limit: Maximum number of results
            
        Returns:
            List of matching enrichment statuses
        """
        with self._lock:
            statuses = list(self._statuses.values())
            
            # Apply filters
            if status_filter is not None:
                statuses = [s for s in statuses if s.status == status_filter]
            
            if enrichment_type_filter is not None:
                statuses = [s for s in statuses if enrichment_type_filter in s.enrichment_types]
            
            # Sort by last updated (most recent first)
            statuses.sort(key=lambda s: s.last_updated, reverse=True)
            
            # Apply limit
            if limit is not None:
                statuses = statuses[:limit]
            
            return statuses
    
    def get_summary(self) -> Dict[str, Any]:
        """Get summary statistics of enrichment statuses.
        
        Returns:
            Dictionary with summary statistics
        """
        with self._lock:
            total = len(self._statuses)
            if total == 0:
                return {
                    "total": 0,
                    "completed": 0,
                    "failed": 0,
                    "pending": 0,
                    "in_progress": 0,
                    "success_rate": 0.0
                }
            
            status_counts = defaultdict(int)
            for status in self._statuses.values():
                status_counts[status.status] += 1
            
            completed = status_counts[StatusState.COMPLETED]
            failed = status_counts[StatusState.FAILED]
            pending = status_counts[StatusState.PENDING]
            in_progress = status_counts[StatusState.IN_PROGRESS]
            
            # Calculate success rate (completed / (completed + failed))
            attempted = completed + failed
            success_rate = completed / attempted if attempted > 0 else 0.0
            
            return {
                "total": total,
                "completed": completed,
                "failed": failed,
                "pending": pending,
                "in_progress": in_progress,
                "success_rate": success_rate
            }
    
    def batch_update(self, updates: List[Dict[str, Any]]) -> int:
        """Batch update multiple statuses.
        
        Args:
            updates: List of update dictionaries with award_id and update fields
            
        Returns:
            Number of successfully updated statuses
        """
        updated_count = 0
        
        with self._lock:
            for update in updates:
                award_id = update.get("award_id")
                if not award_id or award_id not in self._statuses:
                    continue
                
                status = self._statuses[award_id]
                
                # Update fields if provided
                if "status" in update:
                    status.status = StatusState(update["status"])
                
                if "confidence_score" in update:
                    status.confidence_score = update["confidence_score"]
                
                if "error_message" in update:
                    status.error_message = update["error_message"]
                
                if "data_sources" in update:
                    status.data_sources = update["data_sources"]
                
                status.last_updated = datetime.now()
                updated_count += 1
        
        return updated_count
    
    def cleanup_old_statuses(self, max_age: timedelta) -> int:
        """Remove old status entries.
        
        Args:
            max_age: Maximum age of status entries to keep
            
        Returns:
            Number of cleaned up statuses
        """
        cutoff_time = datetime.now() - max_age
        cleaned_count = 0
        
        with self._lock:
            to_remove = []
            for award_id, status in self._statuses.items():
                if status.last_updated < cutoff_time:
                    to_remove.append(award_id)
            
            for award_id in to_remove:
                del self._statuses[award_id]
                cleaned_count += 1
        
        return cleaned_count
    
    def save(self) -> None:
        """Save statuses to file."""
        with self._lock:
            data = {
                "version": "1.0",
                "timestamp": datetime.now().isoformat(),
                "statuses": {
                    award_id: status.to_dict()
                    for award_id, status in self._statuses.items()
                }
            }
            
            # Write to temporary file first, then rename for atomicity
            temp_file = self.status_file.with_suffix('.tmp')
            try:
                with open(temp_file, 'w') as f:
                    json.dump(data, f, indent=2, default=str)
                
                # Atomic rename
                temp_file.replace(self.status_file)
            except Exception:
                # Clean up temp file on error
                if temp_file.exists():
                    temp_file.unlink()
                raise
    
    def load(self) -> None:
        """Load statuses from file."""
        if not self.status_file.exists():
            return
        
        with self._lock:
            try:
                with open(self.status_file, 'r') as f:
                    data = json.load(f)
                
                # Validate file format
                if "statuses" not in data:
                    raise ValueError("Invalid status file format")
                
                # Load statuses
                self._statuses.clear()
                for award_id, status_data in data["statuses"].items():
                    try:
                        status = EnrichmentStatus.from_dict(status_data)
                        self._statuses[award_id] = status
                    except Exception as e:
                        # Log error but continue loading other statuses
                        print(f"Warning: Failed to load status for {award_id}: {e}")
                        continue
                        
            except Exception as e:
                print(f"Warning: Failed to load status file {self.status_file}: {e}")
                # Don't raise - start with empty statuses
    
    def get_enrichment_progress(self, enrichment_type: EnrichmentType) -> Dict[str, Any]:
        """Get progress statistics for specific enrichment type.
        
        Args:
            enrichment_type: Type of enrichment to analyze
            
        Returns:
            Progress statistics dictionary
        """
        with self._lock:
            relevant_statuses = [
                status for status in self._statuses.values()
                if enrichment_type in status.enrichment_types
            ]
            
            if not relevant_statuses:
                return {
                    "enrichment_type": enrichment_type.value,
                    "total": 0,
                    "completed": 0,
                    "failed": 0,
                    "pending": 0,
                    "in_progress": 0,
                    "success_rate": 0.0,
                    "avg_confidence": 0.0
                }
            
            total = len(relevant_statuses)
            status_counts = defaultdict(int)
            confidence_scores = []
            
            for status in relevant_statuses:
                status_counts[status.status] += 1
                if status.status == StatusState.COMPLETED:
                    confidence_scores.append(status.confidence_score)
            
            completed = status_counts[StatusState.COMPLETED]
            failed = status_counts[StatusState.FAILED]
            pending = status_counts[StatusState.PENDING]
            in_progress = status_counts[StatusState.IN_PROGRESS]
            
            # Calculate metrics
            attempted = completed + failed
            success_rate = completed / attempted if attempted > 0 else 0.0
            avg_confidence = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0.0
            
            return {
                "enrichment_type": enrichment_type.value,
                "total": total,
                "completed": completed,
                "failed": failed,
                "pending": pending,
                "in_progress": in_progress,
                "success_rate": success_rate,
                "avg_confidence": avg_confidence
            }
    
    def get_failed_awards(self, enrichment_type: Optional[EnrichmentType] = None) -> List[Dict[str, Any]]:
        """Get list of failed awards with error details.
        
        Args:
            enrichment_type: Optional filter by enrichment type
            
        Returns:
            List of failed award information
        """
        with self._lock:
            failed_statuses = [
                status for status in self._statuses.values()
                if status.status == StatusState.FAILED
            ]
            
            if enrichment_type is not None:
                failed_statuses = [
                    status for status in failed_statuses
                    if enrichment_type in status.enrichment_types
                ]
            
            return [
                {
                    "award_id": status.award_id,
                    "enrichment_types": [et.value for et in status.enrichment_types],
                    "error_message": status.error_message,
                    "last_updated": status.last_updated.isoformat()
                }
                for status in failed_statuses
            ]
    
    def reset_failed_statuses(self, award_ids: Optional[List[str]] = None) -> int:
        """Reset failed statuses back to pending for retry.
        
        Args:
            award_ids: Optional list of specific award IDs to reset
            
        Returns:
            Number of statuses reset
        """
        reset_count = 0
        
        with self._lock:
            for award_id, status in self._statuses.items():
                if status.status == StatusState.FAILED:
                    if award_ids is None or award_id in award_ids:
                        status.status = StatusState.PENDING
                        status.error_message = None
                        status.last_updated = datetime.now()
                        reset_count += 1
        
        return reset_count
    
    def __len__(self) -> int:
        """Get total number of tracked statuses."""
        with self._lock:
            return len(self._statuses)
    
    def __contains__(self, award_id: str) -> bool:
        """Check if award ID is being tracked."""
        with self._lock:
            return award_id in self._statuses
