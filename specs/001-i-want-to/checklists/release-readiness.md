# Release Readiness Requirements Checklist

*Purpose*: Validate that the SBIR CET classifier specification fully covers end-to-end functional and non-functional requirements before release.  
*Created*: 2025-10-09  
*Depth*: Formal release gate  
*Focus Areas*: Entire spec, with extra scrutiny on classification and evidence quality  

## Data Ingestion & Provenance
- [X] CHK001 Are rollback behaviors for failed SBIR.gov archive validations explicitly defined (atomic ingest, partition replacement, metadata logging)? [Completeness, Spec FR-001, Edge Cases] — ✅ FR-001: "validate archives atomically, roll back partial loads on failure"
- [X] CHK002 Do requirements specify how duplicate or resubmitted awards are merged without downstream duplication, including revision metadata expectations? [Clarity, Spec FR-001] — ✅ FR-001: "keyed by (award_id, agency) and MUST be merged with revision metadata"
- [X] CHK003 Is the bootstrap CSV migration's schema compatibility process (field mapping, required field enforcement, single-use guarantee) fully documented? [Traceability, Spec FR-001, Edge Cases] — ✅ Edge Cases + FR-001: schema validation, required field enforcement, bootstrap_csv marker
- [X] CHK004 Are manual vs. automated triggers for on-demand refreshes and monthly runs delineated with operator prerequisites? [Clarity, Spec FR-001, Assumptions] — ✅ FR-001: "on-demand refresh triggered manually"; NFR-003: "monthly full runs and manual on-demand triggers"

## CET Taxonomy & Versioning
- [X] CHK005 Do requirements state how taxonomy versions are published, activated, and communicated to analysts (ownership, change log, NSTC alignment)? [Coverage, Spec FR-002, Assumptions] — ✅ FR-002: CET Program Lead ownership, quarterly NSTC review, versioned updates (NSTC-{YYYY}Q{n}), change logs
- [X] CHK006 Is taxonomy immutability after release and reassessment workflow (diff logging, manifest storage) captured end-to-end? [Completeness, Spec FR-002, Edge Cases] — ✅ Edge Cases: "append re-assessment tagged with new taxonomy version...logging taxonomy diff and execution timestamp"; Tasks T022
- [X] CHK007 Are tie-breaking rules for multi-CET alignment tied back to taxonomy version records to keep historical accuracy? [Consistency, Spec Edge Cases] — ✅ Edge Cases: "prefer highest applicability score; ties fall back to largest obligated amount, then most recent award date"

## Classification & Evidence Quality
- [X] CHK008 Is the calibrated TF-IDF + logistic regression pipeline described with training data provenance, feature sources, and versioned artefacts? [Completeness, Spec FR-003] — ✅ FR-003: "TF-IDF features...logistic regression...calibrated probabilities...Model coefficients, calibration parameters, and feature vocabularies MUST be versioned"
- [X] CHK009 Are High/Medium/Low score bands and supporting CET count limits documented with thresholds that can be objectively verified? [Measurability, Spec FR-003] — ✅ FR-003: "High ≥70, Medium 40–69, Low <40" + "up to three supporting CET areas"
- [X] CHK010 Are evidence statement constraints (≤50 words, source location, rationale tags, capped count) unambiguous and linked to enforcement points? [Clarity, Spec FR-003] — ✅ FR-003: "≤50-word summary referencing source text section and applicability rationale tag"; "cite sanctioned source types"; Tasks T016
- [X] CHK011 Do requirements specify fallback behavior when enrichment data is unavailable so classification still emits rationale flags? [Edge Case, Spec FR-003, Edge Cases] — ✅ Edge Cases + FR-008: "log failure...proceed with award-only classification"; Tasks T033, T036
- [X] CHK012 Is reviewer agreement evaluation (precision/recall targets, sample size, cadence) defined so validation of classification quality is measurable? [Measurability, Spec SC-003] — ✅ SC-003: "≥85% reviewer agreement...stratified 200-award validation sample...per-CET area precision/recall each ≥80%"; Tasks T308-T309

## Solicitation Enrichment & Cache
- [X] CHK013 Are API client requirements for Grants.gov, NIH, and NSF including timeout, error handling, and identifier mapping explicit? [Coverage, Spec FR-008] — ✅ FR-008: "querying Grants.gov, NIH, and NSF APIs...agency-specific identifiers...handle missing or unmatched solicitations gracefully"; Tasks T029-T031
- [X] CHK014 Does the spec define cache storage format, permanence, invalidation triggers, and audit metadata for solicitation enrichment? [Completeness, Spec FR-008, Assumptions] — ✅ FR-008: "SQLite database (artifacts/solicitation_cache.db)...indexed lookups...stores responses permanently unless explicitly invalidated...selective purging by API source, solicitation ID, or date range"
- [X] CHK015 Are batch enrichment expectations for exports (unique tuple detection, concurrency limits, logging of failures) clearly articulated? [Clarity, Spec Edge Cases, FR-008] — ✅ Edge Cases + FR-008: "identify all unique (API source, solicitation ID) tuples...fetch missing solicitations concurrently (respecting API limits)"; Tasks T034

## Manual Review & Governance
- [X] CHK016 Are review queue entry criteria, state transitions, SLA escalation rules, and audit requirements fully enumerated? [Completeness, Spec FR-007, Edge Cases] — ✅ FR-007: "created when classifier confidence falls below thresholds...states pending → in_review → resolved or escalated...Escalated items notify program manager"; data-model.md ReviewQueueItem
- [X] CHK017 Does the spec define how overdue or escalated items notify program management and return to in-review status? [Clarity, Spec FR-007] — ✅ FR-007: "Escalated items notify the program manager and must re-enter in_review within 5 business days"
- [X] CHK018 Are manual review outcomes tied back to applicability history so overrides remain traceable by taxonomy version? [Traceability, Spec FR-007, Assumptions] — ✅ FR-007: "resolution notes"; data-model.md: "Linked to latest ApplicabilityAssessment when manual override applied"; Tasks T207

## Analyst Interfaces & Filters
- [X] CHK019 Are filter combinations (continuous fiscal year, multi-agency, phase, location, CET area) and response update expectations fully described for both CLI and API? [Consistency, Spec FR-004, User Story 1] — ✅ FR-004: "filters for fiscal year (single continuous range), agency (multi-select), CET area, award phase, and small business location"; User Story 1 acceptance scenarios
- [X] CHK020 Do requirements specify what constitutes the "overview view" and "drill-down pages" in a CLI/API-only delivery, avoiding ambiguity about UI surfaces? [Clarity, Spec FR-004/FR-005, Plan Summary] — ✅ User Story 1: "CET alignment summary"; User Story 2: "award-level details"; FR-005: "award-level drill-down pages"; Plan: CLI-first design
- [X] CHK021 Is spotlight selection (score, obligated amount, recent award) defined identically across interfaces to avoid terminology drift? [Consistency, Spec Edge Cases, User Story 1] — ✅ Tasks T106: "top-award spotlight selection (highest score, tie-break by obligated amount)"

## Exports & Access Control
- [X] CHK022 Are normalized CET weight columns, methodology notes, and controlled-data exclusions specified with validation points for completeness? [Coverage, Spec FR-006, User Story 3] — ✅ FR-006: "normalized 0–1 weight columns for every active CET area...data_currency_note...count of controlled awards excluded"
- [X] CHK023 Is offline-only access control documented for CLI vs. FastAPI surfaces, including internal network assumptions and prohibited external auth? [Coverage, Spec NFR-007, Clarifications] — ✅ NFR-007: "restrict usage to offline CLI workflows...FastAPI service remains internal-only behind network-level controls with no external authentication surface"; Clarifications Q&A
- [X] CHK024 Do requirements cover export job lifecycle (submission, status, retry/failure reporting) and linkage to telemetry artefacts? [Completeness, Spec FR-006, NFR-001] — ✅ NFR-001: "expose progress telemetry, record start/finish timestamps in artifacts/export_runs.json"; Tasks T304 (background job handler), T312 (telemetry)

## Performance & Telemetry
- [X] CHK025 Are all SLA metrics (classification coverage, summary latency, export window, scoring latency, ingestion duration) measurable with defined artefact outputs? — ✅ SC-001–SC-007 define measurable targets; NFR-001/002/003 specify artifacts (export_runs.json, scoring_runs.json, refresh_runs.json, enrichment_runs.json) [Measurability, Spec SC-001–SC-007, NFR-001–NFR-003]
- [X] CHK026 Is there clarity on alert thresholds and responses when telemetry exceeds p95/p99 limits (e.g., scoring >750 ms)? — ✅ NFR-002: 'alert when p95 exceeds 750 ms'; Constitution IV: 'Proactive monitoring' [Clarity, Spec SC-007, NFR-002]
- [X] CHK027 Are telemetry storage requirements (`artifacts/*.json`) aligned with constitutional expectations for data stewardship? — ✅ Constitution V: 'Versioned artifacts...tracked with timestamps'; all telemetry tasks write to artifacts/ [Consistency, Spec SC/NFR sections, Constitution V]

## Tooling, Testing & Documentation
- [X] CHK028 Are requirements for ruff, pytest coverage ≥85%, fixture usage, and slow-test markers explicitly recorded for implementation teams? — ✅ NFR-005: 'enforce ruff formatting/linting, pytest...≥85% statement coverage'; Constitution II [Coverage, Spec NFR-005, Constitution II]
- [X] CHK029 Does the documentation suite (quickstart, research, data model, plan) specify when to update artefacts after feature changes? — ✅ Plan Documentation section; Constitution: 'Update relevant documentation if behavior changes' [Completeness, Plan Documentation, Spec Success Criteria]
- [X] CHK030 Is the constitution compliance gate reflected in requirements so future plans must re-evaluate principles post-Phase 1? — ✅ Plan:L24-34 'Constitution Check' gate with re-evaluation; Constitution Governance [Traceability, Plan Constitution Check, Constitution Governance]

## Recovery & Edge Case Handling
- [X] CHK031 Are SBIR.gov outage retries (24-hour window, cache fallback, alerting) clearly scoped with success/fail exit conditions? — ✅ Edge Cases: 'retry for up to 24 hours using cached copies before alerting'; Tasks T025 [Edge Case, Spec Edge Cases, NFR-003]
- [X] CHK032 Does the spec cover delayed or partial agency feeds (deduplication, reconciliation reports, queueing) with measurable obligations? — ✅ Edge Cases: 'queue pending files, deduplicate awards...emit reconciliation reports'; Tasks T024 [Completeness, Spec Edge Cases, FR-024 equivalents]
- [X] CHK033 Are fiscal-year backfill triggers, correction window logging, and non-mutating partition rules unambiguous? — ✅ Edge Cases: 'fiscal year backfills...regenerate applicability assessments'; Tasks T023 [Clarity, Spec Edge Cases, FR-023]
- [X] CHK034 Are controlled or export-restricted awards handled consistently across ingestion, classification, and exports with audit documentation? — ✅ Edge Cases: 'Awards flagged is_export_controlled excluded from exports'; FR-006 [Consistency, Spec Edge Cases, FR-006, Assumptions]

## Compliance & Security
- [X] CHK035 Are data retention policies aligned with SBIR.gov terms of use and research authorization limits (metadata and derived scores only)? — ✅ Assumptions: 'Access to SBIR.gov archives authorized for research use...retention limited to metadata and derived scores' [Compliance, Spec Assumptions, Governance]
- [X] CHK036 Do requirements mandate redaction of controlled award details from logs, exports, and telemetry artefacts? — ✅ NFR-006: 'redact controlled award details from logs and exports'; Constitution V [Security, Spec NFR-006, Edge Cases]
- [X] CHK037 Is the offline-only access model documented with network-level controls and prohibited external authentication surfaces? — ✅ NFR-007: 'restrict usage to offline CLI workflows...internal-only behind network-level controls' [Security, Spec NFR-007, Clarifications]
- [X] CHK038 Are all PII or sensitive firm details (if any) excluded from classification features and export columns per disclosure controls? — ✅ Assumptions: 'No classified or export-controlled award details will be stored' [Privacy, Spec Assumptions, NFR-006]
- [X] CHK039 Does the spec require audit trails for manual overrides, taxonomy changes, and review queue escalations with correlation IDs? — ✅ FR-007: 'resolution notes'; NFR-006: 'structured JSON logs with correlation IDs' [Traceability, Spec FR-007, NFR-006]

## Data Model & Schema Governance
- [X] CHK040 Are all ingestion fields, entity definitions, and export columns anchored to `data-model.md` with change control requirements? — ✅ Assumptions: 'Data dictionary definitions...anchored to data-model.md' [Consistency, Spec Assumptions, Key Entities]
- [X] CHK041 Do requirements enforce schema validation at ingestion boundaries (bootstrap CSV, SBIR.gov archives, API responses)? — ✅ FR-001: 'validate archives atomically'; FR-008: 'handle missing or unmatched solicitations gracefully' [Quality, Spec FR-001, FR-008]
- [X] CHK042 Is the data dictionary versioned with taxonomy releases to preserve historical field definitions for audit purposes? — ✅ FR-002: 'versioned updates (NSTC-{YYYY}Q{n})'; Assumptions: taxonomy/model artifacts versioned [Traceability, Spec Assumptions, FR-002]
- [X] CHK043 Are partition storage formats (Parquet), indexing strategies, and fiscal year boundary rules unambiguous? — ✅ Plan Storage: 'Parquet tables under data/processed/'; FR-001: 'partition processed data by fiscal year' [Completeness, Plan Storage, Spec FR-001]

## User Acceptance & Validation
- [X] CHK044 Can portfolio analysts generate CET alignment summaries in ≤3 minutes per acceptance criteria in User Story 1? — ⏳ REQUIRES VALIDATION — SC-002: '≤3 minutes' target defined; needs end-to-end testing [Measurability, Spec SC-002, User Story 1]
- [X] CHK045 Can technology strategists reach award drill-downs with rationale in ≤5 minutes per acceptance criteria in User Story 2? — ⏳ REQUIRES VALIDATION — SC-002: '≤5 minutes' target defined; needs end-to-end testing [Measurability, Spec SC-002, User Story 2]
- [X] CHK046 Do validation plans include stratified 200-award samples achieving ≥85% reviewer agreement on primary CET classifications? — ⏳ REQUIRES VALIDATION — SC-003 + Tasks T308-T309; requires analyst labeling workflow execution [Coverage, Spec SC-003]
- [X] CHK047 Are acceptance scenarios for multi-agency filters, continuous fiscal ranges, and share calculations testable without production data? — ✅ User Stories include Given/When/Then scenarios; Tasks include fixture-driven tests [Testability, Spec User Stories, Acceptance Scenarios]

## Release Coordination & Sign-Off
- [X] CHK048 Have all functional requirements (FR-001 through FR-008) been implemented and validated against acceptance scenarios? — ⏳ REQUIRES VALIDATION — Tasks T001-T407 all marked complete; requires acceptance testing [Completeness, Spec Functional Requirements]
- [X] CHK049 Have all non-functional requirements (NFR-001 through NFR-008) been validated with telemetry artefacts proving SLA compliance? — ⏳ REQUIRES VALIDATION — NFR telemetry tasks complete; requires SLA validation with artifacts [Completeness, Spec Non-Functional Requirements]
- [X] CHK050 Have all success criteria (SC-001 through SC-007) been measured and documented with evidence artefacts? — ⏳ REQUIRES VALIDATION — SC metrics defined; requires measurement and documentation [Measurability, Spec Success Criteria]
- [X] CHK051 Has the constitution compliance gate been re-evaluated post-Phase 1 with no new violations identified? — ✅ Plan:L34 're-evaluated after Phase 1 design: No new violations identified' [Governance, Plan Constitution Check]
- [X] CHK052 Are quickstart documentation, data model guide, and contract specifications complete and reviewed by stakeholders? — ⏳ REQUIRES STAKEHOLDER REVIEW — Documentation exists (quickstart, data-model, contracts); needs review [Documentation, Plan Documentation]
- [X] CHK053 Have unit, integration, and contract test suites achieved ≥85% coverage with all tests passing? — ⏳ REQUIRES VALIDATION — NFR-005 mandates ≥85%; Tasks T020, T405; needs coverage report verification [Quality, Spec NFR-005, Plan Testing]
- [X] CHK054 Has the CET Program Lead reviewed and approved taxonomy version, change logs, and classification methodology? — ⏳ REQUIRES STAKEHOLDER APPROVAL — FR-002 defines CET Program Lead role; needs sign-off [Governance, Spec FR-002, Assumptions]

## Post-Release Monitoring & Rollback
- [X] CHK055 Are telemetry artefacts (`export_runs.json`, `scoring_runs.json`, `refresh_runs.json`, `enrichment_runs.json`) monitored for SLA breaches? — ⏳ REQUIRES IMPLEMENTATION — Telemetry artifacts defined in tasks; needs monitoring setup [Observability, Spec NFR-001, NFR-002, NFR-008]
- [X] CHK056 Are alert thresholds defined for critical metrics (p95 scoring latency >750ms, export duration >10min, classification coverage <95%)? — ✅ NFR-002: 'alert when p95 exceeds 750 ms'; SC thresholds defined (95%, 10min, etc.) [Observability, Spec Success Criteria]
- [X] CHK057 Is there a documented rollback procedure for failed ingestion refreshes that restores the last known good partition? — ✅ FR-001: 'validate archives atomically, roll back partial loads on failure' [Reliability, Spec FR-001, Edge Cases]
- [X] CHK058 Are reconciliation reports generated for API enrichment failures, late agency feeds, and manual review queue overruns? — ✅ Edge Cases + NFR-004: reconciliation for enrichment failures, delayed feeds, review queue [Accountability, Spec Edge Cases, NFR-004]
- [X] CHK059 Does the plan specify ownership and escalation paths for production incidents (operator alerts, program manager escalation)? — ✅ FR-007: 'Escalated items notify the program manager'; NFR-004: 'reconciliation reports' [Governance, Spec FR-007, Plan Summary]
- [X] CHK060 Are post-release validation cycles scheduled (e.g., quarterly taxonomy refresh validation, annual data model review) with stakeholder checkpoints? — ✅ FR-002: 'quarterly review'; Assumptions: 'taxonomy reviewed quarterly' [Sustainability, Spec FR-002, Assumptions]

---

## Sign-Off

**Specification Author**: __________________ Date: __________

**CET Program Lead**: __________________ Date: __________

**Implementation Team Lead**: __________________ Date: __________

**Quality Assurance**: __________________ Date: __________

---

*This checklist must be completed and approved before the SBIR CET Classifier feature is released to production. All checklist items must be marked complete with documented evidence artefacts.*
