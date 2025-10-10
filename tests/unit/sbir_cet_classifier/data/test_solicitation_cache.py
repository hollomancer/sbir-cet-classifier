"""Unit tests for SQLite solicitation cache."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from sbir_cet_classifier.data.solicitation_cache import (
    CachedSolicitation,
    SolicitationCache,
)


@pytest.fixture
def temp_cache_path(tmp_path: Path) -> Path:
    """Provide temporary cache database path."""
    return tmp_path / "test_cache.db"


class TestSolicitationCacheInit:
    """Tests for cache initialization."""

    def test_cache_creates_database_file(self, temp_cache_path: Path) -> None:
        """Should create database file on initialization."""
        assert not temp_cache_path.exists()

        cache = SolicitationCache(temp_cache_path)
        cache.close()

        assert temp_cache_path.exists()

    def test_cache_creates_parent_directories(self, tmp_path: Path) -> None:
        """Should create parent directories if they don't exist."""
        nested_path = tmp_path / "subdir1" / "subdir2" / "cache.db"
        assert not nested_path.parent.exists()

        cache = SolicitationCache(nested_path)
        cache.close()

        assert nested_path.exists()
        assert nested_path.parent.exists()

    def test_cache_initializes_schema(self, temp_cache_path: Path) -> None:
        """Should initialize database schema."""
        cache = SolicitationCache(temp_cache_path)

        # Verify tables exist by attempting to query
        cursor = cache.connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='solicitations'"
        )
        table = cursor.fetchone()

        assert table is not None
        assert table[0] == "solicitations"

        cache.close()

    def test_cache_works_as_context_manager(self, temp_cache_path: Path) -> None:
        """Should work as context manager."""
        with SolicitationCache(temp_cache_path) as cache:
            assert cache.connection is not None

        # Connection should be closed after context exit


class TestPutAndGet:
    """Tests for put and get operations."""

    def test_put_and_get_solicitation(self, temp_cache_path: Path) -> None:
        """Should store and retrieve solicitation."""
        cache = SolicitationCache(temp_cache_path)

        cache.put(
            "grants.gov",
            "SOL-2024-001",
            "SBIR Phase I Research Program",
            ["AI", "robotics", "autonomy"],
        )

        result = cache.get("grants.gov", "SOL-2024-001")

        assert result is not None
        assert isinstance(result, CachedSolicitation)
        assert result.api_source == "grants.gov"
        assert result.solicitation_id == "SOL-2024-001"
        assert result.description == "SBIR Phase I Research Program"
        assert result.technical_keywords == ["AI", "robotics", "autonomy"]
        assert isinstance(result.retrieved_at, datetime)

        cache.close()

    def test_get_returns_none_for_nonexistent(self, temp_cache_path: Path) -> None:
        """Should return None for nonexistent solicitation."""
        cache = SolicitationCache(temp_cache_path)

        result = cache.get("grants.gov", "NONEXISTENT")

        assert result is None

        cache.close()

    def test_put_replaces_existing_entry(self, temp_cache_path: Path) -> None:
        """Should replace existing entry on duplicate key."""
        cache = SolicitationCache(temp_cache_path)

        # First insert
        cache.put("grants.gov", "SOL-001", "Original description", ["keyword1"])

        # Second insert with same key
        cache.put("grants.gov", "SOL-001", "Updated description", ["keyword2"])

        result = cache.get("grants.gov", "SOL-001")

        assert result is not None
        assert result.description == "Updated description"
        assert result.technical_keywords == ["keyword2"]

        cache.close()

    def test_put_handles_empty_keywords(self, temp_cache_path: Path) -> None:
        """Should handle empty keyword list."""
        cache = SolicitationCache(temp_cache_path)

        cache.put("grants.gov", "SOL-001", "Description", [])

        result = cache.get("grants.gov", "SOL-001")

        assert result is not None
        assert result.technical_keywords == []

        cache.close()

    def test_put_handles_special_characters(self, temp_cache_path: Path) -> None:
        """Should handle special characters in description."""
        cache = SolicitationCache(temp_cache_path)

        description = "SBIR Phase I: R&D for AI/ML & IoT systems (2024)"
        cache.put("grants.gov", "SOL-001", description, ["AI/ML"])

        result = cache.get("grants.gov", "SOL-001")

        assert result is not None
        assert result.description == description
        assert result.technical_keywords == ["AI/ML"]

        cache.close()


class TestCacheByAPISource:
    """Tests for caching across different API sources."""

    def test_same_id_different_api_sources(self, temp_cache_path: Path) -> None:
        """Should store same solicitation ID from different API sources separately."""
        cache = SolicitationCache(temp_cache_path)

        cache.put("grants.gov", "12345", "Grants.gov description", ["keyword1"])
        cache.put("nih", "12345", "NIH description", ["keyword2"])
        cache.put("nsf", "12345", "NSF description", ["keyword3"])

        grants_result = cache.get("grants.gov", "12345")
        nih_result = cache.get("nih", "12345")
        nsf_result = cache.get("nsf", "12345")

        assert grants_result is not None
        assert nih_result is not None
        assert nsf_result is not None

        assert grants_result.description == "Grants.gov description"
        assert nih_result.description == "NIH description"
        assert nsf_result.description == "NSF description"

        cache.close()


class TestPurgeOperations:
    """Tests for purge operations."""

    def test_purge_by_api_source(self, temp_cache_path: Path) -> None:
        """Should purge all entries for specific API source."""
        cache = SolicitationCache(temp_cache_path)

        # Add entries for multiple API sources
        cache.put("grants.gov", "SOL-001", "Grants 1", ["kw1"])
        cache.put("grants.gov", "SOL-002", "Grants 2", ["kw2"])
        cache.put("nih", "SOL-003", "NIH 1", ["kw3"])
        cache.put("nsf", "SOL-004", "NSF 1", ["kw4"])

        # Purge grants.gov entries
        purged_count = cache.purge_by_api_source("grants.gov")

        assert purged_count == 2

        # Verify grants.gov entries removed
        assert cache.get("grants.gov", "SOL-001") is None
        assert cache.get("grants.gov", "SOL-002") is None

        # Verify other sources still exist
        assert cache.get("nih", "SOL-003") is not None
        assert cache.get("nsf", "SOL-004") is not None

        cache.close()

    def test_purge_by_solicitation_id(self, temp_cache_path: Path) -> None:
        """Should purge entries matching solicitation ID across all sources."""
        cache = SolicitationCache(temp_cache_path)

        # Add same solicitation ID across multiple sources
        cache.put("grants.gov", "SOL-001", "Grants description", ["kw1"])
        cache.put("nih", "SOL-001", "NIH description", ["kw2"])
        cache.put("nsf", "SOL-002", "NSF description", ["kw3"])

        # Purge SOL-001 across all sources
        purged_count = cache.purge_by_solicitation_id("SOL-001")

        assert purged_count == 2

        # Verify SOL-001 removed from all sources
        assert cache.get("grants.gov", "SOL-001") is None
        assert cache.get("nih", "SOL-001") is None

        # Verify SOL-002 still exists
        assert cache.get("nsf", "SOL-002") is not None

        cache.close()

    def test_purge_by_date_range_end_only(self, temp_cache_path: Path) -> None:
        """Should purge entries before end date."""
        cache = SolicitationCache(temp_cache_path)

        # Manually insert entries with specific timestamps
        old_time = (datetime.now(UTC) - timedelta(days=30)).isoformat()
        recent_time = datetime.now(UTC).isoformat()

        cache.connection.execute(
            "INSERT INTO solicitations VALUES (?, ?, ?, ?, ?)",
            ("grants.gov", "OLD-001", "Old description", '["kw"]', old_time),
        )
        cache.connection.execute(
            "INSERT INTO solicitations VALUES (?, ?, ?, ?, ?)",
            ("grants.gov", "RECENT-001", "Recent description", '["kw"]', recent_time),
        )
        cache.connection.commit()

        # Purge entries older than 15 days
        cutoff = datetime.now(UTC) - timedelta(days=15)
        purged_count = cache.purge_by_date_range(end_date=cutoff)

        assert purged_count == 1

        # Verify old entry removed, recent entry preserved
        assert cache.get("grants.gov", "OLD-001") is None
        assert cache.get("grants.gov", "RECENT-001") is not None

        cache.close()

    def test_purge_by_date_range_start_only(self, temp_cache_path: Path) -> None:
        """Should purge entries after start date."""
        cache = SolicitationCache(temp_cache_path)

        old_time = (datetime.now(UTC) - timedelta(days=30)).isoformat()
        recent_time = datetime.now(UTC).isoformat()

        cache.connection.execute(
            "INSERT INTO solicitations VALUES (?, ?, ?, ?, ?)",
            ("grants.gov", "OLD-001", "Old description", '["kw"]', old_time),
        )
        cache.connection.execute(
            "INSERT INTO solicitations VALUES (?, ?, ?, ?, ?)",
            ("grants.gov", "RECENT-001", "Recent description", '["kw"]', recent_time),
        )
        cache.connection.commit()

        # Purge entries newer than 15 days ago
        cutoff = datetime.now(UTC) - timedelta(days=15)
        purged_count = cache.purge_by_date_range(start_date=cutoff)

        assert purged_count == 1

        # Verify recent entry removed, old entry preserved
        assert cache.get("grants.gov", "OLD-001") is not None
        assert cache.get("grants.gov", "RECENT-001") is None

        cache.close()

    def test_purge_by_date_range_requires_at_least_one_date(self, temp_cache_path: Path) -> None:
        """Should raise ValueError if no dates provided."""
        cache = SolicitationCache(temp_cache_path)

        with pytest.raises(ValueError, match="Must specify at least one"):
            cache.purge_by_date_range()

        cache.close()

    def test_purge_by_api_source_nonexistent(self, temp_cache_path: Path) -> None:
        """Should return 0 when purging nonexistent API source."""
        cache = SolicitationCache(temp_cache_path)

        purged_count = cache.purge_by_api_source("nonexistent")

        assert purged_count == 0

        cache.close()


class TestCacheStats:
    """Tests for cache statistics."""

    def test_get_cache_stats_empty(self, temp_cache_path: Path) -> None:
        """Should return stats for empty cache."""
        cache = SolicitationCache(temp_cache_path)

        stats = cache.get_cache_stats()

        assert stats["total_entries"] == 0
        assert stats["by_api_source"] == {}
        assert stats["oldest_entry"] is None
        assert stats["newest_entry"] is None
        assert stats["cache_path"] == str(temp_cache_path)

        cache.close()

    def test_get_cache_stats_with_entries(self, temp_cache_path: Path) -> None:
        """Should return stats with entry counts."""
        cache = SolicitationCache(temp_cache_path)

        cache.put("grants.gov", "SOL-001", "Description 1", ["kw1"])
        cache.put("grants.gov", "SOL-002", "Description 2", ["kw2"])
        cache.put("nih", "SOL-003", "Description 3", ["kw3"])
        cache.put("nsf", "SOL-004", "Description 4", ["kw4"])
        cache.put("nsf", "SOL-005", "Description 5", ["kw5"])

        stats = cache.get_cache_stats()

        assert stats["total_entries"] == 5
        assert stats["by_api_source"]["grants.gov"] == 2
        assert stats["by_api_source"]["nih"] == 1
        assert stats["by_api_source"]["nsf"] == 2
        assert stats["oldest_entry"] is not None
        assert stats["newest_entry"] is not None

        cache.close()


class TestCachePersistence:
    """Tests for cache persistence across sessions."""

    def test_cache_persists_across_sessions(self, temp_cache_path: Path) -> None:
        """Should persist data across cache sessions."""
        # Session 1: Write data
        cache1 = SolicitationCache(temp_cache_path)
        cache1.put("grants.gov", "SOL-001", "Persistent description", ["keyword"])
        cache1.close()

        # Session 2: Read data
        cache2 = SolicitationCache(temp_cache_path)
        result = cache2.get("grants.gov", "SOL-001")

        assert result is not None
        assert result.description == "Persistent description"
        assert result.technical_keywords == ["keyword"]

        cache2.close()

    def test_cache_handles_existing_database(self, temp_cache_path: Path) -> None:
        """Should open existing database without errors."""
        # Create cache first time
        cache1 = SolicitationCache(temp_cache_path)
        cache1.put("grants.gov", "SOL-001", "Description", ["kw"])
        cache1.close()

        # Open same database again
        cache2 = SolicitationCache(temp_cache_path)
        result = cache2.get("grants.gov", "SOL-001")

        assert result is not None

        cache2.close()


class TestConcurrency:
    """Tests for concurrent cache operations."""

    def test_multiple_puts_same_key(self, temp_cache_path: Path) -> None:
        """Should handle multiple puts to same key (last write wins)."""
        cache = SolicitationCache(temp_cache_path)

        cache.put("grants.gov", "SOL-001", "Version 1", ["kw1"])
        cache.put("grants.gov", "SOL-001", "Version 2", ["kw2"])
        cache.put("grants.gov", "SOL-001", "Version 3", ["kw3"])

        result = cache.get("grants.gov", "SOL-001")

        assert result is not None
        assert result.description == "Version 3"
        assert result.technical_keywords == ["kw3"]

        cache.close()


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_get_with_malformed_json_keywords(self, temp_cache_path: Path) -> None:
        """Should handle malformed JSON in keywords gracefully."""
        cache = SolicitationCache(temp_cache_path)

        # Manually insert malformed data
        cache.connection.execute(
            "INSERT INTO solicitations VALUES (?, ?, ?, ?, ?)",
            ("grants.gov", "BAD-001", "Description", "not valid json", datetime.now(UTC).isoformat()),
        )
        cache.connection.commit()

        result = cache.get("grants.gov", "BAD-001")

        # Should return None gracefully
        assert result is None

        cache.close()

    def test_put_with_very_long_description(self, temp_cache_path: Path) -> None:
        """Should handle very long descriptions."""
        cache = SolicitationCache(temp_cache_path)

        long_description = "x" * 100000  # 100k characters

        cache.put("grants.gov", "SOL-001", long_description, ["kw"])

        result = cache.get("grants.gov", "SOL-001")

        assert result is not None
        assert len(result.description) == 100000

        cache.close()

    def test_put_with_many_keywords(self, temp_cache_path: Path) -> None:
        """Should handle large keyword lists."""
        cache = SolicitationCache(temp_cache_path)

        many_keywords = [f"keyword_{i}" for i in range(1000)]

        cache.put("grants.gov", "SOL-001", "Description", many_keywords)

        result = cache.get("grants.gov", "SOL-001")

        assert result is not None
        assert len(result.technical_keywords) == 1000

        cache.close()
