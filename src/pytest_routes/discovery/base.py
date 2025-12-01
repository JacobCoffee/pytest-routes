"""Base route extractor protocol and types."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class WebSocketMessageType(Enum):
    """Supported WebSocket message types for testing."""

    TEXT = "text"
    BINARY = "binary"
    JSON = "json"


@dataclass
class WebSocketMetadata:
    """Metadata specific to WebSocket routes.

    This dataclass captures WebSocket-specific configuration that differs from
    standard HTTP routes. It includes protocol negotiation details, message
    format specifications, and connection behavior expectations.

    Attributes:
        subprotocols: List of supported WebSocket subprotocols (e.g., ["graphql-ws"]).
            The client may request one of these during the handshake.
        accepted_message_types: List of message types the endpoint accepts.
            Used for generating appropriate test messages.
        sends_message_types: List of message types the endpoint may send.
            Used for response validation.
        auto_accept: Whether the server auto-accepts connections (Litestar style)
            or requires manual accept() call (Starlette/FastAPI style).
        ping_interval: Expected ping interval in seconds, if applicable.
        max_message_size: Maximum message size in bytes, if known.
        close_codes: Expected close codes for normal shutdown.
    """

    subprotocols: list[str] = field(default_factory=list)
    accepted_message_types: list[WebSocketMessageType] = field(
        default_factory=lambda: [WebSocketMessageType.TEXT, WebSocketMessageType.JSON]
    )
    sends_message_types: list[WebSocketMessageType] = field(
        default_factory=lambda: [WebSocketMessageType.TEXT, WebSocketMessageType.JSON]
    )
    auto_accept: bool = True
    ping_interval: float | None = None
    max_message_size: int | None = None
    close_codes: list[int] = field(default_factory=lambda: [1000, 1001])


@dataclass
class RouteInfo:
    """Normalized route information.

    This dataclass represents a discovered route from an ASGI application,
    containing all metadata needed for property-based testing. It supports
    both HTTP routes and WebSocket endpoints through the is_websocket flag
    and optional websocket_metadata field.

    Attributes:
        path: The route path pattern (e.g., "/users/{user_id}").
        methods: HTTP methods for this route (e.g., ["GET", "POST"]).
            For WebSocket routes, this is typically ["WEBSOCKET"] or empty.
        name: Optional route name from the framework.
        handler: Reference to the handler function/coroutine.
        path_params: Mapping of path parameter names to their types.
        query_params: Mapping of query parameter names to their types.
        body_type: Type annotation for the request body, if applicable.
        tags: Framework-assigned tags for grouping/categorization.
        deprecated: Whether the route is marked as deprecated.
        description: Documentation string for the route.
        is_websocket: True if this is a WebSocket endpoint.
        websocket_metadata: Additional WebSocket-specific configuration.
    """

    path: str
    methods: list[str]
    name: str | None = None
    handler: Callable[..., Any] | None = None

    path_params: dict[str, type] = field(default_factory=dict)
    query_params: dict[str, type] = field(default_factory=dict)
    body_type: type | None = None

    tags: list[str] = field(default_factory=list)
    deprecated: bool = False
    description: str | None = None

    is_websocket: bool = False
    websocket_metadata: WebSocketMetadata | None = None

    def __repr__(self) -> str:
        if self.is_websocket:
            return f"RouteInfo(WS {self.path})"
        methods_str = ",".join(self.methods)
        return f"RouteInfo({methods_str} {self.path})"

    @property
    def is_http(self) -> bool:
        """Check if this is an HTTP route (not WebSocket)."""
        return not self.is_websocket

    def get_websocket_metadata(self) -> WebSocketMetadata:
        """Get WebSocket metadata, creating default if not set.

        Returns:
            WebSocketMetadata instance with route-specific or default values.

        Raises:
            ValueError: If called on a non-WebSocket route.
        """
        if not self.is_websocket:
            msg = f"Route {self.path} is not a WebSocket route"
            raise ValueError(msg)
        if self.websocket_metadata is None:
            self.websocket_metadata = WebSocketMetadata()
        return self.websocket_metadata


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
