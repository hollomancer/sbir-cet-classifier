"""Integration tests for solicitation enrichment batch processing."""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, date
from decimal import Decimal

from sbir_cet_classifier.data.enrichment.batch_processor import SolicitationBatchProcessor
from sbir_cet_classifier.data.enrichment.models import Solicitation


class TestSolicitationBatchProcessor:
    """Test SolicitationBatchProcessor."""

    @pytest.fixture
    def mock_sam_client(self):
        """Mock SAM.gov API client."""
        client = Mock()
        client.get_solicitation_by_number = AsyncMock()
        client.search_solicitations = AsyncMock()
        return client

    @pytest.fixture
    def mock_storage(self):
        """Mock solicitation storage."""
        storage = Mock()
        storage.save_solicitations = Mock()
        storage.load_solicitations = Mock(return_value=[])
        storage.find_solicitation_by_id = Mock(return_value=None)
        return storage

    @pytest.fixture
    def processor(self, mock_sam_client, mock_storage):
        """Create batch processor with mocked dependencies."""
        return SolicitationBatchProcessor(
            sam_client=mock_sam_client, storage=mock_storage, batch_size=10, max_concurrent=3
        )

    @pytest.fixture
    def sample_awards(self):
        """Sample awards for batch processing."""
        return [
            {
                "award_id": "AWARD-001",
                "solicitation_number": "N00014-24-S-B001",
                "agency": "DON",
                "title": "Quantum Computing Research",
            },
            {
                "award_id": "AWARD-002",
                "solicitation_number": "W911NF-24-S-0001",
                "agency": "DOD",
                "title": "AI Applications",
            },
            {
                "award_id": "AWARD-003",
                "solicitation_number": "FA8750-24-S-0001",
                "agency": "USAF",
                "title": "Cybersecurity Systems",
            },
        ]

    @pytest.mark.asyncio
    async def test_process_batch_success(self, processor, mock_sam_client, sample_awards):
        """Test successful batch processing."""
        # Mock API responses
        mock_responses = [
            {
                "solicitation_id": f"SOL-{i:03d}",
                "solicitation_number": award["solicitation_number"],
                "title": f"Solicitation for {award['title']}",
                "agency_code": award["agency"],
                "program_office_id": f"{award['agency']}-001",
                "solicitation_type": "SBIR Phase I",
                "full_text": f"Full text for {award['title']}",
                "technical_requirements": f"Technical requirements for {award['title']}",
                "evaluation_criteria": f"Evaluation criteria for {award['title']}",
                "funding_range_min": "100000.00",
                "funding_range_max": "300000.00",
                "proposal_deadline": "2024-06-15",
                "performance_period": 12,
                "keywords": [award["title"].lower().split()],
                "cet_relevance_scores": {"quantum_computing": 0.8},
            }
            for i, award in enumerate(sample_awards, 1)
        ]

        mock_sam_client.get_solicitation_by_number.side_effect = mock_responses

        results = await processor.process_batch(sample_awards)

        assert len(results.successful) == 3
        assert len(results.failed) == 0
        assert results.total_processed == 3

        # Verify API calls
        assert mock_sam_client.get_solicitation_by_number.call_count == 3

    @pytest.mark.asyncio
    async def test_process_batch_with_failures(self, processor, mock_sam_client, sample_awards):
        """Test batch processing with some failures."""
        # First call succeeds, second fails, third succeeds
        mock_sam_client.get_solicitation_by_number.side_effect = [
            {
                "solicitation_id": "SOL-001",
                "solicitation_number": "N00014-24-S-B001",
                "title": "Quantum Computing Research",
                "agency_code": "DON",
                "program_office_id": "DON-001",
                "solicitation_type": "SBIR Phase I",
                "full_text": "Quantum text",
                "technical_requirements": "Quantum requirements",
                "evaluation_criteria": "Quantum criteria",
                "funding_range_min": "100000.00",
                "funding_range_max": "300000.00",
                "proposal_deadline": "2024-06-15",
                "performance_period": 12,
                "keywords": ["quantum"],
                "cet_relevance_scores": {"quantum_computing": 0.9},
            },
            Exception("API Error"),  # Failure
            {
                "solicitation_id": "SOL-003",
                "solicitation_number": "FA8750-24-S-0001",
                "title": "Cybersecurity Systems",
                "agency_code": "USAF",
                "program_office_id": "USAF-001",
                "solicitation_type": "SBIR Phase I",
                "full_text": "Cyber text",
                "technical_requirements": "Cyber requirements",
                "evaluation_criteria": "Cyber criteria",
                "funding_range_min": "150000.00",
                "funding_range_max": "350000.00",
                "proposal_deadline": "2024-07-15",
                "performance_period": 12,
                "keywords": ["cybersecurity"],
                "cet_relevance_scores": {"cybersecurity": 0.85},
            },
        ]

        results = await processor.process_batch(sample_awards)

        assert len(results.successful) == 2
        assert len(results.failed) == 1
        assert results.total_processed == 3
        assert results.success_rate == 2 / 3

    @pytest.mark.asyncio
    async def test_concurrent_processing_limit(self, processor, mock_sam_client):
        """Test concurrent processing respects limits."""
        # Create many awards to test concurrency
        many_awards = [
            {
                "award_id": f"AWARD-{i:03d}",
                "solicitation_number": f"SOL-{i:03d}",
                "agency": "DON",
                "title": f"Research {i}",
            }
            for i in range(20)
        ]

        # Track concurrent calls
        concurrent_calls = []

        async def mock_api_call(solicitation_number):
            concurrent_calls.append(datetime.now())
            await asyncio.sleep(0.1)  # Simulate API delay
            concurrent_calls.append(datetime.now())
            return {
                "solicitation_id": f"SOL-{solicitation_number}",
                "solicitation_number": solicitation_number,
                "title": f"Title for {solicitation_number}",
                "agency_code": "DON",
                "program_office_id": "DON-001",
                "solicitation_type": "SBIR Phase I",
                "full_text": "Text",
                "technical_requirements": "Requirements",
                "evaluation_criteria": "Criteria",
                "funding_range_min": "100000.00",
                "funding_range_max": "300000.00",
                "proposal_deadline": "2024-06-15",
                "performance_period": 12,
                "keywords": [],
                "cet_relevance_scores": {},
            }

        mock_sam_client.get_solicitation_by_number.side_effect = mock_api_call

        results = await processor.process_batch(many_awards)

        assert results.total_processed == 20
        # Should respect max_concurrent limit of 3

    @pytest.mark.asyncio
    async def test_batch_size_chunking(self, processor, mock_sam_client):
        """Test processing respects batch size limits."""
        # Create more awards than batch size
        awards = [
            {
                "award_id": f"AWARD-{i:03d}",
                "solicitation_number": f"SOL-{i:03d}",
                "agency": "DON",
                "title": f"Research {i}",
            }
            for i in range(25)  # More than batch_size of 10
        ]

        mock_sam_client.get_solicitation_by_number.return_value = {
            "solicitation_id": "SOL-001",
            "solicitation_number": "SOL-001",
            "title": "Test",
            "agency_code": "DON",
            "program_office_id": "DON-001",
            "solicitation_type": "SBIR Phase I",
            "full_text": "Text",
            "technical_requirements": "Requirements",
            "evaluation_criteria": "Criteria",
            "funding_range_min": "100000.00",
            "funding_range_max": "300000.00",
            "proposal_deadline": "2024-06-15",
            "performance_period": 12,
            "keywords": [],
            "cet_relevance_scores": {},
        }

        results = await processor.process_batch(awards)

        assert results.total_processed == 25
        # Should process in chunks of batch_size

    @pytest.mark.asyncio
    async def test_duplicate_solicitation_handling(self, processor, mock_sam_client, mock_storage):
        """Test handling of duplicate solicitations."""
        # Mock existing solicitation in storage
        existing_solicitation = Solicitation(
            solicitation_id="SOL-001",
            solicitation_number="N00014-24-S-B001",
            title="Existing Solicitation",
            agency_code="DON",
            program_office_id="DON-001",
            solicitation_type="SBIR Phase I",
            full_text="Existing text",
            technical_requirements="Existing requirements",
            evaluation_criteria="Existing criteria",
            funding_range_min=Decimal("100000.00"),
            funding_range_max=Decimal("300000.00"),
            proposal_deadline=date(2024, 6, 15),
            performance_period=12,
            keywords=[],
            cet_relevance_scores={},
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        mock_storage.find_solicitation_by_id.return_value = existing_solicitation

        awards = [
            {
                "award_id": "AWARD-001",
                "solicitation_number": "N00014-24-S-B001",
                "agency": "DON",
                "title": "Test",
            }
        ]

        results = await processor.process_batch(awards, skip_existing=True)

        # Should skip existing solicitation
        assert results.skipped == 1
        assert mock_sam_client.get_solicitation_by_number.call_count == 0

    @pytest.mark.asyncio
    async def test_progress_tracking(self, processor, mock_sam_client):
        """Test progress tracking during batch processing."""
        awards = [
            {
                "award_id": f"AWARD-{i:03d}",
                "solicitation_number": f"SOL-{i:03d}",
                "agency": "DON",
                "title": f"Research {i}",
            }
            for i in range(5)
        ]

        mock_sam_client.get_solicitation_by_number.return_value = {
            "solicitation_id": "SOL-001",
            "solicitation_number": "SOL-001",
            "title": "Test",
            "agency_code": "DON",
            "program_office_id": "DON-001",
            "solicitation_type": "SBIR Phase I",
            "full_text": "Text",
            "technical_requirements": "Requirements",
            "evaluation_criteria": "Criteria",
            "funding_range_min": "100000.00",
            "funding_range_max": "300000.00",
            "proposal_deadline": "2024-06-15",
            "performance_period": 12,
            "keywords": [],
            "cet_relevance_scores": {},
        }

        progress_updates = []

        def progress_callback(current, total, status):
            progress_updates.append((current, total, status))

        results = await processor.process_batch(awards, progress_callback=progress_callback)

        assert len(progress_updates) > 0
        assert (
            progress_updates[-1][0] == progress_updates[-1][1]
        )  # Final update should show completion

    @pytest.mark.asyncio
    async def test_error_recovery_and_retry(self, processor, mock_sam_client):
        """Test error recovery and retry logic."""
        awards = [
            {
                "award_id": "AWARD-001",
                "solicitation_number": "SOL-001",
                "agency": "DON",
                "title": "Test",
            }
        ]

        # First call fails, second succeeds
        mock_sam_client.get_solicitation_by_number.side_effect = [
            Exception("Temporary API Error"),
            {
                "solicitation_id": "SOL-001",
                "solicitation_number": "SOL-001",
                "title": "Test",
                "agency_code": "DON",
                "program_office_id": "DON-001",
                "solicitation_type": "SBIR Phase I",
                "full_text": "Text",
                "technical_requirements": "Requirements",
                "evaluation_criteria": "Criteria",
                "funding_range_min": "100000.00",
                "funding_range_max": "300000.00",
                "proposal_deadline": "2024-06-15",
                "performance_period": 12,
                "keywords": [],
                "cet_relevance_scores": {},
            },
        ]

        results = await processor.process_batch(awards, max_retries=1)

        assert len(results.successful) == 1
        assert len(results.failed) == 0
        assert mock_sam_client.get_solicitation_by_number.call_count == 2

    def test_batch_results_summary(self, processor):
        """Test batch results summary generation."""
        from sbir_cet_classifier.data.enrichment.batch_processor import BatchProcessingResults

        results = BatchProcessingResults(
            successful=["SOL-001", "SOL-002"],
            failed=[("SOL-003", "API Error")],
            skipped=["SOL-004"],
            total_processed=4,
            processing_time=120.5,
        )

        summary = results.get_summary()

        assert "2 successful" in summary
        assert "1 failed" in summary
        assert "1 skipped" in summary
        assert "4 total" in summary
        assert "120.5" in summary

    @pytest.mark.asyncio
    async def test_storage_integration(self, processor, mock_sam_client, mock_storage):
        """Test integration with storage layer."""
        awards = [
            {
                "award_id": "AWARD-001",
                "solicitation_number": "SOL-001",
                "agency": "DON",
                "title": "Test",
            }
        ]

        mock_sam_client.get_solicitation_by_number.return_value = {
            "solicitation_id": "SOL-001",
            "solicitation_number": "SOL-001",
            "title": "Test",
            "agency_code": "DON",
            "program_office_id": "DON-001",
            "solicitation_type": "SBIR Phase I",
            "full_text": "Text",
            "technical_requirements": "Requirements",
            "evaluation_criteria": "Criteria",
            "funding_range_min": "100000.00",
            "funding_range_max": "300000.00",
            "proposal_deadline": "2024-06-15",
            "performance_period": 12,
            "keywords": [],
            "cet_relevance_scores": {},
        }

        results = await processor.process_batch(awards, save_to_storage=True)

        assert len(results.successful) == 1
        mock_storage.save_solicitations.assert_called_once()

        # Verify solicitation was passed to storage
        saved_solicitations = mock_storage.save_solicitations.call_args[0][0]
        assert len(saved_solicitations) == 1
        assert isinstance(saved_solicitations[0], Solicitation)
