"""Unit tests for service registry."""

import pytest
from fastapi import HTTPException

from sbir_cet_classifier.common.service_registry import ServiceRegistry, get_registry


# Mock service classes for testing
class MockSummaryService:
    """Mock summary service for testing."""

    def summarize(self):
        return "summary"


class MockAwardsService:
    """Mock awards service for testing."""

    def list_awards(self):
        return []


class TestServiceRegistryInit:
    """Test ServiceRegistry initialization."""

    def test_init_creates_empty_registry(self):
        """Test that new registry is empty."""
        registry = ServiceRegistry()
        assert not registry.is_registered("any_service")


class TestRegister:
    """Test registering services."""

    def test_register_service(self):
        """Test registering a service."""
        registry = ServiceRegistry()
        service = MockSummaryService()

        registry.register("summary", service)

        assert registry.is_registered("summary")

    def test_register_multiple_services(self):
        """Test registering multiple services."""
        registry = ServiceRegistry()
        summary = MockSummaryService()
        awards = MockAwardsService()

        registry.register("summary", summary)
        registry.register("awards", awards)

        assert registry.is_registered("summary")
        assert registry.is_registered("awards")

    def test_register_overwrites_existing(self):
        """Test that registering same name overwrites."""
        registry = ServiceRegistry()
        service1 = MockSummaryService()
        service2 = MockSummaryService()

        registry.register("test", service1)
        registry.register("test", service2)

        retrieved = registry.get("test", MockSummaryService)
        assert retrieved is service2


class TestGet:
    """Test retrieving services."""

    def test_get_registered_service(self):
        """Test getting a registered service."""
        registry = ServiceRegistry()
        service = MockSummaryService()
        registry.register("summary", service)

        retrieved = registry.get("summary", MockSummaryService)

        assert retrieved is service
        assert retrieved.summarize() == "summary"

    def test_get_unregistered_service_raises_http_exception(self):
        """Test that getting unregistered service raises 503."""
        registry = ServiceRegistry()

        with pytest.raises(HTTPException) as exc_info:
            registry.get("missing", MockSummaryService)

        assert exc_info.value.status_code == 503
        assert "missing service not configured" in exc_info.value.detail

    def test_get_returns_correct_service_instance(self):
        """Test that get returns the exact registered instance."""
        registry = ServiceRegistry()
        summary = MockSummaryService()
        awards = MockAwardsService()

        registry.register("summary", summary)
        registry.register("awards", awards)

        retrieved_summary = registry.get("summary", MockSummaryService)
        retrieved_awards = registry.get("awards", MockAwardsService)

        assert retrieved_summary is summary
        assert retrieved_awards is awards


class TestIsRegistered:
    """Test checking service registration."""

    def test_is_registered_returns_true_for_registered_service(self):
        """Test is_registered returns True for registered service."""
        registry = ServiceRegistry()
        service = MockSummaryService()
        registry.register("summary", service)

        assert registry.is_registered("summary") is True

    def test_is_registered_returns_false_for_unregistered_service(self):
        """Test is_registered returns False for unregistered service."""
        registry = ServiceRegistry()

        assert registry.is_registered("missing") is False

    def test_is_registered_after_unregister(self):
        """Test is_registered returns False after unregister."""
        registry = ServiceRegistry()
        service = MockSummaryService()
        registry.register("test", service)

        registry.unregister("test")

        assert registry.is_registered("test") is False


class TestUnregister:
    """Test unregistering services."""

    def test_unregister_existing_service(self):
        """Test unregistering an existing service."""
        registry = ServiceRegistry()
        service = MockSummaryService()
        registry.register("summary", service)

        registry.unregister("summary")

        assert not registry.is_registered("summary")

    def test_unregister_nonexistent_service_does_not_error(self):
        """Test that unregistering nonexistent service doesn't raise."""
        registry = ServiceRegistry()

        # Should not raise
        registry.unregister("nonexistent")

    def test_unregister_then_get_raises(self):
        """Test that getting after unregister raises exception."""
        registry = ServiceRegistry()
        service = MockSummaryService()
        registry.register("test", service)

        registry.unregister("test")

        with pytest.raises(HTTPException):
            registry.get("test", MockSummaryService)


class TestClear:
    """Test clearing all services."""

    def test_clear_removes_all_services(self):
        """Test that clear removes all registered services."""
        registry = ServiceRegistry()
        registry.register("service1", MockSummaryService())
        registry.register("service2", MockAwardsService())
        registry.register("service3", MockSummaryService())

        registry.clear()

        assert not registry.is_registered("service1")
        assert not registry.is_registered("service2")
        assert not registry.is_registered("service3")

    def test_clear_on_empty_registry(self):
        """Test that clear works on empty registry."""
        registry = ServiceRegistry()

        # Should not raise
        registry.clear()

        assert not registry.is_registered("anything")

    def test_register_after_clear(self):
        """Test that services can be registered after clear."""
        registry = ServiceRegistry()
        registry.register("test", MockSummaryService())

        registry.clear()

        new_service = MockAwardsService()
        registry.register("new", new_service)

        assert registry.is_registered("new")
        assert registry.get("new", MockAwardsService) is new_service


class TestGetRegistry:
    """Test global registry accessor."""

    def test_get_registry_returns_singleton(self):
        """Test that get_registry returns the same instance."""
        registry1 = get_registry()
        registry2 = get_registry()

        assert registry1 is registry2

    def test_get_registry_returns_service_registry(self):
        """Test that get_registry returns ServiceRegistry instance."""
        registry = get_registry()

        assert isinstance(registry, ServiceRegistry)

    def test_global_registry_persists_services(self):
        """Test that global registry persists services across calls."""
        registry = get_registry()
        service = MockSummaryService()

        # Clear first to ensure clean state
        registry.clear()

        # Register service
        registry.register("persistent", service)

        # Get registry again and verify service persists
        registry2 = get_registry()
        assert registry2.is_registered("persistent")
        assert registry2.get("persistent", MockSummaryService) is service

        # Clean up
        registry.clear()


class TestServiceRegistryTypeSafety:
    """Test type annotations work correctly."""

    def test_get_with_type_hint_for_ide(self):
        """Test that type hints work for IDE autocomplete."""
        registry = ServiceRegistry()
        service = MockSummaryService()
        registry.register("summary", service)

        # Type hint should allow IDE to infer type
        retrieved: MockSummaryService = registry.get("summary", MockSummaryService)

        # Verify we can call methods (would fail type check if wrong type)
        assert retrieved.summarize() == "summary"
