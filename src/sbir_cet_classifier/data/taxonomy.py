"""Utilities for loading and persisting CET taxonomy versions."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from sbir_cet_classifier.common.schemas import CETArea


@dataclass(frozen=True)
class CETTaxonomy:
    """In-memory representation of a versioned CET taxonomy."""

    version: str
    effective_date: date
    entries: tuple[CETArea, ...]

    def get(self, cet_id: str) -> CETArea | None:
        return next((entry for entry in self.entries if entry.cet_id == cet_id), None)


def load_taxonomy_file(path: Path) -> CETTaxonomy:
    """Load a taxonomy JSON file into a :class:`CETTaxonomy`."""

    payload = json.loads(path.read_text())
    entries = tuple(CETArea(**entry) for entry in payload["entries"])
    effective_date = date.fromisoformat(payload["effective_date"])
    return CETTaxonomy(version=payload["version"], effective_date=effective_date, entries=entries)


class TaxonomyRepository:
    """Manages versioned taxonomy artefacts on disk."""

    def __init__(self, storage_dir: Path) -> None:
        self._storage_dir = storage_dir
        self._storage_dir.mkdir(parents=True, exist_ok=True)

    def save(self, taxonomy: CETTaxonomy) -> Path:
        """Persist a taxonomy version to storage.

        Versions are immutable—attempting to overwrite an existing file raises a :class:`ValueError`.
        """

        output_path = self._storage_dir / f"{taxonomy.version}.json"
        if output_path.exists():
            raise ValueError(f"Taxonomy version {taxonomy.version} already exists")

        payload = {
            "version": taxonomy.version,
            "effective_date": taxonomy.effective_date.isoformat(),
            "entries": [entry.model_dump(mode="json") for entry in taxonomy.entries],
        }
        output_path.write_text(json.dumps(payload, indent=2))
        return output_path

    def load(self, version: str) -> CETTaxonomy:
        path = self._storage_dir / f"{version}.json"
        if not path.exists():
            raise FileNotFoundError(f"Taxonomy version {version} not found")
        return load_taxonomy_file(path)

    def list_versions(self) -> list[str]:
        return sorted(p.stem for p in self._storage_dir.glob("*.json"))

    def latest(self) -> CETTaxonomy:
        versions = self.list_versions()
        if not versions:
            raise FileNotFoundError("No taxonomy versions available")
        return self.load(versions[-1])


def load_taxonomy_from_directory(directory: Path) -> CETTaxonomy:
    """Load the most recent taxonomy stored in `directory`."""

    repo = TaxonomyRepository(directory)
    return repo.latest()


__all__ = [
    "CETTaxonomy",
    "TaxonomyRepository",
    "load_taxonomy_file",
    "load_taxonomy_from_directory",
]
