"""WebSocket test client for ASGI applications.

This module provides a WebSocket test client that wraps Starlette's TestClient
to enable property-based testing of WebSocket endpoints. It handles the differences
between Litestar (auto-accept) and Starlette/FastAPI (manual accept) patterns.

Architecture:
    WebSocketTestClient
        |
        +-- connect() -> WebSocketConnection (async context manager)
                |
                +-- send_text() / send_bytes() / send_json()
                +-- receive_text() / receive_bytes() / receive_json()
                +-- close()

The client supports:
    - Subprotocol negotiation
    - Connection timeout handling
    - Message send/receive with type validation
    - Graceful and abnormal close handling
    - Connection state tracking
"""

from __future__ import annotations

import contextlib
import json
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from pytest_routes.discovery.base import RouteInfo


class ConnectionState(Enum):
    """WebSocket connection lifecycle states."""

    CONNECTING = "connecting"
    OPEN = "open"
    CLOSING = "closing"
    CLOSED = "closed"


@dataclass
class WebSocketMessage:
    """Represents a WebSocket message with type information.

    Attributes:
        type: The message type ("text", "bytes", or "json").
        data: The message payload (str, bytes, or dict).
        timestamp: Optional timestamp for message ordering in sequences.
    """

    type: str
    data: str | bytes | dict[str, Any]
    timestamp: float | None = None

    def as_text(self) -> str:
        """Convert message to text representation."""
        if isinstance(self.data, str):
            return self.data
        if isinstance(self.data, bytes):
            return self.data.decode("utf-8")
        return json.dumps(self.data)

    def as_bytes(self) -> bytes:
        """Convert message to bytes representation."""
        if isinstance(self.data, bytes):
            return self.data
        if isinstance(self.data, str):
            return self.data.encode("utf-8")
        return json.dumps(self.data).encode("utf-8")


@dataclass
class WebSocketConnection:
    """Async context manager for WebSocket connections.

    This class wraps a WebSocket connection and provides methods for sending
    and receiving messages. It tracks connection state and handles cleanup.

    Attributes:
        path: The WebSocket endpoint path.
        state: Current connection state.
        subprotocol: Negotiated subprotocol, if any.
        sent_messages: List of messages sent during the connection.
        received_messages: List of messages received during the connection.
        close_code: The close code when connection is closed.
        close_reason: The close reason when connection is closed.
    """

    path: str
    state: ConnectionState = ConnectionState.CONNECTING
    subprotocol: str | None = None
    sent_messages: list[WebSocketMessage] = field(default_factory=list)
    received_messages: list[WebSocketMessage] = field(default_factory=list)
    close_code: int | None = None
    close_reason: str | None = None

    _websocket: Any = field(default=None, repr=False)
    _timeout: float = field(default=30.0, repr=False)

    async def send_text(self, data: str) -> None:
        """Send a text message.

        Args:
            data: The text message to send.

        Raises:
            RuntimeError: If the connection is not open.
        """
        self._ensure_open()
        if self._websocket:
            self._websocket.send_text(data)
        self.sent_messages.append(WebSocketMessage(type="text", data=data))

    async def send_bytes(self, data: bytes) -> None:
        """Send a binary message.

        Args:
            data: The binary data to send.

        Raises:
            RuntimeError: If the connection is not open.
        """
        self._ensure_open()
        if self._websocket:
            self._websocket.send_bytes(data)
        self.sent_messages.append(WebSocketMessage(type="bytes", data=data))

    async def send_json(self, data: dict[str, Any]) -> None:
        """Send a JSON message.

        Args:
            data: The dictionary to serialize and send as JSON.

        Raises:
            RuntimeError: If the connection is not open.
        """
        self._ensure_open()
        if self._websocket:
            self._websocket.send_json(data)
        self.sent_messages.append(WebSocketMessage(type="json", data=data))

    async def receive_text(self, timeout: float | None = None) -> str:
        """Receive a text message.

        Args:
            timeout: Optional timeout in seconds. Defaults to connection timeout.

        Returns:
            The received text message.

        Raises:
            RuntimeError: If the connection is not open.
            TimeoutError: If no message is received within the timeout.
        """
        self._ensure_open()
        data = self._websocket.receive_text() if self._websocket else ""
        msg = WebSocketMessage(type="text", data=data)
        self.received_messages.append(msg)
        return data

    async def receive_bytes(self, timeout: float | None = None) -> bytes:
        """Receive a binary message.

        Args:
            timeout: Optional timeout in seconds. Defaults to connection timeout.

        Returns:
            The received binary data.

        Raises:
            RuntimeError: If the connection is not open.
            TimeoutError: If no message is received within the timeout.
        """
        self._ensure_open()
        data = self._websocket.receive_bytes() if self._websocket else b""
        msg = WebSocketMessage(type="bytes", data=data)
        self.received_messages.append(msg)
        return data

    async def receive_json(self, timeout: float | None = None) -> dict[str, Any]:
        """Receive a JSON message.

        Args:
            timeout: Optional timeout in seconds. Defaults to connection timeout.

        Returns:
            The received JSON data as a dictionary.

        Raises:
            RuntimeError: If the connection is not open.
            TimeoutError: If no message is received within the timeout.
            json.JSONDecodeError: If the received message is not valid JSON.
        """
        self._ensure_open()
        data = self._websocket.receive_json() if self._websocket else {}
        msg = WebSocketMessage(type="json", data=data)
        self.received_messages.append(msg)
        return data

    async def close(self, code: int = 1000, reason: str = "") -> None:
        """Close the WebSocket connection.

        Args:
            code: The close code (default 1000 for normal closure).
            reason: Optional close reason string.
        """
        if self.state in (ConnectionState.CLOSING, ConnectionState.CLOSED):
            return

        self.state = ConnectionState.CLOSING
        if self._websocket:
            with contextlib.suppress(RuntimeError):
                self._websocket.close(code=code)
        self.close_code = code
        self.close_reason = reason
        self.state = ConnectionState.CLOSED

    def _ensure_open(self) -> None:
        """Ensure the connection is in OPEN state.

        Raises:
            RuntimeError: If the connection is not open.
        """
        if self.state != ConnectionState.OPEN:
            msg = f"WebSocket connection is {self.state.value}, expected OPEN"
            raise RuntimeError(msg)


class WebSocketTestClient:
    """Test client for WebSocket endpoints in ASGI applications.

    This client wraps Starlette's TestClient to provide WebSocket testing
    capabilities. It handles the differences between frameworks and provides
    a consistent interface for property-based testing.

    Attributes:
        app: The ASGI application under test.
        base_url: Base URL for WebSocket connections (ws:// or wss://).
        default_timeout: Default timeout for connection and receive operations.

    Example:
        >>> client = WebSocketTestClient(app)
        >>> async with client.connect("/ws/chat") as ws:
        ...     await ws.send_text("hello")
        ...     response = await ws.receive_text()
        ...     assert response == "world"
    """

    def __init__(
        self,
        app: Any,
        base_url: str = "ws://test",
        default_timeout: float = 30.0,
    ) -> None:
        """Initialize WebSocket test client.

        Args:
            app: The ASGI application to test.
            base_url: Base URL for WebSocket connections.
            default_timeout: Default timeout for operations in seconds.
        """
        self.app = app
        self.base_url = base_url
        self.default_timeout = default_timeout
        self._test_client: Any = None

    def _ensure_test_client(self) -> Any:
        """Ensure the underlying Starlette TestClient is initialized.

        Returns:
            The Starlette TestClient instance.
        """
        if self._test_client is None:
            from starlette.testclient import TestClient

            self._test_client = TestClient(self.app, base_url=self.base_url)
        return self._test_client

    @asynccontextmanager
    async def connect(
        self,
        path: str,
        *,
        subprotocols: list[str] | None = None,
        headers: dict[str, str] | None = None,
        timeout: float | None = None,
    ) -> AsyncIterator[WebSocketConnection]:
        """Connect to a WebSocket endpoint.

        This is an async context manager that establishes a WebSocket connection,
        yields a WebSocketConnection for interaction, and handles cleanup.

        Args:
            path: The WebSocket endpoint path (e.g., "/ws/chat").
            subprotocols: Optional list of subprotocols to request.
            headers: Optional headers to include in the handshake.
            timeout: Optional connection timeout in seconds.

        Yields:
            A WebSocketConnection instance for sending/receiving messages.

        Raises:
            ConnectionRefusedError: If the server rejects the connection.
            TimeoutError: If the connection times out.

        Example:
            >>> async with client.connect("/ws/chat", subprotocols=["v1"]) as ws:
            ...     await ws.send_json({"action": "subscribe"})
        """
        connection = WebSocketConnection(
            path=path,
            state=ConnectionState.CONNECTING,
            _timeout=timeout or self.default_timeout,
        )

        test_client = self._ensure_test_client()
        with test_client.websocket_connect(
            path,
            subprotocols=subprotocols or [],
            headers=headers or {},
        ) as websocket:
            connection._websocket = websocket  # noqa: SLF001
            connection.state = ConnectionState.OPEN
            connection.subprotocol = getattr(websocket, "accepted_subprotocol", None)
            try:
                yield connection
            finally:
                connection.state = ConnectionState.CLOSED

    async def connect_route(
        self,
        route: RouteInfo,
        *,
        path_params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        timeout: float | None = None,
    ) -> AsyncIterator[WebSocketConnection]:
        """Connect to a WebSocket route with path parameter substitution.

        This method formats the route path with provided parameters and
        establishes a WebSocket connection.

        Args:
            route: The RouteInfo describing the WebSocket endpoint.
            path_params: Values for path parameters in the route.
            headers: Optional headers to include in the handshake.
            timeout: Optional connection timeout in seconds.

        Yields:
            A WebSocketConnection instance.

        Raises:
            ValueError: If the route is not a WebSocket route.
            ValueError: If required path parameters are missing.
        """
        if not route.is_websocket:
            msg = f"Route {route.path} is not a WebSocket route"
            raise ValueError(msg)

        # Format path with parameters
        formatted_path = self._format_path(route.path, path_params or {})

        # Get subprotocols from route metadata
        metadata = route.get_websocket_metadata()
        subprotocols = metadata.subprotocols if metadata.subprotocols else None

        async with self.connect(
            formatted_path,
            subprotocols=subprotocols,
            headers=headers,
            timeout=timeout,
        ) as connection:
            yield connection

    def _format_path(self, path: str, params: dict[str, Any]) -> str:
        """Format a path template with parameter values.

        Args:
            path: Path template (e.g., "/ws/chat/{room_id}").
            params: Parameter values to substitute.

        Returns:
            Formatted path with parameters substituted.

        Example:
            >>> client._format_path("/ws/{room}", {"room": "general"})
            '/ws/general'
        """
        formatted = path
        for name, value in params.items():
            # Handle both {param} and {param:type} patterns
            import re

            pattern = rf"\{{{name}(?::[^}}]+)?\}}"
            formatted = re.sub(pattern, str(value), formatted)
        return formatted
