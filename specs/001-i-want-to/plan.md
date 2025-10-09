# Implementation Plan: SBIR Award Applicability Assessment

**Branch**: `[001-i-want-to]` | **Date**: 2025-10-09 | **Spec**: `/specs/001-i-want-to/spec.md`
**Input**: Feature specification from `/specs/001-i-want-to/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

Deliver an offline-first analyst workflow that ingests SBIR.gov awards, classifies each award against the CET taxonomy with calibrated scores and evidence snippets, surfaces portfolio summaries and drill-downs, and exports governed datasets while preserving taxonomy history and manual review accountability.

## Technical Context

**Language/Version**: Python 3.11 (per constitution mandate)  
**Primary Dependencies**: pandas, scikit-learn, spaCy, pydantic, typer, FastAPI, uvicorn, pyarrow, rich  
**Storage**: Raw ZIP/CSV under `data/raw/`, partitioned Parquet tables under `data/processed/`, artefacts + manifests in `artifacts/`  
**Testing**: pytest with unit/integration/contract suites, coverage tracked via pytest-cov  
**Target Platform**: Offline Typer CLI on analyst workstations; internal-only FastAPI service behind trusted network  
**Project Type**: Single Python package (`src/sbir_cet_classifier`) with mirrored tests  
**Performance Goals**: ≥95% automated classifications per refresh; exports ≤10 minutes for ≤50k awards; scoring batches ≤500 ms median / ≤750 ms p95; ingestion refresh ≤2 hours for ≤120k awards  
**Constraints**: Evidence summaries ≤50 words with rationale tags; manual review queue resolved quarterly; taxonomy/version manifests immutable; access restricted to offline CLI and internal API; structured telemetry for refresh, scoring, export jobs  
**Scale/Scope**: Historical SBIR corpus (1983–present, ≈300k+ awards) with refreshes up to 120k records per run and analyst queries spanning tens of thousands of awards across agencies

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **Gate — Code Quality First**: PASS — Plan retains single Python package, enforces typing, and integrates ruff + pytest in tooling tasks.  
- **Gate — Testing Defines Delivery**: PASS — Contract/unit/integration suites defined per feature area with coverage targets ≥85%, aligning with Constitution principle II.  
- **Gate — Consistent User Experience**: PASS — CLI and internal FastAPI share service layer and schema contracts, ensuring parity in filters and responses.  
- **Gate — Performance With Accountability**: PASS — Plan commits to telemetry artefacts (`artifacts/export_runs.json`, `artifacts/scoring_runs.json`, `artifacts/refresh_runs.json`) and performance SLAs, satisfying monitoring expectations.  
- **Gate — Reliable Data Stewardship**: PASS — Immutable raw data, versioned taxonomy/model artefacts, and manual review governance preserved throughout ingestion and export pipelines.

*Re-evaluated after Phase 1 design (2025-10-09): No new violations identified; data model, contracts, and quickstart map directly to constitutional principles.*

## Project Structure

### Documentation (this feature)

```
specs/001-i-want-to/
├── plan.md              # Implementation plan (this file)
├── research.md          # Phase 0 research synthesis
├── data-model.md        # Phase 1 entity model
├── quickstart.md        # Phase 1 onboarding notes
├── contracts/           # Phase 1 API contracts (OpenAPI)
└── tasks.md             # Phase 2 execution tracker (via /speckit.tasks)
```

### Source Code (repository root)

```
src/
└── sbir_cet_classifier/
    ├── api/
    │   └── routes/
    ├── cli/
    ├── common/
    ├── data/
    ├── evaluation/
    ├── features/
    ├── models/
    └── services/

tests/
├── contract/
│   └── sbir_cet_classifier/
├── integration/
│   └── sbir_cet_classifier/
├── unit/
│   └── sbir_cet_classifier/
└── fixtures/
```

**Structure Decision**: Maintain a single Python package with domain-focused subpackages (data ingestion, feature engineering, models, evaluation, API/CLI surfaces) and mirrored test hierarchy to satisfy constitution guidance and support modular ownership.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| _None_ | N/A | N/A |
