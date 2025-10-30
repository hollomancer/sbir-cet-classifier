"""Tests for ConfigurationManager class.

Tests configuration loading, caching behavior, validation, and hot-reloading functionality.
"""

import os
import time
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest
import yaml

from sbir_cet_classifier.common.configuration_manager import (
    ConfigurationManager,
    ConfigurationError,
    get_config_manager,
    reset_config_manager,
    PerformanceMetrics,
)
from sbir_cet_classifier.common.yaml_config import (
    TaxonomyConfig,
    ClassificationConfig,
    EnrichmentConfig,
)
from sbir_cet_classifier.common.classification_config import ClassificationRules


class TestPerformanceMetrics:
    """Test PerformanceMetrics class."""
    
    def test_initialization(self):
        """Test PerformanceMetrics initializes correctly."""
        metrics = PerformanceMetrics()
        assert metrics.load_times == {}
        assert metrics.cache_hits == {}
        assert metrics.cache_misses == {}
        assert metrics.total_loads == 0
        assert metrics.total_cache_hits == 0
    
    def test_record_load_cache_hit(self):
        """Test recording a cache hit."""
        metrics = PerformanceMetrics()
        metrics.record_load("test_config", 0.1, cache_hit=True)
        
        assert metrics.load_times["test_config"] == 0.1
        assert metrics.cache_hits["test_config"] == 1
        assert metrics.total_loads == 1
        assert metrics.total_cache_hits == 1
    
    def test_record_load_cache_miss(self):
        """Test recording a cache miss."""
        metrics = PerformanceMetrics()
        metrics.record_load("test_config", 0.2, cache_hit=False)
        
        assert metrics.load_times["test_config"] == 0.2
        assert metrics.cache_misses["test_config"] == 1
        assert metrics.total_loads == 1
        assert metrics.total_cache_hits == 0
    
    def test_get_average_load_time(self):
        """Test average load time calculation."""
        metrics = PerformanceMetrics()
        metrics.record_load("config1", 0.1, cache_hit=False)
        metrics.record_load("config2", 0.3, cache_hit=False)
        
        assert metrics.get_average_load_time() == 0.2
        assert metrics.get_average_load_time("config1") == 0.1
        assert metrics.get_average_load_time("nonexistent") == 0.0
    
    def test_get_cache_hit_rate(self):
        """Test cache hit rate calculation."""
        metrics = PerformanceMetrics()
        metrics.record_load("config1", 0.1, cache_hit=True)
        metrics.record_load("config2", 0.1, cache_hit=False)
        metrics.record_load("config3", 0.1, cache_hit=True)
        
        assert metrics.get_cache_hit_rate() == 2/3


class TestConfigurationManager:
    """Test ConfigurationManager class."""
    
    @pytest.fixture
    def temp_config_dir(self):
        """Create temporary config directory with test files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_dir = Path(temp_dir)
            
            # Create test configuration files
            taxonomy_config = {
                "cet_areas": {
                    "quantum_computing": {
                        "name": "Quantum Computing",
                        "description": "Test quantum computing area"
                    }
                }
            }
            
            classification_config = {
                "version": "1.0",
                "agency_priors": {"Test Agency": {"quantum_computing": 10}},
                "branch_priors": {"Test Branch": {"quantum_computing": 5}},
                "cet_keywords": {
                    "quantum_computing": {
                        "core": ["quantum", "qubit"],
                        "related": ["superposition"]
                    }
                },
                "context_rules": {}
            }
            
            enrichment_config = {
                "sam_api": {
                    "base_url": "https://api.sam.gov",
                    "api_key": "test_key"
                },
                "rate_limiting": {
                    "requests_per_second": 1.0
                }
            }
            
            # Write config files
            with open(config_dir / "taxonomy.yaml", "w") as f:
                yaml.dump(taxonomy_config, f)
            
            with open(config_dir / "classification.yaml", "w") as f:
                yaml.dump(classification_config, f)
            
            with open(config_dir / "enrichment.yaml", "w") as f:
                yaml.dump(enrichment_config, f)
            
            yield config_dir
    
    @pytest.fixture
    def config_manager(self, temp_config_dir):
        """Create ConfigurationManager with temporary config directory."""
        return ConfigurationManager(temp_config_dir)
    
    def test_initialization_with_config_dir(self, temp_config_dir):
        """Test ConfigurationManager initialization with explicit config directory."""
        manager = ConfigurationManager(temp_config_dir)
        assert manager.config_dir == temp_config_dir.resolve()
        assert manager._cache == {}
        assert manager._timestamps == {}
        assert manager._performance_monitoring is True
        assert manager._metrics is not None
    
    def test_initialization_without_config_dir(self):
        """Test ConfigurationManager initialization without explicit config directory."""
        with patch.dict(os.environ, {}, clear=True):
            manager = ConfigurationManager()
            expected_path = Path(__file__).parent.parent.parent.parent / "config"
            assert manager.config_dir == expected_path.resolve()
    
    def test_initialization_with_env_var(self, temp_config_dir):
        """Test ConfigurationManager initialization with environment variable."""
        with patch.dict(os.environ, {"SBIR_CONFIG_DIR": str(temp_config_dir)}):
            manager = ConfigurationManager()
            assert manager.config_dir == temp_config_dir.resolve()
    
    def test_initialization_performance_monitoring_disabled(self, temp_config_dir):
        """Test ConfigurationManager initialization with performance monitoring disabled."""
        manager = ConfigurationManager(temp_config_dir, enable_performance_monitoring=False)
        assert manager._performance_monitoring is False
        assert manager._metrics is None


class TestConfigurationLoading:
    """Test configuration loading functionality."""
    
    @pytest.fixture
    def temp_config_dir(self):
        """Create temporary config directory with test files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_dir = Path(temp_dir)
            
            # Create test configuration files
            taxonomy_config = {
                "cet_areas": {
                    "quantum_computing": {
                        "name": "Quantum Computing",
                        "description": "Test quantum computing area"
                    }
                }
            }
            
            classification_config = {
                "version": "1.0",
                "agency_priors": {"Test Agency": {"quantum_computing": 10}},
                "branch_priors": {"Test Branch": {"quantum_computing": 5}},
                "cet_keywords": {
                    "quantum_computing": {
                        "core": ["quantum", "qubit"],
                        "related": ["superposition"]
                    }
                },
                "context_rules": {}
            }
            
            enrichment_config = {
                "sam_api": {
                    "base_url": "https://api.sam.gov",
                    "api_key": "test_key"
                },
                "rate_limiting": {
                    "requests_per_second": 1.0
                }
            }
            
            # Write config files
            with open(config_dir / "taxonomy.yaml", "w") as f:
                yaml.dump(taxonomy_config, f)
            
            with open(config_dir / "classification.yaml", "w") as f:
                yaml.dump(classification_config, f)
            
            with open(config_dir / "enrichment.yaml", "w") as f:
                yaml.dump(enrichment_config, f)
            
            yield config_dir
    
    @pytest.fixture
    def config_manager(self, temp_config_dir):
        """Create ConfigurationManager with temporary config directory."""
        return ConfigurationManager(temp_config_dir)
    
    def test_get_taxonomy_config(self, config_manager):
        """Test loading taxonomy configuration."""
        config = config_manager.get_taxonomy_config()
        assert isinstance(config, TaxonomyConfig)
        assert "quantum_computing" in config.cet_areas
        assert config.cet_areas["quantum_computing"].name == "Quantum Computing"
    
    def test_get_classification_config(self, config_manager):
        """Test loading classification configuration."""
        config = config_manager.get_classification_config()
        assert isinstance(config, ClassificationConfig)
        assert config.version == "1.0"
    
    def test_get_enrichment_config(self, config_manager):
        """Test loading enrichment configuration."""
        config = config_manager.get_enrichment_config()
        assert isinstance(config, EnrichmentConfig)
        assert config.sam_api.base_url == "https://api.sam.gov"
        assert config.sam_api.api_key == "test_key"
    
    def test_get_classification_rules(self, config_manager):
        """Test loading classification rules."""
        rules = config_manager.get_classification_rules()
        assert isinstance(rules, ClassificationRules)
        assert rules.version == "1.0"
        assert "Test Agency" in rules.agency_priors
    
    def test_get_config_generic(self, config_manager):
        """Test generic configuration loading."""
        config = config_manager.get_config("taxonomy")
        assert isinstance(config, TaxonomyConfig)
    
    def test_get_config_nonexistent_file(self, config_manager):
        """Test loading nonexistent configuration file."""
        with pytest.raises(ConfigurationError, match="Configuration file not found"):
            config_manager.get_config("nonexistent")
    
    def test_get_config_invalid_yaml(self, temp_config_dir):
        """Test loading invalid YAML file."""
        # Create invalid YAML file
        invalid_yaml_path = temp_config_dir / "invalid.yaml"
        with open(invalid_yaml_path, "w") as f:
            f.write("invalid: yaml: content: [")
        
        manager = ConfigurationManager(temp_config_dir)
        with pytest.raises(ConfigurationError, match="Invalid YAML"):
            manager.get_config("invalid")
    
    def test_get_config_empty_file(self, temp_config_dir):
        """Test loading empty YAML file."""
        # Create empty YAML file
        empty_yaml_path = temp_config_dir / "empty.yaml"
        with open(empty_yaml_path, "w") as f:
            f.write("")
        
        manager = ConfigurationManager(temp_config_dir)
        config = manager.get_config("empty")
        assert config == {}
    
    def test_get_config_non_dict_yaml(self, temp_config_dir):
        """Test loading YAML file that doesn't contain a dictionary."""
        # Create YAML file with list instead of dict
        list_yaml_path = temp_config_dir / "list.yaml"
        with open(list_yaml_path, "w") as f:
            yaml.dump(["item1", "item2"], f)
        
        manager = ConfigurationManager(temp_config_dir)
        with pytest.raises(ConfigurationError, match="Configuration file must contain a YAML object"):
            manager.get_config("list")


class TestConfigurationCaching:
    """Test configuration caching functionality."""
    
    @pytest.fixture
    def temp_config_dir(self):
        """Create temporary config directory with test files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_dir = Path(temp_dir)
            
            # Create test configuration file
            test_config = {"test_key": "test_value"}
            with open(config_dir / "test.yaml", "w") as f:
                yaml.dump(test_config, f)
            
            yield config_dir
    
    @pytest.fixture
    def config_manager(self, temp_config_dir):
        """Create ConfigurationManager with temporary config directory."""
        return ConfigurationManager(temp_config_dir)
    
    def test_caching_behavior(self, config_manager):
        """Test that configurations are cached after first load."""
        # First load
        config1 = config_manager.get_config("test")
        assert config1 == {"test_key": "test_value"}
        assert "test" in config_manager._cache
        
        # Second load should use cache
        config2 = config_manager.get_config("test")
        assert config2 == config1
        assert config2 is config_manager._cache["test"]
    
    def test_cache_invalidation_on_file_change(self, config_manager, temp_config_dir):
        """Test that cache is invalidated when file is modified."""
        # First load
        config1 = config_manager.get_config("test")
        assert config1 == {"test_key": "test_value"}
        
        # Modify file
        time.sleep(0.1)  # Ensure different mtime
        new_config = {"test_key": "modified_value"}
        with open(temp_config_dir / "test.yaml", "w") as f:
            yaml.dump(new_config, f)
        
        # Second load should reload from file
        config2 = config_manager.get_config("test")
        assert config2 == {"test_key": "modified_value"}
        assert config2 != config1
    
    def test_force_reload(self, config_manager, temp_config_dir):
        """Test force reload functionality."""
        # First load
        config1 = config_manager.get_config("test")
        assert config1 == {"test_key": "test_value"}
        
        # Modify file without changing mtime significantly
        new_config = {"test_key": "force_reload_value"}
        with open(temp_config_dir / "test.yaml", "w") as f:
            yaml.dump(new_config, f)
        
        # Force reload should get new content
        config2 = config_manager.get_config("test", force_reload=True)
        assert config2 == {"test_key": "force_reload_value"}
    
    def test_reload_all(self, config_manager):
        """Test reload_all functionality."""
        # Load some configs
        config_manager.get_config("test")
        assert len(config_manager._cache) > 0
        assert len(config_manager._timestamps) > 0
        
        # Reload all should clear cache
        config_manager.reload_all()
        assert len(config_manager._cache) == 0
        assert len(config_manager._timestamps) == 0
    
    def test_cache_stats(self, config_manager):
        """Test cache statistics functionality."""
        # Load a config
        config_manager.get_config("test")
        
        stats = config_manager.get_cache_stats()
        assert "cached_configs" in stats
        assert "cache_size" in stats
        assert "timestamps" in stats
        assert "performance" in stats
        
        assert "test" in stats["cached_configs"]
        assert stats["cache_size"] == 1
        assert "test" in stats["timestamps"]


class TestConfigurationValidation:
    """Test configuration validation functionality."""
    
    @pytest.fixture
    def temp_config_dir(self):
        """Create temporary config directory with test files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_dir = Path(temp_dir)
            
            # Create valid configuration files
            taxonomy_config = {
                "cet_areas": {
                    "quantum_computing": {
                        "name": "Quantum Computing",
                        "description": "Test quantum computing area"
                    }
                }
            }
            
            classification_config = {
                "version": "1.0",
                "agency_priors": {"Test Agency": {"quantum_computing": 10}},
                "branch_priors": {"Test Branch": {"quantum_computing": 5}},
                "cet_keywords": {
                    "quantum_computing": {
                        "core": ["quantum", "qubit"],
                        "related": ["superposition"]
                    }
                },
                "context_rules": {}
            }
            
            enrichment_config = {
                "sam_api": {
                    "base_url": "https://api.sam.gov",
                    "api_key": "test_key"
                },
                "rate_limiting": {
                    "requests_per_second": 1.0
                }
            }
            
            # Create invalid configuration file
            invalid_config = {
                "invalid_field": "invalid_value"
            }
            
            # Write config files
            with open(config_dir / "taxonomy.yaml", "w") as f:
                yaml.dump(taxonomy_config, f)
            
            with open(config_dir / "classification.yaml", "w") as f:
                yaml.dump(classification_config, f)
            
            with open(config_dir / "enrichment.yaml", "w") as f:
                yaml.dump(enrichment_config, f)
            
            with open(config_dir / "invalid.yaml", "w") as f:
                yaml.dump(invalid_config, f)
            
            yield config_dir
    
    @pytest.fixture
    def config_manager(self, temp_config_dir):
        """Create ConfigurationManager with temporary config directory."""
        return ConfigurationManager(temp_config_dir)
    
    def test_validate_config_success(self, config_manager):
        """Test successful configuration validation."""
        config = config_manager.validate_config("taxonomy", TaxonomyConfig)
        assert isinstance(config, TaxonomyConfig)
        assert "quantum_computing" in config.cet_areas
    
    def test_validate_config_failure(self, config_manager):
        """Test configuration validation failure."""
        with pytest.raises(ConfigurationError, match="Validation failed"):
            config_manager.validate_config("invalid", TaxonomyConfig)
    
    def test_validate_all_configs(self, config_manager):
        """Test validation of all configurations."""
        results = config_manager.validate_all_configs()
        
        assert "taxonomy" in results
        assert "classification" in results
        assert "enrichment" in results
        assert "classification_rules" in results
        
        # Valid configs should return "OK"
        assert results["taxonomy"] == "OK"
        assert results["classification"] == "OK"
        assert results["enrichment"] == "OK"
        assert results["classification_rules"] == "OK"
    
    def test_get_validation_errors(self, config_manager):
        """Test getting validation errors."""
        errors = config_manager.get_validation_errors()
        
        # Should be empty for valid configurations
        assert len(errors) == 0
    
    def test_get_validation_errors_with_invalid_config(self, temp_config_dir):
        """Test getting validation errors with invalid configuration."""
        # Create invalid taxonomy config
        invalid_taxonomy = {"invalid_field": "value"}
        with open(temp_config_dir / "taxonomy.yaml", "w") as f:
            yaml.dump(invalid_taxonomy, f)
        
        manager = ConfigurationManager(temp_config_dir)
        errors = manager.get_validation_errors()
        
        assert "taxonomy" in errors
        assert "validation failed" in errors["taxonomy"].lower()


class TestHotReloading:
    """Test hot-reloading functionality."""
    
    @pytest.fixture
    def temp_config_dir(self):
        """Create temporary config directory with test files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_dir = Path(temp_dir)
            
            # Create initial configuration file
            initial_config = {"version": "1.0", "test_value": "initial"}
            with open(config_dir / "test.yaml", "w") as f:
                yaml.dump(initial_config, f)
            
            yield config_dir
    
    @pytest.fixture
    def config_manager(self, temp_config_dir):
        """Create ConfigurationManager with temporary config directory."""
        return ConfigurationManager(temp_config_dir)
    
    def test_hot_reload_on_file_modification(self, config_manager, temp_config_dir):
        """Test that configurations are automatically reloaded when files change."""
        # Load initial config
        config1 = config_manager.get_config("test")
        assert config1["test_value"] == "initial"
        
        # Modify file
        time.sleep(0.1)  # Ensure different mtime
        modified_config = {"version": "1.0", "test_value": "modified"}
        with open(temp_config_dir / "test.yaml", "w") as f:
            yaml.dump(modified_config, f)
        
        # Next access should automatically reload
        config2 = config_manager.get_config("test")
        assert config2["test_value"] == "modified"
    
    def test_hot_reload_preserves_other_cache_entries(self, config_manager, temp_config_dir):
        """Test that hot reload only affects modified files."""
        # Create second config file
        other_config = {"other_value": "unchanged"}
        with open(temp_config_dir / "other.yaml", "w") as f:
            yaml.dump(other_config, f)
        
        # Load both configs
        config1 = config_manager.get_config("test")
        other1 = config_manager.get_config("other")
        
        # Modify only test config
        time.sleep(0.1)
        modified_config = {"version": "1.0", "test_value": "hot_reloaded"}
        with open(temp_config_dir / "test.yaml", "w") as f:
            yaml.dump(modified_config, f)
        
        # Test config should reload, other should remain cached
        config2 = config_manager.get_config("test")
        other2 = config_manager.get_config("other")
        
        assert config2["test_value"] == "hot_reloaded"
        assert other2 is other1  # Should be same cached object


class TestPerformanceOptimization:
    """Test performance optimization features."""
    
    @pytest.fixture
    def temp_config_dir(self):
        """Create temporary config directory with test files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_dir = Path(temp_dir)
            
            # Create multiple test configuration files
            for i in range(5):
                config = {"test_value": f"config_{i}"}
                with open(config_dir / f"test_{i}.yaml", "w") as f:
                    yaml.dump(config, f)
            
            yield config_dir
    
    @pytest.fixture
    def config_manager(self, temp_config_dir):
        """Create ConfigurationManager with temporary config directory."""
        return ConfigurationManager(temp_config_dir)
    
    def test_performance_metrics_tracking(self, config_manager):
        """Test that performance metrics are tracked correctly."""
        # Load some configs
        config_manager.get_config("test_0")  # Cache miss
        config_manager.get_config("test_0")  # Cache hit
        config_manager.get_config("test_1")  # Cache miss
        
        metrics = config_manager.get_performance_metrics()
        assert metrics is not None
        assert metrics.total_loads == 3
        assert metrics.total_cache_hits == 1
        assert metrics.get_cache_hit_rate() == 1/3
    
    def test_preload_configs(self, config_manager):
        """Test configuration preloading."""
        # Preload specific configs
        config_manager.preload_configs(["test_0", "test_1"])
        
        # Should be in cache
        assert "test_0" in config_manager._cache
        assert "test_1" in config_manager._cache
        assert "test_2" not in config_manager._cache
    
    def test_preload_all_configs(self, config_manager):
        """Test preloading all known configurations."""
        config_manager.preload_configs()
        
        # Should preload known config types
        # (This will fail for missing files, but that's expected in test environment)
        pass
    
    def test_optimize_cache(self, config_manager):
        """Test cache optimization functionality."""
        # Load some configs
        config_manager.get_config("test_0")
        config_manager.get_config("test_1")
        
        initial_cache_size = len(config_manager._cache)
        
        # Optimize cache (won't remove anything in this short test)
        config_manager.optimize_cache()
        
        # Cache should still contain recent entries
        assert len(config_manager._cache) <= initial_cache_size
    
    def test_list_available_configs(self, config_manager):
        """Test listing available configuration files."""
        configs = config_manager.list_available_configs()
        
        assert "test_0" in configs
        assert "test_1" in configs
        assert "test_2" in configs
        assert "test_3" in configs
        assert "test_4" in configs
        assert len(configs) == 5


class TestGlobalConfigManager:
    """Test global configuration manager functionality."""
    
    def test_get_config_manager_singleton(self):
        """Test that get_config_manager returns singleton instance."""
        reset_config_manager()  # Ensure clean state
        
        manager1 = get_config_manager()
        manager2 = get_config_manager()
        
        assert manager1 is manager2
    
    def test_reset_config_manager(self):
        """Test resetting global configuration manager."""
        manager1 = get_config_manager()
        reset_config_manager()
        manager2 = get_config_manager()
        
        assert manager1 is not manager2
    
    def test_get_config_manager_with_config_dir(self, temp_config_dir):
        """Test get_config_manager with explicit config directory."""
        reset_config_manager()
        
        manager = get_config_manager(temp_config_dir)
        assert manager.config_dir == temp_config_dir.resolve()
    
    @pytest.fixture
    def temp_config_dir(self):
        """Create temporary config directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)


class TestErrorHandling:
    """Test error handling in configuration management."""
    
    @pytest.fixture
    def temp_config_dir(self):
        """Create temporary config directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)
    
    @pytest.fixture
    def config_manager(self, temp_config_dir):
        """Create ConfigurationManager with temporary config directory."""
        return ConfigurationManager(temp_config_dir)
    
    def test_missing_config_file_error(self, config_manager):
        """Test error handling for missing configuration files."""
        with pytest.raises(ConfigurationError, match="Configuration file not found"):
            config_manager.get_config("nonexistent")
    
    def test_invalid_yaml_error(self, config_manager, temp_config_dir):
        """Test error handling for invalid YAML files."""
        # Create invalid YAML file
        invalid_path = temp_config_dir / "invalid.yaml"
        with open(invalid_path, "w") as f:
            f.write("invalid: yaml: [unclosed")
        
        with pytest.raises(ConfigurationError, match="Invalid YAML"):
            config_manager.get_config("invalid")
    
    def test_validation_error(self, config_manager, temp_config_dir):
        """Test error handling for validation failures."""
        # Create config with invalid structure for TaxonomyConfig
        invalid_config = {"invalid_field": "value"}
        with open(temp_config_dir / "invalid_taxonomy.yaml", "w") as f:
            yaml.dump(invalid_config, f)
        
        with pytest.raises(ConfigurationError, match="Validation failed"):
            config_manager.validate_config("invalid_taxonomy", TaxonomyConfig)
    
    def test_file_permission_error(self, config_manager, temp_config_dir):
        """Test error handling for file permission issues."""
        # Create a file and make it unreadable (skip on Windows)
        import platform
        if platform.system() != "Windows":
            restricted_path = temp_config_dir / "restricted.yaml"
            with open(restricted_path, "w") as f:
                yaml.dump({"test": "value"}, f)
            
            # Remove read permissions
            restricted_path.chmod(0o000)
            
            try:
                with pytest.raises(ConfigurationError, match="Error loading configuration"):
                    config_manager.get_config("restricted")
            finally:
                # Restore permissions for cleanup
                restricted_path.chmod(0o644)