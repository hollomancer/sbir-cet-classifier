"""Tests for enrichment CLI commands."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from click.testing import CliRunner
from pathlib import Path
import json
import click

from sbir_cet_classifier.cli.commands import (
    enrich_single,
    enrich_batch,
    enrichment_status as enrich_status,
)


class TestEnrichSingleCommand:
    """Test single award enrichment command."""

    @pytest.fixture
    def runner(self):
        """Create CLI test runner."""
        return CliRunner()

    @pytest.fixture
    def mock_enricher(self):
        """Mock enrichment service."""
        with patch("sbir_cet_classifier.cli.commands.EnrichmentService") as mock:
            yield mock.return_value

    def test_enrich_single_success(self, runner, mock_enricher):
        """Test successful single award enrichment."""
        # Mock successful enrichment
        mock_enricher.enrich_award.return_value = {
            "award_id": "AWARD-001",
            "status": "completed",
            "confidence_score": 0.95,
            "enrichment_types": ["awardee", "program_office"],
        }

        result = runner.invoke(enrich_single, ["AWARD-001"])

        assert result.exit_code == 0
        assert "AWARD-001" in result.output
        assert "completed" in result.output
        mock_enricher.enrich_award.assert_called_once_with("AWARD-001", None)

    def test_enrich_single_with_types(self, runner, mock_enricher):
        """Test single award enrichment with specific types."""
        mock_enricher.enrich_award.return_value = {
            "award_id": "AWARD-001",
            "status": "completed",
            "confidence_score": 0.90,
            "enrichment_types": ["awardee"],
        }

        result = runner.invoke(enrich_single, ["AWARD-001", "--types", "awardee"])

        assert result.exit_code == 0
        mock_enricher.enrich_award.assert_called_once_with("AWARD-001", ["awardee"])

    def test_enrich_single_failure(self, runner, mock_enricher):
        """Test single award enrichment failure."""
        mock_enricher.enrich_award.side_effect = Exception("API error")

        result = runner.invoke(enrich_single, ["AWARD-001"])

        assert result.exit_code == 1
        assert "Error" in result.output

    def test_enrich_single_json_output(self, runner, mock_enricher):
        """Test single award enrichment with JSON output."""
        mock_result = {
            "award_id": "AWARD-001",
            "status": "completed",
            "confidence_score": 0.95,
            "enrichment_types": ["awardee"],
        }
        mock_enricher.enrich_award.return_value = mock_result

        result = runner.invoke(enrich_single, ["AWARD-001", "--output-format", "json"])

        assert result.exit_code == 0
        output_data = json.loads(result.output)
        assert output_data["award_id"] == "AWARD-001"
        assert output_data["status"] == "completed"


class TestEnrichBatchCommand:
    """Test batch enrichment command."""

    @pytest.fixture
    def runner(self):
        """Create CLI test runner."""
        return CliRunner()

    @pytest.fixture
    def mock_batch_enricher(self):
        """Mock batch enrichment service."""
        with patch("sbir_cet_classifier.cli.commands.BatchEnrichmentService") as mock:
            yield mock.return_value

    @pytest.fixture
    def temp_award_file(self, tmp_path):
        """Create temporary award file."""
        award_file = tmp_path / "awards.csv"
        award_file.write_text("award_id,title\nAWARD-001,Test Award 1\nAWARD-002,Test Award 2\n")
        return str(award_file)

    def test_enrich_batch_success(self, runner, mock_batch_enricher, temp_award_file):
        """Test successful batch enrichment."""
        mock_batch_enricher.enrich_batch.return_value = {
            "total_processed": 2,
            "successful": 2,
            "failed": 0,
            "success_rate": 1.0,
        }

        result = runner.invoke(
            enrich_batch, ["--input-file", temp_award_file, "--batch-size", "10"]
        )

        assert result.exit_code == 0
        assert "2" in result.output  # Total processed
        mock_batch_enricher.enrich_batch.assert_called_once()

    def test_enrich_batch_with_progress(self, runner, mock_batch_enricher, temp_award_file):
        """Test batch enrichment with progress reporting."""

        # Mock progress callback
        def mock_enrich_with_progress(*args, **kwargs):
            progress_callback = kwargs.get("progress_callback")
            if progress_callback:
                progress_callback(1, 2)  # 1 of 2 completed
                progress_callback(2, 2)  # 2 of 2 completed
            return {"total_processed": 2, "successful": 2, "failed": 0, "success_rate": 1.0}

        mock_batch_enricher.enrich_batch.side_effect = mock_enrich_with_progress

        result = runner.invoke(enrich_batch, ["--input-file", temp_award_file, "--show-progress"])

        assert result.exit_code == 0

    def test_enrich_batch_parallel(self, runner, mock_batch_enricher, temp_award_file):
        """Test batch enrichment with parallel processing."""
        mock_batch_enricher.enrich_batch.return_value = {
            "total_processed": 2,
            "successful": 2,
            "failed": 0,
            "success_rate": 1.0,
        }

        result = runner.invoke(
            enrich_batch, ["--input-file", temp_award_file, "--parallel", "--max-workers", "4"]
        )

        assert result.exit_code == 0

    def test_enrich_batch_resume(self, runner, mock_batch_enricher, temp_award_file):
        """Test batch enrichment resume functionality."""
        mock_batch_enricher.resume_batch.return_value = {
            "total_processed": 1,
            "successful": 1,
            "failed": 0,
            "success_rate": 1.0,
            "resumed_from": 1,
        }

        result = runner.invoke(enrich_batch, ["--input-file", temp_award_file, "--resume"])

        assert result.exit_code == 0
        mock_batch_enricher.resume_batch.assert_called_once()


class TestEnrichStatusCommand:
    """Test enrichment status command."""

    @pytest.fixture
    def runner(self):
        """Create CLI test runner."""
        return CliRunner()

    @pytest.fixture
    def mock_status_tracker(self):
        """Mock status tracker."""
        with patch("sbir_cet_classifier.cli.commands.EnrichmentStatusTracker") as mock:
            yield mock.return_value

    def test_status_summary(self, runner, mock_status_tracker):
        """Test status summary display."""
        mock_status_tracker.get_summary.return_value = {
            "total": 100,
            "completed": 85,
            "failed": 10,
            "pending": 5,
            "success_rate": 0.85,
        }

        result = runner.invoke(enrich_status, ["--summary"])

        assert result.exit_code == 0
        assert "100" in result.output  # Total
        assert "85" in result.output  # Completed
        assert "85%" in result.output  # Success rate

    def test_status_by_award(self, runner, mock_status_tracker):
        """Test status for specific award."""
        from sbir_cet_classifier.data.enrichment.status import EnrichmentStatus
        from datetime import datetime

        mock_status = EnrichmentStatus(
            award_id="AWARD-001",
            enrichment_types=[EnrichmentType.AWARDEE],
            status=StatusState.COMPLETED,
            confidence_score=0.95,
            last_updated=datetime(2024, 1, 15),
            error_message=None,
            data_sources=["SAM.gov API"],
        )
        mock_status_tracker.get_status.return_value = mock_status

        result = runner.invoke(enrich_status, ["--award-id", "AWARD-001"])

        assert result.exit_code == 0
        assert "AWARD-001" in result.output
        assert "completed" in result.output

    def test_status_failed_only(self, runner, mock_status_tracker):
        """Test listing only failed enrichments."""
        mock_failed_statuses = [
            Mock(award_id="AWARD-001", status=StatusState.FAILED, error_message="API error"),
            Mock(award_id="AWARD-002", status=StatusState.FAILED, error_message="Rate limit"),
        ]
        mock_status_tracker.list_statuses.return_value = mock_failed_statuses

        result = runner.invoke(enrich_status, ["--failed-only"])

        assert result.exit_code == 0
        assert "AWARD-001" in result.output
        assert "AWARD-002" in result.output
        mock_status_tracker.list_statuses.assert_called_with(status_filter=StatusState.FAILED)


class TestEnrichAwardeeCommand:
    """Test awardee-specific enrichment command."""

    @pytest.fixture
    def runner(self):
        """Create CLI test runner."""
        return CliRunner()

    @pytest.fixture
    def mock_awardee_service(self):
        """Mock awardee enrichment service."""
        with patch("sbir_cet_classifier.cli.commands.AwardeeEnrichmentService") as mock:
            yield mock.return_value

    def test_enrich_awardee_success(self, runner, mock_awardee_service):
        """Test successful awardee enrichment."""
        mock_awardee_service.enrich_awardee.return_value = {
            "award_id": "AWARD-001",
            "awardee_uei": "ABC123DEF456",
            "confidence_score": 0.95,
            "data_sources": ["SAM.gov API"],
        }

        result = runner.invoke(enrich_awardee, ["AWARD-001"])

        assert result.exit_code == 0
        assert "AWARD-001" in result.output
        mock_awardee_service.enrich_awardee.assert_called_once_with("AWARD-001")

    def test_enrich_awardee_with_confidence_threshold(self, runner, mock_awardee_service):
        """Test awardee enrichment with confidence threshold."""
        mock_awardee_service.enrich_awardee.return_value = {
            "award_id": "AWARD-001",
            "awardee_uei": "ABC123DEF456",
            "confidence_score": 0.60,
            "data_sources": ["SAM.gov API"],
        }

        result = runner.invoke(enrich_awardee, ["AWARD-001", "--min-confidence", "0.8"])

        # Should warn about low confidence
        assert result.exit_code == 0
        assert "confidence" in result.output.lower()


class TestEnrichProgramCommand:
    """Test program office enrichment command."""

    @pytest.fixture
    def runner(self):
        """Create CLI test runner."""
        return CliRunner()

    @pytest.fixture
    def mock_program_service(self):
        """Mock program office enrichment service."""
        with patch("sbir_cet_classifier.cli.commands.ProgramOfficeEnrichmentService") as mock:
            yield mock.return_value

    def test_enrich_program_success(self, runner, mock_program_service):
        """Test successful program office enrichment."""
        mock_program_service.enrich_program_office.return_value = {
            "award_id": "AWARD-001",
            "agency": "NSF",
            "office_name": "CISE",
            "strategic_focus": ["AI", "Cybersecurity"],
        }

        result = runner.invoke(enrich_program, ["AWARD-001"])

        assert result.exit_code == 0
        assert "AWARD-001" in result.output
        mock_program_service.enrich_program_office.assert_called_once_with("AWARD-001")


class TestEnrichSolicitationCommand:
    """Test solicitation enrichment command."""

    @pytest.fixture
    def runner(self):
        """Create CLI test runner."""
        return CliRunner()

    @pytest.fixture
    def mock_solicitation_service(self):
        """Mock solicitation enrichment service."""
        with patch("sbir_cet_classifier.cli.commands.SolicitationEnrichmentService") as mock:
            yield mock.return_value

    def test_enrich_solicitation_success(self, runner, mock_solicitation_service):
        """Test successful solicitation enrichment."""
        mock_solicitation_service.enrich_solicitation.return_value = {
            "award_id": "AWARD-001",
            "solicitation_id": "SOL-2024-001",
            "technical_requirements": ["AI", "Machine Learning"],
            "topic_areas": ["Computer Science"],
        }

        result = runner.invoke(enrich_solicitation, ["AWARD-001"])

        assert result.exit_code == 0
        assert "AWARD-001" in result.output
        mock_solicitation_service.enrich_solicitation.assert_called_once_with("AWARD-001")


class TestEnrichModificationsCommand:
    """Test award modifications enrichment command."""

    @pytest.fixture
    def runner(self):
        """Create CLI test runner."""
        return CliRunner()

    @pytest.fixture
    def mock_modifications_service(self):
        """Mock modifications enrichment service."""
        with patch("sbir_cet_classifier.cli.commands.ModificationsEnrichmentService") as mock:
            yield mock.return_value

    def test_enrich_modifications_success(self, runner, mock_modifications_service):
        """Test successful modifications enrichment."""
        mock_modifications_service.enrich_modifications.return_value = {
            "award_id": "AWARD-001",
            "modifications_count": 2,
            "total_funding_change": 50000.0,
            "modification_types": ["Funding Increase", "Scope Change"],
        }

        result = runner.invoke(enrich_modifications, ["AWARD-001"])

        assert result.exit_code == 0
        assert "AWARD-001" in result.output
        mock_modifications_service.enrich_modifications.assert_called_once_with("AWARD-001")


class TestCLIIntegration:
    """Test CLI integration scenarios."""

    @pytest.fixture
    def runner(self):
        """Create CLI test runner."""
        return CliRunner()

    def test_help_messages(self, runner):
        """Test that all commands show proper help."""
        commands = [
            enrich_single,
            enrich_batch,
            enrich_status,
            enrich_awardee,
            enrich_program,
            enrich_solicitation,
            enrich_modifications,
        ]

        for command in commands:
            result = runner.invoke(command, ["--help"])
            assert result.exit_code == 0
            assert "Usage:" in result.output

    def test_invalid_arguments(self, runner):
        """Test handling of invalid arguments."""
        # Test missing required argument
        result = runner.invoke(enrich_single, [])
        assert result.exit_code != 0

        # Test invalid option
        result = runner.invoke(enrich_single, ["AWARD-001", "--invalid-option"])
        assert result.exit_code != 0

    @patch("sbir_cet_classifier.cli.commands.EnrichmentService")
    def test_verbose_output(self, mock_service, runner):
        """Test verbose output mode."""
        mock_service.return_value.enrich_award.return_value = {
            "award_id": "AWARD-001",
            "status": "completed",
            "confidence_score": 0.95,
        }

        result = runner.invoke(enrich_single, ["AWARD-001", "--verbose"])

        assert result.exit_code == 0
        # Verbose mode should show more detailed output
        assert len(result.output) > 50  # Should be more than minimal output

    @patch("sbir_cet_classifier.cli.commands.EnrichmentService")
    def test_quiet_output(self, mock_service, runner):
        """Test quiet output mode."""
        mock_service.return_value.enrich_award.return_value = {
            "award_id": "AWARD-001",
            "status": "completed",
            "confidence_score": 0.95,
        }

        result = runner.invoke(enrich_single, ["AWARD-001", "--quiet"])

        assert result.exit_code == 0
        # Quiet mode should show minimal output
        assert len(result.output) < 50

    def test_configuration_loading(self, runner):
        """Test that CLI commands load configuration properly."""
        with patch("sbir_cet_classifier.cli.commands.load_config") as mock_load_config:
            mock_load_config.return_value = {"sam_api": {"base_url": "test"}}

            result = runner.invoke(enrich_status, ["--summary"])

            # Should attempt to load configuration
            mock_load_config.assert_called()

    def test_error_handling(self, runner):
        """Test error handling in CLI commands."""
        with patch("sbir_cet_classifier.cli.commands.EnrichmentService") as mock_service:
            # Simulate service initialization error
            mock_service.side_effect = Exception("Configuration error")

            result = runner.invoke(enrich_single, ["AWARD-001"])

            assert result.exit_code == 1
            assert "Error" in result.output
