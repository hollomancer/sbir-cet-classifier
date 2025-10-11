---
description: "Task list for SAM.gov API Data Enrichment feature implementation with TDD"
---

# Tasks: SAM.gov API Data Enrichment

**Input**: Design documents from `/specs/002-use-the-sam/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

**Testing Approach**: Test-Driven Development (TDD) - Tests written before implementation per constitution requirements
**Coverage Target**: ≥85% test coverage as mandated by project constitution

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`
- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3, US4)
- **[T]**: Test task (written before implementation)
- Include exact file paths in descriptions

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and SAM.gov integration foundation

- [x] T001 Create enrichment module structure in `src/sbir_cet_classifier/data/enrichment/`
- [x] T002 Create test structure in `tests/unit/enrichment/`, `tests/integration/enrichment/`, `tests/contract/enrichment/`
- [x] T003 Install additional dependencies: httpx>=0.25.0, tenacity>=8.2.0, pydantic>=2.0.0
- [x] T003a Create YAML configuration files in `config/enrichment.yaml` and `config/sam_api.yaml`
- [x] T004 [P] Configure SAM.gov API credentials and environment variables in project config
- [x] T005 [P] Create base configuration schema in `src/sbir_cet_classifier/common/config.py` for enrichment settings
- [x] T006 [P] Set up logging configuration for enrichment operations

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that all user stories depend on

### Tests First (TDD)
- [x] T007 [T] Write SAM.gov API client tests in `tests/unit/enrichment/test_sam_client.py`
- [x] T008 [T] Write rate limiting and circuit breaker tests
- [x] T009 [T] Write base enrichment service interface tests in `tests/unit/enrichment/test_enrichers.py`
- [x] T010 [T] Write Pydantic schema validation tests in `tests/unit/enrichment/test_schemas.py`
- [x] T011 [T] Write enrichment status tracking tests in `tests/unit/enrichment/test_status.py`
- [x] T012 [T] Write Parquet schema extension tests in `tests/unit/test_storage.py`
- [x] T013 [T] Write CLI command tests in `tests/unit/test_cli_enrichment.py`

### Implementation
- [x] T014 Create SAM.gov API client in `src/sbir_cet_classifier/data/enrichment/sam_client.py`
- [x] T015 Implement rate limiting and circuit breaker patterns in SAM.gov client
- [x] T016 Create base enrichment service interface in `src/sbir_cet_classifier/data/enrichment/enrichers.py`
- [x] T017 Implement data validation schemas using Pydantic for all SAM.gov API responses
- [x] T018 Create enrichment status tracking system in `src/sbir_cet_classifier/data/enrichment/status.py`
- [x] T019 Extend existing Parquet schema for enriched data storage in `src/sbir_cet_classifier/data/storage.py`
- [x] T020 Create base CLI commands for enrichment in `src/sbir_cet_classifier/cli/commands.py`

**Checkpoint**: ✅ Core SAM.gov integration infrastructure complete with ≥85% test coverage

## Phase 3: User Story 1 - Enhanced Award Analysis (Priority: P1)

**Story Goal**: Researchers can access comprehensive awardee background information for portfolio analysis

**Independent Test**: Query any existing award and verify enriched awardee data appears with historical performance metrics

### Tests First (TDD)
- [x] T021 [T] [US1] Write AwardeeProfile entity model tests in `tests/unit/enrichment/test_models.py`
- [x] T022 [T] [US1] Write awardee data matching logic tests (award number, UEI/DUNS, fuzzy matching)
- [x] T023 [T] [US1] [P] Write awardee historical data retrieval tests in `tests/unit/enrichment/test_awardee_service.py`
- [x] T024 [T] [US1] [P] Write awardee profile enrichment workflow tests
- [x] T025 [T] [US1] Write awardee_profiles.parquet storage tests in `tests/unit/test_awardee_storage.py`
- [x] T026 [T] [US1] Write CLI command `enrich-awardee` tests in `tests/unit/test_cli_awardee.py`
- [x] T027 [T] [US1] [P] Write awardee profile data validation tests
- [x] T028 [T] [US1] Write confidence scoring tests for awardee matches
- [x] T029 [T] [US1] Write integration tests in `tests/integration/enrichment/test_awardee_integration.py`

### Implementation
- [x] T030 [US1] Create AwardeeProfile entity model in `src/sbir_cet_classifier/data/enrichment/models.py`
- [x] T031 [US1] Implement awardee data matching logic (award number, UEI/DUNS, fuzzy name matching)
- [x] T032 [US1] [P] Create awardee historical data retrieval service in `src/sbir_cet_classifier/data/enrichment/awardee_service.py`
- [x] T033 [US1] [P] Implement awardee profile enrichment workflow in enrichers.py
- [x] T034 [US1] Create awardee_profiles.parquet storage schema and writer
- [x] T035 [US1] Add CLI command `enrich-awardee` for single award awardee enrichment
- [x] T036 [US1] [P] Create data validation for awardee profile consistency
- [x] T037 [US1] Implement confidence scoring for awardee matches
- [x] T038 [US1] Add awardee enrichment to existing award display/export functionality

**Checkpoint**: ✅ User Story 1 complete - Awardee enrichment functional with ≥85% test coverage

## Phase 4: User Story 4 - Enhanced Classification via Solicitation Analysis (Priority: P2)

**Story Goal**: CET classification system leverages solicitation text for improved accuracy

**Independent Test**: Compare classification accuracy before and after solicitation text enrichment

### Tests First (TDD)
- [x] T039 [T] [US4] Write Solicitation entity model tests in `tests/unit/enrichment/test_models.py`
- [x] T040 [T] [US4] [P] Write solicitation text retrieval tests in `tests/unit/enrichment/test_solicitation_service.py`
- [x] T041 [T] [US4] [P] Write solicitation text parsing and keyword extraction tests
- [x] T042 [T] [US4] Write solicitations.parquet storage tests in `tests/unit/test_solicitation_storage.py`
- [x] T043 [T] [US4] Write enhanced CET classifier tests in `tests/unit/test_enhanced_scoring.py`
- [x] T044 [T] [US4] Write solicitation-enhanced TF-IDF vectorization tests
- [x] T045 [T] [US4] [P] Write batch processing pipeline tests for solicitation enrichment
- [x] T046 [T] [US4] Write CLI command `enrich-solicitation` tests
- [x] T047 [T] [US4] Write CET relevance scoring tests for solicitation text
- [x] T048 [T] [US4] Write A/B testing framework tests in `tests/integration/test_classification_accuracy.py`

### Implementation
- [x] T049 [US4] Create Solicitation entity model in `src/sbir_cet_classifier/data/enrichment/models.py`
- [x] T050 [US4] [P] Implement solicitation text retrieval service in `src/sbir_cet_classifier/data/enrichment/solicitation_service.py`
- [x] T051 [US4] [P] Create solicitation text parsing and keyword extraction
- [x] T052 [US4] Create solicitations.parquet storage schema and writer
- [x] T053 [US4] Extend existing CET classifier in `src/sbir_cet_classifier/models/scoring.py` to incorporate solicitation text
- [x] T054 [US4] Implement solicitation-enhanced TF-IDF vectorization
- [x] T055 [US4] [P] Add solicitation enrichment to batch processing pipeline
- [x] T056 [US4] Create CLI command `enrich-solicitation` for solicitation text enrichment
- [x] T057 [US4] Implement CET relevance scoring for solicitation text
- [x] T058 [US4] Add A/B testing framework to measure classification accuracy improvement

**Checkpoint**: ✅ User Story 4 complete - Enhanced classification functional with ≥85% test coverage

**Checkpoint**: ✅ User Story 4 complete - Enhanced classification functional with ≥85% test coverage

## Phase 5: User Story 2 - Program Context Discovery (Priority: P2)

**Story Goal**: Analysts can understand broader program context through agency program office information

**Independent Test**: Examine any award and verify program office details and related opportunities are displayed

### Tests First (TDD)
- [x] T059 [T] [US2] Write ProgramOffice entity model tests in `tests/unit/enrichment/test_models.py`
- [x] T060 [T] [US2] [P] Write program office data retrieval tests in `tests/unit/enrichment/test_program_service.py`
- [x] T061 [T] [US2] [P] Write related opportunities discovery tests
- [x] T062 [T] [US2] Write program_offices.parquet storage tests in `tests/unit/test_program_storage.py`
- [x] T063 [T] [US2] Write program office enrichment workflow tests
- [x] T064 [T] [US2] Write CLI command `enrich-program` tests
- [x] T065 [T] [US2] [P] Write program office data validation tests
- [x] T066 [T] [US2] Write strategic focus area analysis tests
- [x] T067 [T] [US2] Write integration tests in `tests/integration/enrichment/test_program_integration.py`

### Implementation
- [x] T068 [US2] Create ProgramOffice entity model in `src/sbir_cet_classifier/data/enrichment/models.py`
- [x] T069 [US2] [P] Implement program office data retrieval service in `src/sbir_cet_classifier/data/enrichment/program_service.py`
- [x] T070 [US2] [P] Create related opportunities discovery logic
- [x] T071 [US2] Create program_offices.parquet storage schema and writer
- [x] T072 [US2] Implement program office enrichment workflow in enrichers.py
- [x] T073 [US2] Add CLI command `enrich-program` for program office enrichment
- [x] T074 [US2] [P] Create program office data validation and consistency checks
- [x] T075 [US2] Add program context to award display and analytics functionality
- [x] T076 [US2] Implement strategic focus area analysis and categorization

**Checkpoint**: ✅ User Story 2 complete - Program context discovery functional with ≥85% test coverage

## Phase 6: User Story 3 - Comprehensive Award Lifecycle Tracking (Priority: P3)

**Story Goal**: Portfolio managers can track complete award lifecycle including modifications and amendments

**Independent Test**: Examine awards with known modifications and verify amendment history is captured chronologically

### Tests First (TDD)
- [x] T077 [T] [US3] Write AwardModification entity model tests in `tests/unit/enrichment/test_models.py`
- [x] T078 [T] [US3] [P] Write award modification retrieval tests in `tests/unit/enrichment/test_modification_service.py`
- [x] T079 [T] [US3] [P] Write award lifecycle timeline construction tests
- [x] T080 [T] [US3] Write award_modifications.parquet storage tests in `tests/unit/test_modification_storage.py`
- [x] T081 [T] [US3] Write modification tracking workflow tests
- [x] T082 [T] [US3] Write CLI command `enrich-modifications` tests
- [x] T083 [T] [US3] [P] Write modification data validation and chronological ordering tests
- [x] T084 [T] [US3] Write funding change analysis tests
- [x] T085 [T] [US3] Write integration tests in `tests/integration/enrichment/test_modification_integration.py`

### Implementation
- [x] T086 [US3] Create AwardModification entity model in `src/sbir_cet_classifier/data/enrichment/models.py`
- [x] T087 [US3] [P] Implement award modification retrieval service in `src/sbir_cet_classifier/data/enrichment/modification_service.py`
- [x] T088 [US3] [P] Create award lifecycle timeline construction logic
- [x] T089 [US3] Create award_modifications.parquet storage schema and writer
- [x] T090 [US3] Implement modification tracking workflow in enrichers.py
- [x] T091 [US3] Add CLI command `enrich-modifications` for award modification enrichment
- [x] T092 [US3] [P] Create modification data validation and chronological ordering
- [x] T093 [US3] Add award timeline visualization to display functionality
- [x] T094 [US3] Implement funding change analysis and reporting

**Checkpoint**: ✅ User Story 3 complete - Award lifecycle tracking functional with ≥85% test coverage

## Phase 7: Integration & Polish

**Purpose**: Cross-cutting concerns and system integration

### Tests First (TDD)
- [x] T095 [T] [P] Write comprehensive batch enrichment pipeline tests in `tests/integration/test_batch_enrichment.py`
- [x] T096 [T] [P] Write enrichment job management and progress tracking tests
- [x] T097 [T] [P] Write comprehensive error handling and retry logic tests
- [x] T098 [T] [P] Write enrichment data quality metrics tests in `tests/unit/test_quality_metrics.py`
- [x] T099 [T] Write unified CLI command `enrich-batch` tests
- [x] T100 [T] [P] Write enrichment status dashboard tests
- [x] T101 [T] [P] Write data consistency validation tests in `tests/integration/test_data_consistency.py`
- [x] T102 [T] [P] Write performance optimization tests (parallel processing, caching)
- [x] T103 [T] Write enriched data export functionality tests
- [x] T104 [T] [P] Write enrichment configuration validation tests

### Implementation
- [x] T105 [P] Implement comprehensive batch enrichment pipeline combining all enrichment types
- [x] T106 [P] Create enrichment job management and progress tracking
- [x] T107 [P] Add comprehensive error handling and retry logic across all services
- [x] T108 [P] Implement enrichment data quality metrics and reporting
- [x] T109 Create unified CLI command `enrich-batch` for bulk processing of all enrichment types
- [x] T110 [P] Add enrichment status dashboard and monitoring
- [x] T111 [P] Implement data consistency validation across all enriched entities
- [x] T112 [P] Create enrichment performance optimization (parallel processing, caching)
- [x] T113 Add enriched data to existing export functionality
- [x] T114 [P] Create enrichment configuration validation and management
- [x] T115 Update documentation and quickstart guide for enrichment features

**Final Checkpoint**: ✅ SAM.gov API enrichment feature complete with comprehensive test coverage

## Phase 9: Partial Enrichment Handling (Critical Gap Resolution)

**Purpose**: Handle graceful degradation when SAM.gov data is incomplete or unavailable

### Tests First (TDD)
- [x] T116 [T] Write partial enrichment scenario tests in `tests/unit/enrichment/test_partial_enrichment.py`
- [x] T117 [T] Write graceful degradation tests for missing awardee data
- [x] T118 [T] Write fallback mechanism tests when API data unavailable
- [x] T119 [T] Write enrichment confidence scoring tests for partial data

### Implementation
- [x] T120 Implement partial enrichment handling in `src/sbir_cet_classifier/data/enrichment/enrichers.py`
- [x] T121 Create fallback mechanisms for missing SAM.gov data
- [x] T122 Add enrichment confidence scoring based on data completeness
- [x] T123 Update CLI commands to report partial enrichment status
- [x] T124 Add partial enrichment scenarios to batch processing pipeline

**Checkpoint**: ✅ Partial enrichment handling complete with graceful degradation

## Phase 8: High-Impact Refactoring (Post-Feature Implementation)

**Purpose**: Repository consolidation, performance optimization, and architectural improvements

### Root-Level Script Consolidation (Highest Priority)
- [ ] R001 [P] Audit all root-level Python scripts and categorize by functionality
- [ ] R002 Move `classify_awards.py` functionality to `src/sbir_cet_classifier/cli/classification.py`
- [ ] R003 Move `classify_nih_*.py` scripts to `src/sbir_cet_classifier/cli/nih_commands.py`
- [ ] R004 Move `test_nih_*.py` scripts to `tests/integration/nih/`
- [ ] R005 Move `benchmark_pipeline.py` to `src/sbir_cet_classifier/cli/benchmark.py`
- [ ] R006 Refactor `ingest_awards.py` into `src/sbir_cet_classifier/cli/ingestion.py`
- [ ] R007 [P] Extract common functionality from scripts to `src/sbir_cet_classifier/common/script_utils.py`
- [ ] R008 [P] Create unified CLI entry point in `src/sbir_cet_classifier/cli/app.py`
- [ ] R009 Update all script imports and dependencies
- [ ] R010 Remove original root-level scripts after migration verification

### Configuration Management Unification (High Priority)
- [ ] R011 Create unified configuration module structure in `src/sbir_cet_classifier/common/config/`
- [ ] R012 [P] Implement `BaseConfig` class with Pydantic validation
- [ ] R013 [P] Create `StorageConfig` class to replace current storage path logic
- [ ] R014 [P] Create `ClassificationConfig` class for ML model parameters
- [ ] R015 [P] Create `APIConfig` class for all external API configurations
- [ ] R016 Implement configuration hierarchy (env vars → YAML → defaults)
- [ ] R017 [P] Add configuration validation and error handling
- [ ] R018 Migrate all hardcoded configurations to unified system
- [ ] R019 [P] Update all modules to use new configuration system
- [ ] R020 Remove legacy configuration files and code

### Data Layer Consolidation (Medium Priority)
- [ ] R021 Create repository pattern interfaces in `src/sbir_cet_classifier/data/repositories/`
- [ ] R022 [P] Implement `AwardRepository` for award data access
- [ ] R023 [P] Implement `AssessmentRepository` for classification results
- [ ] R024 [P] Implement `TaxonomyRepository` for CET taxonomy data
- [ ] R025 [P] Implement `EnrichmentRepository` for enriched data access
- [ ] R026 Create caching layer with configurable backends (memory/Redis)
- [ ] R027 [P] Implement data model classes with Pydantic validation
- [ ] R028 [P] Add connection pooling for database/file operations
- [ ] R029 Migrate all direct data access to use repositories
- [ ] R030 Add data migration utilities for schema changes

### Performance Optimizations (Medium Priority)
- [ ] R031 [P] Implement async SAM.gov API client using httpx
- [ ] R032 [P] Add connection pooling for HTTP requests
- [ ] R033 [P] Implement chunked processing for large datasets
- [ ] R034 [P] Add memory usage monitoring and optimization
- [ ] R035 Create caching layer for frequently accessed data
- [ ] R036 [P] Implement parallel processing for classification tasks
- [ ] R037 [P] Add batch processing optimizations for enrichment
- [ ] R038 Optimize Parquet file loading with lazy evaluation
- [ ] R039 [P] Add performance monitoring and metrics collection
- [ ] R040 Implement data compression for storage optimization

### Dependency Injection Architecture (Medium Priority)
- [ ] R041 Install and configure dependency-injector package
- [ ] R042 [P] Create application container in `src/sbir_cet_classifier/common/container.py`
- [ ] R043 [P] Define service providers for repositories
- [ ] R044 [P] Define service providers for API clients
- [ ] R045 [P] Define service providers for configuration
- [ ] R046 Refactor CLI commands to use dependency injection
- [ ] R047 [P] Refactor API routes to use dependency injection
- [ ] R048 [P] Update service instantiation throughout codebase
- [ ] R049 Add container configuration validation
- [ ] R050 Update tests to use dependency injection

### Documentation Consolidation (Low Priority)
- [ ] R051 [P] Audit all 96 Markdown files and categorize by purpose
- [ ] R052 [P] Create new documentation structure in `docs/`
- [ ] R053 [P] Consolidate user guides into `docs/user-guide/`
- [ ] R054 [P] Consolidate developer docs into `docs/developer/`
- [ ] R055 [P] Consolidate operations docs into `docs/operations/`
- [ ] R056 Move historical documents to `docs/archive/`
- [ ] R057 [P] Update all documentation cross-references
- [ ] R058 [P] Create unified table of contents
- [ ] R059 Remove duplicate and outdated documentation
- [ ] R060 Add documentation validation and link checking

**Refactoring Checkpoint**: ✅ Repository consolidation and optimization complete

## Refactoring Success Metrics

### Code Quality Targets
- **Lines of Code**: Reduce by 25-30% (from ~15,422 to ~11,000)
- **Cyclomatic Complexity**: Reduce average from ~8 to ~5
- **Test Coverage**: Maintain ≥85%
- **Documentation Coverage**: Increase to 95%

### Performance Targets
- **Startup Time**: <2 seconds
- **Memory Usage**: <1GB for typical workloads
- **API Response Time**: <100ms p95
- **Data Loading**: 4-6x faster (from 2-3s to 0.5s)
- **API Throughput**: 5x faster (from 100/min to 500/min)

### Maintainability Targets
- **Configuration Changes**: Single file updates
- **New Feature Addition**: <1 day for simple features
- **Bug Fix Time**: <2 hours average
- **Onboarding Time**: <1 day for new developers

## Implementation Priority

1. **Phase 8.1**: Root-Level Script Consolidation (R001-R010) - 2 weeks
2. **Phase 8.2**: Configuration Unification (R011-R020) - 2 weeks  
3. **Phase 8.3**: Data Layer Consolidation (R021-R030) - 2 weeks
4. **Phase 8.4**: Performance Optimizations (R031-R040) - 1 week
5. **Phase 8.5**: Dependency Injection (R041-R050) - 1 week
6. **Phase 8.6**: Documentation Cleanup (R051-R060) - 1 week

**Total Refactoring Effort**: 9 weeks
**Expected ROI**: High - 25-30% code reduction, 2-5x performance improvement

## Dependencies

### User Story Completion Order
1. **Phase 3 (US1)** → Independent (can start after Phase 2)
2. **Phase 4 (US4)** → Independent (can start after Phase 2) 
3. **Phase 5 (US2)** → Independent (can start after Phase 2)
4. **Phase 6 (US3)** → Independent (can start after Phase 2)
5. **Phase 7** → Requires all user stories complete

### Critical Path
- Phase 1 → Phase 2 → Any User Story Phase → Phase 7
- User Story phases can run in parallel after Phase 2 completion
- **TDD Requirement**: All test tasks must complete before corresponding implementation tasks

## Test Coverage Strategy

### Unit Tests (≥85% coverage target)
- **Core Services**: SAM.gov client, enrichment services, data models
- **Data Processing**: Matching logic, validation, confidence scoring
- **CLI Commands**: All enrichment commands and batch operations
- **Storage**: Parquet schema extensions and data writers

### Integration Tests
- **API Integration**: Live SAM.gov API testing with circuit breakers
- **End-to-End Workflows**: Complete enrichment pipelines per user story
- **Data Consistency**: Cross-entity validation and referential integrity
- **Performance**: Batch processing and parallel execution validation

### Contract Tests
- **SAM.gov API**: Response schema validation and error handling
- **Internal APIs**: Enrichment service contracts and data schemas
- **Storage Contracts**: Parquet file format and schema compliance

## Implementation Strategy

### MVP Scope (Minimum Viable Product)
- **Phase 1-2**: Foundation with comprehensive test coverage
- **Phase 3**: User Story 1 only (Enhanced Award Analysis) with full TDD
- Basic enrichment pipeline with awardee data and ≥85% test coverage

### TDD Workflow per User Story
1. **Red**: Write failing tests for user story requirements
2. **Green**: Implement minimal code to pass tests
3. **Refactor**: Optimize implementation while maintaining test coverage
4. **Validate**: Ensure ≥85% coverage before story completion

### Incremental Delivery with Test Gates
1. **Release 1**: US1 (Awardee enrichment) - Full test coverage
2. **Release 2**: US1 + US4 (Enhanced classification) - Regression tests
3. **Release 3**: US1 + US4 + US2 (Program context) - Integration tests
4. **Release 4**: All user stories + polish - Performance tests

## Task Summary

- **Total Tasks**: 124 (59 test tasks + 65 implementation tasks)
- **Test Tasks**: 59 tasks following TDD approach
- **Implementation Tasks**: 65 tasks with test-first development
- **Setup/Foundation**: 21 tasks (7 setup + 14 foundation with tests)
- **US1 (Enhanced Award Analysis)**: 18 tasks (9 tests + 9 implementation)
- **US4 (Enhanced Classification)**: 20 tasks (10 tests + 10 implementation)
- **US2 (Program Context)**: 18 tasks (9 tests + 9 implementation)
- **US3 (Lifecycle Tracking)**: 18 tasks (9 tests + 9 implementation)
- **Integration & Polish**: 21 tasks (10 tests + 11 implementation)
- **Partial Enrichment**: 9 tasks (4 tests + 5 implementation)
- **Parallel Opportunities**: 35+ tasks marked [P] for concurrent execution
- **Test Coverage**: ≥85% coverage mandated by constitution, validated at each checkpoint
