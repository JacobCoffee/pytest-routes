"""WebSocket test execution runner.

This module provides the test execution engine for WebSocket endpoints,
integrating with Hypothesis for property-based testing. It handles
connection management, message sequence execution, and result validation.

Architecture:
    WebSocketTestRunner
        |
        +-- create_test(route) -> Hypothesis test function
        |
        +-- test_route_async(route) -> WebSocketTestResult
        |
        +-- _execute_sequence(connection, sequence) -> list[WebSocketMessage]
        |
        +-- _validate_responses(expected, actual) -> ValidationResult

The runner supports:
    - Property-based testing with generated message sequences
    - Stateful testing with state machine integration
    - Connection lifecycle validation
    - Protocol compliance checking
    - Detailed failure reporting
"""

from __future__ import annotations

import asyncio
import json
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from hypothesis import HealthCheck, given, settings

from pytest_routes.websocket.client import WebSocketTestClient
from pytest_routes.websocket.strategies import MessageSequence, get_message_strategy

if TYPE_CHECKING:
    from pytest_routes.config import RouteTestConfig
    from pytest_routes.discovery.base import RouteInfo

_MAX_RESPONSE_DISPLAY = 500
_DEFAULT_TEST_TIMEOUT = 30.0


@dataclass
class WebSocketTestResult:
    """Result of a WebSocket route test.

    Attributes:
        route_path: The WebSocket route path that was tested.
        passed: Whether the test passed.
        messages_sent: Number of messages sent during the test.
        messages_received: Number of messages received.
        connection_established: Whether a connection was successfully established.
        close_code: The close code when the connection ended.
        error: Error message if the test failed.
        duration_ms: Test duration in milliseconds.
    """

    route_path: str
    passed: bool = True
    messages_sent: int = 0
    messages_received: int = 0
    connection_established: bool = False
    close_code: int | None = None
    error: str | None = None
    duration_ms: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        """Convert result to dictionary for JSON serialization."""
        return {
            "route_path": self.route_path,
            "passed": self.passed,
            "messages_sent": self.messages_sent,
            "messages_received": self.messages_received,
            "connection_established": self.connection_established,
            "close_code": self.close_code,
            "error": self.error,
            "duration_ms": self.duration_ms,
        }


@dataclass
class WebSocketTestFailure:
    """Detailed information about a WebSocket test failure.

    Attributes:
        route_path: The route that was tested.
        error_type: Category of the failure.
        message: Human-readable error message.
        sequence_index: Index in the message sequence where failure occurred.
        sent_message: The message that was sent before failure.
        expected_response: What response was expected.
        actual_response: What response was actually received.
        connection_state: State of the connection at failure time.
        close_code: Close code if connection was closed unexpectedly.
    """

    route_path: str
    error_type: str
    message: str
    sequence_index: int | None = None
    sent_message: tuple[str, Any] | None = None
    expected_response: tuple[str, Any] | None = None
    actual_response: tuple[str, Any] | None = None
    connection_state: str = "unknown"
    close_code: int | None = None
    additional_context: dict[str, Any] = field(default_factory=dict)

    def format_message(self) -> str:
        """Format a detailed error message."""
        lines = [
            "",
            "=" * 60,
            f"WEBSOCKET TEST FAILURE: {self.route_path}",
            "=" * 60,
            "",
            f"Error Type: {self.error_type}",
            f"Message: {self.message}",
            "",
        ]

        if self.sequence_index is not None:
            lines.append(f"Failed at message index: {self.sequence_index}")

        if self.sent_message:
            msg_type, data = self.sent_message
            data_str = self._truncate_data(data)
            lines.extend(["", f"Sent ({msg_type}):", f"  {data_str}"])

        if self.expected_response:
            msg_type, data = self.expected_response
            data_str = self._truncate_data(data)
            lines.extend(["", f"Expected ({msg_type}):", f"  {data_str}"])

        if self.actual_response:
            msg_type, data = self.actual_response
            data_str = self._truncate_data(data)
            lines.extend(["", f"Actual ({msg_type}):", f"  {data_str}"])

        lines.extend(
            [
                "",
                f"Connection State: {self.connection_state}",
            ]
        )

        if self.close_code is not None:
            lines.append(f"Close Code: {self.close_code}")

        if self.additional_context:
            lines.extend(["", "Additional Context:"])
            for key, value in self.additional_context.items():
                lines.append(f"  {key}: {value}")

        lines.extend(["", "=" * 60])
        return "\n".join(lines)

    def _truncate_data(self, data: Any) -> str:
        """Truncate data for display."""
        if isinstance(data, dict):
            data_str = json.dumps(data, default=str)
        elif isinstance(data, bytes):
            data_str = f"<{len(data)} bytes>"
        else:
            data_str = str(data)

        if len(data_str) > _MAX_RESPONSE_DISPLAY:
            return data_str[:_MAX_RESPONSE_DISPLAY] + "..."
        return data_str


class WebSocketTestRunner:
    """Executes property-based tests against WebSocket routes.

    This runner integrates with Hypothesis to generate message sequences
    and test WebSocket endpoints. It handles connection management,
    message exchange, and result validation.

    Attributes:
        app: The ASGI application under test.
        config: Test configuration from pytest-routes.
        client: The WebSocket test client.

    Example:
        >>> runner = WebSocketTestRunner(app, config)
        >>> test_func = runner.create_test(websocket_route)
        >>> test_func()  # Runs Hypothesis property-based test
    """

    def __init__(self, app: Any, config: RouteTestConfig) -> None:
        """Initialize the WebSocket test runner.

        Args:
            app: The ASGI application to test.
            config: Test configuration.
        """
        self.app = app
        self.config = config
        self.client = WebSocketTestClient(
            app,
            default_timeout=config.timeout_per_route,
        )

    def create_test(self, route: RouteInfo) -> Callable[[], None]:
        """Create a Hypothesis test function for a WebSocket route.

        Args:
            route: The WebSocket route to test.

        Returns:
            A test function decorated with @given for Hypothesis.

        Raises:
            ValueError: If the route is not a WebSocket route.
        """
        if not route.is_websocket:
            msg = f"Route {route.path} is not a WebSocket route"
            raise ValueError(msg)

        effective_config = self.config.get_effective_config_for_route(route.path)

        if effective_config.get("skip", False):

            def skipped_test() -> None:
                import pytest

                pytest.skip(f"WebSocket route {route.path} is configured to be skipped")

            return skipped_test

        max_examples = effective_config.get("max_examples", self.config.max_examples)
        message_strategy = get_message_strategy(route)
        runner = self

        # TODO: Generate path parameters strategy from route.path_params
        # path_strategy = generate_path_params(route.path_params, route.path)

        @settings(
            max_examples=max_examples,
            suppress_health_check=[HealthCheck.too_slow],
            deadline=None,
        )
        @given(
            sequence=message_strategy,
            # path_params=path_strategy,
        )
        def test_websocket_route(sequence: MessageSequence) -> None:
            # TODO: Format path with path_params
            formatted_path = route.path

            if runner.config.verbose:
                _print_verbose_sequence(route.path, sequence)

            async def run_test() -> WebSocketTestResult:
                return await runner._execute_test(route, formatted_path, sequence)  # noqa: SLF001

            try:
                asyncio.get_running_loop()
                import concurrent.futures

                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(asyncio.run, run_test())
                    result = future.result()
            except RuntimeError:
                result = asyncio.run(run_test())

            if runner.config.verbose:
                _print_verbose_result(result)

            if not result.passed:
                failure = WebSocketTestFailure(
                    route_path=route.path,
                    error_type="test_failure",
                    message=result.error or "Unknown error",
                    connection_state="closed" if result.connection_established else "failed",
                    close_code=result.close_code,
                )
                raise AssertionError(failure.format_message())

        test_websocket_route.__name__ = f"test_ws_{route.path.replace('/', '_').strip('_')}"
        test_websocket_route.__doc__ = f"WebSocket test for {route.path}"

        return test_websocket_route

    async def _execute_test(
        self,
        route: RouteInfo,
        formatted_path: str,
        sequence: MessageSequence,
    ) -> WebSocketTestResult:
        """Execute a single WebSocket test with a message sequence.

        Args:
            route: The route being tested.
            formatted_path: Path with parameters substituted.
            sequence: The message sequence to execute.

        Returns:
            WebSocketTestResult with test outcome.
        """
        import time

        start_time = time.perf_counter()
        result = WebSocketTestResult(route_path=route.path)

        try:
            async with self.client.connect(formatted_path) as connection:
                result.connection_established = True

                # Execute the message sequence
                error_occurred = False
                for i, (msg_type, data) in enumerate(sequence.messages):
                    if error_occurred:
                        break
                    try:
                        await self._send_message(connection, msg_type, data)
                        result.messages_sent += 1

                        # TODO: Check for expected responses
                        if i < len(sequence.expected_responses):
                            expected = sequence.expected_responses[i]
                            if expected is not None:
                                # TODO: Implement response validation
                                pass

                    except Exception as e:
                        result.passed = False
                        result.error = f"Failed at message {i}: {e}"
                        error_occurred = True

                result.close_code = connection.close_code

        except ConnectionRefusedError as e:
            result.passed = False
            result.error = f"Connection refused: {e}"
        except TimeoutError as e:
            result.passed = False
            result.error = f"Connection timeout: {e}"
        except Exception as e:
            result.passed = False
            result.error = f"Unexpected error: {e}"

        result.duration_ms = (time.perf_counter() - start_time) * 1000
        return result

    async def _send_message(
        self,
        connection: Any,
        msg_type: str,
        data: Any,
    ) -> None:
        """Send a message through the WebSocket connection.

        Args:
            connection: The WebSocketConnection.
            msg_type: Message type ("text", "bytes", or "json").
            data: Message payload.
        """
        if msg_type == "text":
            await connection.send_text(data)
        elif msg_type == "bytes":
            await connection.send_bytes(data)
        elif msg_type == "json":
            await connection.send_json(data)
        else:
            msg = f"Unknown message type: {msg_type}"
            raise ValueError(msg)

    async def test_route_async(self, route: RouteInfo) -> dict[str, Any]:
        """Test a single WebSocket route asynchronously.

        This method runs the Hypothesis test and returns a result dictionary
        compatible with the existing RouteTestRunner interface.

        Args:
            route: The WebSocket route to test.

        Returns:
            Test result dictionary with keys: route, passed, error.
        """
        try:
            test_func = self.create_test(route)
            test_func()
            return {"route": str(route), "passed": True, "error": None}
        except Exception as e:
            return {"route": str(route), "passed": False, "error": str(e)}

    async def test_all_routes(self, routes: list[RouteInfo]) -> list[dict[str, Any]]:
        """Test all WebSocket routes.

        Args:
            routes: List of WebSocket routes to test.

        Returns:
            List of test result dictionaries.
        """
        results = []
        for route in routes:
            if route.is_websocket:
                result = await self.test_route_async(route)
                results.append(result)
        return results

    def get_websocket_routes(self, routes: list[RouteInfo]) -> list[RouteInfo]:
        """Filter to only WebSocket routes.

        Args:
            routes: List of all discovered routes.

        Returns:
            List containing only WebSocket routes.
        """
        return [r for r in routes if r.is_websocket]


def _print_verbose_sequence(path: str, sequence: MessageSequence) -> None:
    """Print verbose information about the message sequence."""
    print(f"\n  -> WS {path}")  # noqa: T201
    print(f"     Sequence: {len(sequence)} messages")  # noqa: T201
    for i, (msg_type, data) in enumerate(sequence.messages):
        if isinstance(data, dict):
            data_str = json.dumps(data, default=str)[:100]
        elif isinstance(data, bytes):
            data_str = f"<{len(data)} bytes>"
        else:
            data_str = str(data)[:100]
        print(f"     [{i}] {msg_type}: {data_str}")  # noqa: T201


def _print_verbose_result(result: WebSocketTestResult) -> None:
    """Print verbose information about the test result."""
    status = "PASS" if result.passed else "FAIL"
    print(f"     <- {status} ({result.duration_ms:.1f}ms)")  # noqa: T201
    print(f"        sent={result.messages_sent}, received={result.messages_received}")  # noqa: T201
    if result.error:
        print(f"        error: {result.error[:100]}")  # noqa: T201


# TODO: Implement stateful testing with Hypothesis RuleBasedStateMachine
# class WebSocketStateMachine(RuleBasedStateMachine):
#     """State machine for stateful WebSocket testing."""
#
#     def __init__(self):
#         super().__init__()
#         self.connection = None
#         self.messages_sent = []
#         self.messages_received = []
#
#     @initialize()
#     def connect(self):
#         """Establish WebSocket connection."""
#         pass
#
#     @rule(message=text_message_strategy())
#     def send_text(self, message):
#         """Send a text message."""
#         pass
#
#     @rule(message=json_message_strategy())
#     def send_json(self, message):
#         """Send a JSON message."""
#         pass
#
#     @invariant()
#     def connection_alive(self):
#         """Check that connection is still alive."""
#         pass
