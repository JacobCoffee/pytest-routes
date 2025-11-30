"""WebSocket testing module for pytest-routes.

This module provides property-based testing capabilities for WebSocket endpoints
in ASGI applications. It supports both Litestar (auto-accept) and Starlette/FastAPI
(manual accept) WebSocket patterns.

Architecture Overview:
    - WebSocketTestClient: Low-level client wrapping Starlette TestClient
    - WebSocketTestRunner: High-level test orchestration with Hypothesis integration
    - Message strategies: Hypothesis strategies for generating test messages

Usage:
    The module is designed to integrate seamlessly with the existing pytest-routes
    plugin. WebSocket routes are discovered alongside HTTP routes and tested using
    the same configuration system.

Example:
    >>> from pytest_routes.websocket import WebSocketTestClient, WebSocketTestRunner
    >>> from pytest_routes.discovery.base import RouteInfo, WebSocketMetadata
    >>>
    >>> # Create a test client
    >>> client = WebSocketTestClient(app)
    >>>
    >>> # Test a WebSocket route
    >>> async with client.connect("/ws/chat") as ws:
    ...     await ws.send_text("hello")
    ...     response = await ws.receive_text()
"""

from __future__ import annotations

from pytest_routes.websocket.client import (
    WebSocketConnection,
    WebSocketTestClient,
)
from pytest_routes.websocket.config import (
    WebSocketTestConfig,
    add_websocket_cli_options,
    build_websocket_config_from_cli,
    merge_websocket_configs,
)
from pytest_routes.websocket.runner import (
    WebSocketTestFailure,
    WebSocketTestResult,
    WebSocketTestRunner,
)
from pytest_routes.websocket.strategies import (
    MessageSequence,
    binary_message_strategy,
    graphql_subscription_strategy,
    json_message_strategy,
    message_sequence_strategy,
    register_message_strategy,
    text_message_strategy,
)

__all__ = [
    "MessageSequence",
    "WebSocketConnection",
    "WebSocketTestClient",
    "WebSocketTestConfig",
    "WebSocketTestFailure",
    "WebSocketTestResult",
    "WebSocketTestRunner",
    "add_websocket_cli_options",
    "binary_message_strategy",
    "build_websocket_config_from_cli",
    "graphql_subscription_strategy",
    "json_message_strategy",
    "merge_websocket_configs",
    "message_sequence_strategy",
    "register_message_strategy",
    "text_message_strategy",
]
