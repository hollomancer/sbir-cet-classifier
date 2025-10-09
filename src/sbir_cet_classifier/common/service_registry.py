"""Centralized service registry for dependency injection."""

from typing import Any, TypeVar

from fastapi import HTTPException, status

T = TypeVar('T')


class ServiceRegistry:
    """Centralized service registry with type-safe access.

    Provides a single place to register and retrieve service instances,
    eliminating the need for duplicate global variables and getter functions
    across multiple modules.

    Example:
        # At application startup
        registry = ServiceRegistry()
        registry.register("summary", summary_service)
        registry.register("awards", awards_service)

        # In route handlers
        summary_service = registry.get("summary", SummaryService)
        awards_service = registry.get("awards", AwardsService)
    """

    def __init__(self):
        """Initialize an empty service registry."""
        self._services: dict[str, Any] = {}

    def register(self, name: str, service: Any) -> None:
        """Register a service instance.

        Args:
            name: Unique name for the service
            service: Service instance to register
        """
        self._services[name] = service

    def get(self, name: str, service_type: type[T]) -> T:
        """Get a registered service or raise HTTP 503.

        Args:
            name: Name of the service to retrieve
            service_type: Type hint for the service (for type checking)

        Returns:
            The registered service instance

        Raises:
            HTTPException: 503 if service is not registered
        """
        service = self._services.get(name)
        if service is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"{name} service not configured"
            )
        return service

    def is_registered(self, name: str) -> bool:
        """Check if a service is registered.

        Args:
            name: Name of the service to check

        Returns:
            True if service is registered, False otherwise
        """
        return name in self._services

    def unregister(self, name: str) -> None:
        """Unregister a service.

        Args:
            name: Name of the service to unregister
        """
        self._services.pop(name, None)

    def clear(self) -> None:
        """Clear all registered services."""
        self._services.clear()


# Global service registry instance
_registry = ServiceRegistry()


def get_registry() -> ServiceRegistry:
    """Get the global service registry instance.

    Returns:
        The global ServiceRegistry instance
    """
    return _registry
