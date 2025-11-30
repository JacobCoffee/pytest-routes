"""WebSocket-specific configuration for pytest-routes.

This module extends the base pytest-routes configuration with WebSocket-specific
options. It integrates with the existing configuration system and supports
both CLI options and pyproject.toml settings.

Configuration Priority:
    1. CLI options (--routes-ws-*)
    2. pyproject.toml [tool.pytest-routes.websocket]
    3. Built-in defaults
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class WebSocketTestConfig:
    """Configuration for WebSocket route testing.

    This configuration extends the base RouteTestConfig with WebSocket-specific
    options for controlling connection behavior, message generation, and
    validation rules.

    Attributes:
        enabled: Whether WebSocket testing is enabled.
        max_messages: Maximum number of messages per test sequence.
        connection_timeout: Timeout for establishing connections in seconds.
        message_timeout: Timeout for receiving messages in seconds.
        max_message_size: Maximum size for generated messages in bytes.
        test_close_codes: List of close codes to test for graceful shutdown.
        validate_subprotocols: Whether to validate subprotocol negotiation.
        include_patterns: Glob patterns to include WebSocket routes.
        exclude_patterns: Glob patterns to exclude WebSocket routes.
    """

    enabled: bool = True
    max_messages: int = 10
    connection_timeout: float = 30.0
    message_timeout: float = 10.0
    max_message_size: int = 65536
    test_close_codes: list[int] = field(default_factory=lambda: [1000, 1001])
    validate_subprotocols: bool = True
    include_patterns: list[str] = field(default_factory=list)
    exclude_patterns: list[str] = field(default_factory=lambda: ["/ws/internal/*"])

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> WebSocketTestConfig:
        """Create config from dictionary.

        Args:
            data: Configuration dictionary (e.g., from pyproject.toml).

        Returns:
            WebSocketTestConfig instance.

        Example:
            >>> config_data = {
            ...     "enabled": True,
            ...     "max_messages": 20,
            ...     "connection_timeout": 60.0,
            ... }
            >>> config = WebSocketTestConfig.from_dict(config_data)
            >>> config.max_messages
            20
        """
        defaults = cls()
        return cls(
            enabled=data.get("enabled", defaults.enabled),
            max_messages=data.get("max_messages", defaults.max_messages),
            connection_timeout=data.get("connection_timeout", defaults.connection_timeout),
            message_timeout=data.get("message_timeout", defaults.message_timeout),
            max_message_size=data.get("max_message_size", defaults.max_message_size),
            test_close_codes=data.get("test_close_codes", defaults.test_close_codes),
            validate_subprotocols=data.get("validate_subprotocols", defaults.validate_subprotocols),
            include_patterns=data.get("include", defaults.include_patterns),
            exclude_patterns=data.get("exclude", defaults.exclude_patterns),
        )


def add_websocket_cli_options(parser: Any) -> None:
    """Add WebSocket-specific CLI options to pytest.

    This function is called from the main plugin to register WebSocket options.

    Args:
        parser: The pytest argument parser.

    CLI Options:
        --routes-ws: Enable WebSocket testing
        --routes-ws-max-messages: Maximum messages per test (default: 10)
        --routes-ws-timeout: Connection timeout in seconds (default: 30)
        --routes-ws-exclude: Comma-separated exclude patterns
        --routes-ws-include: Comma-separated include patterns
    """
    group = parser.getgroup("routes-websocket", "WebSocket testing options")

    group.addoption(
        "--routes-ws",
        action="store_true",
        default=False,
        help="Enable WebSocket route testing",
    )
    group.addoption(
        "--routes-ws-max-messages",
        type=int,
        default=10,
        help="Maximum messages per WebSocket test sequence (default: 10)",
    )
    group.addoption(
        "--routes-ws-timeout",
        type=float,
        default=30.0,
        help="WebSocket connection timeout in seconds (default: 30)",
    )
    group.addoption(
        "--routes-ws-message-timeout",
        type=float,
        default=10.0,
        help="WebSocket message receive timeout in seconds (default: 10)",
    )
    group.addoption(
        "--routes-ws-exclude",
        action="store",
        default="",
        help="Comma-separated patterns to exclude WebSocket routes",
    )
    group.addoption(
        "--routes-ws-include",
        action="store",
        default="",
        help="Comma-separated patterns to include WebSocket routes",
    )


def build_websocket_config_from_cli(config: Any) -> WebSocketTestConfig:
    """Build WebSocket configuration from pytest CLI options.

    Args:
        config: The pytest Config object.

    Returns:
        WebSocketTestConfig populated from CLI options.
    """
    exclude_patterns = []
    if exclude_str := config.getoption("--routes-ws-exclude", default=""):
        exclude_patterns = [p.strip() for p in exclude_str.split(",") if p.strip()]

    include_patterns = []
    if include_str := config.getoption("--routes-ws-include", default=""):
        include_patterns = [p.strip() for p in include_str.split(",") if p.strip()]

    return WebSocketTestConfig(
        enabled=config.getoption("--routes-ws", default=False),
        max_messages=config.getoption("--routes-ws-max-messages", default=10),
        connection_timeout=config.getoption("--routes-ws-timeout", default=30.0),
        message_timeout=config.getoption("--routes-ws-message-timeout", default=10.0),
        exclude_patterns=exclude_patterns,
        include_patterns=include_patterns,
    )


def merge_websocket_configs(
    cli_config: WebSocketTestConfig | None,
    file_config: WebSocketTestConfig | None,
) -> WebSocketTestConfig:
    """Merge CLI and file configurations with CLI taking precedence.

    Args:
        cli_config: Configuration from CLI options.
        file_config: Configuration from pyproject.toml.

    Returns:
        Merged configuration.
    """
    if cli_config is None and file_config is None:
        return WebSocketTestConfig()

    if cli_config is None:
        return file_config or WebSocketTestConfig()

    if file_config is None:
        return cli_config

    defaults = WebSocketTestConfig()

    return WebSocketTestConfig(
        enabled=cli_config.enabled if cli_config.enabled != defaults.enabled else file_config.enabled,
        max_messages=(
            cli_config.max_messages if cli_config.max_messages != defaults.max_messages else file_config.max_messages
        ),
        connection_timeout=(
            cli_config.connection_timeout
            if cli_config.connection_timeout != defaults.connection_timeout
            else file_config.connection_timeout
        ),
        message_timeout=(
            cli_config.message_timeout
            if cli_config.message_timeout != defaults.message_timeout
            else file_config.message_timeout
        ),
        max_message_size=(
            cli_config.max_message_size
            if cli_config.max_message_size != defaults.max_message_size
            else file_config.max_message_size
        ),
        test_close_codes=(
            cli_config.test_close_codes
            if cli_config.test_close_codes != defaults.test_close_codes
            else file_config.test_close_codes
        ),
        validate_subprotocols=(
            cli_config.validate_subprotocols
            if cli_config.validate_subprotocols != defaults.validate_subprotocols
            else file_config.validate_subprotocols
        ),
        include_patterns=(cli_config.include_patterns if cli_config.include_patterns else file_config.include_patterns),
        exclude_patterns=(cli_config.exclude_patterns if cli_config.exclude_patterns else file_config.exclude_patterns),
    )


# TODO: Integration with main RouteTestConfig
# The WebSocketTestConfig should be added as a field to RouteTestConfig:
#
# @dataclass
# class RouteTestConfig:
#     ...
#     websocket: WebSocketTestConfig = field(default_factory=WebSocketTestConfig)
#
# Then update load_config_from_pyproject to parse [tool.pytest-routes.websocket]
