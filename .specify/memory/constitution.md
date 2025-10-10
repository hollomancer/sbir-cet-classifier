<!--
Sync Impact Report:
- Version change: 1.0.0 → 1.0.1 (PATCH: clarifications and wording refinements)
- Modified principles: None (wording refinements only)
- Added sections: None
- Removed sections: None
- Templates requiring updates:
  ✅ plan-template.md — Constitution Check section already aligns with 5 principles
  ✅ spec-template.md — Requirements sections already compatible with testing/quality principles
  ✅ tasks-template.md — Task categorization already supports principle-driven work
  ✅ No command files found in .specify/templates/commands/ (directory empty)
- Follow-up TODOs: None
- Rationale: User input emphasizes "command line only - no UI" and "data ingestion, hygiene, enrichment and classification as fast and accurately as possible." Constitution already reflects these constraints (NFR-007 restricts to CLI, Principle IV defines performance targets). This patch update clarifies CLI-first orientation and reinforces performance accountability without changing core governance.
-->

# SBIR CET Classifier Constitution

## Core Principles

### I. Code Quality First

Code quality is non-negotiable. Every feature MUST maintain the project's quality standards:

- **Single Python package structure** — All production code lives in `src/sbir_cet_classifier/` with domain-focused subpackages (data, features, models, evaluation, api, cli, common)
- **Static typing enforced** — Use type hints throughout; validated by ruff type checker
- **Ruff formatting and linting** — All code MUST pass `ruff format` and `ruff check` before merge
- **Mirrored test hierarchy** — Tests organized under `tests/{unit,integration,contract}/sbir_cet_classifier/` matching src structure
- **No exotic dependencies** — Prefer standard libraries (pandas, scikit-learn, spaCy) over niche packages

**Rationale**: Quality debt compounds. Enforcing structure and tooling from day one prevents technical debt accumulation and ensures maintainability as the project scales.

### II. Testing Defines Delivery

Testing is the definition of "done." Features are complete only when tests pass:

- **≥85% statement coverage** — Tracked via pytest-cov; enforced before merge
- **Three-tier test strategy**:
  - **Unit tests** — Fast, isolated component tests in `tests/unit/`
  - **Contract tests** — API schema validation in `tests/contract/`
  - **Integration tests** — End-to-end workflows in `tests/integration/`
- **Fast test discipline** — Mark slow tests with `@pytest.mark.slow`; default runs exclude them
- **Fixture-driven design** — Reusable test data under `tests/fixtures/`

**Rationale**: Tests provide executable specifications and regression protection. Without comprehensive tests, features cannot be trusted or safely refactored.

### III. Consistent User Experience

CLI and API surfaces MUST provide equivalent functionality with consistent schemas:

- **CLI-first design** — Primary interface is Typer-based CLI for analyst workflows; FastAPI service is internal-only
- **Shared service layer** — Both CLI (Typer) and API (FastAPI) call the same domain services in `src/sbir_cet_classifier/features/`
- **Pydantic schema contracts** — Domain models defined once in `src/sbir_cet_classifier/common/schemas.py`
- **Filter parity** — Identical filter options (fiscal year, agency, CET area, phase, location) across interfaces
- **Structured output** — CLI supports both human-readable (Rich) and JSON output; API returns JSON

**Rationale**: Users should not experience capability gaps based on interface choice. CLI-first design prioritizes analyst productivity for data ingestion, hygiene, enrichment, and classification workflows. Shared logic eliminates duplication and ensures behavioral consistency.

### IV. Performance With Accountability

Performance targets are commitments backed by instrumentation. This project prioritizes speed and accuracy for data ingestion, hygiene, enrichment, and classification:

- **Defined SLAs** — Every performance requirement MUST specify measurable criteria:
  - Automated classification: ≥95% of awards
  - Summary generation: ≤3 minutes
  - Award drill-down: ≤5 minutes
  - Export (50k awards): ≤10 minutes
  - Scoring (100 awards): ≤500ms median, ≤750ms p95
  - Ingestion (120k awards): ≤2 hours
- **Telemetry artifacts** — Performance data written to `artifacts/`:
  - `export_runs.json` — Export timing and status
  - `scoring_runs.json` — Scoring latency distributions (p50/p95/p99)
  - `refresh_runs.json` — Ingestion execution logs
  - `enrichment_runs.json` — Enrichment cache hit rates and latency metrics
- **Proactive monitoring** — Alert when p95 latencies exceed thresholds

**Rationale**: "Fast enough" is subjective. Measurable targets and instrumentation enable objective performance validation and regression detection. This project's core mission—data ingestion, hygiene, enrichment, and classification—demands speed and accuracy; accountability comes from continuous measurement.

### V. Reliable Data Stewardship

Data integrity and governance are paramount:

- **Immutable raw data** — Original sources (SBIR.gov ZIPs, awards CSV) never modified
- **Versioned artifacts** — Taxonomy versions (`NSTC-{YYYY}Q{n}`), model coefficients, and feature vocabularies tracked with timestamps
- **Partitioned storage** — Processed data partitioned by fiscal year for efficient backfill/reprocessing
- **Data hygiene enforcement** — Validation at ingestion (schema compliance, date parsing, agency mapping) with per-record error isolation and logging
- **Manual review governance** — Review queue with SLA tracking, escalation logic, and audit trails
- **Controlled data exclusion** — Awards flagged `is_export_controlled` excluded from exports but preserved in aggregates

**Rationale**: Analysts trust systems that preserve provenance and auditability. Immutability and versioning enable reproducible analysis and compliance validation. Data hygiene checks catch quality issues early and prevent downstream corruption.

## Quality Standards

### Documentation Requirements

- **README.md** — Quick start, architecture overview, testing instructions
- **specs/{feature}/spec.md** — Functional requirements, success criteria, assumptions
- **specs/{feature}/plan.md** — Implementation plan with constitution compliance check
- **specs/{feature}/tasks.md** — Task breakdown with phase grouping and dependencies
- **specs/{feature}/data-model.md** — Entity schemas and validation rules
- **specs/{feature}/quickstart.md** — Operational runbook for common workflows

### Code Review Gates

All pull requests MUST:

1. Pass `ruff format --check` and `ruff check` (zero violations)
2. Pass `pytest -m "not slow"` (all fast tests green)
3. Maintain or improve coverage (≥85% statement coverage)
4. Include tests for new functionality (unit + integration as appropriate)
5. Update relevant documentation (spec, plan, quickstart) if behavior changes

### Complexity Constraints

- **No deep learning** — Stick to scikit-learn TF-IDF + logistic regression (interpretable, fast)
- **No databases** — Use Parquet files for storage (simplicity, portability); SQLite only for caching (enrichment cache)
- **Offline-first** — No authentication layers; CLI for analysts, internal-only API
- **Single-package architecture** — Avoid microservices complexity
- **CLI-driven workflows** — Command line is the primary analyst interface; API serves internal needs only

**Rationale**: Complexity must be justified. The SBIR CET classification problem does not require sophisticated infrastructure; simple solutions reduce operational burden and align with the project's CLI-first, performance-focused mission.

## Governance

### Constitution Authority

This constitution supersedes all other development practices. When conflicts arise between this document and other guidance (README, PR templates, etc.), **the constitution wins**.

### Amendment Process

Constitution changes require:

1. **Documented justification** — Why is the change necessary? What problem does it solve?
2. **Impact analysis** — Which existing code/tests/docs are affected?
3. **Migration plan** — How will non-compliant code be brought into compliance?
4. **Version bump** — Follow semantic versioning:
   - **MAJOR**: Backward-incompatible principle changes (e.g., removing a core principle)
   - **MINOR**: New principles or material expansions (e.g., adding a 6th principle)
   - **PATCH**: Clarifications, wording fixes, non-semantic refinements

### Compliance Verification

- **Pre-merge checks** — CI MUST validate ruff, pytest, and coverage before allowing merge
- **Plan phase gate** — Every feature plan includes a "Constitution Check" section validating alignment with all 5 principles
- **Periodic audits** — Quarterly review of codebase against constitutional requirements

### Enforcement

Non-compliance is not acceptable:

- **Blocking violations** — Code violating principles I-V cannot be merged
- **Remediation timeline** — Existing violations identified in audits MUST be fixed within one sprint (2 weeks)
- **Escalation** — Persistent violations require architecture review and potential principle amendment

**Version**: 1.0.1 | **Ratified**: 2025-10-09 | **Last Amended**: 2025-10-10
