"""Test execution runner."""

from __future__ import annotations

import asyncio
import contextlib
import json
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from pytest_routes.execution.client import RouteTestClient
from pytest_routes.generation.body import generate_body
from pytest_routes.generation.path import format_path, generate_path_params
from pytest_routes.generation.strategies import strategy_for_type

if TYPE_CHECKING:
    from pytest_routes.config import RouteTestConfig
    from pytest_routes.discovery.base import RouteInfo
    from pytest_routes.validation.response import ResponseValidator

# Constants
_MAX_EXPECTED_CODES_DISPLAY = 10
_MAX_RESPONSE_BODY_DISPLAY = 500
_SERVER_ERROR_THRESHOLD = 500
_MAX_VERBOSE_BODY_DISPLAY = 200


def _print_verbose_request(
    method: str,
    path: str,
    path_params: dict[str, Any],
    query_params: dict[str, Any],
    body: Any,
) -> None:
    """Print verbose request details."""
    print(f"\n  → {method} {path}")
    if path_params:
        print(f"    path_params: {path_params}")
    if query_params:
        print(f"    query_params: {query_params}")
    if body is not None:
        body_str = json.dumps(body, default=str)
        if len(body_str) > _MAX_VERBOSE_BODY_DISPLAY:
            body_str = body_str[:_MAX_VERBOSE_BODY_DISPLAY] + "..."
        print(f"    body: {body_str}")


def _print_verbose_response(response: Any) -> None:
    """Print verbose response details."""
    status = response.status_code
    status_emoji = "✓" if 200 <= status < 400 else "✗" if status >= 400 else "→"
    print(f"    ← {status_emoji} {status}")


@dataclass
class RouteTestFailure:
    """Detailed information about a route test failure."""

    route_path: str
    method: str
    status_code: int
    expected_codes: list[int]
    request_path: str
    path_params: dict[str, Any] = field(default_factory=dict)
    query_params: dict[str, Any] = field(default_factory=dict)
    body: Any = None
    response_body: str | None = None
    error_type: str = "unexpected_status"

    def _format_expected_codes(self) -> str:
        """Format expected codes with truncation."""
        truncated = self.expected_codes[:_MAX_EXPECTED_CODES_DISPLAY]
        ellipsis = "..." if len(self.expected_codes) > _MAX_EXPECTED_CODES_DISPLAY else ""
        return f"  Expected: {truncated}{ellipsis}"

    def _base_lines(self) -> list[str]:
        """Build base error lines."""
        return [
            "",
            "=" * 60,
            f"ROUTE TEST FAILURE: {self.method} {self.route_path}",
            "=" * 60,
            "",
            "Error Type:",
            f"  {self.error_type}",
            "",
            "Request Details:",
            f"  Method: {self.method}",
            f"  Path: {self.request_path}",
            f"  Status Code: {self.status_code}",
            self._format_expected_codes(),
        ]

    def format_message(self) -> str:
        """Format a detailed error message with shrunk example."""
        lines = self._base_lines()

        if self.path_params:
            lines.extend(["", "Path Parameters (shrunk example):"])
            for key, value in self.path_params.items():
                lines.append(f"  {key}: {value!r}")

        if self.query_params:
            lines.extend(["", "Query Parameters (shrunk example):"])
            for key, value in self.query_params.items():
                lines.append(f"  {key}: {value!r}")

        if self.body is not None:
            lines.extend(["", "Request Body (shrunk example):"])
            try:
                body_str = json.dumps(self.body, indent=2, default=str)
                for line in body_str.split("\n"):
                    lines.append(f"  {line}")
            except (TypeError, ValueError):
                lines.append(f"  {self.body!r}")

        if self.response_body:
            lines.extend(["", "Response Body (truncated):"])
            truncated = self.response_body[:_MAX_RESPONSE_BODY_DISPLAY]
            if len(self.response_body) > _MAX_RESPONSE_BODY_DISPLAY:
                truncated += "..."
            for line in truncated.split("\n"):
                lines.append(f"  {line}")

        lines.extend(["", "=" * 60])
        return "\n".join(lines)


class RouteTestRunner:
    """Executes smoke tests against routes."""

    def __init__(self, app: Any, config: RouteTestConfig) -> None:
        """Initialize test runner.

        Args:
            app: The ASGI application.
            config: Test configuration.
        """
        self.app = app
        self.config = config
        self.client = RouteTestClient(app)
        self._validators: list[ResponseValidator] = []
        self._init_validators()

    def _init_validators(self) -> None:
        """Initialize response validators based on config."""
        if not self.config.validate_responses:
            return

        # Import validators only when needed
        from pytest_routes.validation.response import (
            ContentTypeValidator,
            StatusCodeValidator,
        )

        # Build validators based on config
        for validator_name in self.config.response_validators:
            if validator_name == "status_code":
                self._validators.append(StatusCodeValidator(self.config.allowed_status_codes))
            elif validator_name == "content_type":
                self._validators.append(ContentTypeValidator())
            # Additional validators can be added here

    def create_test(self, route: RouteInfo) -> Callable[[], None]:
        """Create a Hypothesis test for a route.

        Args:
            route: The route to test.

        Returns:
            A test function decorated with @given.
        """
        path_strategy = generate_path_params(route.path_params, route.path)
        query_strategy = (
            st.fixed_dictionaries({name: strategy_for_type(typ) for name, typ in route.query_params.items()})
            if route.query_params
            else st.just({})
        )
        body_strategy = generate_body(route.body_type)

        runner = self

        @settings(
            max_examples=self.config.max_examples,
            suppress_health_check=[HealthCheck.too_slow],
            deadline=None,
        )
        @given(
            path_params=path_strategy,
            query_params=query_strategy,
            body=body_strategy,
        )
        def test_route(path_params: dict[str, Any], query_params: dict[str, Any], body: Any) -> None:
            # Format path with params
            formatted_path = format_path(route.path, path_params)

            # Verbose: print request details before making request
            if runner.config.verbose:
                _print_verbose_request(
                    method=route.methods[0],
                    path=formatted_path,
                    path_params=path_params,
                    query_params=query_params,
                    body=body,
                )

            # Execute request - use new event loop to avoid conflicts with running loops
            async def run_request() -> Any:
                return await runner.client.request(
                    method=route.methods[0],
                    path=formatted_path,
                    params=query_params or None,
                    json=body if body is not None else None,
                    timeout=runner.config.timeout_per_route,
                )

            try:
                # Try to get the running loop
                asyncio.get_running_loop()
                # If we're in an async context, use nest_asyncio-like approach
                import concurrent.futures

                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(asyncio.run, run_request())
                    response = future.result()
            except RuntimeError:
                # No running loop, we can use asyncio.run directly
                response = asyncio.run(run_request())

            # Verbose: print response details
            if runner.config.verbose:
                _print_verbose_response(response)

            # Validate response with detailed error reporting
            runner._validate_response_detailed(
                response=response,
                route=route,
                formatted_path=formatted_path,
                path_params=path_params,
                query_params=query_params,
                body=body,
            )

        # Set test name for better reporting
        method = route.methods[0]
        test_route.__name__ = f"test_{method}_{route.path.replace('/', '_').strip('_')}"
        test_route.__doc__ = f"Smoke test for {method} {route.path}"

        return test_route

    def _validate_response(self, response: Any, route: RouteInfo) -> None:
        """Validate response meets smoke test criteria.

        Args:
            response: The HTTP response.
            route: The route that was tested.

        Raises:
            AssertionError: If validation fails.
        """
        # Check for 5xx errors
        if self.config.fail_on_5xx and response.status_code >= _SERVER_ERROR_THRESHOLD:
            msg = f"Route {route.methods[0]} {route.path} returned 5xx: {response.status_code}"
            raise AssertionError(msg)

        # Check allowed status codes
        if response.status_code not in self.config.allowed_status_codes:
            msg = f"Route {route.methods[0]} {route.path} returned unexpected status: {response.status_code}"
            raise AssertionError(msg)

    def _validate_response_detailed(
        self,
        response: Any,
        route: RouteInfo,
        formatted_path: str,
        path_params: dict[str, Any],
        query_params: dict[str, Any],
        body: Any,
    ) -> None:
        """Validate response with detailed error reporting.

        Args:
            response: The HTTP response.
            route: The route that was tested.
            formatted_path: The actual request path.
            path_params: Path parameters used.
            query_params: Query parameters used.
            body: Request body used.

        Raises:
            AssertionError: If validation fails with detailed error.
        """
        # Get response body for error reporting
        response_body = None
        with contextlib.suppress(Exception):
            response_body = response.text

        # Check for 5xx errors
        if self.config.fail_on_5xx and response.status_code >= _SERVER_ERROR_THRESHOLD:
            failure = RouteTestFailure(
                route_path=route.path,
                method=route.methods[0],
                status_code=response.status_code,
                expected_codes=self.config.allowed_status_codes,
                request_path=formatted_path,
                path_params=path_params,
                query_params=query_params,
                body=body,
                response_body=response_body,
                error_type="server_error_5xx",
            )
            raise AssertionError(failure.format_message())

        # Check allowed status codes
        if response.status_code not in self.config.allowed_status_codes:
            failure = RouteTestFailure(
                route_path=route.path,
                method=route.methods[0],
                status_code=response.status_code,
                expected_codes=self.config.allowed_status_codes,
                request_path=formatted_path,
                path_params=path_params,
                query_params=query_params,
                body=body,
                response_body=response_body,
                error_type="unexpected_status",
            )
            raise AssertionError(failure.format_message())

        # Run optional response validators
        if self.config.validate_responses and self._validators:
            validation_errors = []
            for validator in self._validators:
                result = validator.validate(response, route)
                if not result.valid:
                    validation_errors.extend(result.errors)

            if validation_errors and self.config.fail_on_validation_error:
                failure = RouteTestFailure(
                    route_path=route.path,
                    method=route.methods[0],
                    status_code=response.status_code,
                    expected_codes=self.config.allowed_status_codes,
                    request_path=formatted_path,
                    path_params=path_params,
                    query_params=query_params,
                    body=body,
                    response_body=response_body,
                    error_type="validation_error",
                )
                # Add validation errors to the failure message
                base_msg = failure.format_message()
                validation_msg = "\n\nValidation Errors:\n" + "\n".join(f"  - {err}" for err in validation_errors)
                raise AssertionError(base_msg + validation_msg)

    async def test_route_async(self, route: RouteInfo) -> dict[str, Any]:
        """Test a single route asynchronously.

        Args:
            route: The route to test.

        Returns:
            Test result dictionary.
        """
        try:
            test_func = self.create_test(route)
            test_func()
            return {"route": str(route), "passed": True, "error": None}
        except Exception as e:
            return {"route": str(route), "passed": False, "error": str(e)}

    async def test_all_routes(self, routes: list[RouteInfo]) -> list[dict[str, Any]]:
        """Test all routes.

        Args:
            routes: List of routes to test.

        Returns:
            List of test results.
        """
        results = []
        for route in routes:
            result = await self.test_route_async(route)
            results.append(result)
        return results
