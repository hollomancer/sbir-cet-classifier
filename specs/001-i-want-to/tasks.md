# Tasks: SBIR Award Applicability Assessment

**Input**: Design documents from `/specs/001-i-want-to/`
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Establish project scaffolding, dependency management, and tooling required for implementation.

- [X] T001 [Shared] Create Python package skeleton (`src/sbir_cet_classifier/{data,features,models,evaluation,common,cli,api}`) plus mirrored `tests/{unit,integration,contract}/sbir_cet_classifier` directories.
- [X] T002 [Shared] Extend `pyproject.toml` with runtime deps (pandas, scikit-learn, spacy, pydantic, typer, fastapi, uvicorn) and dev extras (ruff, pytest, coverage).
- [X] T003 [P][Shared] Configure `ruff`, `pytest.ini`, and pre-commit hooks to enforce linting, formatting, and type-checking before PRs.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core data ingestion, taxonomy, scoring, storage, and interface scaffolding required by all user stories.  
**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [X] T010 [Shared] Implement configuration module (`src/sbir_cet_classifier/common/config.py`) with environment-driven paths for `data/raw/`, `data/processed/`, and `artifacts/`.
- [X] T011 [Shared] Define Pydantic domain schemas (`src/sbir_cet_classifier/common/schemas.py`) covering SBIR awards, CET areas, applicability assessments, evidence statements, and review queue items.
- [X] T012 [P][Shared] Build SBIR.gov ingestion pipeline (`src/sbir_cet_classifier/data/ingest.py`) that downloads/unzips bulk files, normalizes records, and persists raw snapshots; include fixture-driven unit tests in `tests/unit/sbir_cet_classifier/data/test_ingest.py`.
- [X] T013 [P][Shared] Implement CET taxonomy loader (`src/sbir_cet_classifier/data/taxonomy.py`) supporting versioned definitions and immutability guarantees; cover with unit tests.
- [X] T014 [P][Shared] Create Parquet writer/reader utilities (`src/sbir_cet_classifier/data/store.py`) to materialize processed tables with partitioning by fiscal year.
- [X] T015 [Shared] Develop applicability scoring pipeline (`src/sbir_cet_classifier/models/applicability.py`) using TF-IDF + calibrated classifier, returning score, classification band, and supporting CET candidates.
- [X] T016 [P][Shared] Implement evidence extraction helpers using spaCy (`src/sbir_cet_classifier/features/evidence.py`) enforcing ≤50-word summaries and rationale tagging.
- [X] T017 [Shared] Create manual review repository (`src/sbir_cet_classifier/features/review_queue.py`) with SLA tracking and escalation logic tied to fiscal quarter boundaries.
- [X] T018 [P][Shared] Scaffold Typer CLI entry (`src/sbir_cet_classifier/cli/app.py`) with commands for refresh, summary, awards, review-queue, and exports (stubs call underlying services).
- [X] T019 [P][Shared] Scaffold FastAPI application (`src/sbir_cet_classifier/api/router.py`) aligning to `contracts/openapi.yaml` structure and sharing service layer with CLI.
- [X] T020 [Shared] Add unit/integration smoke tests covering schema validation, ingestion-store round trip, and CLI bootstrapping (`tests/integration/sbir_cet_classifier/test_bootstrap.py`).
- [X] T021 [Shared] Implement classification coverage metrics module (`src/sbir_cet_classifier/models/applicability_metrics.py`) that logs automated vs. manual rates and writes `artifacts/coverage.json` during refresh.

**Checkpoint**: Foundation ready—services, CLI, and API skeletons operational with tests.

---

## Phase 3: User Story 1 – Portfolio Analyst Reviews Alignment (Priority: P1) 🎯 MVP

**Goal**: Deliver CET summary view with counts, obligated dollars, share, and top award per CET area honoring active filters.  
**Independent Test**: Load SBIR dataset for a fiscal range, filter by agency, and verify CET summary renders with metrics and classification coverage within two interactions.

### Tests for User Story 1
- [X] T101 [P][US1] Contract test for `GET /applicability/summary` ensuring schema compliance and taxonomy version metadata (`tests/contract/test_summary_endpoint.py`).
- [X] T102 [P][US1] Integration test for summary filters + CLI parity using fixture data (`tests/integration/sbir_cet_classifier/summary/test_summary_filters.py`).

### Implementation for User Story 1
- [X] T103 [P][US1] Implement summary aggregation service (`src/sbir_cet_classifier/features/summary.py`) computing counts, obligated dollars, share, and classification breakdown per CET.
- [X] T104 [US1] Wire Typer command `summary` (`src/sbir_cet_classifier/cli/summary.py`) to aggregation service with options for fiscal year range, agencies, phases, CET areas, and location.
- [X] T105 [US1] Implement FastAPI handler (`src/sbir_cet_classifier/api/routes/summary.py`) to expose `GET /applicability/summary` with pagination metadata and filter echoing.
- [X] T106 [US1] Add top-award spotlight selection (highest score, tie-break by obligated amount) and ensure supporting evidence snippet surfaces in response.
- [X] T107 [US1] Update `tests/unit/sbir_cet_classifier/features/test_summary.py` with unit coverage for aggregation edge cases (no data, mixed agencies, incomplete awards).
- [X] T311 [US1] Measure end-to-end summary generation (CLI and API) against the 3-minute SLA and document results in `specs/001-i-want-to/checklists/summary.md`.

**Checkpoint**: CET summary accessible via CLI and API, passing contract + integration tests.

---

## Phase 4: User Story 2 – Technology Strategist Investigates Gaps (Priority: P2)

**Goal**: Enable drill-down into CET areas, list award-level applicability details, and highlight gaps/manual review needs.  
**Independent Test**: From CET summary, select an underperforming area and access award details with evidence snippets and gap insights in under 5 minutes.

### Tests for User Story 2
- [ ] T201 [P][US2] Contract tests for `GET /applicability/awards` and `GET /applicability/cet/{cetId}` covering pagination, evidence arrays, and gap payloads (`tests/contract/test_awards_and_cet_endpoints.py`).
- [ ] T202 [US2] Integration test simulating strategist drill-down flow, including multi-agency comparisons and manual review surfacing (`tests/integration/sbir_cet_classifier/awards/test_award_gap_flow.py`).

### Implementation for User Story 2
- [ ] T203 [P][US2] Implement award listing service (`src/sbir_cet_classifier/features/awards.py`) returning paged applicability details, evidence statements, and taxonomy versions.
- [ ] T204 [US2] Implement CET gap analytics module (`src/sbir_cet_classifier/features/gaps.py`) comparing actual vs. target shares and generating narrative insights.
- [ ] T205 [P][US2] Wire Typer commands `awards list` and `awards show` (`src/sbir_cet_classifier/cli/awards.py`) to services with pagination + CET filters.
- [ ] T206 [US2] Implement FastAPI routes for `GET /applicability/awards` and `GET /applicability/awards/{awardId}` plus CET detail route (`src/sbir_cet_classifier/api/routes/awards.py`).
- [ ] T207 [US2] Integrate review queue repository so awards missing abstracts/keywords surface with `data_incomplete` flags and escalate overdue items.
- [ ] T208 [US2] Ensure multi-CET alignment logic records tie-breaking rationale and persists historical assessments for taxonomy version changes.

**Checkpoint**: Strategist workflow delivers award drill-down, gap analytics, and manual review visibility across API and CLI.

---

## Phase 5: User Story 3 – Data Steward Shares Findings (Priority: P3)

**Goal**: Provide governed export generation aligned with active filters, excluding controlled awards while preserving aggregates.  
**Independent Test**: Execute export command/request and confirm structured file delivery with methodology notes within service window.

### Tests for User Story 3
- [ ] T301 [P][US3] Contract test for `POST /exports` and `GET /exports?jobId=...` verifying status transitions and download URL schema (`tests/contract/test_exports_endpoint.py`).
- [ ] T302 [US3] Integration test covering CLI export lifecycle, file generation, and exclusion of `is_export_controlled` awards (`tests/integration/sbir_cet_classifier/exports/test_export_flow.py`).

### Implementation for User Story 3
- [ ] T303 [US3] Implement export orchestrator (`src/sbir_cet_classifier/features/exporter.py`) producing CSV/Parquet files with methodology footnotes and metadata manifests.
- [ ] T304 [P][US3] Add background job handler or async task queue stub (`src/sbir_cet_classifier/api/background.py`) processing export jobs and enforcing SLA timing.
- [ ] T305 [US3] Wire Typer commands `export create` and `export status` (`src/sbir_cet_classifier/cli/export.py`) to orchestrator with consistent filter parsing.
- [ ] T306 [US3] Implement FastAPI routes for export submission/status (`src/sbir_cet_classifier/api/routes/exports.py`) plus controlled-data guardrails.
- [ ] T307 [US3] Extend review queue integration to mark exports including unresolved items and append escalation notes to metadata.
- [ ] T308 [US3] Build reviewer agreement evaluation script (`src/sbir_cet_classifier/evaluation/reviewer_agreement.py`) to compare model output against analyst labels on the 200-award sample.
- [ ] T309 [US3] Coordinate analyst labeling workflow and persist agreement reports under `artifacts/reviewer_agreement.json`, updating checklists/requirements.md.
- [ ] T310 [US3] Add export performance test ensuring CSV/Parquet jobs for 50k awards finish within 10 minutes (`tests/integration/sbir_cet_classifier/exports/test_export_sla.py`).

**Checkpoint**: Export pipeline operational with governance controls and validated via tests.

---

## Phase N: Polish & Cross-Cutting Concerns

- [ ] T401 [Shared] Document operational runbooks, metrics tracking, and update `specs/001-i-want-to/quickstart.md` with any command-line changes.
- [ ] T402 [Shared] Validate Quickstart instructions end-to-end (venv, refresh, summary, awards, export) and capture screenshots/metrics for PR artifacts.
- [ ] T403 [Shared] Profile scoring pipeline and report inference latency vs. 500 ms target; optimize TF-IDF caching or batch sizing if needed.
- [ ] T404 [Shared] Harden logging/observability (structured JSON, trace IDs) and ensure sensitive data exclusions per constitution.
- [ ] T405 [Shared] Final regression pass—run `ruff`, `pytest -m "not slow"`, and `check-prerequisites.sh --require-tasks --include-tasks`, updating `specs/001-i-want-to/checklists/*.md` accordingly.
- [ ] T406 [Shared] Validate automated coverage ≥95% and document evidence in `specs/001-i-want-to/checklists/classification.md` alongside reviewer agreement results.
