"""Integration tests for complete enrichment pipeline.

Tests end-to-end enrichment workflow:
- Award → Enrichment Orchestrator → Cache/API → Classification
- Cache hit/miss scenarios
- Batch enrichment optimization
- Classification with enriched vs. award-only data
- Graceful degradation on API failures
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from sbir_cet_classifier.common.schemas import Award
from sbir_cet_classifier.data.external.nih import SolicitationData as NIHSolicitation
from sbir_cet_classifier.data.solicitation_cache import SolicitationCache
from sbir_cet_classifier.features.batch_enrichment import BatchEnrichmentOptimizer
from sbir_cet_classifier.features.enrichment import EnrichmentOrchestrator
from sbir_cet_classifier.models.applicability import (
    build_enriched_text,
    prepare_award_text_for_classification,
)
from sbir_cet_classifier.models.enrichment_metrics import EnrichmentMetrics


@pytest.fixture
def temp_cache_path(tmp_path: Path) -> Path:
    """Provide temporary cache database path."""
    return tmp_path / "test_cache.db"


@pytest.fixture
def temp_artifacts_dir(tmp_path: Path) -> Path:
    """Provide temporary artifacts directory."""
    artifacts_dir = tmp_path / "artifacts"
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    return artifacts_dir


@pytest.fixture
def sample_awards() -> list[Award]:
    """Create sample awards for testing."""
    return [
        Award(
            award_id="DOD-001",
            agency="DOD",
            sub_agency="DARPA",
            topic_code="AF241-001",
            abstract="Advanced AI algorithms for autonomous systems",
            keywords=["AI", "machine learning", "autonomy"],
            phase="I",
            firm_name="TechCorp",
            firm_city="Boston",
            firm_state="MA",
            award_amount=150000.0,
            award_date=datetime(2024, 1, 15).date(),
            source_version="test",
            ingested_at=datetime.now(UTC),
        ),
        Award(
            award_id="NIH-001",
            agency="NIH",
            topic_code="PA-23-123",
            abstract="Novel cancer treatment using immunotherapy",
            keywords=["cancer", "immunotherapy", "treatment"],
            phase="II",
            firm_name="BioTech",
            firm_city="San Diego",
            firm_state="CA",
            award_amount=750000.0,
            award_date=datetime(2023, 6, 1).date(),
            source_version="test",
            ingested_at=datetime.now(UTC),
        ),
    ]


@pytest.fixture
def mock_api_responses() -> dict[str, object | None]:
    """Mock API responses for different solicitations."""
    return {
        "AF241-001": NIHSolicitation(
            solicitation_id="AF241-001",
            description="SBIR Phase I: Artificial Intelligence for Defense Applications",
            technical_keywords=["artificial intelligence", "defense", "autonomy", "machine learning"],
            api_source="grants.gov",
        ),
        "PA-23-123": NIHSolicitation(
            solicitation_id="PA-23-123",
            description="NIH SBIR: Cancer Immunotherapy Research",
            technical_keywords=["cancer", "immunotherapy", "oncology", "biomedical"],
            api_source="nih",
        ),
    }


class TestEnrichmentPipelineEndToEnd:
    """Test complete enrichment pipeline from award to enriched classification."""

    def test_single_award_enrichment_cache_miss(
        self,
        temp_cache_path: Path,
        temp_artifacts_dir: Path,
        sample_awards: list[Award],
        mock_api_responses: dict,
    ) -> None:
        """Test enriching single award with cache miss (API call required)."""
        award = sample_awards[0]  # DOD award

        with patch("sbir_cet_classifier.data.external.nih.NIHClient") as mock_client_class:
            # Mock API client
            mock_client = MagicMock()
            mock_client.lookup_solicitation.return_value = mock_api_responses["AF241-001"]
            mock_client_class.return_value = mock_client

            # Create orchestrator with temp cache
            metrics = EnrichmentMetrics(artifacts_dir=temp_artifacts_dir)
            orchestrator = EnrichmentOrchestrator(
                cache_path=temp_cache_path,
                metrics=metrics,
            )

            # Enrich award
            enriched = orchestrator.enrich_award(award)

            # Verify enrichment succeeded
            assert enriched.enrichment_status == "enriched"
            assert enriched.solicitation_description is not None
            assert "Artificial Intelligence for Defense" in enriched.solicitation_description
            assert len(enriched.solicitation_keywords) > 0
            assert "artificial intelligence" in enriched.solicitation_keywords
            assert enriched.api_source == "grants.gov"

            # Verify API was called
            mock_client.lookup_solicitation.assert_called_once()

            # Verify cache was populated
            cache = SolicitationCache(temp_cache_path)
            cached = cache.get("grants.gov", "AF241-001")
            assert cached is not None
            assert cached.description == enriched.solicitation_description

            orchestrator.close()

    def test_single_award_enrichment_cache_hit(
        self,
        temp_cache_path: Path,
        temp_artifacts_dir: Path,
        sample_awards: list[Award],
        mock_api_responses: dict,
    ) -> None:
        """Test enriching single award with cache hit (no API call)."""
        award = sample_awards[0]  # DOD award

        # Pre-populate cache
        cache = SolicitationCache(temp_cache_path)
        sol_data = mock_api_responses["AF241-001"]
        cache.put(
            sol_data.api_source,
            sol_data.solicitation_id,
            sol_data.description,
            sol_data.technical_keywords,
        )
        cache.close()

        with patch("sbir_cet_classifier.data.external.nih.NIHClient") as mock_client_class:
            # Mock API client (should NOT be called)
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client

            # Create orchestrator
            metrics = EnrichmentMetrics(artifacts_dir=temp_artifacts_dir)
            orchestrator = EnrichmentOrchestrator(
                cache_path=temp_cache_path,
                metrics=metrics,
            )

            # Enrich award
            enriched = orchestrator.enrich_award(award)

            # Verify enrichment succeeded from cache
            assert enriched.enrichment_status == "enriched"
            assert enriched.solicitation_description is not None
            assert "Artificial Intelligence for Defense" in enriched.solicitation_description

            # Verify API was NOT called (cache hit)
            mock_client.lookup_solicitation.assert_not_called()

            orchestrator.close()

    def test_batch_enrichment_with_duplicate_solicitations(
        self,
        temp_cache_path: Path,
        temp_artifacts_dir: Path,
        mock_api_responses: dict,
    ) -> None:
        """Test batch enrichment deduplicates awards sharing same solicitation."""
        # Create 5 awards, 3 sharing same solicitation
        awards = [
            Award(
                award_id=f"DOD-{i:03d}",
                agency="DOD",
                topic_code="AF241-001",  # Same solicitation
                abstract=f"AI research project {i}",
                keywords=["AI", "autonomy"],
                phase="I",
                firm_name=f"TechCorp{i}",
                firm_city="Boston",
                firm_state="MA",
                award_amount=150000.0,
                award_date=datetime(2024, 1, 15).date(),
                source_version="test",
                ingested_at=datetime.now(UTC),
            )
            for i in range(1, 4)
        ]

        # Add 2 awards with different solicitations
        awards.extend([
            Award(
                award_id="NIH-001",
                agency="NIH",
                topic_code="PA-23-123",
                abstract="Cancer research",
                keywords=["cancer"],
                phase="II",
                firm_name="BioTech",
                firm_city="San Diego",
                firm_state="CA",
                award_amount=750000.0,
                award_date=datetime(2023, 6, 1).date(),
                source_version="test",
                ingested_at=datetime.now(UTC),
            ),
            Award(
                award_id="DOD-004",
                agency="DOD",
                topic_code="AF241-001",  # Same as first 3 DOD awards
                abstract="More AI research",
                keywords=["AI"],
                phase="I",
                firm_name="TechCorp4",
                firm_city="Austin",
                firm_state="TX",
                award_amount=150000.0,
                award_date=datetime(2024, 3, 20).date(),
                source_version="test",
                ingested_at=datetime.now(UTC),
            ),
        ])

        with patch("sbir_cet_classifier.data.external.nih.NIHClient") as mock_grants, \
             patch("sbir_cet_classifier.data.external.nih.NIHClient") as mock_nih:

            # Mock all API clients
            mock_grants.return_value.lookup_solicitation.return_value = mock_api_responses["AF241-001"]
            mock_nih.return_value.lookup_solicitation.return_value = mock_api_responses["PA-23-123"]

            # Create batch optimizer
            metrics = EnrichmentMetrics(artifacts_dir=temp_artifacts_dir)
            optimizer = BatchEnrichmentOptimizer(metrics=metrics)

            # Enrich batch
            enriched_awards = optimizer.enrich_batch(awards)

            # Verify all awards enriched
            assert len(enriched_awards) == 5

            # Verify deduplication - only 2 unique solicitations
            stats = optimizer.get_stats()
            assert stats.total_awards == 5
            assert stats.unique_solicitations == 2
            assert stats.deduplication_ratio == 2 / 5  # 40% unique

            # Verify all DOD awards have same solicitation data
            dod_awards = [ea for ea in enriched_awards if ea.award.award_id.startswith("DOD")]
            assert len(dod_awards) == 4
            for enriched in dod_awards:
                assert enriched.enrichment_status == "enriched"
                assert "Artificial Intelligence for Defense" in enriched.solicitation_description

            optimizer.close()

    def test_enriched_classification_vs_award_only(
        self,
        temp_cache_path: Path,
        temp_artifacts_dir: Path,
        sample_awards: list[Award],
        mock_api_responses: dict,
    ) -> None:
        """Test that enriched text improves classification features."""
        award = sample_awards[0]  # DOD AI award

        # Prepare award-only text
        award_only_text = prepare_award_text_for_classification(
            abstract=award.abstract,
            keywords=award.keywords,
        )

        # Prepare enriched text
        sol_data = mock_api_responses["AF241-001"]
        enriched_text = build_enriched_text(
            award_text=award_only_text,
            solicitation_description=sol_data.description,
            solicitation_keywords=sol_data.technical_keywords,
        )

        # Verify enriched text is longer and contains solicitation keywords
        assert len(enriched_text) > len(award_only_text)
        assert "Defense Applications" in enriched_text
        assert "artificial intelligence" in enriched_text.lower()
        assert award_only_text in enriched_text  # Award text preserved

        # Verify award-only fallback works
        award_only_fallback = build_enriched_text(
            award_text=award_only_text,
            solicitation_description=None,
            solicitation_keywords=None,
        )
        assert award_only_fallback == award_only_text

    def test_graceful_degradation_on_api_failure(
        self,
        temp_cache_path: Path,
        temp_artifacts_dir: Path,
        sample_awards: list[Award],
    ) -> None:
        """Test that enrichment fails gracefully when API unavailable."""
        award = sample_awards[0]  # DOD award

        with patch("sbir_cet_classifier.data.external.nih.NIHClient") as mock_client_class:
            # Mock API to return None (not found / error)
            mock_client = MagicMock()
            mock_client.lookup_solicitation.return_value = None
            mock_client_class.return_value = mock_client

            # Create orchestrator
            metrics = EnrichmentMetrics(artifacts_dir=temp_artifacts_dir)
            orchestrator = EnrichmentOrchestrator(
                cache_path=temp_cache_path,
                metrics=metrics,
            )

            # Enrich award
            enriched = orchestrator.enrich_award(award)

            # Verify enrichment failed gracefully
            assert enriched.enrichment_status == "enrichment_failed"
            assert enriched.solicitation_description is None
            assert enriched.failure_reason is not None
            assert "not found" in enriched.failure_reason.lower() or "error" in enriched.failure_reason.lower()

            # Award data still preserved
            assert enriched.award.award_id == award.award_id

            orchestrator.close()

    def test_multi_agency_enrichment(
        self,
        temp_cache_path: Path,
        temp_artifacts_dir: Path,
        sample_awards: list[Award],
        mock_api_responses: dict,
    ) -> None:
        """Test enrichment across multiple agencies using different APIs."""
        with patch("sbir_cet_classifier.data.external.nih.NIHClient") as mock_grants, \
             patch("sbir_cet_classifier.data.external.nih.NIHClient") as mock_nih:

            # Mock all API clients
            mock_grants.return_value.lookup_solicitation.return_value = mock_api_responses["AF241-001"]
            mock_nih.return_value.lookup_solicitation.return_value = mock_api_responses["PA-23-123"]

            # Create orchestrator
            metrics = EnrichmentMetrics(artifacts_dir=temp_artifacts_dir)
            orchestrator = EnrichmentOrchestrator(
                cache_path=temp_cache_path,
                metrics=metrics,
            )

            # Enrich all awards (DOD, NIH)
            enriched_awards = [orchestrator.enrich_award(award) for award in sample_awards]

            # Verify all enriched successfully
            assert len(enriched_awards) == 2
            assert all(ea.enrichment_status == "enriched" for ea in enriched_awards)

            # Verify correct API source used for each agency
            assert enriched_awards[0].api_source == "grants.gov"  # DOD
            assert enriched_awards[1].api_source == "nih"  # NIH

            # Verify content specific to each agency
            assert "Defense" in enriched_awards[0].solicitation_description
            assert "Cancer" in enriched_awards[1].solicitation_description

            orchestrator.close()

    def test_enrichment_metrics_tracking(
        self,
        temp_cache_path: Path,
        temp_artifacts_dir: Path,
        sample_awards: list[Award],
        mock_api_responses: dict,
    ) -> None:
        """Test that enrichment metrics are properly tracked and persisted."""
        with patch("sbir_cet_classifier.data.external.nih.NIHClient") as mock_grants, \
             patch("sbir_cet_classifier.data.external.nih.NIHClient") as mock_nih:

            # Mock API clients with slight delays
            mock_grants.return_value.lookup_solicitation.return_value = mock_api_responses["AF241-001"]
            mock_nih.return_value.lookup_solicitation.return_value = mock_api_responses["PA-23-123"]

            # Create orchestrator
            metrics = EnrichmentMetrics(artifacts_dir=temp_artifacts_dir)
            orchestrator = EnrichmentOrchestrator(
                cache_path=temp_cache_path,
                metrics=metrics,
            )

            # Enrich first time (all cache misses)
            for award in sample_awards:
                orchestrator.enrich_award(award)

            # Enrich second time (all cache hits)
            for award in sample_awards:
                orchestrator.enrich_award(award)

            # Get metrics summary
            summary = metrics.get_summary()

            # Verify metrics captured
            assert summary["total_awards_processed"] == 4  # 2 awards x 2 passes
            assert summary["awards_enriched"] == 4

            # Verify per-API metrics
            api_sources = summary["api_sources"]
            assert "grants.gov" in api_sources
            assert "nih" in api_sources

            # Verify cache hit tracking
            # First pass: 2 cache misses, Second pass: 2 cache hits
            total_hits = sum(src["cache_hits"] for src in api_sources.values())
            total_misses = sum(src["cache_misses"] for src in api_sources.values())
            assert total_hits == 2
            assert total_misses == 2

            # Flush metrics to file
            metrics_file = orchestrator.flush_metrics()
            assert metrics_file.exists()
            assert metrics_file.name == "enrichment_runs.json"

            orchestrator.close()

    def test_award_without_solicitation_id(
        self,
        temp_cache_path: Path,
        temp_artifacts_dir: Path,
    ) -> None:
        """Test handling of awards without solicitation identifiers."""
        award = Award(
            award_id="NO-SOL-001",
            agency="DOD",
            topic_code="UNKNOWN",  # No valid solicitation ID
            abstract="Research project without topic code",
            keywords=["research"],
            phase="I",
            firm_name="ResearchCorp",
            firm_city="Cambridge",
            firm_state="MA",
            award_amount=100000.0,
            award_date=datetime(2024, 1, 1).date(),
            source_version="test",
            ingested_at=datetime.now(UTC),
        )

        metrics = EnrichmentMetrics(artifacts_dir=temp_artifacts_dir)
        orchestrator = EnrichmentOrchestrator(
            cache_path=temp_cache_path,
            metrics=metrics,
        )

        # Enrich award
        enriched = orchestrator.enrich_award(award)

        # Verify enrichment not attempted
        assert enriched.enrichment_status == "not_attempted"
        assert enriched.failure_reason is not None
        assert "No solicitation" in enriched.failure_reason

        # Award data preserved
        assert enriched.award.award_id == award.award_id

        orchestrator.close()


class TestEnrichmentCacheOperations:
    """Test SQLite cache operations in enrichment workflow."""

    def test_cache_persistence_across_sessions(
        self,
        temp_cache_path: Path,
        mock_api_responses: dict,
    ) -> None:
        """Test that cache persists across orchestrator sessions."""
        sol_data = mock_api_responses["AF241-001"]

        # Session 1: Populate cache
        cache1 = SolicitationCache(temp_cache_path)
        cache1.put(
            sol_data.api_source,
            sol_data.solicitation_id,
            sol_data.description,
            sol_data.technical_keywords,
        )
        cache1.close()

        # Session 2: Retrieve from cache
        cache2 = SolicitationCache(temp_cache_path)
        cached = cache2.get(sol_data.api_source, sol_data.solicitation_id)
        cache2.close()

        # Verify data persisted
        assert cached is not None
        assert cached.description == sol_data.description
        assert cached.technical_keywords == sol_data.technical_keywords

    def test_cache_stats_after_enrichment(
        self,
        temp_cache_path: Path,
        temp_artifacts_dir: Path,
        sample_awards: list[Award],
        mock_api_responses: dict,
    ) -> None:
        """Test cache statistics tracking."""
        with patch("sbir_cet_classifier.data.external.nih.NIHClient") as mock_grants, \
             patch("sbir_cet_classifier.data.external.nih.NIHClient") as mock_nih:

            mock_grants.return_value.lookup_solicitation.return_value = mock_api_responses["AF241-001"]
            mock_nih.return_value.lookup_solicitation.return_value = mock_api_responses["PA-23-123"]

            metrics = EnrichmentMetrics(artifacts_dir=temp_artifacts_dir)
            orchestrator = EnrichmentOrchestrator(
                cache_path=temp_cache_path,
                metrics=metrics,
            )

            # Enrich all awards
            for award in sample_awards:
                orchestrator.enrich_award(award)

            orchestrator.close()

            # Check cache stats
            cache = SolicitationCache(temp_cache_path)
            stats = cache.get_cache_stats()

            assert stats["total_entries"] == 2
            assert stats["by_api_source"]["grants.gov"] == 1
            assert stats["by_api_source"]["nih"] == 1

            cache.close()
