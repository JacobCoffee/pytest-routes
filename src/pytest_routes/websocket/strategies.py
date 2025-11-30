"""Hypothesis strategies for WebSocket message generation.

This module provides strategies for generating WebSocket test messages
using Hypothesis. It supports text, binary, and JSON message types,
as well as message sequences for stateful testing.

Architecture:
    Message Strategies (atomic)
        - text_message_strategy: Generate text messages
        - binary_message_strategy: Generate binary messages
        - json_message_strategy: Generate JSON messages

    Sequence Strategies (composite)
        - message_sequence_strategy: Generate sequences of messages
        - stateful_sequence_strategy: Generate sequences with state dependencies

    Custom Registration
        - register_message_strategy: Register custom strategies per route

The strategies integrate with the existing pytest-routes strategy system
and can be customized per-route using the configuration system.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from hypothesis import strategies as st

if TYPE_CHECKING:
    from hypothesis.strategies import SearchStrategy

    from pytest_routes.discovery.base import RouteInfo, WebSocketMessageType


@dataclass
class MessageSequence:
    """Represents a sequence of WebSocket messages for testing.

    This class captures a series of messages to send and expected
    response patterns, enabling stateful testing of WebSocket endpoints.

    Attributes:
        messages: List of (type, data) tuples representing messages to send.
        expected_responses: Optional list of expected response patterns.
        delay_between: Optional delay between messages in seconds.
        description: Human-readable description of what this sequence tests.
    """

    messages: list[tuple[str, Any]] = field(default_factory=list)
    expected_responses: list[tuple[str, Any] | None] = field(default_factory=list)
    delay_between: float = 0.0
    description: str = ""

    def add_text(self, data: str, expected: str | None = None) -> MessageSequence:
        """Add a text message to the sequence.

        Args:
            data: The text message to send.
            expected: Optional expected response text.

        Returns:
            Self for method chaining.
        """
        self.messages.append(("text", data))
        self.expected_responses.append(("text", expected) if expected else None)
        return self

    def add_bytes(self, data: bytes, expected: bytes | None = None) -> MessageSequence:
        """Add a binary message to the sequence.

        Args:
            data: The binary message to send.
            expected: Optional expected response bytes.

        Returns:
            Self for method chaining.
        """
        self.messages.append(("bytes", data))
        self.expected_responses.append(("bytes", expected) if expected else None)
        return self

    def add_json(
        self,
        data: dict[str, Any],
        expected: dict[str, Any] | None = None,
    ) -> MessageSequence:
        """Add a JSON message to the sequence.

        Args:
            data: The JSON message to send.
            expected: Optional expected response JSON.

        Returns:
            Self for method chaining.
        """
        self.messages.append(("json", data))
        self.expected_responses.append(("json", expected) if expected else None)
        return self

    def __len__(self) -> int:
        """Return the number of messages in the sequence."""
        return len(self.messages)


_CUSTOM_MESSAGE_STRATEGIES: dict[str, SearchStrategy[MessageSequence]] = {}

_DEFAULT_TEXT_MIN_SIZE = 1
_DEFAULT_TEXT_MAX_SIZE = 1000
_DEFAULT_BINARY_MIN_SIZE = 1
_DEFAULT_BINARY_MAX_SIZE = 1000
_DEFAULT_JSON_MAX_DEPTH = 3
_DEFAULT_SEQUENCE_MIN_SIZE = 1
_DEFAULT_SEQUENCE_MAX_SIZE = 10


def text_message_strategy(
    min_size: int = _DEFAULT_TEXT_MIN_SIZE,
    max_size: int = _DEFAULT_TEXT_MAX_SIZE,
    alphabet: str | None = None,
) -> SearchStrategy[tuple[str, str]]:
    """Generate text WebSocket messages.

    Args:
        min_size: Minimum message length.
        max_size: Maximum message length.
        alphabet: Optional character set to use.

    Returns:
        Hypothesis strategy producing ("text", str) tuples.

    Example:
        >>> from hypothesis import given
        >>> @given(text_message_strategy())
        ... def test_text_message(msg):
        ...     msg_type, data = msg
        ...     assert msg_type == "text"
        ...     assert isinstance(data, str)
    """
    if alphabet:
        text_strat = st.text(alphabet=alphabet, min_size=min_size, max_size=max_size)
    else:
        text_strat = st.text(min_size=min_size, max_size=max_size)

    return st.tuples(st.just("text"), text_strat)


def binary_message_strategy(
    min_size: int = _DEFAULT_BINARY_MIN_SIZE,
    max_size: int = _DEFAULT_BINARY_MAX_SIZE,
) -> SearchStrategy[tuple[str, bytes]]:
    """Generate binary WebSocket messages.

    Args:
        min_size: Minimum message length in bytes.
        max_size: Maximum message length in bytes.

    Returns:
        Hypothesis strategy producing ("bytes", bytes) tuples.

    Example:
        >>> from hypothesis import given
        >>> @given(binary_message_strategy(max_size=100))
        ... def test_binary_message(msg):
        ...     msg_type, data = msg
        ...     assert msg_type == "bytes"
        ...     assert len(data) <= 100
    """
    return st.tuples(st.just("bytes"), st.binary(min_size=min_size, max_size=max_size))


def json_message_strategy(
    required_keys: dict[str, SearchStrategy[Any]] | None = None,
    optional_keys: dict[str, SearchStrategy[Any]] | None = None,
    max_depth: int = _DEFAULT_JSON_MAX_DEPTH,
) -> SearchStrategy[tuple[str, dict[str, Any]]]:
    """Generate JSON WebSocket messages.

    This strategy produces JSON-serializable dictionaries. You can specify
    required and optional keys with their own strategies, or let it generate
    arbitrary JSON structures.

    Args:
        required_keys: Mapping of required key names to their value strategies.
        optional_keys: Mapping of optional key names to their value strategies.
        max_depth: Maximum nesting depth for generated structures.

    Returns:
        Hypothesis strategy producing ("json", dict) tuples.

    Example:
        >>> from hypothesis import given, strategies as st
        >>> @given(
        ...     json_message_strategy(
        ...         required_keys={"action": st.sampled_from(["ping", "subscribe"])},
        ...         optional_keys={"channel": st.text(min_size=1)},
        ...     )
        ... )
        ... def test_json_message(msg):
        ...     msg_type, data = msg
        ...     assert "action" in data
    """
    if required_keys or optional_keys:
        # Build a fixed structure with specified keys
        fixed_required = st.fixed_dictionaries(required_keys or {})

        if optional_keys:
            # Optionally include some optional keys
            optional_strat = st.fixed_dictionaries(
                {},
                optional=optional_keys,
            )
            json_strat = st.builds(
                lambda req, opt: {**req, **opt},
                fixed_required,
                optional_strat,
            )
        else:
            json_strat = fixed_required
    else:
        # Generate arbitrary JSON-compatible structures
        json_strat = _arbitrary_json_strategy(max_depth=max_depth)

    return st.tuples(st.just("json"), json_strat)


def _arbitrary_json_strategy(max_depth: int = 3) -> SearchStrategy[dict[str, Any]]:
    """Generate arbitrary JSON-compatible dictionaries.

    Args:
        max_depth: Maximum nesting depth.

    Returns:
        Strategy for JSON-compatible dictionaries.
    """
    # JSON-compatible leaf values
    json_leaves = st.one_of(
        st.none(),
        st.booleans(),
        st.integers(min_value=-1000000, max_value=1000000),
        st.floats(allow_nan=False, allow_infinity=False),
        st.text(max_size=100),
    )

    if max_depth <= 1:
        return st.dictionaries(st.text(min_size=1, max_size=20), json_leaves, max_size=5)

    # Recursive structure
    json_values = st.recursive(
        json_leaves,
        lambda children: st.one_of(
            st.lists(children, max_size=5),
            st.dictionaries(st.text(min_size=1, max_size=20), children, max_size=5),
        ),
        max_leaves=20,
    )

    return st.dictionaries(st.text(min_size=1, max_size=20), json_values, min_size=1, max_size=10)


def message_sequence_strategy(
    message_types: list[WebSocketMessageType] | None = None,
    min_length: int = _DEFAULT_SEQUENCE_MIN_SIZE,
    max_length: int = _DEFAULT_SEQUENCE_MAX_SIZE,
) -> SearchStrategy[MessageSequence]:
    """Generate sequences of WebSocket messages for stateful testing.

    This strategy produces MessageSequence objects containing multiple
    messages of varying types. It's useful for testing message ordering,
    state transitions, and protocol compliance.

    Args:
        message_types: List of allowed message types. Defaults to text and JSON.
        min_length: Minimum number of messages in the sequence.
        max_length: Maximum number of messages in the sequence.

    Returns:
        Hypothesis strategy producing MessageSequence objects.

    Example:
        >>> from hypothesis import given
        >>> from pytest_routes.discovery.base import WebSocketMessageType
        >>> @given(
        ...     message_sequence_strategy(
        ...         message_types=[WebSocketMessageType.JSON],
        ...         min_length=1,
        ...         max_length=5,
        ...     )
        ... )
        ... def test_message_sequence(seq):
        ...     assert 1 <= len(seq) <= 5
        ...     for msg_type, _ in seq.messages:
        ...         assert msg_type == "json"
    """
    from pytest_routes.discovery.base import WebSocketMessageType

    if message_types is None:
        message_types = [WebSocketMessageType.TEXT, WebSocketMessageType.JSON]

    # Build strategy for individual messages based on allowed types
    message_strategies = []
    for msg_type in message_types:
        if msg_type == WebSocketMessageType.TEXT:
            message_strategies.append(text_message_strategy())
        elif msg_type == WebSocketMessageType.BINARY:
            message_strategies.append(binary_message_strategy())
        elif msg_type == WebSocketMessageType.JSON:
            message_strategies.append(json_message_strategy())

    if not message_strategies:
        message_strategies = [text_message_strategy()]

    single_message = st.one_of(*message_strategies)

    # Generate a list of messages
    messages_list = st.lists(single_message, min_size=min_length, max_size=max_length)

    @st.composite
    def build_sequence(draw: st.DrawFn) -> MessageSequence:
        messages = draw(messages_list)
        return MessageSequence(messages=messages)

    return build_sequence()


def register_message_strategy(
    route_path: str,
    strategy: SearchStrategy[MessageSequence],
) -> None:
    """Register a custom message strategy for a specific route.

    This allows you to define route-specific message generation logic,
    such as protocol-specific message formats or required handshake sequences.

    Args:
        route_path: The WebSocket route path (e.g., "/ws/chat").
        strategy: The Hypothesis strategy to use for this route.

    Example:
        >>> from hypothesis import strategies as st
        >>> # Define a custom strategy for a chat WebSocket
        >>> chat_strategy = st.builds(
        ...     MessageSequence,
        ...     messages=st.just(
        ...         [
        ...             ("json", {"type": "join", "room": "general"}),
        ...             ("json", {"type": "message", "text": "hello"}),
        ...         ]
        ...     ),
        ... )
        >>> register_message_strategy("/ws/chat", chat_strategy)
    """
    _CUSTOM_MESSAGE_STRATEGIES[route_path] = strategy


def unregister_message_strategy(route_path: str) -> bool:
    """Unregister a custom message strategy.

    Args:
        route_path: The WebSocket route path to unregister.

    Returns:
        True if a strategy was unregistered, False if none was registered.
    """
    return _CUSTOM_MESSAGE_STRATEGIES.pop(route_path, None) is not None


def get_message_strategy(route: RouteInfo) -> SearchStrategy[MessageSequence]:
    """Get the appropriate message strategy for a route.

    This function checks for custom registered strategies first, then
    falls back to generating a strategy based on the route's metadata.

    Args:
        route: The RouteInfo for the WebSocket endpoint.

    Returns:
        A Hypothesis strategy for generating message sequences.

    Raises:
        ValueError: If the route is not a WebSocket route.
    """
    if not route.is_websocket:
        msg = f"Route {route.path} is not a WebSocket route"
        raise ValueError(msg)

    # Check for custom strategy
    if route.path in _CUSTOM_MESSAGE_STRATEGIES:
        return _CUSTOM_MESSAGE_STRATEGIES[route.path]

    # Generate strategy based on route metadata
    metadata = route.get_websocket_metadata()
    return message_sequence_strategy(
        message_types=metadata.accepted_message_types,
        min_length=1,
        max_length=5,
    )


def graphql_subscription_strategy(
    operation_name: str = "subscription",
    variables: SearchStrategy[dict[str, Any]] | None = None,
) -> SearchStrategy[MessageSequence]:
    """Generate GraphQL subscription message sequences.

    This is a specialized strategy for testing GraphQL WebSocket subscriptions
    following the graphql-ws protocol.

    Args:
        operation_name: The GraphQL operation name.
        variables: Strategy for generating query variables.

    Returns:
        Strategy producing GraphQL subscription message sequences.

    Example:
        >>> @given(
        ...     graphql_subscription_strategy(
        ...         operation_name="onMessage",
        ...         variables=st.fixed_dictionaries({"channel": st.text()}),
        ...     )
        ... )
        ... def test_graphql_subscription(seq):
        ...     # First message should be connection_init
        ...     msg_type, data = seq.messages[0]
        ...     assert data.get("type") == "connection_init"
    """
    variables_strat = variables or st.just({})

    @st.composite
    def build_graphql_sequence(draw: st.DrawFn) -> MessageSequence:
        vars_data = draw(variables_strat)
        subscription_id = draw(st.text(min_size=1, max_size=20, alphabet="abcdef0123456789"))

        return MessageSequence(
            messages=[
                ("json", {"type": "connection_init"}),
                (
                    "json",
                    {
                        "id": subscription_id,
                        "type": "subscribe",
                        "payload": {
                            "operationName": operation_name,
                            "variables": vars_data,
                            "query": f"subscription {operation_name} {{ ... }}",
                        },
                    },
                ),
            ],
            description=f"GraphQL subscription: {operation_name}",
        )

    return build_graphql_sequence()


# TODO: Add more specialized strategies:
# - socket_io_strategy: For Socket.IO protocol testing
# - phoenix_channel_strategy: For Phoenix channels testing
# - action_cable_strategy: For Rails Action Cable testing
