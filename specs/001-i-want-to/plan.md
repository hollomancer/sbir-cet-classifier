# Implementation Plan: SBIR Award Applicability Assessment

**Branch**: `[001-i-want-to]` | **Date**: 2025-10-08 | **Spec**: `/specs/001-i-want-to/spec.md`
**Input**: Feature specification from `/specs/001-i-want-to/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

Ingest SBIR.gov bulk award data, align each record to the CET taxonomy with scored applicability tiers, and surface analyst workflows (filters, drill-downs, exports) that respect manual review governance and taxonomy versioning.

## Technical Context

<!--
  ACTION REQUIRED: Replace the content in this section with the technical details
  for the project. The structure here is presented in advisory capacity to guide
  the iteration process.
-->

**Language/Version**: Python 3.11 (constitution mandate)  
**Primary Dependencies**: pandas, scikit-learn, spacy, pydantic, typer, fastapi, uvicorn  
**Storage**: Raw SBIR.gov ZIP/CSV in `data/raw/`, normalized Parquet in `data/processed/`, artefacts+manifests in `artifacts/`  
**Testing**: pytest with unit + integration mirrors under `tests/`  
**Target Platform**: Typer CLI for automation + spec-aligned Jupyter notebooks on analyst workstations
**Project Type**: Single Python package with modular subpackages (`data`, `features`, `models`, `evaluation`)  
**Performance Goals**: ≥95% automated classifications, exports within service window, inference ≤500 ms median batch (per constitution/performance goals)  
**Constraints**: Manual refresh trigger, taxonomy version preservation, evidence statements ≤50 words, review queue cleared quarterly  
**Scale/Scope**: Full SBIR award corpus (1983–present) across agencies; filtered analyst sessions servicing tens of thousands of awards per request

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **Gate — Code Quality First**: PASS — Plan commits to Python package layout with type hints, shared utilities, and ruff enforcement before merge.
- **Gate — Testing Defines Delivery**: PASS — Research and design will enumerate tests ahead of implementation; unit/integration suites will anchor acceptance criteria.
- **Gate — Consistent User Experience**: PASS — Deliverables will document CLI/notebook entry points, aligning option names with CET taxonomy terminology.
- **Gate — Performance with Accountability**: PASS — Performance targets from success criteria and constitution will be tracked in design metrics.
- **Gate — Reliable Data Stewardship**: PASS — Data ingestion and artefact management will adhere to immutable raw data principle and metadata logging.

*Re-evaluated after Phase 1 design (2025-10-08): No new violations identified; data-model, contracts, and quickstart reinforce compliance paths.*

## Project Structure

### Documentation (this feature)

```
specs/001-i-want-to/
├── plan.md          # Implementation plan (this file)
├── research.md      # Phase 0 research synthesis
├── data-model.md    # Phase 1 entity model
├── quickstart.md    # Phase 1 onboarding notes
├── contracts/       # Phase 1 API contracts
└── tasks.md         # Phase 2 execution tracker (later)
```

### Source Code (repository root)
<!--
  ACTION REQUIRED: Replace the placeholder tree below with the concrete layout
  for this feature. Delete unused options and expand the chosen structure with
  real paths (e.g., apps/admin, packages/something). The delivered plan must
  not include Option labels.
-->

```
src/
└── sbir_cet_classifier/
    ├── cli/
    ├── api/
    ├── data/
    ├── features/
    ├── models/
    ├── evaluation/
    └── common/

tests/
├── unit/
│   └── sbir_cet_classifier/
├── integration/
│   └── sbir_cet_classifier/
├── contract/
│   └── sbir_cet_classifier/
└── fixtures/
```

**Structure Decision**: Single Python package mirroring constitution guidance; subpackages separate data ingestion, feature engineering, modeling, and evaluation with aligned test mirrors.

## Complexity Tracking

*Fill ONLY if Constitution Check has violations that must be justified*

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
