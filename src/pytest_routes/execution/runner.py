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
    from pytest_routes.auth.providers import AuthProvider
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
    request_headers: dict[str, str] = field(default_factory=dict)
    response_headers: dict[str, str] = field(default_factory=dict)
    auth_type: str | None = None

    def _format_expected_codes(self) -> str:
        """Format expected codes with truncation."""
        truncated = self.expected_codes[:_MAX_EXPECTED_CODES_DISPLAY]
        ellipsis = "..." if len(self.expected_codes) > _MAX_EXPECTED_CODES_DISPLAY else ""
        return f"  Expected: {truncated}{ellipsis}"

    def _base_lines(self) -> list[str]:
        """Build base error lines."""
        lines = [
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

        if self.auth_type:
            lines.append(f"  Auth: {self.auth_type}")

        return lines

    def _format_params_section(self, title: str, params: dict[str, Any]) -> list[str]:
        """Format a parameters section."""
        if not params:
            return []
        lines = ["", f"{title}:"]
        for key, value in params.items():
            lines.append(f"  {key}: {value!r}")
        return lines

    def _format_headers_section(self, title: str, headers: dict[str, str], limit: int | None = None) -> list[str]:
        """Format a headers section."""
        if not headers:
            return []
        lines = ["", f"{title}:"]
        items = list(headers.items())[:limit] if limit else list(headers.items())
        for key, val in items:
            display_val = val[:20] + "..." if key.lower() == "authorization" and len(val) > 20 else val
            lines.append(f"  {key}: {display_val}")
        return lines

    def _format_body_section(self) -> list[str]:
        """Format the request body section."""
        if self.body is None:
            return []
        lines = ["", "Request Body (shrunk example):"]
        try:
            body_str = json.dumps(self.body, indent=2, default=str)
            lines.extend(f"  {line}" for line in body_str.split("\n"))
        except (TypeError, ValueError):
            lines.append(f"  {self.body!r}")
        return lines

    def _format_response_body_section(self) -> list[str]:
        """Format the response body section."""
        if not self.response_body:
            return []
        lines = ["", "Response Body (truncated):"]
        truncated = self.response_body[:_MAX_RESPONSE_BODY_DISPLAY]
        if len(self.response_body) > _MAX_RESPONSE_BODY_DISPLAY:
            truncated += "..."
        lines.extend(f"  {line}" for line in truncated.split("\n"))
        return lines

    def format_message(self) -> str:
        """Format a detailed error message with shrunk example."""
        lines = self._base_lines()
        lines.extend(self._format_params_section("Path Parameters (shrunk example)", self.path_params))
        lines.extend(self._format_params_section("Query Parameters (shrunk example)", self.query_params))
        lines.extend(self._format_headers_section("Request Headers", self.request_headers))
        lines.extend(self._format_body_section())
        lines.extend(self._format_headers_section("Response Headers", self.response_headers, limit=10))
        lines.extend(self._format_response_body_section())
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

    def _get_auth_for_route(self, route: RouteInfo) -> AuthProvider | None:
        """Get the authentication provider for a route.

        Checks for route-specific auth override, then falls back to config auth.

        Args:
            route: The route to get auth for.

        Returns:
            AuthProvider if configured, None otherwise.
        """
        effective_config = self.config.get_effective_config_for_route(route.path)
        return effective_config.get("auth")

    def _get_auth_type_name(self, auth: AuthProvider | None) -> str | None:
        """Get a descriptive name for the auth type."""
        if auth is None:
            return None
        return type(auth).__name__

    def create_test(self, route: RouteInfo) -> Callable[[], None]:
        """Create a Hypothesis test for a route.

        Args:
            route: The route to test.

        Returns:
            A test function decorated with @given.
        """
        effective_config = self.config.get_effective_config_for_route(route.path)

        if effective_config.get("skip", False):

            def skipped_test() -> None:
                import pytest

                pytest.skip(f"Route {route.path} is configured to be skipped")

            return skipped_test

        max_examples = effective_config.get("max_examples", self.config.max_examples)
        path_strategy = generate_path_params(route.path_params, route.path)
        query_strategy = (
            st.fixed_dictionaries({name: strategy_for_type(typ) for name, typ in route.query_params.items()})
            if route.query_params
            else st.just({})
        )
        body_strategy = generate_body(route.body_type)

        runner = self
        auth = self._get_auth_for_route(route)

        @settings(
            max_examples=max_examples,
            suppress_health_check=[HealthCheck.too_slow],
            deadline=None,
        )
        @given(
            path_params=path_strategy,
            query_params=query_strategy,
            body=body_strategy,
        )
        def test_route(path_params: dict[str, Any], query_params: dict[str, Any], body: Any) -> None:
            formatted_path = format_path(route.path, path_params)

            auth_headers: dict[str, str] = {}
            auth_query_params: dict[str, str] = {}
            if auth:
                auth_headers = auth.get_headers()
                auth_query_params = auth.get_query_params()

            merged_query_params = {**query_params, **auth_query_params}

            if runner.config.verbose:
                _print_verbose_request(
                    method=route.methods[0],
                    path=formatted_path,
                    path_params=path_params,
                    query_params=merged_query_params,
                    body=body,
                )

            async def run_request() -> Any:
                return await runner.client.request(
                    method=route.methods[0],
                    path=formatted_path,
                    params=merged_query_params or None,
                    json=body if body is not None else None,
                    headers=auth_headers or None,
                    timeout=runner.config.timeout_per_route,
                )

            try:
                asyncio.get_running_loop()
                import concurrent.futures

                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(asyncio.run, run_request())
                    response = future.result()
            except RuntimeError:
                response = asyncio.run(run_request())

            if runner.config.verbose:
                _print_verbose_response(response)

            runner._validate_response_detailed(
                response=response,
                route=route,
                formatted_path=formatted_path,
                path_params=path_params,
                query_params=merged_query_params,
                body=body,
                request_headers=auth_headers,
                auth_type=runner._get_auth_type_name(auth),
            )

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
        request_headers: dict[str, str] | None = None,
        auth_type: str | None = None,
    ) -> None:
        """Validate response with detailed error reporting.

        Args:
            response: The HTTP response.
            route: The route that was tested.
            formatted_path: The actual request path.
            path_params: Path parameters used.
            query_params: Query parameters used.
            body: Request body used.
            request_headers: Headers that were sent with the request.
            auth_type: Type of authentication used.

        Raises:
            AssertionError: If validation fails with detailed error.
        """
        response_body = None
        with contextlib.suppress(Exception):
            response_body = response.text

        response_headers = {}
        with contextlib.suppress(Exception):
            response_headers = dict(response.headers)

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
                request_headers=request_headers or {},
                response_headers=response_headers,
                auth_type=auth_type,
            )
            raise AssertionError(failure.format_message())

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
                request_headers=request_headers or {},
                response_headers=response_headers,
                auth_type=auth_type,
            )
            raise AssertionError(failure.format_message())

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
                    request_headers=request_headers or {},
                    response_headers=response_headers,
                    auth_type=auth_type,
                )
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
