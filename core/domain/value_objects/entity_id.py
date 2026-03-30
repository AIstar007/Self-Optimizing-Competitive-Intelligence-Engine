"""
EntityId Value Object

Represents a unique identifier for domain entities.
Immutable and value-based equality.
"""

from dataclasses import dataclass
from typing import Any
from uuid import uuid4, UUID


@dataclass(frozen=True, slots=True)
class EntityId:
    """
    Value object representing a unique entity identifier.

    EntityIds are immutable and have value-based equality.
    Two EntityId instances with the same value are considered equal.

    Attributes:
        value: The underlying UUID string value
    """

    value: str

    def __post_init__(self) -> None:
        """Validate the EntityId value."""
        if not self.value:
            raise ValueError("EntityId value cannot be empty")
        try:
            UUID(self.value)
        except ValueError as e:
            raise ValueError(f"EntityId must be a valid UUID: {e}") from e

    @classmethod
    def generate(cls) -> "EntityId":
        """Generate a new EntityId with a random UUID."""
        return cls(str(uuid4()))

    @classmethod
    def from_string(cls, value: str) -> "EntityId":
        """Create an EntityId from a string."""
        return cls(value)

    @classmethod
    def from_uuid(cls, uuid_value: UUID) -> "EntityId":
        """Create an EntityId from a UUID object."""
        return cls(str(uuid_value))

    @property
    def uuid(self) -> UUID:
        """Get the value as a UUID object."""
        return UUID(self.value)

    def __str__(self) -> str:
        """String representation."""
        return self.value

    def __repr__(self) -> str:
        """Representation."""
        return f"EntityId({self.value})"

    def __eq__(self, other: Any) -> bool:
        """Value-based equality."""
        if not isinstance(other, EntityId):
            return False
        return self.value == other.value

    def __hash__(self) -> int:
        """Hash for use in sets and dict keys."""
        return hash(self.value)


__all__ = ["EntityId"]