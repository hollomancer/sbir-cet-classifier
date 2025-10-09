# Phase 0 Research — SBIR Award Applicability Assessment

## Task Overview
- Research primary dependencies for SBIR CET applicability classification workflow.
- Research storage formats and artefact handling for SBIR.gov datasets and derived outputs.
- Research analyst delivery surface (CLI, notebook, web) suitable for CET alignment workflows.

## Findings

### Primary Dependencies
- Decision: Adopt `pandas`, `scikit-learn`, and `spacy` as the core data and NLP stack, with `pydantic` for schema validation and `typer` for CLI orchestration.
- Rationale: `pandas` readily ingests SBIR.gov CSV exports and scales to 50k+ award slices on analyst hardware; `scikit-learn` provides reliable TF-IDF + calibrated models for 0–100 applicability scoring with strong calibration utilities; `spacy` supports sentence segmentation for evidence snippets; `pydantic` enforces structured payloads; `typer` aligns with prior CLI ergonomics and supports nested commands for refresh, scoring, and export tasks.
- Alternatives considered: `polars` (faster columnar ops but weaker ecosystem for downstream ML pipelines); `transformers` + deep classifiers (higher accuracy but overkill for initial scope and heavier dependencies); custom CLI via `argparse` (less ergonomic and harder to maintain command hierarchies).

### Storage Strategy
- Decision: Store raw SBIR.gov ZIP/CSV drops under `data/raw/` (immutable), persist normalized award tables as partitioned Parquet in `data/processed/`, and capture model artefacts/metadata in `artifacts/` with sidecar JSON manifests.
- Rationale: Parquet keeps filtered analyst workflows performant while reducing disk footprint; immutable raw drops satisfy data lineage; JSON manifests document taxonomy version, model hash, and refresh timestamp to support audit trails per constitution.
- Alternatives considered: SQLite warehouse (adds deployment overhead without multi-user requirements); feather files (fast but weaker compression); leaving data only in CSV (simpler but slower filters and higher I/O costs).

### Delivery Surface
- Decision: Provide a `typer`-based CLI for refresh/classify/export flows supplemented by spec-aligned Jupyter notebooks (`specs/001-i-want-to/notebooks/001-analysis.ipynb`) for exploratory analysis and validation dashboards.
- Rationale: CLI ensures consistent automation hooks and supports analysts running scripted reports; notebooks mirror spec ID, satisfying constitution UX guidance and enabling rapid validation; both reuse the same service layer for deterministic outputs.
- Alternatives considered: Full web frontend (higher upfront cost, requires hosting); Streamlit dashboard (fast but diverges from CLI/notebook parity and raises packaging overhead); pure notebook delivery (lacks repeatable automation for exports and refresh cadence).
