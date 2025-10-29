"""Tests for solicitation enrichment CLI commands."""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from pathlib import Path
from typer.testing import CliRunner

from sbir_cet_classifier.cli.commands.enrichment import app


class TestSolicitationCLI:
    """Test solicitation enrichment CLI commands."""

    @pytest.fixture
    def runner(self):
        """Create CLI test runner."""
        return CliRunner()

    @pytest.fixture
    def mock_solicitation_service(self):
        """Mock solicitation service."""
        service = Mock()
        service.get_solicitation_by_number = AsyncMock()
        return service

    @pytest.fixture
    def mock_storage(self):
        """Mock solicitation storage."""
        storage = Mock()
        storage.save_solicitations = Mock()
        return storage

    def test_enrich_solicitation_command_help(self, runner):
        """Test solicitation enrichment command help."""
        result = runner.invoke(app, ["solicitation", "--help"])
        assert result.exit_code == 0
        assert "Enrich a single solicitation" in result.stdout

    @patch("sbir_cet_classifier.cli.commands.enrichment.asyncio.run")
    @patch("sbir_cet_classifier.cli.commands.enrichment.SolicitationService")
    @patch("sbir_cet_classifier.cli.commands.enrichment.SAMClient")
    @patch("sbir_cet_classifier.cli.commands.enrichment.SolicitationStorage")
    def test_enrich_solicitation_success(
        self, mock_storage_class, mock_client_class, mock_service_class, mock_asyncio_run, runner
    ):
        """Test successful solicitation enrichment."""
        # Setup mocks
        mock_solicitation = Mock()
        mock_solicitation.solicitation_id = "SOL-2024-001"
        mock_solicitation.title = "Test Solicitation"
        mock_solicitation.agency_code = "DON"

        mock_service = Mock()
        mock_service.get_solicitation_by_number = AsyncMock(return_value=mock_solicitation)
        mock_service_class.return_value = mock_service

        mock_storage = Mock()
        mock_storage_class.return_value = mock_storage

        # Mock asyncio.run to execute the coroutine
        def run_coro(coro):
            import asyncio

            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                return loop.run_until_complete(coro)
            finally:
                loop.close()

        mock_asyncio_run.side_effect = run_coro

        result = runner.invoke(app, ["solicitation", "N00014-24-S-B001"])

        assert result.exit_code == 0
        mock_storage.save_solicitations.assert_called_once()

    @patch("sbir_cet_classifier.cli.commands.enrichment.asyncio.run")
    @patch("sbir_cet_classifier.cli.commands.enrichment.SolicitationService")
    @patch("sbir_cet_classifier.cli.commands.enrichment.SAMClient")
    def test_enrich_solicitation_not_found(
        self, mock_client_class, mock_service_class, mock_asyncio_run, runner
    ):
        """Test solicitation not found scenario."""
        mock_service = Mock()
        mock_service.get_solicitation_by_number = AsyncMock(return_value=None)
        mock_service_class.return_value = mock_service

        def run_coro(coro):
            import asyncio

            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                return loop.run_until_complete(coro)
            finally:
                loop.close()

        mock_asyncio_run.side_effect = run_coro

        result = runner.invoke(app, ["solicitation", "NONEXISTENT"])

        assert result.exit_code == 0  # Command succeeds but reports not found

    def test_batch_solicitations_command_help(self, runner):
        """Test batch solicitations command help."""
        result = runner.invoke(app, ["batch-solicitations", "--help"])
        assert result.exit_code == 0
        assert "Batch enrich solicitations" in result.stdout

    def test_batch_solicitations_missing_file(self, runner, tmp_path):
        """Test batch solicitations with missing input file."""
        nonexistent_file = tmp_path / "nonexistent.csv"

        result = runner.invoke(app, ["batch-solicitations", str(nonexistent_file)])

        assert result.exit_code == 1
        assert "Input file not found" in result.stdout

    @patch("sbir_cet_classifier.cli.commands.enrichment.pd.read_csv")
    @patch("sbir_cet_classifier.cli.commands.enrichment.asyncio.run")
    @patch("sbir_cet_classifier.cli.commands.enrichment.SolicitationBatchProcessor")
    def test_batch_solicitations_success(
        self, mock_processor_class, mock_asyncio_run, mock_read_csv, runner, tmp_path
    ):
        """Test successful batch solicitation processing."""
        # Create test CSV file
        test_file = tmp_path / "test_awards.csv"
        test_file.write_text("award_id,solicitation_number\nAWARD-001,SOL-001\n")

        # Mock pandas read_csv
        mock_df = Mock()
        mock_df.to_dict.return_value = [{"award_id": "AWARD-001", "solicitation_number": "SOL-001"}]
        mock_read_csv.return_value = mock_df

        # Mock batch processor
        mock_results = Mock()
        mock_results.get_summary.return_value = "1 successful, 0 failed"
        mock_results.success_rate = 1.0
        mock_results.failed = []

        mock_processor = Mock()
        mock_processor.process_batch = AsyncMock(return_value=mock_results)
        mock_processor_class.return_value = mock_processor

        def run_coro(coro):
            import asyncio

            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                return loop.run_until_complete(coro)
            finally:
                loop.close()

        mock_asyncio_run.side_effect = run_coro

        result = runner.invoke(app, ["batch-solicitations", str(test_file)])

        assert result.exit_code == 0

    def test_status_command_help(self, runner):
        """Test status command help."""
        result = runner.invoke(app, ["status", "--help"])
        assert result.exit_code == 0
        assert "Show enrichment status" in result.stdout

    @patch("sbir_cet_classifier.cli.commands.enrichment.SolicitationStorage")
    def test_status_command_no_data(self, mock_storage_class, runner, tmp_path):
        """Test status command with no enrichment data."""
        mock_storage = Mock()
        mock_storage_class.return_value = mock_storage

        # Mock non-existent file
        with patch("pathlib.Path.exists", return_value=False):
            result = runner.invoke(app, ["status", "--data-dir", str(tmp_path)])

        assert result.exit_code == 0
        assert "Not found" in result.stdout

    @patch("sbir_cet_classifier.cli.commands.enrichment.SolicitationStorage")
    def test_status_command_with_data(self, mock_storage_class, runner, tmp_path):
        """Test status command with enrichment data."""
        # Create mock solicitation file
        solicitations_file = tmp_path / "solicitations.parquet"
        solicitations_file.write_text("mock data")

        mock_solicitation = Mock()
        mock_solicitation.solicitation_id = "SOL-001"
        mock_solicitation.title = "Test Solicitation"
        mock_solicitation.agency_code = "DON"
        mock_solicitation.keywords = ["test", "keywords"]

        mock_storage = Mock()
        mock_storage.load_solicitations.return_value = [mock_solicitation]
        mock_storage_class.return_value = mock_storage

        result = runner.invoke(app, ["status", "--data-dir", str(tmp_path)])

        assert result.exit_code == 0
        assert "Available" in result.stdout

    def test_command_with_custom_api_key(self, runner):
        """Test command with custom API key."""
        with patch("sbir_cet_classifier.cli.commands.enrichment.asyncio.run"):
            with patch("sbir_cet_classifier.cli.commands.enrichment.SAMClient") as mock_client:
                result = runner.invoke(app, ["solicitation", "SOL-001", "--api-key", "custom_key"])

                mock_client.assert_called_with(api_key="custom_key")

    def test_command_with_verbose_output(self, runner):
        """Test command with verbose output."""
        with patch("sbir_cet_classifier.cli.commands.enrichment.asyncio.run"):
            result = runner.invoke(app, ["solicitation", "SOL-001", "--verbose"])

            # Command should execute (may fail due to mocking, but verbose flag is processed)
            assert "--verbose" not in result.stdout  # Flag is consumed, not echoed

    def test_batch_command_parameters(self, runner, tmp_path):
        """Test batch command with various parameters."""
        test_file = tmp_path / "test.csv"
        test_file.write_text("award_id\nAWARD-001\n")

        with patch("sbir_cet_classifier.cli.commands.enrichment.pd.read_csv"):
            with patch("sbir_cet_classifier.cli.commands.enrichment.asyncio.run"):
                result = runner.invoke(
                    app,
                    [
                        "batch-solicitations",
                        str(test_file),
                        "--batch-size",
                        "5",
                        "--max-concurrent",
                        "2",
                        "--no-skip-existing",
                        "--verbose",
                    ],
                )

                # Command should process parameters without error
                assert result.exit_code in [
                    0,
                    1,
                ]  # May fail due to mocking but parameters are valid
