"""Tests for WebSocket testing functionality."""

from __future__ import annotations

from typing import Any
from unittest.mock import Mock

import pytest
from hypothesis import given
from hypothesis import strategies as st

from pytest_routes.discovery.base import RouteInfo, WebSocketMessageType, WebSocketMetadata
from pytest_routes.websocket.client import ConnectionState, WebSocketConnection, WebSocketMessage, WebSocketTestClient
from pytest_routes.websocket.config import (
    WebSocketTestConfig,
    build_websocket_config_from_cli,
    merge_websocket_configs,
)
from pytest_routes.websocket.runner import WebSocketTestFailure, WebSocketTestResult
from pytest_routes.websocket.strategies import (
    MessageSequence,
    binary_message_strategy,
    json_message_strategy,
    message_sequence_strategy,
    register_message_strategy,
    text_message_strategy,
    unregister_message_strategy,
)


class TestWebSocketTestConfig:
    """Tests for WebSocketTestConfig."""

    def test_default_values(self) -> None:
        """Test that WebSocketTestConfig has correct defaults."""
        config = WebSocketTestConfig()

        assert config.enabled is True
        assert config.max_messages == 10
        assert config.connection_timeout == 30.0
        assert config.message_timeout == 10.0
        assert config.max_message_size == 65536
        assert config.test_close_codes == [1000, 1001]
        assert config.validate_subprotocols is True
        assert config.include_patterns == []
        assert config.exclude_patterns == ["/ws/internal/*"]

    def test_from_dict_with_all_fields(self) -> None:
        """Test creating config from dictionary with all fields."""
        data = {
            "enabled": False,
            "max_messages": 20,
            "connection_timeout": 60.0,
            "message_timeout": 15.0,
            "max_message_size": 131072,
            "test_close_codes": [1000, 1001, 1002],
            "validate_subprotocols": False,
            "include": ["/ws/public/*"],
            "exclude": ["/ws/internal/*", "/ws/admin/*"],
        }

        config = WebSocketTestConfig.from_dict(data)

        assert config.enabled is False
        assert config.max_messages == 20
        assert config.connection_timeout == 60.0
        assert config.message_timeout == 15.0
        assert config.max_message_size == 131072
        assert config.test_close_codes == [1000, 1001, 1002]
        assert config.validate_subprotocols is False
        assert config.include_patterns == ["/ws/public/*"]
        assert config.exclude_patterns == ["/ws/internal/*", "/ws/admin/*"]

    def test_from_dict_with_partial_fields(self) -> None:
        """Test creating config from dictionary with only some fields."""
        data = {
            "max_messages": 15,
            "connection_timeout": 45.0,
        }

        config = WebSocketTestConfig.from_dict(data)

        assert config.max_messages == 15
        assert config.connection_timeout == 45.0
        assert config.enabled is True
        assert config.message_timeout == 10.0

    def test_from_dict_with_empty_dict(self) -> None:
        """Test creating config from empty dictionary uses defaults."""
        config = WebSocketTestConfig.from_dict({})

        defaults = WebSocketTestConfig()
        assert config.enabled == defaults.enabled
        assert config.max_messages == defaults.max_messages
        assert config.connection_timeout == defaults.connection_timeout

    def test_build_config_from_cli_defaults(self) -> None:
        """Test building config from CLI with default values."""
        mock_config = Mock()
        mock_config.getoption = Mock(side_effect=lambda opt, default=None: default)

        config = build_websocket_config_from_cli(mock_config)

        assert config.enabled is False
        assert config.max_messages == 10
        assert config.connection_timeout == 30.0
        assert config.message_timeout == 10.0
        assert config.exclude_patterns == []
        assert config.include_patterns == []

    def test_build_config_from_cli_with_values(self) -> None:
        """Test building config from CLI with specified values."""
        mock_config = Mock()

        def getoption(opt: str, default: Any = None) -> Any:
            values = {
                "--routes-ws": True,
                "--routes-ws-max-messages": 25,
                "--routes-ws-timeout": 45.0,
                "--routes-ws-message-timeout": 12.0,
                "--routes-ws-exclude": "/ws/internal/*,/ws/admin/*",
                "--routes-ws-include": "/ws/public/*",
            }
            return values.get(opt, default)

        mock_config.getoption = getoption

        config = build_websocket_config_from_cli(mock_config)

        assert config.enabled is True
        assert config.max_messages == 25
        assert config.connection_timeout == 45.0
        assert config.message_timeout == 12.0
        assert config.exclude_patterns == ["/ws/internal/*", "/ws/admin/*"]
        assert config.include_patterns == ["/ws/public/*"]

    def test_merge_configs_both_none(self) -> None:
        """Test merging when both configs are None returns defaults."""
        result = merge_websocket_configs(None, None)

        assert isinstance(result, WebSocketTestConfig)
        assert result.enabled is True
        assert result.max_messages == 10

    def test_merge_configs_cli_only(self) -> None:
        """Test merging when only CLI config exists."""
        cli_config = WebSocketTestConfig(enabled=True, max_messages=20)

        result = merge_websocket_configs(cli_config, None)

        assert result.enabled is True
        assert result.max_messages == 20

    def test_merge_configs_file_only(self) -> None:
        """Test merging when only file config exists."""
        file_config = WebSocketTestConfig(enabled=False, max_messages=15)

        result = merge_websocket_configs(None, file_config)

        assert result.enabled is False
        assert result.max_messages == 15

    def test_merge_configs_cli_overrides_file(self) -> None:
        """Test that CLI config takes precedence over file config when values differ from defaults."""
        cli_config = WebSocketTestConfig(enabled=False, max_messages=25, connection_timeout=60.0)
        file_config = WebSocketTestConfig(enabled=True, max_messages=10, message_timeout=15.0)

        result = merge_websocket_configs(cli_config, file_config)

        assert result.enabled is False
        assert result.max_messages == 25
        assert result.connection_timeout == 60.0
        assert result.message_timeout == 15.0

    def test_merge_configs_file_fills_defaults(self) -> None:
        """Test that file config fills in when CLI uses defaults."""
        cli_config = WebSocketTestConfig()
        file_config = WebSocketTestConfig(max_messages=20, connection_timeout=45.0)

        result = merge_websocket_configs(cli_config, file_config)

        assert result.max_messages == 20
        assert result.connection_timeout == 45.0


class TestConnectionState:
    """Tests for ConnectionState enum."""

    def test_enum_values(self) -> None:
        """Test that ConnectionState has correct enum values."""
        assert ConnectionState.CONNECTING.value == "connecting"
        assert ConnectionState.OPEN.value == "open"
        assert ConnectionState.CLOSING.value == "closing"
        assert ConnectionState.CLOSED.value == "closed"

    def test_enum_members(self) -> None:
        """Test that all expected enum members exist."""
        states = {state.name for state in ConnectionState}
        assert states == {"CONNECTING", "OPEN", "CLOSING", "CLOSED"}


class TestWebSocketMessage:
    """Tests for WebSocketMessage dataclass."""

    def test_text_message_as_text(self) -> None:
        """Test text message conversion to text."""
        msg = WebSocketMessage(type="text", data="hello world")
        assert msg.as_text() == "hello world"

    def test_bytes_message_as_text(self) -> None:
        """Test bytes message conversion to text."""
        msg = WebSocketMessage(type="bytes", data=b"hello")
        assert msg.as_text() == "hello"

    def test_json_message_as_text(self) -> None:
        """Test JSON message conversion to text."""
        msg = WebSocketMessage(type="json", data={"key": "value"})
        assert msg.as_text() == '{"key": "value"}'

    def test_bytes_message_as_bytes(self) -> None:
        """Test bytes message conversion to bytes."""
        msg = WebSocketMessage(type="bytes", data=b"hello")
        assert msg.as_bytes() == b"hello"

    def test_text_message_as_bytes(self) -> None:
        """Test text message conversion to bytes."""
        msg = WebSocketMessage(type="text", data="hello")
        assert msg.as_bytes() == b"hello"

    def test_json_message_as_bytes(self) -> None:
        """Test JSON message conversion to bytes."""
        msg = WebSocketMessage(type="json", data={"key": "value"})
        assert msg.as_bytes() == b'{"key": "value"}'


class TestWebSocketConnection:
    """Tests for WebSocketConnection."""

    def test_initial_state(self) -> None:
        """Test initial connection state."""
        conn = WebSocketConnection(path="/ws/test")

        assert conn.path == "/ws/test"
        assert conn.state == ConnectionState.CONNECTING
        assert conn.subprotocol is None
        assert conn.sent_messages == []
        assert conn.received_messages == []
        assert conn.close_code is None
        assert conn.close_reason is None

    @pytest.mark.asyncio
    async def test_send_text_requires_open(self) -> None:
        """Test that send_text raises when connection not open."""
        conn = WebSocketConnection(path="/ws/test", state=ConnectionState.CLOSED)

        with pytest.raises(RuntimeError, match="WebSocket connection is closed"):
            await conn.send_text("hello")

    @pytest.mark.asyncio
    async def test_send_text_records_message(self) -> None:
        """Test that send_text records the message."""
        conn = WebSocketConnection(path="/ws/test", state=ConnectionState.OPEN)

        await conn.send_text("hello")

        assert len(conn.sent_messages) == 1
        assert conn.sent_messages[0].type == "text"
        assert conn.sent_messages[0].data == "hello"

    @pytest.mark.asyncio
    async def test_send_bytes_records_message(self) -> None:
        """Test that send_bytes records the message."""
        conn = WebSocketConnection(path="/ws/test", state=ConnectionState.OPEN)

        await conn.send_bytes(b"binary data")

        assert len(conn.sent_messages) == 1
        assert conn.sent_messages[0].type == "bytes"
        assert conn.sent_messages[0].data == b"binary data"

    @pytest.mark.asyncio
    async def test_send_json_records_message(self) -> None:
        """Test that send_json records the message."""
        conn = WebSocketConnection(path="/ws/test", state=ConnectionState.OPEN)

        await conn.send_json({"key": "value"})

        assert len(conn.sent_messages) == 1
        assert conn.sent_messages[0].type == "json"
        assert conn.sent_messages[0].data == {"key": "value"}

    @pytest.mark.asyncio
    async def test_receive_text_records_message(self) -> None:
        """Test that receive_text records the message."""
        mock_ws = Mock()
        mock_ws.receive_text = Mock(return_value="received")

        conn = WebSocketConnection(path="/ws/test", state=ConnectionState.OPEN, _websocket=mock_ws)

        result = await conn.receive_text()

        assert result == "received"
        assert len(conn.received_messages) == 1
        assert conn.received_messages[0].type == "text"
        assert conn.received_messages[0].data == "received"

    @pytest.mark.asyncio
    async def test_receive_bytes_records_message(self) -> None:
        """Test that receive_bytes records the message."""
        mock_ws = Mock()
        mock_ws.receive_bytes = Mock(return_value=b"received")

        conn = WebSocketConnection(path="/ws/test", state=ConnectionState.OPEN, _websocket=mock_ws)

        result = await conn.receive_bytes()

        assert result == b"received"
        assert len(conn.received_messages) == 1
        assert conn.received_messages[0].type == "bytes"

    @pytest.mark.asyncio
    async def test_receive_json_records_message(self) -> None:
        """Test that receive_json records the message."""
        mock_ws = Mock()
        mock_ws.receive_json = Mock(return_value={"response": "data"})

        conn = WebSocketConnection(path="/ws/test", state=ConnectionState.OPEN, _websocket=mock_ws)

        result = await conn.receive_json()

        assert result == {"response": "data"}
        assert len(conn.received_messages) == 1
        assert conn.received_messages[0].type == "json"

    @pytest.mark.asyncio
    async def test_close_updates_state(self) -> None:
        """Test that close updates connection state."""
        mock_ws = Mock()
        mock_ws.close = Mock()

        conn = WebSocketConnection(path="/ws/test", state=ConnectionState.OPEN, _websocket=mock_ws)

        await conn.close(code=1000, reason="normal")

        assert conn.state == ConnectionState.CLOSED
        assert conn.close_code == 1000
        assert conn.close_reason == "normal"

    @pytest.mark.asyncio
    async def test_close_idempotent(self) -> None:
        """Test that close can be called multiple times safely."""
        conn = WebSocketConnection(path="/ws/test", state=ConnectionState.CLOSED)

        await conn.close()
        await conn.close()

        assert conn.state == ConnectionState.CLOSED


class TestWebSocketTestClient:
    """Tests for WebSocketTestClient."""

    def test_initialization(self) -> None:
        """Test client initialization."""
        mock_app = Mock()
        client = WebSocketTestClient(mock_app, base_url="ws://test", default_timeout=60.0)

        assert client.app is mock_app
        assert client.base_url == "ws://test"
        assert client.default_timeout == 60.0

    def test_format_path_simple(self) -> None:
        """Test path formatting without parameters."""
        client = WebSocketTestClient(Mock())

        result = client._format_path("/ws/chat", {})

        assert result == "/ws/chat"

    def test_format_path_with_params(self) -> None:
        """Test path formatting with parameters."""
        client = WebSocketTestClient(Mock())

        result = client._format_path("/ws/room/{room_id}", {"room_id": "general"})

        assert result == "/ws/room/general"

    def test_format_path_with_typed_params(self) -> None:
        """Test path formatting with type annotations."""
        client = WebSocketTestClient(Mock())

        result = client._format_path("/ws/user/{user_id:int}", {"user_id": 123})

        assert result == "/ws/user/123"

    def test_format_path_multiple_params(self) -> None:
        """Test path formatting with multiple parameters."""
        client = WebSocketTestClient(Mock())

        result = client._format_path("/ws/{org}/{room}", {"org": "acme", "room": "general"})

        assert result == "/ws/acme/general"


class TestWebSocketTestResult:
    """Tests for WebSocketTestResult."""

    def test_default_values(self) -> None:
        """Test default result values."""
        result = WebSocketTestResult(route_path="/ws/test")

        assert result.route_path == "/ws/test"
        assert result.passed is True
        assert result.messages_sent == 0
        assert result.messages_received == 0
        assert result.connection_established is False
        assert result.close_code is None
        assert result.error is None
        assert result.duration_ms == 0.0

    def test_to_dict(self) -> None:
        """Test conversion to dictionary."""
        result = WebSocketTestResult(
            route_path="/ws/test",
            passed=False,
            messages_sent=5,
            messages_received=3,
            connection_established=True,
            close_code=1000,
            error="Test error",
            duration_ms=123.45,
        )

        data = result.to_dict()

        assert data["route_path"] == "/ws/test"
        assert data["passed"] is False
        assert data["messages_sent"] == 5
        assert data["messages_received"] == 3
        assert data["connection_established"] is True
        assert data["close_code"] == 1000
        assert data["error"] == "Test error"
        assert data["duration_ms"] == 123.45

    def test_passed_state(self) -> None:
        """Test passed result state."""
        result = WebSocketTestResult(route_path="/ws/test", passed=True, messages_sent=10)

        assert result.passed is True
        assert result.error is None

    def test_failed_state(self) -> None:
        """Test failed result state."""
        result = WebSocketTestResult(route_path="/ws/test", passed=False, error="Connection failed")

        assert result.passed is False
        assert result.error == "Connection failed"


class TestWebSocketTestFailure:
    """Tests for WebSocketTestFailure."""

    def test_format_message_basic(self) -> None:
        """Test basic failure message formatting."""
        failure = WebSocketTestFailure(
            route_path="/ws/test",
            error_type="connection_error",
            message="Failed to connect",
        )

        formatted = failure.format_message()

        assert "WEBSOCKET TEST FAILURE" in formatted
        assert "/ws/test" in formatted
        assert "connection_error" in formatted
        assert "Failed to connect" in formatted

    def test_format_message_with_sequence_index(self) -> None:
        """Test failure message with sequence index."""
        failure = WebSocketTestFailure(
            route_path="/ws/test",
            error_type="message_error",
            message="Invalid message",
            sequence_index=3,
        )

        formatted = failure.format_message()

        assert "Failed at message index: 3" in formatted

    def test_format_message_with_sent_message(self) -> None:
        """Test failure message with sent message."""
        failure = WebSocketTestFailure(
            route_path="/ws/test",
            error_type="send_error",
            message="Failed to send",
            sent_message=("text", "hello world"),
        )

        formatted = failure.format_message()

        assert "Sent (text):" in formatted
        assert "hello world" in formatted

    def test_format_message_with_expected_and_actual(self) -> None:
        """Test failure message with expected and actual responses."""
        failure = WebSocketTestFailure(
            route_path="/ws/test",
            error_type="validation_error",
            message="Response mismatch",
            expected_response=("json", {"status": "ok"}),
            actual_response=("json", {"status": "error"}),
        )

        formatted = failure.format_message()

        assert "Expected (json):" in formatted
        assert "Actual (json):" in formatted

    def test_truncate_data_short_string(self) -> None:
        """Test data truncation for short strings."""
        failure = WebSocketTestFailure(
            route_path="/ws/test",
            error_type="test",
            message="test",
        )

        result = failure._truncate_data("short string")

        assert result == "short string"

    def test_truncate_data_long_string(self) -> None:
        """Test data truncation for long strings."""
        failure = WebSocketTestFailure(
            route_path="/ws/test",
            error_type="test",
            message="test",
        )

        long_string = "x" * 600
        result = failure._truncate_data(long_string)

        assert result.endswith("...")
        assert len(result) <= 503

    def test_truncate_data_bytes(self) -> None:
        """Test data truncation for bytes."""
        failure = WebSocketTestFailure(
            route_path="/ws/test",
            error_type="test",
            message="test",
        )

        result = failure._truncate_data(b"binary data")

        assert result == "<11 bytes>"

    def test_truncate_data_dict(self) -> None:
        """Test data truncation for dictionaries."""
        failure = WebSocketTestFailure(
            route_path="/ws/test",
            error_type="test",
            message="test",
        )

        result = failure._truncate_data({"key": "value"})

        assert '"key": "value"' in result


class TestMessageStrategies:
    """Tests for message generation strategies."""

    @given(text_message_strategy())
    def test_text_message_strategy_generates_text(self, msg: tuple[str, str]) -> None:
        """Test that text strategy generates text messages."""
        msg_type, data = msg
        assert msg_type == "text"
        assert isinstance(data, str)

    @given(text_message_strategy())
    def test_text_message_strategy_property(self, msg: tuple[str, str]) -> None:
        """Property test for text message strategy."""
        msg_type, data = msg
        assert msg_type == "text"
        assert isinstance(data, str)

    @given(text_message_strategy(min_size=5, max_size=10))
    def test_text_message_strategy_with_size_limits(self, msg: tuple[str, str]) -> None:
        """Test text strategy with size constraints."""
        msg_type, data = msg
        assert msg_type == "text"
        assert 5 <= len(data) <= 10

    @given(text_message_strategy(alphabet="abc", min_size=1))
    def test_text_message_strategy_with_alphabet(self, msg: tuple[str, str]) -> None:
        """Test text strategy with custom alphabet."""
        msg_type, data = msg
        assert msg_type == "text"
        assert all(c in "abc" for c in data)

    @given(binary_message_strategy())
    def test_binary_message_strategy_generates_bytes(self, msg: tuple[str, bytes]) -> None:
        """Test that binary strategy generates bytes messages."""
        msg_type, data = msg
        assert msg_type == "bytes"
        assert isinstance(data, bytes)

    @given(binary_message_strategy())
    def test_binary_message_strategy_property(self, msg: tuple[str, bytes]) -> None:
        """Property test for binary message strategy."""
        msg_type, data = msg
        assert msg_type == "bytes"
        assert isinstance(data, bytes)

    @given(binary_message_strategy(min_size=10, max_size=20))
    def test_binary_message_strategy_with_size_limits(self, msg: tuple[str, bytes]) -> None:
        """Test binary strategy with size constraints."""
        msg_type, data = msg
        assert msg_type == "bytes"
        assert 10 <= len(data) <= 20

    @given(json_message_strategy())
    def test_json_message_strategy_generates_dict(self, msg: tuple[str, dict]) -> None:
        """Test that JSON strategy generates dict messages."""
        msg_type, data = msg
        assert msg_type == "json"
        assert isinstance(data, dict)

    @given(json_message_strategy())
    def test_json_message_strategy_property(self, msg: tuple[str, dict]) -> None:
        """Property test for JSON message strategy."""
        msg_type, data = msg
        assert msg_type == "json"
        assert isinstance(data, dict)

    @given(json_message_strategy(required_keys={"action": st.just("ping")}))
    def test_json_message_strategy_with_required_keys(self, msg: tuple[str, dict]) -> None:
        """Test JSON strategy with required keys."""
        msg_type, data = msg
        assert msg_type == "json"
        assert "action" in data
        assert data["action"] == "ping"

    @given(json_message_strategy(required_keys={"type": st.just("message")}, optional_keys={"text": st.text()}))
    def test_json_message_strategy_with_optional_keys(self, msg: tuple[str, dict]) -> None:
        """Test JSON strategy with optional keys."""
        msg_type, data = msg
        assert msg_type == "json"
        assert "type" in data


class TestMessageSequence:
    """Tests for MessageSequence dataclass."""

    def test_empty_sequence(self) -> None:
        """Test creating empty message sequence."""
        seq = MessageSequence()

        assert seq.messages == []
        assert seq.expected_responses == []
        assert seq.delay_between == 0.0
        assert seq.description == ""

    def test_add_text(self) -> None:
        """Test adding text message to sequence."""
        seq = MessageSequence()
        result = seq.add_text("hello")

        assert result is seq
        assert len(seq.messages) == 1
        assert seq.messages[0] == ("text", "hello")

    def test_add_text_with_expected(self) -> None:
        """Test adding text message with expected response."""
        seq = MessageSequence()
        seq.add_text("hello", expected="world")

        assert len(seq.expected_responses) == 1
        assert seq.expected_responses[0] == ("text", "world")

    def test_add_bytes(self) -> None:
        """Test adding bytes message to sequence."""
        seq = MessageSequence()
        seq.add_bytes(b"data")

        assert len(seq.messages) == 1
        assert seq.messages[0] == ("bytes", b"data")

    def test_add_json(self) -> None:
        """Test adding JSON message to sequence."""
        seq = MessageSequence()
        seq.add_json({"key": "value"})

        assert len(seq.messages) == 1
        assert seq.messages[0] == ("json", {"key": "value"})

    def test_method_chaining(self) -> None:
        """Test method chaining for building sequences."""
        seq = MessageSequence().add_text("hello").add_json({"type": "ping"}).add_bytes(b"data")

        assert len(seq) == 3
        assert seq.messages[0][0] == "text"
        assert seq.messages[1][0] == "json"
        assert seq.messages[2][0] == "bytes"

    def test_len(self) -> None:
        """Test sequence length."""
        seq = MessageSequence()
        assert len(seq) == 0

        seq.add_text("hello")
        assert len(seq) == 1

        seq.add_json({})
        assert len(seq) == 2


class TestMessageSequenceStrategy:
    """Tests for message_sequence_strategy."""

    @given(message_sequence_strategy())
    def test_generates_sequence(self, seq: MessageSequence) -> None:
        """Test that strategy generates MessageSequence."""
        assert isinstance(seq, MessageSequence)

    @given(message_sequence_strategy(min_length=1, max_length=5))
    def test_sequence_length_property(self, seq: MessageSequence) -> None:
        """Property test for sequence length constraints."""
        assert 1 <= len(seq) <= 5

    @given(message_sequence_strategy(message_types=[WebSocketMessageType.TEXT], min_length=1, max_length=3))
    def test_sequence_with_text_only(self, seq: MessageSequence) -> None:
        """Test sequence strategy with text messages only."""
        assert len(seq) >= 1
        for msg_type, _ in seq.messages:
            assert msg_type == "text"

    @given(message_sequence_strategy(message_types=[WebSocketMessageType.JSON], min_length=1, max_length=3))
    def test_sequence_with_json_only(self, seq: MessageSequence) -> None:
        """Test sequence strategy with JSON messages only."""
        for msg_type, _ in seq.messages:
            assert msg_type == "json"

    @given(message_sequence_strategy(message_types=[WebSocketMessageType.BINARY], min_length=1, max_length=3))
    def test_sequence_with_binary_only(self, seq: MessageSequence) -> None:
        """Test sequence strategy with binary messages only."""
        for msg_type, _ in seq.messages:
            assert msg_type == "bytes"


class TestCustomMessageStrategies:
    """Tests for custom message strategy registration."""

    def test_register_message_strategy(self) -> None:
        """Test registering a custom message strategy."""
        custom_strategy = st.builds(MessageSequence, messages=st.just([("text", "custom")]))

        register_message_strategy("/ws/custom", custom_strategy)

        route = RouteInfo(
            path="/ws/custom",
            methods=[],
            is_websocket=True,
            websocket_metadata=WebSocketMetadata(),
        )

        from pytest_routes.websocket.strategies import get_message_strategy

        strategy = get_message_strategy(route)

        @given(strategy)
        def check_strategy(seq: MessageSequence) -> None:
            assert len(seq.messages) == 1
            assert seq.messages[0] == ("text", "custom")

        check_strategy()

        unregister_message_strategy("/ws/custom")

    def test_unregister_message_strategy_exists(self) -> None:
        """Test unregistering an existing strategy."""
        custom_strategy = st.builds(MessageSequence, messages=st.just([]))
        register_message_strategy("/ws/test", custom_strategy)

        result = unregister_message_strategy("/ws/test")

        assert result is True

    def test_unregister_message_strategy_not_exists(self) -> None:
        """Test unregistering a non-existent strategy."""
        result = unregister_message_strategy("/ws/nonexistent")

        assert result is False
