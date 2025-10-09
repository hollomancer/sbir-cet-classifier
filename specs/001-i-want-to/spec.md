# Feature Specification: SBIR Award Applicability Assessment

**Feature Branch**: `[001-i-want-to]`  
**Created**: 2025-10-08  
**Status**: Draft  
**Input**: User description: "I want to analyze all SBIR awards and determine how applicable they are to critical and emerging technology areas."

## Clarifications

### Session 2025-10-08

- Q: How should the High/Medium/Low applicability levels be determined for SBIR awards? → A: Option A (Fixed score bands using the 0–100 applicability score)
- Q: What requirements should govern the supporting evidence statements that accompany each CET applicability classification? → A: Option B (Provide summary sentence ≤50 words referencing source section and rationale tag)
- Q: When the CET taxonomy is updated, how should previously classified awards be handled? → A: Option C (Maintain historical classifications and append a new assessment tagged with taxonomy version)
- Q: What resolution target should apply to items in the manual review queue? → A: Option C (Resolve 100% of items by end of fiscal quarter)
- Q: For analysts comparing multiple agencies or fiscal ranges, what experience should the filters support? → A: Option B (Multiple agencies but a single continuous fiscal range)
- Q: Which data source will serve as the authoritative SBIR award feed for this personal project? → A: Option A (Public SBIR.gov bulk data downloads)
- Q: What refresh cadence should the SBIR.gov data ingestion follow? → A: Option C (On-demand refresh triggered manually)
- Q: How should the project handle Phase III or other non-standard awards present in the SBIR.gov dataset? → A: Option A (Include them in classification alongside Phase I/II)
- Q: How should CET weights and classifiers appear in the export CSV? → A: Option A (Include a normalized 0–1 weight column for every CET area, with weights per award summing to 1)

### Session 2025-10-09

- Q: Who should be able to call the CLI and FastAPI endpoints, and how should we authenticate/authorize them? → A: Limit to offline CLI; FastAPI internal only

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Portfolio Analyst Reviews Alignment (Priority: P1)

A federal portfolio analyst wants to understand how SBIR investments support critical and emerging technology (CET) focus areas.

**Why this priority**: Leadership decisions depend on timely evidence that current awards advance CET priorities.

**Independent Test**: Load the consolidated SBIR award dataset and confirm the analyst can produce a CET alignment summary without additional tooling.

**Acceptance Scenarios**:

1. **Given** the SBIR award dataset for a selected fiscal year and the current CET taxonomy, **When** the analyst opens the overview view, **Then** they see each CET area with counts, obligated dollars, and share of total awards (calculated as `awards_in_area / total_visible_awards` and `obligated_in_area / total_visible_obligated`).  
2. **Given** the same dataset, **When** the analyst filters to a specific agency (e.g., Air Force), **Then** the view refreshes within two interactions, keeps the same share calculations, and highlights the most applicable award.  
3. **Given** a multi-agency selection spanning a continuous fiscal year range, **When** the analyst compares CET areas, **Then** the interface aggregates share metrics across agencies while preserving per-agency drill-down availability.

---

### User Story 2 - Technology Strategist Investigates Gaps (Priority: P2)

A technology strategy lead needs to identify CET areas with low SBIR coverage and drill down to representative awards.

**Why this priority**: Gap analysis informs future solicitations and budgets.

**Independent Test**: From the CET summary, select an area and confirm the strategist can review top awards, supporting rationale, and gaps in under 5 minutes.

**Acceptance Scenarios**:

1. **Given** a CET area with lower SBIR coverage than peer areas in the selected view, **When** the strategist selects that area, **Then** they see award-level details including applicability scores, rationale snippets, and metadata needed for follow-up outreach.

---

### User Story 3 - Data Steward Shares Findings (Priority: P3)

A data steward needs to export the CET applicability results for cross-agency collaboration.

**Why this priority**: Stakeholders outside the platform require offline access for workshops and compliance reviews.

**Independent Test**: Trigger an export and confirm the steward receives a structured file containing all visible fields within the 10-minute service window defined in SC-004.

**Acceptance Scenarios**:

1. **Given** an analyst-curated filter set, **When** the steward requests an export, **Then** the system generates a downloadable file containing award-level CET classifications, summary metrics, and footnotes describing data currency.

---

### Edge Cases

- Awards missing abstracts or keywords must be surfaced for manual review with a “data incomplete” status, routed into the manual review queue, retried against agency supplements/contracting officer addenda, and re-evaluated automatically once missing text is ingested.  
- Awards that legitimately map to multiple CET areas must show all applicable categories with a tie-breaking explanation for the primary alignment.  
- Newly introduced CET areas must be versioned so historical reports retain the taxonomy in effect at the time of analysis.  
- Awards referencing controlled information must be excluded from exports while remaining visible in aggregate totals.
- When taxonomy updates occur, the system must append a re-assessment tagged with the new taxonomy version while preserving earlier classification history, re-running the classification pipeline for affected awards and logging the taxonomy diff and execution timestamp.
- When SBIR.gov publishes corrected award data, the ingestion pipeline must support fiscal year backfills that rerun processing for the affected partitions, regenerate applicability assessments, and record the applied correction window.  
- If agency feeds are delayed or arrive asynchronously, the ingestion process must queue pending files, deduplicate awards using `award_id` and `agency`, and emit reconciliation reports for late arrivals.  
- Tie-breaking for awards aligned to multiple CET areas must prefer the highest applicability score; ties fall back to the largest obligated amount, then the most recent award date.  
- If SBIR.gov bulk archives are unavailable, the system must retry for up to 24 hours using cached copies before alerting the operator and flagging the refresh as incomplete.  
- Manual refresh operations must choose between incremental (single fiscal range) and full reprocess modes; incremental runs apply when the requested window spans ≤3 contiguous fiscal years (or when explicitly approved for emergency corrections), while full reprocess is required for broader scopes or structural schema changes. Incremental runs update the selected fiscal years in place without mutating other partitions, and operator rationale must be logged in the refresh manifest.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST ingest the authoritative SBIR award dataset (Phase I, II, and III) sourced from the SBIR.gov bulk download endpoints (e.g., `https://www.sbir.gov/sites/default/files/sbir_awards_FY{YYYY}.zip`) covering fiscal years 1983–present. Ingestion executes a scheduled monthly refresh with optional manual triggers and MUST capture for every record: `award_id`, `agency`, `sub_agency` (when available), `topic_code`, `abstract`, `keywords`, `phase`, `firm_name`, `firm_city`, `firm_state`, `award_amount`, `award_date`, and ingestion metadata (`source_version`, `ingested_at`). Records missing required narrative text (abstract or keywords) MUST be flagged for manual review while preserving the raw record. The ingestion pipeline MUST validate archives atomically, roll back partial loads on failure, log malformed records with remediation notes, and partition processed data by fiscal year so reprocessing can replace a single partition without impacting others. Duplicate or resubmitted awards are keyed by (`award_id`, `agency`) and MUST be merged with revision metadata rather than duplicated downstream.  
- **FR-002**: System MUST maintain a standardized catalog of critical and emerging technology areas, including definitions, parent groupings, and effective dates, and expose the active version to users. The CET Program Lead owns the taxonomy, conducts a quarterly review in coordination with the National Science and Technology Council, and publishes versioned updates (`NSTC-{YYYY}Q{n}`) with change logs distributed to analysts and model maintainers.  
- **FR-003**: System MUST evaluate every award against the CET catalog to assign a primary applicability classification (High ≥70, Medium 40–69, Low <40 on the 0–100 applicability score) and up to three supporting CET areas with concise evidence statements that capture a ≤50-word summary referencing the source text section and an applicability rationale tag. Applicability scores MUST be produced by a calibrated multinomial logistic regression model trained on TF-IDF features derived from award abstracts, keywords, and solicitation text, with calibrated probabilities scaled linearly to the 0–100 range. Model coefficients, calibration parameters, and feature vocabularies MUST be versioned alongside taxonomy updates. Evidence statements MUST cite one of the sanctioned source types (`abstract`, `keywords`, `solicitation`, or `reviewer_notes`), include the excerpt location, and record a rationale tag from the approved taxonomy appendix.  
- **FR-004**: System MUST provide interactive filters for fiscal year (single continuous range), agency (multi-select), CET area, award phase, and small business location, updating summary metrics and counts within two user interactions.  
- **FR-005**: System MUST display award-level drill-down pages summarizing applicability scores, evidence statements, source text excerpts, and taxonomy version used.  
- **FR-006**: System MUST allow authorized users to export the filtered dataset and summary tables to a structured file (e.g., CSV or spreadsheet) accompanied by data currency and methodology notes, and each export row MUST include normalized 0–1 weight columns for every active CET area such that the weights per award sum to 1. Exports MUST surface a `data_currency_note` indicating the ingestion timestamp and SBIR.gov source archive version, list the count of controlled awards excluded from line-level output, and preserve aggregate totals for those exclusions.  
- **FR-007**: System MUST track the percentage of awards classified automatically versus flagged for review, present unresolved items in a review queue, and ensure 100% of queued items are resolved by the end of each fiscal quarter. Review queue entries MUST be created when classifier confidence falls below calibrated thresholds, required narrative fields are missing, or analysts flag conflicts. Each queue item MUST capture an assigned reviewer, opened timestamp, due-by date (end of fiscal quarter), and resolution notes. Items transition through the states `pending` → `in_review` → `resolved` or `escalated` (if overdue). Escalated items notify the program manager and must re-enter `in_review` within 5 business days.

### Non-Functional Requirements

- **NFR-001**: Exports covering up to 50,000 awards MUST complete within a 10-minute service window, expose progress telemetry, and record start/finish timestamps in `artifacts/export_runs.json`.  
- **NFR-002**: Applicability scoring MUST process batches of 100 awards with ≤500 ms median latency on the reference analyst workstation (Apple M2 Pro, 16 GB RAM) or the equivalent cloud profile (AWS m6i.xlarge), log p50/p95 metrics per run, persist results under `artifacts/scoring_runs.json`, and alert when p95 exceeds 750 ms.  
- **NFR-003**: Ingestion refreshes MUST support monthly full runs and manual on-demand triggers, retry failed SBIR.gov downloads for 24 hours using cached archives, and log remediation notes for partitions requiring backfill.  
- **NFR-004**: Manual review operations MUST enforce quarterly resolution SLAs, produce reconciliation reports for delayed agency feeds, and maintain audit trails for taxonomy re-assessments and tie-breaking rationale.  
- **NFR-005**: Development MUST use Python 3.11+, enforce `ruff` formatting/linting, `pytest -m "not slow"` smoke passes, and maintain ≥85% statement coverage across unit/integration suites before merge.  
- **NFR-006**: Observability MUST include structured JSON logs with correlation IDs across ingestion, scoring, API, and CLI surfaces, and redact controlled award details from logs and exports.  
- **NFR-007**: Access control MUST restrict usage to offline CLI workflows operated within trusted workstations; the FastAPI service remains internal-only behind network-level controls with no external authentication surface.

### Key Entities *(include if feature involves data)*

- **SBIR Award**: A unique record containing agency metadata, topic identifiers, abstracts, keywords, funding amount, phase, firm location, and award date.  
- **CET Area**: A taxonomy entry representing a critical or emerging technology category with definition, parent group, effective date, and status (active, retired).  
- **Applicability Assessment**: The output linking an SBIR Award to one or more CET Areas with a classification level, applicability score, evidence rationale, reviewer notes, and assessment timestamp.  
- **Review Queue Item**: A placeholder for awards lacking sufficient data or consensus, tracking assigned reviewer, status, and resolution notes.

### Assumptions

- CET taxonomy references the most recent National Science and Technology Council critical and emerging technology list and is reviewed quarterly.  
- The consolidated SBIR dataset (1983–present) is accessible with abstracts and keywords; awards without text will require manual review, temporary `data_incomplete` status, and follow-up ingestion once missing text sources (e.g., agency supplements) are recovered.  
- Applicability classifications use a standardized rubric mapping narrative evidence to High/Medium/Low and a 0–100 score for reporting consistency.  
- Applicability scoring uses TF-IDF vectorization with logistic regression and isotonic calibration, producing reproducible 0–100 scores aligned with FR-003 thresholds.  
- No classified or export-controlled award details will be stored; aggregate metrics will respect existing disclosure controls.
- SBIR.gov bulk award archives publish monthly; the project retains read access to historical ZIP archives and caches the two most recent refreshes to mitigate downtime.  
- Manual review is initiated when an award lacks narrative text, when ingestion detects malformed fields, or when classifier confidence drops below calibration thresholds.  
- Ingestion runs operate as partitioned full refreshes per fiscal year; incremental runs append new fiscal periods without mutating closed partitions, keeping change logs for reconciliation.  
- Access to SBIR.gov archives is authorized for research use under public data terms, with retention limited to metadata and derived applicability scores.  
- Data dictionary definitions for each ingestion field are anchored to the schema described in `data-model.md`, and any schema change requires corresponding export updates.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: ≥95% of SBIR awards within a selected fiscal year receive an automated High/Medium/Low applicability classification with at least one CET area identified, measured per refresh run as `auto_classified / total_awards` and logged to the review dashboard. Percentage calculations MUST use the same denominators (total visible awards and obligated dollars) as the CET overview metrics and export `share` fields.  
- **SC-002**: Portfolio analysts can generate a CET alignment summary for any agency and fiscal year in ≤3 minutes, and technology strategists can reach award-level drill-downs with supporting rationale in ≤5 minutes during user acceptance testing.  
- **SC-003**: Expert reviewers agree with the automated primary CET classification for ≥85% of a stratified 200-award validation sample collected after each taxonomy refresh, with per-CET area precision and recall each ≥80% on the same sample.  
- **SC-004**: Exports covering up to 50,000 awards complete within a 10-minute service window and contain 100% of fields visible in the interface, with zero critical data quality defects logged post-release.  
- **SC-005**: Manual review queue resolves 100% of flagged awards by the end of each fiscal quarter, with overdue items escalated to the program manager.
- **SC-006**: Monthly ingestion refreshes processing up to 120,000 awards complete within 2 hours wall-clock time, log ≤0.5% malformed records (all routed to remediation), and achieve ≥99% field completeness across required attributes.  
- **SC-007**: Automated applicability scoring processes batches of 100 awards with ≤500 ms median latency on reference hardware and logs per-run latency distributions for regression tracking.  
