# Data Model: SAM.gov API Enrichment

**Feature**: SAM.gov API Data Enrichment  
**Phase**: 1 - Design & Contracts  
**Date**: 2025-10-10

## Entity Relationships

```
Award (existing) ──┐
                   ├── EnrichedAward (1:1)
                   └── AwardeeProfile (N:1)
                        └── HistoricalAward (1:N)

Award ──── ProgramOffice (N:1)
       └── Solicitation (N:1)
       └── AwardModification (1:N)

EnrichmentStatus ──── Award (1:1)
```

## Core Entities

### EnrichedAward (extends existing Award)

**Purpose**: Extended award record with SAM.gov enrichment data

**Fields**:
- `award_id` (string, PK): Original award identifier
- `sam_award_id` (string, nullable): SAM.gov award identifier
- `enrichment_timestamp` (datetime): When enrichment was performed
- `enrichment_confidence` (float): Overall enrichment confidence score (0-1)
- `awardee_profile_id` (string, FK): Link to awardee profile
- `program_office_id` (string, FK): Link to program office
- `solicitation_id` (string, FK): Link to solicitation
- `has_modifications` (boolean): Whether award has modifications/amendments

**Validation Rules**:
- `enrichment_confidence` must be between 0.0 and 1.0
- `enrichment_timestamp` must not be in the future
- At least one enrichment field must be populated if record exists

**State Transitions**:
- Created → Enriching → Enriched → Validated
- Failed enrichment transitions to Error state with retry capability

### AwardeeProfile

**Purpose**: Historical performance and organizational data for award recipients

**Fields**:
- `profile_id` (string, PK): Unique awardee identifier (DUNS/UEI based)
- `organization_name` (string): Official organization name
- `duns_number` (string, nullable): DUNS identifier
- `uei_identifier` (string, nullable): Unique Entity Identifier
- `organization_type` (string): Business type (small business, university, etc.)
- `cage_code` (string, nullable): Commercial and Government Entity code
- `total_awards_count` (integer): Total number of awards received
- `total_award_value` (decimal): Total dollar value of all awards
- `success_rate` (float): Percentage of successfully completed awards
- `average_award_duration` (integer): Average award duration in days
- `primary_naics_codes` (array[string]): Primary NAICS industry codes
- `geographic_locations` (array[string]): Operating locations
- `first_award_date` (date): Date of first government award
- `last_award_date` (date): Date of most recent award
- `created_at` (datetime): Profile creation timestamp
- `updated_at` (datetime): Last profile update

**Validation Rules**:
- Either `duns_number` or `uei_identifier` must be present
- `success_rate` must be between 0.0 and 1.0
- `total_awards_count` must be non-negative
- `first_award_date` must be <= `last_award_date`

### ProgramOffice

**Purpose**: Agency program office details and strategic information

**Fields**:
- `office_id` (string, PK): Unique program office identifier
- `agency_code` (string): Parent agency code
- `agency_name` (string): Full agency name
- `office_name` (string): Program office name
- `office_description` (text): Office mission and focus areas
- `contact_email` (string, nullable): Primary contact email
- `contact_phone` (string, nullable): Primary contact phone
- `website_url` (string, nullable): Office website URL
- `strategic_focus_areas` (array[string]): Key technology/research areas
- `annual_budget` (decimal, nullable): Annual program budget
- `active_solicitations_count` (integer): Number of active solicitations
- `total_awards_managed` (integer): Total awards under management
- `created_at` (datetime): Record creation timestamp
- `updated_at` (datetime): Last update timestamp

**Validation Rules**:
- `agency_code` must be valid government agency code
- `contact_email` must be valid email format if present
- `annual_budget` must be non-negative if present
- `active_solicitations_count` must be non-negative

### Solicitation

**Purpose**: Complete solicitation text and technical requirements

**Fields**:
- `solicitation_id` (string, PK): Unique solicitation identifier
- `solicitation_number` (string): Official solicitation number
- `title` (string): Solicitation title
- `agency_code` (string): Issuing agency code
- `program_office_id` (string, FK): Link to program office
- `solicitation_type` (string): Type (SBIR Phase I/II, STTR, etc.)
- `topic_number` (string, nullable): Specific topic number
- `full_text` (text): Complete solicitation text
- `technical_requirements` (text): Extracted technical requirements
- `evaluation_criteria` (text): Award evaluation criteria
- `funding_range_min` (decimal): Minimum funding amount
- `funding_range_max` (decimal): Maximum funding amount
- `proposal_deadline` (date): Proposal submission deadline
- `award_start_date` (date, nullable): Expected award start date
- `performance_period` (integer): Performance period in months
- `keywords` (array[string]): Extracted technical keywords
- `cet_relevance_scores` (json): Pre-computed CET category relevance
- `created_at` (datetime): Record creation timestamp
- `updated_at` (datetime): Last update timestamp

**Validation Rules**:
- `funding_range_min` must be <= `funding_range_max`
- `proposal_deadline` must be in the past for closed solicitations
- `performance_period` must be positive
- `cet_relevance_scores` must be valid JSON with numeric values

### AwardModification

**Purpose**: Award amendments, modifications, and lifecycle changes

**Fields**:
- `modification_id` (string, PK): Unique modification identifier
- `award_id` (string, FK): Parent award identifier
- `modification_number` (string): Sequential modification number
- `modification_type` (string): Type (funding change, scope, timeline, etc.)
- `modification_date` (date): Date modification was executed
- `description` (text): Modification description
- `funding_change` (decimal, nullable): Change in funding amount
- `new_end_date` (date, nullable): Updated award end date
- `scope_changes` (text, nullable): Description of scope changes
- `justification` (text): Modification justification
- `approving_official` (string): Name of approving official
- `created_at` (datetime): Record creation timestamp

**Validation Rules**:
- `modification_date` must be >= original award start date
- `funding_change` can be positive or negative
- `modification_number` must be unique within award
- `modification_type` must be from predefined enum

### EnrichmentStatus

**Purpose**: Track enrichment completion and data quality

**Fields**:
- `status_id` (string, PK): Unique status identifier
- `award_id` (string, FK): Target award identifier
- `enrichment_type` (string): Type of enrichment (awardee, program, solicitation, etc.)
- `status` (string): Current status (pending, in_progress, completed, failed)
- `confidence_score` (float): Data quality confidence (0-1)
- `error_message` (text, nullable): Error details if failed
- `data_source` (string): SAM.gov API endpoint used
- `api_response_code` (integer, nullable): HTTP response code
- `processing_duration` (integer): Processing time in milliseconds
- `retry_count` (integer): Number of retry attempts
- `created_at` (datetime): Initial enrichment attempt
- `updated_at` (datetime): Last status update
- `completed_at` (datetime, nullable): Completion timestamp

**Validation Rules**:
- `confidence_score` must be between 0.0 and 1.0
- `status` must be from predefined enum
- `retry_count` must be non-negative
- `completed_at` must be >= `created_at` if present

## Data Volume Estimates

Based on 997 sample awards scaling to 200k+ awards:

- **EnrichedAward**: 1:1 with awards (997 → 200k records)
- **AwardeeProfile**: ~30% unique awardees (300 → 60k records)
- **ProgramOffice**: ~50 unique offices across all awards
- **Solicitation**: ~200 unique solicitations (many awards per solicitation)
- **AwardModification**: ~20% of awards have modifications (200 → 40k records)
- **EnrichmentStatus**: 5x awards (tracking multiple enrichment types per award)

**Total Storage**: Estimated 5-10x increase from current data volume.

## Integration Points

### Existing Schema Extensions

**awards.parquet** (existing):
- Add `enrichment_status` column (string)
- Add `last_enriched` column (datetime)
- Add `enrichment_confidence` column (float)

**assessments.parquet** (existing):
- Add `solicitation_enhanced` column (boolean)
- Add `solicitation_confidence_boost` column (float)

### New Parquet Files

- `enriched_awards.parquet`: EnrichedAward entities
- `awardee_profiles.parquet`: AwardeeProfile entities  
- `program_offices.parquet`: ProgramOffice entities
- `solicitations.parquet`: Solicitation entities
- `award_modifications.parquet`: AwardModification entities
- `enrichment_status.parquet`: EnrichmentStatus tracking
