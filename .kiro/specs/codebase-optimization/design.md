# Design Document

## Overview

This design outlines a comprehensive optimization strategy for the SBIR CET Classifier codebase. The optimization focuses on eliminating technical debt, consolidating redundant implementations, improving performance, and enhancing maintainability while preserving all existing functionality.

The design follows a phased approach that prioritizes high-impact, low-risk optimizations first, followed by more complex architectural improvements. Each optimization maintains backward compatibility and includes comprehensive testing to ensure no regression in functionality.

## Architecture

### Current State Analysis

The current codebase exhibits several patterns that create complexity and maintenance overhead:

1. **Dual Storage Implementations**: Both `storage.py` (deprecated) and `storage_v2.py` exist with overlapping functionality
2. **Compatibility Shims**: `enhanced_vectorization.py` provides deprecated compatibility layers
3. **Scattered Configuration**: Multiple YAML loading and validation implementations
4. **Complex Service Registry**: Over-engineered dependency injection for simple use cases
5. **Redundant Test Utilities**: Duplicate fixtures and setup code across test modules
6. **Inconsistent Error Handling**: Multiple error handling patterns without standardization

### Target Architecture

The optimized architecture will feature:

1. **Unified Storage Layer**: Single, type-safe storage interface with consistent patterns
2. **Streamlined ML Pipeline**: Canonical vectorization and classification without deprecated layers
3. **Centralized Configuration**: Single configuration management system with caching
4. **Simplified Service Management**: Direct instantiation where appropriate, registry only when needed
5. **Consolidated Test Framework**: Shared utilities and consistent patterns
6. **Standardized Error Handling**: Consistent exception hierarchy and logging

## Components and Interfaces

### 1. Storage Layer Consolidation

**Current Issues:**
- `storage.py` marked deprecated but still imported
- Duplicate schema definitions between storage modules
- Multiple writer/reader classes with similar functionality

**Design Solution:**
```python
# Unified storage interface
class UnifiedStorageManager:
    def __init__(self, data_dir: Path):
        self.awardee_storage = StorageFactory.create_awardee_storage(data_dir)
        self.program_storage = StorageFactory.create_program_office_storage(data_dir)
        # ... other storage types
    
    def get_storage(self, data_type: str) -> ParquetStorage:
        """Get typed storage by data type name"""
        
    def migrate_legacy_data(self) -> None:
        """Migrate data from deprecated storage formats"""
```

**Key Changes:**
- Remove `storage.py` entirely
- Consolidate all storage operations through `storage_v2.py`
- Provide migration utilities for existing data
- Standardize schema definitions in single location

### 2. ML Pipeline Simplification

**Current Issues:**
- `enhanced_vectorization.py` contains deprecated compatibility shims
- Multiple vectorization implementations with overlapping functionality
- Complex inheritance hierarchies in scoring models

**Design Solution:**
```python
# Canonical vectorization interface
class TextVectorizer:
    """Unified text vectorization with configurable sources"""
    
    def __init__(self, config: VectorizationConfig):
        self.config = config
        self.vectorizer = self._create_vectorizer()
    
    def fit_transform(self, documents: List[Dict[str, str]]) -> csr_matrix:
        """Vectorize documents with configured source weights"""
        
    def transform(self, documents: List[Dict[str, str]]) -> csr_matrix:
        """Transform new documents using fitted vectorizer"""

# Simplified scoring pipeline
class ClassificationPipeline:
    def __init__(self, vectorizer: TextVectorizer, classifier: Any):
        self.vectorizer = vectorizer
        self.classifier = classifier
    
    def predict_proba(self, documents: List[Dict[str, str]]) -> np.ndarray:
        """End-to-end classification with probability scores"""
```

**Key Changes:**
- Remove `enhanced_vectorization.py` compatibility module
- Consolidate vectorization logic into single canonical implementation
- Simplify classification pipeline with clear interfaces
- Maintain all existing ML functionality and performance

### 3. Configuration Management Optimization

**Current Issues:**
- Multiple YAML loading implementations across modules
- Redundant validation logic
- No configuration caching mechanism

**Design Solution:**
```python
class ConfigurationManager:
    """Centralized configuration management with caching"""
    
    def __init__(self, config_dir: Path):
        self.config_dir = config_dir
        self._cache: Dict[str, Any] = {}
        self._timestamps: Dict[str, float] = {}
    
    def get_config(self, config_name: str, force_reload: bool = False) -> Dict[str, Any]:
        """Get configuration with automatic caching and reload detection"""
        
    def validate_config(self, config_name: str, config_data: Dict[str, Any]) -> None:
        """Validate configuration against schema"""
        
    def reload_all(self) -> None:
        """Force reload all cached configurations"""
```

**Key Changes:**
- Consolidate all YAML loading into single manager
- Implement intelligent caching with file modification detection
- Centralize validation logic with clear error messages
- Provide configuration hot-reloading capabilities

### 4. CLI Interface Streamlining

**Current Issues:**
- Duplicate command implementations
- Inconsistent error handling across commands
- Multiple formatter classes with similar functionality

**Design Solution:**
```python
# Base command class with consistent patterns
class BaseCommand:
    """Base class for CLI commands with standard error handling"""
    
    def __init__(self, config_manager: ConfigurationManager):
        self.config = config_manager
        self.logger = self._setup_logging()
    
    def handle_errors(self, func: Callable) -> Callable:
        """Decorator for consistent error handling"""
        
    def format_output(self, data: Any, format_type: str) -> str:
        """Unified output formatting"""

# Consolidated formatter
class OutputFormatter:
    """Single formatter for all CLI output types"""
    
    def format_table(self, data: List[Dict], columns: List[str]) -> str:
        """Format data as table"""
        
    def format_json(self, data: Any) -> str:
        """Format data as JSON"""
        
    def format_summary(self, data: Dict) -> str:
        """Format summary statistics"""
```

**Key Changes:**
- Create base command class with shared functionality
- Consolidate formatting logic into single class
- Standardize error handling and logging patterns
- Maintain all existing CLI functionality

### 5. Test Framework Consolidation

**Current Issues:**
- Duplicate test fixtures across modules
- Inconsistent test setup and teardown patterns
- Redundant mock implementations

**Design Solution:**
```python
# Centralized test utilities
class TestDataFactory:
    """Factory for generating consistent test data"""
    
    @staticmethod
    def create_sample_awards(count: int = 10) -> List[Dict]:
        """Generate sample award data"""
        
    @staticmethod
    def create_sample_assessments(count: int = 10) -> List[Dict]:
        """Generate sample assessment data"""

class TestStorageManager:
    """Manages temporary storage for tests"""
    
    def __init__(self, tmp_path: Path):
        self.tmp_path = tmp_path
        self.storage_manager = UnifiedStorageManager(tmp_path)
    
    def setup_test_data(self) -> None:
        """Setup standard test data"""
        
    def cleanup(self) -> None:
        """Clean up test resources"""
```

**Key Changes:**
- Consolidate test fixtures into shared modules
- Create standard test data factories
- Implement consistent test setup/teardown patterns
- Reduce test execution time through optimized fixtures

## Data Models

### Configuration Schema Optimization

```python
@dataclass
class OptimizedConfig:
    """Unified configuration model"""
    classification: ClassificationConfig
    enrichment: EnrichmentConfig
    storage: StorageConfig
    api: APIConfig
    
    @classmethod
    def from_yaml_files(cls, config_dir: Path) -> 'OptimizedConfig':
        """Load configuration from YAML files"""
        
    def validate(self) -> List[str]:
        """Validate configuration and return errors"""
```

### Storage Schema Consolidation

```python
class SchemaRegistry:
    """Central registry for all Parquet schemas"""
    
    _schemas: Dict[str, pa.Schema] = {
        'awards': AWARD_SCHEMA,
        'assessments': ASSESSMENT_SCHEMA,
        'awardee_profiles': AWARDEE_PROFILE_SCHEMA,
        # ... other schemas
    }
    
    @classmethod
    def get_schema(cls, data_type: str) -> pa.Schema:
        """Get schema by data type"""
        
    @classmethod
    def validate_data(cls, data_type: str, df: pd.DataFrame) -> None:
        """Validate DataFrame against schema"""
```

## Error Handling

### Standardized Exception Hierarchy

```python
class SBIRCETError(Exception):
    """Base exception for SBIR CET system"""
    pass

class ConfigurationError(SBIRCETError):
    """Configuration-related errors"""
    pass

class StorageError(SBIRCETError):
    """Storage-related errors"""
    pass

class ClassificationError(SBIRCETError):
    """Classification-related errors"""
    pass

class EnrichmentError(SBIRCETError):
    """Enrichment-related errors"""
    pass
```

### Consistent Error Handling Patterns

```python
class ErrorHandler:
    """Centralized error handling and logging"""
    
    @staticmethod
    def handle_storage_error(error: Exception, context: str) -> None:
        """Handle storage-related errors with context"""
        
    @staticmethod
    def handle_api_error(error: Exception, endpoint: str) -> HTTPException:
        """Convert internal errors to HTTP exceptions"""
        
    @staticmethod
    def log_error(error: Exception, context: Dict[str, Any]) -> None:
        """Log error with structured context"""
```

## Testing Strategy

### Performance Testing Framework

```python
class PerformanceBenchmark:
    """Framework for measuring optimization improvements"""
    
    def benchmark_storage_operations(self) -> Dict[str, float]:
        """Benchmark storage read/write performance"""
        
    def benchmark_classification_pipeline(self) -> Dict[str, float]:
        """Benchmark ML pipeline performance"""
        
    def benchmark_configuration_loading(self) -> Dict[str, float]:
        """Benchmark configuration loading performance"""
```

### Migration Testing

```python
class MigrationTester:
    """Test data migration and backward compatibility"""
    
    def test_storage_migration(self) -> None:
        """Test migration from old to new storage format"""
        
    def test_api_compatibility(self) -> None:
        """Test API backward compatibility"""
        
    def test_cli_compatibility(self) -> None:
        """Test CLI backward compatibility"""
```

## Implementation Phases

### Phase 1: Storage Layer Consolidation (Low Risk)
- Remove deprecated `storage.py`
- Consolidate schema definitions
- Implement migration utilities
- Update all imports to use unified storage

### Phase 2: Configuration Optimization (Low Risk)
- Implement centralized configuration manager
- Add configuration caching
- Consolidate YAML loading logic
- Update all modules to use new configuration system

### Phase 3: Test Framework Consolidation (Medium Risk)
- Create shared test utilities
- Consolidate test fixtures
- Optimize test execution
- Ensure 100% test coverage maintained

### Phase 4: CLI Streamlining (Medium Risk)
- Create base command classes
- Consolidate formatting logic
- Standardize error handling
- Maintain all CLI functionality

### Phase 5: ML Pipeline Simplification (High Risk)
- Remove deprecated vectorization modules
- Consolidate ML logic
- Optimize performance
- Extensive testing to ensure accuracy maintained

### Phase 6: Service Management Simplification (Medium Risk)
- Simplify service registry
- Implement direct instantiation where appropriate
- Optimize service lifecycle management
- Maintain API compatibility

## Performance Targets

- **Configuration Loading**: 25% improvement in loading time
- **Test Execution**: 20% reduction in total test time
- **Data Processing**: 30% improvement in throughput
- **Memory Usage**: 15% reduction in peak memory usage
- **Codebase Size**: 20% reduction in total lines of code
- **Module Count**: 15% reduction in number of modules

## Migration Strategy

### Backward Compatibility
- All existing APIs maintain compatibility
- Data migration utilities for storage format changes
- Deprecation warnings for removed functionality
- Clear migration documentation

### Rollback Plan
- Each phase can be independently rolled back
- Comprehensive backup of original implementations
- Feature flags for new vs. old implementations during transition
- Automated testing to detect regressions

## Risk Mitigation

### High-Risk Areas
- ML pipeline changes (accuracy impact)
- Storage format migrations (data loss risk)
- API interface changes (breaking changes)

### Mitigation Strategies
- Extensive A/B testing for ML changes
- Comprehensive data backup and validation
- Gradual rollout with feature flags
- Automated regression testing
- Performance monitoring and alerting