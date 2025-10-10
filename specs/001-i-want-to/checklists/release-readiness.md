# Release Readiness Requirements Checklist

*Purpose*: Validate that the SBIR CET classifier specification fully covers end-to-end functional and non-functional requirements before release.  
*Created*: 2025-10-09  
*Depth*: Formal release gate  
*Focus Areas*: Entire spec, with extra scrutiny on classification and evidence quality  

## Data Ingestion & Provenance
- [ ] CHK001 Are rollback behaviors for failed SBIR.gov archive validations explicitly defined (atomic ingest, partition replacement, metadata logging)? [Completeness, Spec FR-001, Edge Cases]
- [ ] CHK002 Do requirements specify how duplicate or resubmitted awards are merged without downstream duplication, including revision metadata expectations? [Clarity, Spec FR-001]
- [ ] CHK003 Is the bootstrap CSV migration’s schema compatibility process (field mapping, required field enforcement, single-use guarantee) fully documented? [Traceability, Spec FR-001, Edge Cases]
- [ ] CHK004 Are manual vs. automated triggers for on-demand refreshes and monthly runs delineated with operator prerequisites? [Clarity, Spec FR-001, Assumptions]

## CET Taxonomy & Versioning
- [ ] CHK005 Do requirements state how taxonomy versions are published, activated, and communicated to analysts (ownership, change log, NSTC alignment)? [Coverage, Spec FR-002, Assumptions]
- [ ] CHK006 Is taxonomy immutability after release and reassessment workflow (diff logging, manifest storage) captured end-to-end? [Completeness, Spec FR-002, Edge Cases]
- [ ] CHK007 Are tie-breaking rules for multi-CET alignment tied back to taxonomy version records to keep historical accuracy? [Consistency, Spec Edge Cases]

## Classification & Evidence Quality
- [ ] CHK008 Is the calibrated TF-IDF + logistic regression pipeline described with training data provenance, feature sources, and versioned artefacts? [Completeness, Spec FR-003]
- [ ] CHK009 Are High/Medium/Low score bands and supporting CET count limits documented with thresholds that can be objectively verified? [Measurability, Spec FR-003]
- [ ] CHK010 Are evidence statement constraints (≤50 words, source location, rationale tags, capped count) unambiguous and linked to enforcement points? [Clarity, Spec FR-003]
- [ ] CHK011 Do requirements specify fallback behavior when enrichment data is unavailable so classification still emits rationale flags? [Edge Case, Spec FR-003, Edge Cases]
- [ ] CHK012 Is reviewer agreement evaluation (precision/recall targets, sample size, cadence) defined so validation of classification quality is measurable? [Measurability, Spec SC-003]

## Solicitation Enrichment & Cache
- [ ] CHK013 Are API client requirements for Grants.gov, NIH, and NSF including timeout, error handling, and identifier mapping explicit? [Coverage, Spec FR-008]
- [ ] CHK014 Does the spec define cache storage format, permanence, invalidation triggers, and audit metadata for solicitation enrichment? [Completeness, Spec FR-008, Assumptions]
- [ ] CHK015 Are batch enrichment expectations for exports (unique tuple detection, concurrency limits, logging of failures) clearly articulated? [Clarity, Spec Edge Cases, FR-008]

## Manual Review & Governance
- [ ] CHK016 Are review queue entry criteria, state transitions, SLA escalation rules, and audit requirements fully enumerated? [Completeness, Spec FR-007, Edge Cases]
- [ ] CHK017 Does the spec define how overdue or escalated items notify program management and return to in-review status? [Clarity, Spec FR-007]
- [ ] CHK018 Are manual review outcomes tied back to applicability history so overrides remain traceable by taxonomy version? [Traceability, Spec FR-007, Assumptions]

## Analyst Interfaces & Filters
- [ ] CHK019 Are filter combinations (continuous fiscal year, multi-agency, phase, location, CET area) and response update expectations fully described for both CLI and API? [Consistency, Spec FR-004, User Story 1]
- [ ] CHK020 Do requirements specify what constitutes the “overview view” and “drill-down pages” in a CLI/API-only delivery, avoiding ambiguity about UI surfaces? [Clarity, Spec FR-004/FR-005, Plan Summary]
- [ ] CHK021 Is spotlight selection (score, obligated amount, recent award) defined identically across interfaces to avoid terminology drift? [Consistency, Spec Edge Cases, User Story 1]

## Exports & Access Control
- [ ] CHK022 Are normalized CET weight columns, methodology notes, and controlled-data exclusions specified with validation points for completeness? [Coverage, Spec FR-006, User Story 3]
- [ ] CHK023 Is offline-only access control documented for CLI vs. FastAPI surfaces, including internal network assumptions and prohibited external auth? [Coverage, Spec NFR-007, Clarifications]
- [ ] CHK024 Do requirements cover export job lifecycle (submission, status, retry/failure reporting) and linkage to telemetry artefacts? [Completeness, Spec FR-006, NFR-001]

## Performance & Telemetry
- [ ] CHK025 Are all SLA metrics (classification coverage, summary latency, export window, scoring latency, ingestion duration) measurable with defined artefact outputs? [Measurability, Spec SC-001–SC-007, NFR-001–NFR-003]
- [ ] CHK026 Is there clarity on alert thresholds and responses when telemetry exceeds p95/p99 limits (e.g., scoring >750 ms)? [Clarity, Spec SC-007, NFR-002]
- [ ] CHK027 Are telemetry storage requirements (`artifacts/*.json`) aligned with constitutional expectations for data stewardship? [Consistency, Spec SC/NFR sections, Constitution V]

## Tooling, Testing & Documentation
- [ ] CHK028 Are requirements for ruff, pytest coverage ≥85%, fixture usage, and slow-test markers explicitly recorded for implementation teams? [Coverage, Spec NFR-005, Constitution II]
- [ ] CHK029 Does the documentation suite (quickstart, research, data model, plan) specify when to update artefacts after feature changes? [Completeness, Plan Documentation, Spec Success Criteria]
- [ ] CHK030 Is the constitution compliance gate reflected in requirements so future plans must re-evaluate principles post-Phase 1? [Traceability, Plan Constitution Check, Constitution Governance]

## Recovery & Edge Case Handling
- [ ] CHK031 Are SBIR.gov outage retries (24-hour window, cache fallback, alerting) clearly scoped with success/fail exit conditions? [Edge Case, Spec Edge Cases, NFR-003]
- [ ] CHK032 Does the spec cover delayed or partial agency feeds (deduplication, reconciliation reports, queueing) with measurable obligations? [Completeness, Spec Edge Cases, FR-024 equivalents]
- [ ] CHK033 Are fiscal-year backfill triggers, correction window logging, and non-mutating partition rules unambiguous? [Clarity, Spec Edge Cases, FR-023]
- [ ] CHK034 Are controlled or export-restricted awards handled consistently across ingestion, classification, and exports with audit documentation? [Consistency, Spec Edge Cases, FR-006, Assumptions]

## Compliance & Security
- [ ] CHK035 Are data retention policies aligned with SBIR.gov terms of use and research authorization limits (metadata and derived scores only)? [Compliance, Spec Assumptions, Governance]
- [ ] CHK036 Do requirements mandate redaction of controlled award details from logs, exports, and telemetry artefacts? [Security, Spec NFR-006, Edge Cases]
- [ ] CHK037 Is the offline-only access model documented with network-level controls and prohibited external authentication surfaces? [Security, Spec NFR-007, Clarifications]
- [ ] CHK038 Are all PII or sensitive firm details (if any) excluded from classification features and export columns per disclosure controls? [Privacy, Spec Assumptions, NFR-006]
- [ ] CHK039 Does the spec require audit trails for manual overrides, taxonomy changes, and review queue escalations with correlation IDs? [Traceability, Spec FR-007, NFR-006]

## Data Model & Schema Governance
- [ ] CHK040 Are all ingestion fields, entity definitions, and export columns anchored to `data-model.md` with change control requirements? [Consistency, Spec Assumptions, Key Entities]
- [ ] CHK041 Do requirements enforce schema validation at ingestion boundaries (bootstrap CSV, SBIR.gov archives, API responses)? [Quality, Spec FR-001, FR-008]
- [ ] CHK042 Is the data dictionary versioned with taxonomy releases to preserve historical field definitions for audit purposes? [Traceability, Spec Assumptions, FR-002]
- [ ] CHK043 Are partition storage formats (Parquet), indexing strategies, and fiscal year boundary rules unambiguous? [Completeness, Plan Storage, Spec FR-001]

## User Acceptance & Validation
- [ ] CHK044 Can portfolio analysts generate CET alignment summaries in ≤3 minutes per acceptance criteria in User Story 1? [Measurability, Spec SC-002, User Story 1]
- [ ] CHK045 Can technology strategists reach award drill-downs with rationale in ≤5 minutes per acceptance criteria in User Story 2? [Measurability, Spec SC-002, User Story 2]
- [ ] CHK046 Do validation plans include stratified 200-award samples achieving ≥85% reviewer agreement on primary CET classifications? [Coverage, Spec SC-003]
- [ ] CHK047 Are acceptance scenarios for multi-agency filters, continuous fiscal ranges, and share calculations testable without production data? [Testability, Spec User Stories, Acceptance Scenarios]

## Release Coordination & Sign-Off
- [ ] CHK048 Have all functional requirements (FR-001 through FR-008) been implemented and validated against acceptance scenarios? [Completeness, Spec Functional Requirements]
- [ ] CHK049 Have all non-functional requirements (NFR-001 through NFR-008) been validated with telemetry artefacts proving SLA compliance? [Completeness, Spec Non-Functional Requirements]
- [ ] CHK050 Have all success criteria (SC-001 through SC-007) been measured and documented with evidence artefacts? [Measurability, Spec Success Criteria]
- [ ] CHK051 Has the constitution compliance gate been re-evaluated post-Phase 1 with no new violations identified? [Governance, Plan Constitution Check]
- [ ] CHK052 Are quickstart documentation, data model guide, and contract specifications complete and reviewed by stakeholders? [Documentation, Plan Documentation]
- [ ] CHK053 Have unit, integration, and contract test suites achieved ≥85% coverage with all tests passing? [Quality, Spec NFR-005, Plan Testing]
- [ ] CHK054 Has the CET Program Lead reviewed and approved taxonomy version, change logs, and classification methodology? [Governance, Spec FR-002, Assumptions]

## Post-Release Monitoring & Rollback
- [ ] CHK055 Are telemetry artefacts (`export_runs.json`, `scoring_runs.json`, `refresh_runs.json`, `enrichment_runs.json`) monitored for SLA breaches? [Observability, Spec NFR-001, NFR-002, NFR-008]
- [ ] CHK056 Are alert thresholds defined for critical metrics (p95 scoring latency >750ms, export duration >10min, classification coverage <95%)? [Observability, Spec Success Criteria]
- [ ] CHK057 Is there a documented rollback procedure for failed ingestion refreshes that restores the last known good partition? [Reliability, Spec FR-001, Edge Cases]
- [ ] CHK058 Are reconciliation reports generated for API enrichment failures, late agency feeds, and manual review queue overruns? [Accountability, Spec Edge Cases, NFR-004]
- [ ] CHK059 Does the plan specify ownership and escalation paths for production incidents (operator alerts, program manager escalation)? [Governance, Spec FR-007, Plan Summary]
- [ ] CHK060 Are post-release validation cycles scheduled (e.g., quarterly taxonomy refresh validation, annual data model review) with stakeholder checkpoints? [Sustainability, Spec FR-002, Assumptions]

---

## Sign-Off

**Specification Author**: __________________ Date: __________

**CET Program Lead**: __________________ Date: __________

**Implementation Team Lead**: __________________ Date: __________

**Quality Assurance**: __________________ Date: __________

---

*This checklist must be completed and approved before the SBIR CET Classifier feature is released to production. All checklist items must be marked complete with documented evidence artefacts.*
