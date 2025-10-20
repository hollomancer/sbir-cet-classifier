<!--
Sync Impact Report:
- Version change: 1.0.0 → 1.1.0 (minor version - added new configuration principle)
- Modified principles: Added VI. User-Configurable Parameters
- Added sections: New principle for YAML configuration requirement
- Removed sections: N/A
- Templates requiring updates: 
  ✅ plan-template.md (Constitution Check section already aligned)
  ✅ spec-template.md (no constitution references, aligned with principles)
  ✅ tasks-template.md (no constitution references, aligned with principles)
  ✅ All other templates reviewed and aligned
- Follow-up TODOs: None
-->

# SBIR CET Classifier Constitution

## Core Principles

### I. Modular Architecture
Every feature MUST be implemented as a self-contained module within the established package structure. Modules MUST be independently testable, documented with clear interfaces, and follow the existing src/sbir_cet_classifier/ organization. Cross-module dependencies MUST be explicit and minimal.

### II. CLI-First Interface
All functionality MUST be accessible via command-line interface using Typer. Commands MUST follow the pattern: input via arguments/stdin → processing → output to stdout/files. Both JSON and human-readable formats MUST be supported for data interchange.

### III. Test-Driven Development (NON-NEGOTIABLE)
Tests MUST be written before implementation. The Red-Green-Refactor cycle is strictly enforced: write failing test → implement minimal code → refactor. All code MUST maintain ≥85% test coverage. Integration tests are required for data pipelines and ML model changes.

### IV. Performance-First Design
All data processing MUST target production-scale performance: ≥5,000 records/second ingestion, ≤500ms median scoring latency for 100 awards, ≤2 hours processing for 200k+ awards. Performance regressions MUST be caught in CI/CD pipeline.

### V. Data Quality Assurance
All data transformations MUST include validation, error handling, and quality metrics. Success rates ≥95% are required for production pipelines. Data inconsistencies MUST be logged with structured telemetry for debugging and monitoring.

### VI. User-Configurable Parameters
All classification parameters, model hyperparameters, and processing settings MUST be externalized to YAML configuration files. Users MUST be able to modify classification behavior without code changes. Configuration validation MUST prevent invalid parameter combinations that could degrade system performance or accuracy.

## Data Quality Standards

### Schema Validation
All data inputs and outputs MUST conform to defined Pydantic schemas. Schema changes MUST be backward compatible or include migration procedures. Parquet files MUST maintain consistent column types and naming conventions.

### ML Model Governance
Model changes MUST include accuracy benchmarks against existing baselines. Classification accuracy regressions >2% require explicit justification. Model artifacts MUST be versioned and reproducible with documented hyperparameters.

### External API Integration
Third-party API integrations MUST implement circuit breakers, exponential backoff, and rate limiting. API failures MUST degrade gracefully without corrupting existing data. All API responses MUST be validated against expected schemas.

## Development Workflow

### Code Quality Gates
All code MUST pass ruff linting and formatting checks. Type hints are required for public interfaces. Documentation MUST be updated for user-facing changes. No code may be merged without passing all tests.

### Feature Development
New features MUST follow the specification-driven development process: spec.md → plan.md → implementation → testing. Breaking changes require version bumps and migration documentation. Feature flags MUST be used for experimental functionality.

### Deployment Standards
Production deployments MUST be reproducible with pinned dependencies. Configuration MUST be externalized via environment variables. Rollback procedures MUST be documented and tested.

## Governance

This constitution supersedes all other development practices. Amendments require documentation of rationale, impact analysis, and team approval. All pull requests MUST verify constitutional compliance during review.

Complexity violations MUST be explicitly justified with business rationale and simpler alternatives documented as rejected. The constitution guides architectural decisions but does not override critical business requirements with proper justification.

Runtime development guidance is maintained in AGENTS.md and project documentation. Constitutional violations in legacy code MUST be addressed during refactoring but do not block urgent fixes.

**Version**: 1.1.0 | **Ratified**: 2025-10-10 | **Last Amended**: 2025-10-10
