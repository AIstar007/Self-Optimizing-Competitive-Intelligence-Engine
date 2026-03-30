"""Base use case classes for application layer."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Generic, TypeVar

InputT = TypeVar("InputT")
OutputT = TypeVar("OutputT")


@dataclass
class UseCaseResponse(Generic[OutputT]):
    """Standard response format for all use cases."""

    success: bool
    data: OutputT | None = None
    error: str | None = None
    message: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


class UseCase(ABC, Generic[InputT, OutputT]):
    """Abstract base class for all use cases."""

    @abstractmethod
    async def execute(self, request: InputT) -> UseCaseResponse[OutputT]:
        """Execute the use case with the given request."""
        pass

    def _success(self, data: OutputT, message: str = "", metadata: dict[str, Any] | None = None) -> UseCaseResponse[OutputT]:
        """Create a successful response."""
        return UseCaseResponse(
            success=True,
            data=data,
            message=message,
            metadata=metadata or {},
        )

    def _error(self, error: str, message: str = "", metadata: dict[str, Any] | None = None) -> UseCaseResponse[OutputT]:
        """Create an error response."""
        return UseCaseResponse(
            success=False,
            error=error,
            message=message,
            metadata=metadata or {},
        )
