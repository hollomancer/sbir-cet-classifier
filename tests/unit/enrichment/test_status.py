"""Tests for enrichment status tracking system."""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch
from pathlib import Path

from sbir_cet_classifier.data.enrichment.status import (
    EnrichmentStatusTracker,
    EnrichmentStatus,
    EnrichmentType,
    StatusState,
)


class TestEnrichmentStatusTracker:
    """Test enrichment status tracking functionality."""
    
    @pytest.fixture
    def temp_status_file(self, tmp_path):
        """Create temporary status file for testing."""
        return tmp_path / "enrichment_status.json"
    
    @pytest.fixture
    def tracker(self, temp_status_file):
        """Create status tracker instance."""
        return EnrichmentStatusTracker(status_file=temp_status_file)
    
    def test_create_status_entry(self, tracker):
        """Test creating new status entry."""
        award_id = "AWARD-2024-001"
        enrichment_types = [EnrichmentType.AWARDEE, EnrichmentType.PROGRAM_OFFICE]
        
        status = tracker.create_status(award_id, enrichment_types)
        
        assert status.award_id == award_id
        assert status.enrichment_types == enrichment_types
        assert status.status == StatusState.PENDING
        assert status.confidence_score == 0.0
        assert status.error_message is None
        
    def test_update_status_success(self, tracker):
        """Test updating status to success."""
        award_id = "AWARD-2024-001"
        enrichment_types = [EnrichmentType.AWARDEE]
        
        # Create initial status
        status = tracker.create_status(award_id, enrichment_types)
        
        # Update to success
        updated_status = tracker.update_status(
            award_id=award_id,
            status=StatusState.COMPLETED,
            confidence_score=0.95,
            data_sources=["SAM.gov API"]
        )
        
        assert updated_status.status == StatusState.COMPLETED
        assert updated_status.confidence_score == 0.95
        assert updated_status.data_sources == ["SAM.gov API"]
        assert updated_status.error_message is None
        
    def test_update_status_failure(self, tracker):
        """Test updating status to failure."""
        award_id = "AWARD-2024-001"
        enrichment_types = [EnrichmentType.AWARDEE]
        
        # Create initial status
        status = tracker.create_status(award_id, enrichment_types)
        
        # Update to failure
        error_msg = "API rate limit exceeded"
        updated_status = tracker.update_status(
            award_id=award_id,
            status=StatusState.FAILED,
            error_message=error_msg
        )
        
        assert updated_status.status == StatusState.FAILED
        assert updated_status.confidence_score == 0.0
        assert updated_status.error_message == error_msg
        
    def test_get_status(self, tracker):
        """Test retrieving status by award ID."""
        award_id = "AWARD-2024-001"
        enrichment_types = [EnrichmentType.SOLICITATION]
        
        # Create status
        original_status = tracker.create_status(award_id, enrichment_types)
        
        # Retrieve status
        retrieved_status = tracker.get_status(award_id)
        
        assert retrieved_status is not None
        assert retrieved_status.award_id == award_id
        assert retrieved_status.enrichment_types == enrichment_types
        
    def test_get_nonexistent_status(self, tracker):
        """Test retrieving status for non-existent award."""
        status = tracker.get_status("NONEXISTENT-AWARD")
        assert status is None
        
    def test_list_statuses_by_state(self, tracker):
        """Test listing statuses filtered by state."""
        # Create multiple statuses
        tracker.create_status("AWARD-001", [EnrichmentType.AWARDEE])
        tracker.create_status("AWARD-002", [EnrichmentType.PROGRAM_OFFICE])
        tracker.create_status("AWARD-003", [EnrichmentType.MODIFICATIONS])
        
        # Update one to completed
        tracker.update_status("AWARD-002", StatusState.COMPLETED, confidence_score=0.9)
        
        # Update one to failed
        tracker.update_status("AWARD-003", StatusState.FAILED, error_message="Test error")
        
        # Test filtering
        pending_statuses = tracker.list_statuses(status_filter=StatusState.PENDING)
        completed_statuses = tracker.list_statuses(status_filter=StatusState.COMPLETED)
        failed_statuses = tracker.list_statuses(status_filter=StatusState.FAILED)
        
        assert len(pending_statuses) == 1
        assert len(completed_statuses) == 1
        assert len(failed_statuses) == 1
        
        assert pending_statuses[0].award_id == "AWARD-001"
        assert completed_statuses[0].award_id == "AWARD-002"
        assert failed_statuses[0].award_id == "AWARD-003"
        
    def test_list_statuses_by_enrichment_type(self, tracker):
        """Test listing statuses filtered by enrichment type."""
        # Create statuses with different enrichment types
        tracker.create_status("AWARD-001", [EnrichmentType.AWARDEE])
        tracker.create_status("AWARD-002", [EnrichmentType.PROGRAM_OFFICE])
        tracker.create_status("AWARD-003", [EnrichmentType.AWARDEE, EnrichmentType.SOLICITATION])
        
        # Filter by awardee enrichment
        awardee_statuses = tracker.list_statuses(enrichment_type_filter=EnrichmentType.AWARDEE)
        
        assert len(awardee_statuses) == 2
        award_ids = [status.award_id for status in awardee_statuses]
        assert "AWARD-001" in award_ids
        assert "AWARD-003" in award_ids
        
    def test_get_summary_statistics(self, tracker):
        """Test getting summary statistics."""
        # Create various statuses
        tracker.create_status("AWARD-001", [EnrichmentType.AWARDEE])
        tracker.create_status("AWARD-002", [EnrichmentType.PROGRAM_OFFICE])
        tracker.create_status("AWARD-003", [EnrichmentType.SOLICITATION])
        
        # Update statuses
        tracker.update_status("AWARD-001", StatusState.COMPLETED, confidence_score=0.95)
        tracker.update_status("AWARD-002", StatusState.FAILED, error_message="Test error")
        # AWARD-003 remains pending
        
        summary = tracker.get_summary()
        
        assert summary["total"] == 3
        assert summary["completed"] == 1
        assert summary["failed"] == 1
        assert summary["pending"] == 1
        assert summary["success_rate"] == 0.5  # 1 completed out of 2 attempted (completed + failed)
        
    def test_persistence(self, tracker, temp_status_file):
        """Test status persistence to file."""
        award_id = "AWARD-2024-001"
        enrichment_types = [EnrichmentType.AWARDEE]
        
        # Create and update status
        tracker.create_status(award_id, enrichment_types)
        tracker.update_status(award_id, StatusState.COMPLETED, confidence_score=0.9)
        
        # Save to file
        tracker.save()
        
        # Create new tracker and load
        new_tracker = EnrichmentStatusTracker(status_file=temp_status_file)
        new_tracker.load()
        
        # Verify status persisted
        loaded_status = new_tracker.get_status(award_id)
        assert loaded_status is not None
        assert loaded_status.status == StatusState.COMPLETED
        assert loaded_status.confidence_score == 0.9
        
    def test_batch_update(self, tracker):
        """Test batch updating multiple statuses."""
        # Create multiple statuses
        award_ids = ["AWARD-001", "AWARD-002", "AWARD-003"]
        for award_id in award_ids:
            tracker.create_status(award_id, [EnrichmentType.AWARDEE])
        
        # Batch update
        updates = [
            {"award_id": "AWARD-001", "status": StatusState.COMPLETED, "confidence_score": 0.9},
            {"award_id": "AWARD-002", "status": StatusState.COMPLETED, "confidence_score": 0.8},
            {"award_id": "AWARD-003", "status": StatusState.FAILED, "error_message": "Test error"}
        ]
        
        tracker.batch_update(updates)
        
        # Verify updates
        status_001 = tracker.get_status("AWARD-001")
        status_002 = tracker.get_status("AWARD-002")
        status_003 = tracker.get_status("AWARD-003")
        
        assert status_001.status == StatusState.COMPLETED
        assert status_002.confidence_score == 0.8
        assert status_003.error_message == "Test error"
        
    def test_cleanup_old_statuses(self, tracker):
        """Test cleanup of old status entries."""
        # Create statuses with different timestamps
        now = datetime.now()
        old_time = now - timedelta(days=30)
        
        # Mock datetime for old status
        with patch('sbir_cet_classifier.data.enrichment.status.datetime') as mock_datetime:
            mock_datetime.now.return_value = old_time
            tracker.create_status("OLD-AWARD", [EnrichmentType.AWARDEE])
        
        # Create recent status
        tracker.create_status("NEW-AWARD", [EnrichmentType.AWARDEE])
        
        # Cleanup statuses older than 7 days
        cleanup_threshold = timedelta(days=7)
        cleaned_count = tracker.cleanup_old_statuses(cleanup_threshold)
        
        assert cleaned_count == 1
        assert tracker.get_status("OLD-AWARD") is None
        assert tracker.get_status("NEW-AWARD") is not None
        
    def test_concurrent_access(self, tracker):
        """Test thread-safe operations."""
        import threading
        import time
        
        results = []
        
        def create_statuses(start_id):
            for i in range(5):
                award_id = f"AWARD-{start_id}-{i}"
                try:
                    tracker.create_status(award_id, [EnrichmentType.AWARDEE])
                    results.append(f"Created {award_id}")
                except Exception as e:
                    results.append(f"Error creating {award_id}: {e}")
        
        # Create multiple threads
        threads = []
        for i in range(3):
            thread = threading.Thread(target=create_statuses, args=(i,))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads
        for thread in threads:
            thread.join()
        
        # Verify all statuses were created
        all_statuses = tracker.list_statuses()
        assert len(all_statuses) == 15  # 3 threads * 5 statuses each
        
        # Verify no errors in results
        error_results = [r for r in results if "Error" in r]
        assert len(error_results) == 0


class TestEnrichmentStatus:
    """Test EnrichmentStatus model."""
    
    def test_status_creation(self):
        """Test creating status with all fields."""
        status = EnrichmentStatus(
            award_id="AWARD-001",
            enrichment_types=[EnrichmentType.AWARDEE, EnrichmentType.SOLICITATION],
            status=StatusState.COMPLETED,
            confidence_score=0.95,
            last_updated=datetime.now(),
            error_message=None,
            data_sources=["SAM.gov API", "Cache"]
        )
        
        assert status.award_id == "AWARD-001"
        assert len(status.enrichment_types) == 2
        assert status.status == StatusState.COMPLETED
        assert status.confidence_score == 0.95
        
    def test_status_serialization(self):
        """Test status serialization to dict."""
        status = EnrichmentStatus(
            award_id="AWARD-001",
            enrichment_types=[EnrichmentType.AWARDEE],
            status=StatusState.PENDING,
            confidence_score=0.0,
            last_updated=datetime(2024, 1, 15, 10, 30, 0),
            error_message=None,
            data_sources=[]
        )
        
        status_dict = status.to_dict()
        
        assert status_dict["award_id"] == "AWARD-001"
        assert status_dict["enrichment_types"] == ["awardee"]
        assert status_dict["status"] == "pending"
        assert status_dict["confidence_score"] == 0.0
        
    def test_status_deserialization(self):
        """Test status deserialization from dict."""
        status_dict = {
            "award_id": "AWARD-001",
            "enrichment_types": ["awardee", "program_office"],
            "status": "completed",
            "confidence_score": 0.85,
            "last_updated": "2024-01-15T10:30:00",
            "error_message": None,
            "data_sources": ["SAM.gov API"]
        }
        
        status = EnrichmentStatus.from_dict(status_dict)
        
        assert status.award_id == "AWARD-001"
        assert len(status.enrichment_types) == 2
        assert status.status == StatusState.COMPLETED
        assert status.confidence_score == 0.85


class TestEnrichmentType:
    """Test EnrichmentType enum."""
    
    def test_enrichment_type_values(self):
        """Test enrichment type enum values."""
        assert EnrichmentType.AWARDEE.value == "awardee"
        assert EnrichmentType.PROGRAM_OFFICE.value == "program_office"
        assert EnrichmentType.SOLICITATION.value == "solicitation"
        assert EnrichmentType.MODIFICATIONS.value == "modifications"
        
    def test_enrichment_type_from_string(self):
        """Test creating enrichment type from string."""
        assert EnrichmentType("awardee") == EnrichmentType.AWARDEE
        assert EnrichmentType("program_office") == EnrichmentType.PROGRAM_OFFICE
        
    def test_invalid_enrichment_type(self):
        """Test invalid enrichment type raises error."""
        with pytest.raises(ValueError):
            EnrichmentType("invalid_type")


class TestStatusState:
    """Test StatusState enum."""
    
    def test_status_state_values(self):
        """Test status state enum values."""
        assert StatusState.PENDING.value == "pending"
        assert StatusState.IN_PROGRESS.value == "in_progress"
        assert StatusState.COMPLETED.value == "completed"
        assert StatusState.FAILED.value == "failed"
        
    def test_status_state_from_string(self):
        """Test creating status state from string."""
        assert StatusState("pending") == StatusState.PENDING
        assert StatusState("completed") == StatusState.COMPLETED
        
    def test_invalid_status_state(self):
        """Test invalid status state raises error."""
        with pytest.raises(ValueError):
            StatusState("invalid_state")
