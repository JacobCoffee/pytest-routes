"""Base route extractor protocol and types."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any


@dataclass
class RouteInfo:
    """Normalized route information."""

    path: str
    methods: list[str]
    name: str | None = None
    handler: Callable[..., Any] | None = None

    # Parameter info extracted from path and handler
    path_params: dict[str, type] = field(default_factory=dict)
    query_params: dict[str, type] = field(default_factory=dict)
    body_type: type | None = None

    # Framework-specific metadata
    tags: list[str] = field(default_factory=list)
    deprecated: bool = False
    description: str | None = None

    def __repr__(self) -> str:
        methods_str = ",".join(self.methods)
        return f"RouteInfo({methods_str} {self.path})"


class RouteExtractor(ABC):
    """Abstract base for route extraction from ASGI apps."""

    @abstractmethod
    def extract_routes(self, app: Any) -> list[RouteInfo]:
        """Extract all routes from the application.

        Args:
            app: The ASGI application.

        Returns:
            List of RouteInfo objects representing discovered routes.
        """
        ...

    @abstractmethod
    def supports(self, app: Any) -> bool:
        """Check if this extractor supports the given app type.

        Args:
            app: The ASGI application to check.

        Returns:
            True if this extractor can handle the app.
        """
        ...
