"""SQLite-based solicitation cache for API enrichment.

This module provides persistent caching of solicitation metadata retrieved
from external APIs (Grants.gov, NIH, NSF). Solicitations are cached permanently
unless explicitly invalidated by operators.

The cache is keyed by (API source, solicitation identifier) with indexed lookups
for fast retrieval. Supports selective purging by API source, solicitation ID,
or date range via SQL DELETE operations.

Typical usage:
    from sbir_cet_classifier.data.solicitation_cache import SolicitationCache

    cache = SolicitationCache()

    # Check cache first
    cached = cache.get("grants.gov", "SOL-2023-001")
    if cached:
        print(f"Cache hit: {cached.description}")
    else:
        # Fetch from API and store
        data = fetch_from_api(...)
        cache.put("grants.gov", "SOL-2023-001", data)
"""

from __future__ import annotations

import json
import logging
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# Default cache database location
DEFAULT_CACHE_PATH = Path("artifacts/solicitation_cache.db")

# SQL schema
CREATE_TABLES_SQL = """
CREATE TABLE IF NOT EXISTS solicitations (
    api_source TEXT NOT NULL,
    solicitation_id TEXT NOT NULL,
    description TEXT NOT NULL,
    technical_keywords TEXT NOT NULL,  -- JSON array
    retrieved_at TEXT NOT NULL,  -- ISO 8601 timestamp
    PRIMARY KEY (api_source, solicitation_id)
);

CREATE INDEX IF NOT EXISTS idx_api_source
    ON solicitations(api_source);

CREATE INDEX IF NOT EXISTS idx_solicitation_id
    ON solicitations(solicitation_id);

CREATE INDEX IF NOT EXISTS idx_retrieved_at
    ON solicitations(retrieved_at);
"""


@dataclass
class CachedSolicitation:
    """Represents a cached solicitation entry."""

    api_source: str
    """API source identifier (grants.gov, nih, nsf)."""

    solicitation_id: str
    """Solicitation identifier used in the query."""

    description: str
    """Solicitation description text."""

    technical_keywords: list[str]
    """Technical topic keywords."""

    retrieved_at: datetime
    """Timestamp when solicitation was retrieved from API."""


class SolicitationCache:
    """SQLite-based persistent cache for solicitation metadata.

    Provides methods to get, put, and purge solicitation data cached
    from external APIs. Cache entries are permanent unless explicitly
    purged via operator commands.

    Attributes:
        cache_path: Path to SQLite database file
        connection: SQLite connection instance
    """

    def __init__(self, cache_path: Path = DEFAULT_CACHE_PATH) -> None:
        """Initialize solicitation cache.

        Args:
            cache_path: Path to SQLite database file (default: artifacts/solicitation_cache.db)

        Note:
            Database and tables are created automatically if they don't exist.
        """
        self.cache_path = Path(cache_path)
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)

        self.connection = sqlite3.connect(str(self.cache_path))
        self.connection.row_factory = sqlite3.Row  # Enable dict-like access

        # Initialize schema
        self._init_schema()

        logger.info("Initialized solicitation cache", extra={"cache_path": str(self.cache_path)})

    def __enter__(self) -> SolicitationCache:
        """Context manager entry."""
        return self

    def __exit__(self, *args: object) -> None:
        """Context manager exit - closes database connection."""
        self.close()

    def close(self) -> None:
        """Close database connection."""
        if self.connection:
            self.connection.close()
            logger.debug("Closed solicitation cache connection")

    def _init_schema(self) -> None:
        """Initialize database schema if not exists."""
        try:
            self.connection.executescript(CREATE_TABLES_SQL)
            self.connection.commit()
            logger.debug("Initialized solicitation cache schema")
        except sqlite3.Error as e:
            logger.error("Failed to initialize cache schema", extra={"error": str(e)})
            raise

    def get(
        self,
        api_source: str,
        solicitation_id: str,
    ) -> Optional[CachedSolicitation]:
        """Retrieve solicitation from cache.

        Args:
            api_source: API source identifier (grants.gov, nih, nsf)
            solicitation_id: Solicitation identifier

        Returns:
            CachedSolicitation if found, None if not in cache

        Example:
            >>> cache = SolicitationCache()
            >>> cached = cache.get("grants.gov", "SOL-2023-001")
            >>> if cached:
            ...     print(f"Found: {cached.description}")
        """
        try:
            cursor = self.connection.execute(
                "SELECT * FROM solicitations WHERE api_source = ? AND solicitation_id = ?",
                (api_source, solicitation_id),
            )

            row = cursor.fetchone()
            if row is None:
                logger.debug(
                    "Cache miss",
                    extra={"api_source": api_source, "solicitation_id": solicitation_id},
                )
                return None

            # Deserialize keywords from JSON
            keywords = json.loads(row["technical_keywords"])

            # Parse retrieved_at timestamp
            retrieved_at = datetime.fromisoformat(row["retrieved_at"])

            cached = CachedSolicitation(
                api_source=row["api_source"],
                solicitation_id=row["solicitation_id"],
                description=row["description"],
                technical_keywords=keywords,
                retrieved_at=retrieved_at,
            )

            logger.debug(
                "Cache hit",
                extra={"api_source": api_source, "solicitation_id": solicitation_id},
            )

            return cached

        except (sqlite3.Error, json.JSONDecodeError, ValueError) as e:
            logger.warning(
                "Failed to retrieve from cache",
                extra={"api_source": api_source, "solicitation_id": solicitation_id, "error": str(e)},
            )
            return None

    def put(
        self,
        api_source: str,
        solicitation_id: str,
        description: str,
        technical_keywords: list[str],
    ) -> None:
        """Store solicitation in cache.

        Args:
            api_source: API source identifier (grants.gov, nih, nsf)
            solicitation_id: Solicitation identifier
            description: Solicitation description text
            technical_keywords: Technical topic keywords

        Note:
            Uses INSERT OR REPLACE to handle duplicate keys.

        Example:
            >>> cache = SolicitationCache()
            >>> cache.put(
            ...     "grants.gov",
            ...     "SOL-2023-001",
            ...     "SBIR Phase I Solicitation",
            ...     ["AI", "ML", "robotics"]
            ... )
        """
        retrieved_at = datetime.now(timezone.utc).isoformat()

        # Serialize keywords to JSON
        keywords_json = json.dumps(technical_keywords)

        try:
            self.connection.execute(
                """
                INSERT OR REPLACE INTO solicitations
                (api_source, solicitation_id, description, technical_keywords, retrieved_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (api_source, solicitation_id, description, keywords_json, retrieved_at),
            )

            self.connection.commit()

            logger.debug(
                "Stored solicitation in cache",
                extra={
                    "api_source": api_source,
                    "solicitation_id": solicitation_id,
                    "keywords_count": len(technical_keywords),
                },
            )

        except sqlite3.Error as e:
            logger.error(
                "Failed to store solicitation in cache",
                extra={"api_source": api_source, "solicitation_id": solicitation_id, "error": str(e)},
            )
            raise

    def purge_by_api_source(self, api_source: str) -> int:
        """Purge all cache entries for a specific API source.

        Args:
            api_source: API source identifier to purge (grants.gov, nih, nsf)

        Returns:
            Number of entries purged

        Example:
            >>> cache = SolicitationCache()
            >>> count = cache.purge_by_api_source("grants.gov")
            >>> print(f"Purged {count} Grants.gov solicitations")
        """
        try:
            cursor = self.connection.execute(
                "DELETE FROM solicitations WHERE api_source = ?",
                (api_source,),
            )

            self.connection.commit()
            purged_count = cursor.rowcount

            logger.info(
                "Purged cache by API source",
                extra={"api_source": api_source, "purged_count": purged_count},
            )

            return purged_count

        except sqlite3.Error as e:
            logger.error(
                "Failed to purge cache by API source",
                extra={"api_source": api_source, "error": str(e)},
            )
            raise

    def purge_by_solicitation_id(self, solicitation_id: str) -> int:
        """Purge cache entries matching a solicitation ID across all API sources.

        Args:
            solicitation_id: Solicitation identifier to purge

        Returns:
            Number of entries purged

        Example:
            >>> cache = SolicitationCache()
            >>> count = cache.purge_by_solicitation_id("SOL-2023-001")
            >>> print(f"Purged {count} entries for SOL-2023-001")
        """
        try:
            cursor = self.connection.execute(
                "DELETE FROM solicitations WHERE solicitation_id = ?",
                (solicitation_id,),
            )

            self.connection.commit()
            purged_count = cursor.rowcount

            logger.info(
                "Purged cache by solicitation ID",
                extra={"solicitation_id": solicitation_id, "purged_count": purged_count},
            )

            return purged_count

        except sqlite3.Error as e:
            logger.error(
                "Failed to purge cache by solicitation ID",
                extra={"solicitation_id": solicitation_id, "error": str(e)},
            )
            raise

    def purge_by_date_range(
        self,
        *,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> int:
        """Purge cache entries retrieved within a date range.

        Args:
            start_date: Start of date range (inclusive), None for no lower bound
            end_date: End of date range (inclusive), None for no upper bound

        Returns:
            Number of entries purged

        Raises:
            ValueError: If both start_date and end_date are None

        Example:
            >>> from datetime import datetime, timezone
            >>> cache = SolicitationCache()
            >>> cutoff = datetime(2023, 1, 1, tzinfo=timezone.utc)
            >>> count = cache.purge_by_date_range(end_date=cutoff)
            >>> print(f"Purged {count} entries retrieved before 2023")
        """
        if start_date is None and end_date is None:
            raise ValueError("Must specify at least one of start_date or end_date")

        conditions = []
        params = []

        if start_date:
            conditions.append("retrieved_at >= ?")
            params.append(start_date.isoformat())

        if end_date:
            conditions.append("retrieved_at <= ?")
            params.append(end_date.isoformat())

        where_clause = " AND ".join(conditions)

        try:
            cursor = self.connection.execute(
                f"DELETE FROM solicitations WHERE {where_clause}",
                params,
            )

            self.connection.commit()
            purged_count = cursor.rowcount

            logger.info(
                "Purged cache by date range",
                extra={
                    "start_date": start_date.isoformat() if start_date else None,
                    "end_date": end_date.isoformat() if end_date else None,
                    "purged_count": purged_count,
                },
            )

            return purged_count

        except sqlite3.Error as e:
            logger.error(
                "Failed to purge cache by date range",
                extra={"error": str(e)},
            )
            raise

    def get_cache_stats(self) -> dict:
        """Get cache statistics.

        Returns:
            Dictionary containing cache size, entries per API source, etc.

        Example:
            >>> cache = SolicitationCache()
            >>> stats = cache.get_cache_stats()
            >>> print(f"Total entries: {stats['total_entries']}")
            >>> print(f"By source: {stats['by_api_source']}")
        """
        try:
            # Total entries
            cursor = self.connection.execute("SELECT COUNT(*) as count FROM solicitations")
            total_entries = cursor.fetchone()["count"]

            # Entries per API source
            cursor = self.connection.execute(
                "SELECT api_source, COUNT(*) as count FROM solicitations GROUP BY api_source"
            )
            by_api_source = {row["api_source"]: row["count"] for row in cursor.fetchall()}

            # Oldest and newest entries
            cursor = self.connection.execute(
                "SELECT MIN(retrieved_at) as oldest, MAX(retrieved_at) as newest FROM solicitations"
            )
            date_range = cursor.fetchone()

            return {
                "total_entries": total_entries,
                "by_api_source": by_api_source,
                "oldest_entry": date_range["oldest"],
                "newest_entry": date_range["newest"],
                "cache_path": str(self.cache_path),
            }

        except sqlite3.Error as e:
            logger.error("Failed to get cache stats", extra={"error": str(e)})
            return {
                "total_entries": 0,
                "by_api_source": {},
                "cache_path": str(self.cache_path),
                "error": str(e),
            }
