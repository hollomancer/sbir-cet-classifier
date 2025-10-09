from __future__ import annotations

import json
from datetime import date

from sbir_cet_classifier.common.schemas import CETArea
from sbir_cet_classifier.data.taxonomy import (
    CETTaxonomy,
    TaxonomyRepository,
    load_taxonomy_file,
)


def _sample_taxonomy(tmp_path):
    payload = {
        "version": "NSTC-2025Q1",
        "effective_date": "2025-01-01",
        "entries": [
            {
                "cet_id": "quantum_sensing",
                "name": "Quantum Sensing",
                "definition": "Quantum-based sensing capabilities.",
                "parent_cet_id": None,
                "version": "NSTC-2025Q1",
                "effective_date": "2025-01-01",
                "retired_date": None,
                "status": "active",
            }
        ],
    }
    path = tmp_path / "NSTC-2025Q1.json"
    path.write_text(json.dumps(payload))
    return path


def test_load_taxonomy_file(tmp_path):
    path = _sample_taxonomy(tmp_path)
    taxonomy = load_taxonomy_file(path)

    assert taxonomy.version == "NSTC-2025Q1"
    assert taxonomy.effective_date == date(2025, 1, 1)
    assert taxonomy.get("quantum_sensing") is not None


def test_repository_enforces_version_immutability(tmp_path):
    repo = TaxonomyRepository(tmp_path)
    taxonomy = CETTaxonomy(
        version="NSTC-2025Q1",
        effective_date=date(2025, 1, 1),
        entries=(
            CETArea(
                cet_id="quantum_sensing",
                name="Quantum Sensing",
                definition="Quantum-based sensing capabilities.",
                parent_cet_id=None,
                version="NSTC-2025Q1",
                effective_date=date(2025, 1, 1),
                retired_date=None,
                status="active",
            ),
        ),
    )

    repo.save(taxonomy)
    assert repo.load("NSTC-2025Q1").version == "NSTC-2025Q1"

    try:
        repo.save(taxonomy)
    except ValueError as err:
        assert "already exists" in str(err)
    else:
        raise AssertionError("Expected ValueError when saving duplicate taxonomy version")
