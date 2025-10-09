"""Serialization utilities for dataclasses with automatic camelCase conversion."""

from dataclasses import dataclass, fields
from datetime import date, datetime
from typing import Any


def to_camel_case(snake_str: str) -> str:
    """Convert snake_case to camelCase.

    Args:
        snake_str: String in snake_case format

    Returns:
        String in camelCase format

    Examples:
        >>> to_camel_case("award_id")
        'awardId'
        >>> to_camel_case("primary_cet_id")
        'primaryCetId'
    """
    components = snake_str.split('_')
    return components[0] + ''.join(x.title() for x in components[1:])


@dataclass(frozen=True)
class SerializableDataclass:
    """Base class for dataclasses with automatic camelCase serialization.

    Provides a standard `as_dict()` method that:
    - Converts all snake_case field names to camelCase
    - Recursively serializes nested SerializableDataclass objects
    - Handles lists of SerializableDataclass objects
    - Converts date/datetime objects to ISO strings

    Example:
        @dataclass
        class AwardDetail(SerializableDataclass):
            award_id: str
            firm_name: str
            award_date: date

        award = AwardDetail(
            award_id="123",
            firm_name="Acme Corp",
            award_date=date(2024, 1, 1)
        )

        award.as_dict()
        # Returns: {
        #   "awardId": "123",
        #   "firmName": "Acme Corp",
        #   "awardDate": "2024-01-01"
        # }
    """

    def as_dict(self) -> dict[str, Any]:
        """Convert dataclass to dictionary with camelCase keys.

        Returns:
            Dictionary with camelCase keys and serialized values
        """
        def serialize_value(val: Any) -> Any:
            """Recursively serialize a value."""
            if val is None:
                return None
            elif hasattr(val, 'as_dict'):
                return val.as_dict()
            elif isinstance(val, list):
                return [serialize_value(item) for item in val]
            elif isinstance(val, dict):
                return {k: serialize_value(v) for k, v in val.items()}
            elif isinstance(val, (date, datetime)):
                return val.isoformat()
            else:
                return val

        result = {}
        for field in fields(self):
            value = getattr(self, field.name)
            camel_key = to_camel_case(field.name)
            result[camel_key] = serialize_value(value)

        return result
