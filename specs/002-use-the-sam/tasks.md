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
- [x] T003 Install additional dependencies: requests>=2.31.0, tenacity>=8.2.0, pydantic>=2.0.0
- [x] T004 [P] Configure SAM.gov API credentials and environment variables in project config
- [x] T005 [P] Create base configuration schema in `src/sbir_cet_classifier/common/config.py` for enrichment settings
- [x] T006 [P] Set up logging configuration for enrichment operations

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that all user stories depend on

### Tests First (TDD)
- [x] T007 [T] Write SAM.gov API client tests in `tests/unit/enrichment/test_sam_client.py`
- [x] T008 [T] Write rate limiting and circuit breaker tests
- [x] T009 [T] Write base enrichment service interface tests in `tests/unit/enrichment/test_enrichers.py`
- [ ] T010 [T] Write Pydantic schema validation tests in `tests/unit/enrichment/test_schemas.py`
- [ ] T011 [T] Write enrichment status tracking tests in `tests/unit/enrichment/test_status.py`
- [ ] T012 [T] Write Parquet schema extension tests in `tests/unit/test_storage.py`
- [ ] T013 [T] Write CLI command tests in `tests/unit/test_cli_enrichment.py`

### Implementation
- [x] T014 Create SAM.gov API client in `src/sbir_cet_classifier/data/enrichment/sam_client.py`
- [x] T015 Implement rate limiting and circuit breaker patterns in SAM.gov client
- [x] T016 Create base enrichment service interface in `src/sbir_cet_classifier/data/enrichment/enrichers.py`
- [ ] T017 Implement data validation schemas using Pydantic for all SAM.gov API responses
- [ ] T018 Create enrichment status tracking system in `src/sbir_cet_classifier/data/enrichment/status.py`
- [ ] T019 Extend existing Parquet schema for enriched data storage in `src/sbir_cet_classifier/data/storage.py`
- [x] T020 Create base CLI commands for enrichment in `src/sbir_cet_classifier/cli/commands.py`

**Checkpoint**: ✅ Core SAM.gov integration infrastructure complete with ≥85% test coverage

## Phase 3: User Story 1 - Enhanced Award Analysis (Priority: P1)

**Story Goal**: Researchers can access comprehensive awardee background information for portfolio analysis

**Independent Test**: Query any existing award and verify enriched awardee data appears with historical performance metrics

### Tests First (TDD)
- [ ] T021 [T] [US1] Write AwardeeProfile entity model tests in `tests/unit/enrichment/test_models.py`
- [ ] T022 [T] [US1] Write awardee data matching logic tests (award number, UEI/DUNS, fuzzy matching)
- [ ] T023 [T] [US1] [P] Write awardee historical data retrieval tests in `tests/unit/enrichment/test_awardee_service.py`
- [ ] T024 [T] [US1] [P] Write awardee profile enrichment workflow tests
- [ ] T025 [T] [US1] Write awardee_profiles.parquet storage tests in `tests/unit/test_awardee_storage.py`
- [ ] T026 [T] [US1] Write CLI command `enrich-awardee` tests in `tests/unit/test_cli_awardee.py`
- [ ] T027 [T] [US1] [P] Write awardee profile data validation tests
- [ ] T028 [T] [US1] Write confidence scoring tests for awardee matches
- [ ] T029 [T] [US1] Write integration tests in `tests/integration/enrichment/test_awardee_integration.py`

### Implementation
- [ ] T030 [US1] Create AwardeeProfile entity model in `src/sbir_cet_classifier/data/enrichment/models.py`
- [ ] T031 [US1] Implement awardee data matching logic (award number, UEI/DUNS, fuzzy name matching)
- [ ] T032 [US1] [P] Create awardee historical data retrieval service in `src/sbir_cet_classifier/data/enrichment/awardee_service.py`
- [ ] T033 [US1] [P] Implement awardee profile enrichment workflow in enrichers.py
- [ ] T034 [US1] Create awardee_profiles.parquet storage schema and writer
- [ ] T035 [US1] Add CLI command `enrich-awardee` for single award awardee enrichment
- [ ] T036 [US1] [P] Create data validation for awardee profile consistency
- [ ] T037 [US1] Implement confidence scoring for awardee matches
- [ ] T038 [US1] Add awardee enrichment to existing award display/export functionality

**Checkpoint**: ✅ User Story 1 complete - Awardee enrichment functional with ≥85% test coverage

## Phase 4: User Story 4 - Enhanced Classification via Solicitation Analysis (Priority: P2)

**Story Goal**: CET classification system leverages solicitation text for improved accuracy

**Independent Test**: Compare classification accuracy before and after solicitation text enrichment

### Tests First (TDD)
- [ ] T039 [T] [US4] Write Solicitation entity model tests in `tests/unit/enrichment/test_models.py`
- [ ] T040 [T] [US4] [P] Write solicitation text retrieval tests in `tests/unit/enrichment/test_solicitation_service.py`
- [ ] T041 [T] [US4] [P] Write solicitation text parsing and keyword extraction tests
- [ ] T042 [T] [US4] Write solicitations.parquet storage tests in `tests/unit/test_solicitation_storage.py`
- [ ] T043 [T] [US4] Write enhanced CET classifier tests in `tests/unit/test_enhanced_scoring.py`
- [ ] T044 [T] [US4] Write solicitation-enhanced TF-IDF vectorization tests
- [ ] T045 [T] [US4] [P] Write batch processing pipeline tests for solicitation enrichment
- [ ] T046 [T] [US4] Write CLI command `enrich-solicitation` tests
- [ ] T047 [T] [US4] Write CET relevance scoring tests for solicitation text
- [ ] T048 [T] [US4] Write A/B testing framework tests in `tests/integration/test_classification_accuracy.py`

### Implementation
- [ ] T049 [US4] Create Solicitation entity model in `src/sbir_cet_classifier/data/enrichment/models.py`
- [ ] T050 [US4] [P] Implement solicitation text retrieval service in `src/sbir_cet_classifier/data/enrichment/solicitation_service.py`
- [ ] T051 [US4] [P] Create solicitation text parsing and keyword extraction
- [ ] T052 [US4] Create solicitations.parquet storage schema and writer
- [ ] T053 [US4] Extend existing CET classifier in `src/sbir_cet_classifier/models/scoring.py` to incorporate solicitation text
- [ ] T054 [US4] Implement solicitation-enhanced TF-IDF vectorization
- [ ] T055 [US4] [P] Add solicitation enrichment to batch processing pipeline
- [ ] T056 [US4] Create CLI command `enrich-solicitation` for solicitation text enrichment
- [ ] T057 [US4] Implement CET relevance scoring for solicitation text
- [ ] T058 [US4] Add A/B testing framework to measure classification accuracy improvement

**Checkpoint**: ✅ User Story 4 complete - Enhanced classification functional with ≥85% test coverage

## Phase 5: User Story 2 - Program Context Discovery (Priority: P2)

**Story Goal**: Analysts can understand broader program context through agency program office information

**Independent Test**: Examine any award and verify program office details and related opportunities are displayed

### Tests First (TDD)
- [ ] T059 [T] [US2] Write ProgramOffice entity model tests in `tests/unit/enrichment/test_models.py`
- [ ] T060 [T] [US2] [P] Write program office data retrieval tests in `tests/unit/enrichment/test_program_service.py`
- [ ] T061 [T] [US2] [P] Write related opportunities discovery tests
- [ ] T062 [T] [US2] Write program_offices.parquet storage tests in `tests/unit/test_program_storage.py`
- [ ] T063 [T] [US2] Write program office enrichment workflow tests
- [ ] T064 [T] [US2] Write CLI command `enrich-program` tests
- [ ] T065 [T] [US2] [P] Write program office data validation tests
- [ ] T066 [T] [US2] Write strategic focus area analysis tests
- [ ] T067 [T] [US2] Write integration tests in `tests/integration/enrichment/test_program_integration.py`

### Implementation
- [ ] T068 [US2] Create ProgramOffice entity model in `src/sbir_cet_classifier/data/enrichment/models.py`
- [ ] T069 [US2] [P] Implement program office data retrieval service in `src/sbir_cet_classifier/data/enrichment/program_service.py`
- [ ] T070 [US2] [P] Create related opportunities discovery logic
- [ ] T071 [US2] Create program_offices.parquet storage schema and writer
- [ ] T072 [US2] Implement program office enrichment workflow in enrichers.py
- [ ] T073 [US2] Add CLI command `enrich-program` for program office enrichment
- [ ] T074 [US2] [P] Create program office data validation and consistency checks
- [ ] T075 [US2] Add program context to award display and analytics functionality
- [ ] T076 [US2] Implement strategic focus area analysis and categorization

**Checkpoint**: ✅ User Story 2 complete - Program context discovery functional with ≥85% test coverage

## Phase 6: User Story 3 - Comprehensive Award Lifecycle Tracking (Priority: P3)

**Story Goal**: Portfolio managers can track complete award lifecycle including modifications and amendments

**Independent Test**: Examine awards with known modifications and verify amendment history is captured chronologically

### Tests First (TDD)
- [ ] T077 [T] [US3] Write AwardModification entity model tests in `tests/unit/enrichment/test_models.py`
- [ ] T078 [T] [US3] [P] Write award modification retrieval tests in `tests/unit/enrichment/test_modification_service.py`
- [ ] T079 [T] [US3] [P] Write award lifecycle timeline construction tests
- [ ] T080 [T] [US3] Write award_modifications.parquet storage tests in `tests/unit/test_modification_storage.py`
- [ ] T081 [T] [US3] Write modification tracking workflow tests
- [ ] T082 [T] [US3] Write CLI command `enrich-modifications` tests
- [ ] T083 [T] [US3] [P] Write modification data validation and chronological ordering tests
- [ ] T084 [T] [US3] Write funding change analysis tests
- [ ] T085 [T] [US3] Write integration tests in `tests/integration/enrichment/test_modification_integration.py`

### Implementation
- [ ] T086 [US3] Create AwardModification entity model in `src/sbir_cet_classifier/data/enrichment/models.py`
- [ ] T087 [US3] [P] Implement award modification retrieval service in `src/sbir_cet_classifier/data/enrichment/modification_service.py`
- [ ] T088 [US3] [P] Create award lifecycle timeline construction logic
- [ ] T089 [US3] Create award_modifications.parquet storage schema and writer
- [ ] T090 [US3] Implement modification tracking workflow in enrichers.py
- [ ] T091 [US3] Add CLI command `enrich-modifications` for award modification enrichment
- [ ] T092 [US3] [P] Create modification data validation and chronological ordering
- [ ] T093 [US3] Add award timeline visualization to display functionality
- [ ] T094 [US3] Implement funding change analysis and reporting

**Checkpoint**: ✅ User Story 3 complete - Award lifecycle tracking functional with ≥85% test coverage

## Phase 7: Integration & Polish

**Purpose**: Cross-cutting concerns and system integration

### Tests First (TDD)
- [ ] T095 [T] [P] Write comprehensive batch enrichment pipeline tests in `tests/integration/test_batch_enrichment.py`
- [ ] T096 [T] [P] Write enrichment job management and progress tracking tests
- [ ] T097 [T] [P] Write comprehensive error handling and retry logic tests
- [ ] T098 [T] [P] Write enrichment data quality metrics tests in `tests/unit/test_quality_metrics.py`
- [ ] T099 [T] Write unified CLI command `enrich-batch` tests
- [ ] T100 [T] [P] Write enrichment status dashboard tests
- [ ] T101 [T] [P] Write data consistency validation tests in `tests/integration/test_data_consistency.py`
- [ ] T102 [T] [P] Write performance optimization tests (parallel processing, caching)
- [ ] T103 [T] Write enriched data export functionality tests
- [ ] T104 [T] [P] Write enrichment configuration validation tests

### Implementation
- [ ] T105 [P] Implement comprehensive batch enrichment pipeline combining all enrichment types
- [ ] T106 [P] Create enrichment job management and progress tracking
- [ ] T107 [P] Add comprehensive error handling and retry logic across all services
- [ ] T108 [P] Implement enrichment data quality metrics and reporting
- [ ] T109 Create unified CLI command `enrich-batch` for bulk processing of all enrichment types
- [ ] T110 [P] Add enrichment status dashboard and monitoring
- [ ] T111 [P] Implement data consistency validation across all enriched entities
- [ ] T112 [P] Create enrichment performance optimization (parallel processing, caching)
- [ ] T113 Add enriched data to existing export functionality
- [ ] T114 [P] Create enrichment configuration validation and management
- [ ] T115 Update documentation and quickstart guide for enrichment features

**Final Checkpoint**: ✅ SAM.gov API enrichment feature complete with comprehensive test coverage

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

- **Total Tasks**: 115 (55 test tasks + 60 implementation tasks)
- **Test Tasks**: 55 tasks following TDD approach
- **Implementation Tasks**: 60 tasks with test-first development
- **Setup/Foundation**: 20 tasks (6 setup + 14 foundation with tests)
- **US1 (Enhanced Award Analysis)**: 18 tasks (9 tests + 9 implementation)
- **US4 (Enhanced Classification)**: 20 tasks (10 tests + 10 implementation)
- **US2 (Program Context)**: 18 tasks (9 tests + 9 implementation)
- **US3 (Lifecycle Tracking)**: 18 tasks (9 tests + 9 implementation)
- **Integration & Polish**: 21 tasks (10 tests + 11 implementation)
- **Parallel Opportunities**: 35+ tasks marked [P] for concurrent execution
- **Test Coverage**: ≥85% coverage mandated by constitution, validated at each checkpoint
