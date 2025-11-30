"""Integration tests for pytest-routes plugin."""

from __future__ import annotations

import pytest

from pytest_routes.config import RouteTestConfig
from pytest_routes.discovery import get_extractor
from pytest_routes.execution.runner import RouteTestFailure, RouteTestRunner


class TestEndToEndRouteDiscovery:
    """End-to-end tests for route discovery."""

    def test_litestar_discovery_and_filtering(self, litestar_app):
        """Test complete discovery and filtering workflow for Litestar."""
        # Extract routes
        extractor = get_extractor(litestar_app)
        routes = extractor.extract_routes(litestar_app)

        # Apply config filtering
        config = RouteTestConfig(
            exclude_patterns=["/health"],
            methods=["GET", "POST"],
        )

        filtered = []
        for route in routes:
            if not any(m in config.methods for m in route.methods):
                continue
            excluded = any(route.path == p or route.path.startswith(p.rstrip("*")) for p in config.exclude_patterns)
            if excluded:
                continue
            filtered.append(route)

        # Verify filtering worked
        assert len(filtered) > 0
        assert not any(r.path == "/health" for r in filtered)

    def test_starlette_discovery_and_filtering(self, starlette_app):
        """Test complete discovery and filtering workflow for Starlette."""
        extractor = get_extractor(starlette_app)
        routes = extractor.extract_routes(starlette_app)

        config = RouteTestConfig(methods=["GET"])
        filtered = [r for r in routes if any(m in config.methods for m in r.methods)]

        assert len(filtered) > 0

    def test_fastapi_discovery_and_filtering(self, fastapi_app):
        """Test complete discovery and filtering workflow for FastAPI."""
        extractor = get_extractor(fastapi_app)
        routes = extractor.extract_routes(fastapi_app)

        config = RouteTestConfig(include_patterns=["/users*"])
        filtered = [r for r in routes if any(r.path.startswith(p.rstrip("*")) for p in config.include_patterns)]

        assert all("users" in r.path for r in filtered)


class TestEndToEndRouteExecution:
    """End-to-end tests for route execution."""

    @pytest.mark.asyncio
    async def test_successful_route_execution(self, litestar_app):
        """Test successful execution of a route."""
        config = RouteTestConfig(max_examples=3)
        runner = RouteTestRunner(litestar_app, config)

        extractor = get_extractor(litestar_app)
        routes = extractor.extract_routes(litestar_app)

        # Find root route
        root_route = next((r for r in routes if r.path == "/" and "GET" in r.methods), None)
        assert root_route is not None

        result = await runner.test_route_async(root_route)
        assert result["passed"] is True

    @pytest.mark.asyncio
    async def test_route_with_path_params(self, litestar_app):
        """Test execution of a route with path parameters."""
        config = RouteTestConfig(max_examples=3)
        runner = RouteTestRunner(litestar_app, config)

        extractor = get_extractor(litestar_app)
        routes = extractor.extract_routes(litestar_app)

        # Find user route
        user_route = next((r for r in routes if "user_id" in r.path and "GET" in r.methods), None)
        assert user_route is not None

        result = await runner.test_route_async(user_route)
        assert result["passed"] is True

    @pytest.mark.asyncio
    async def test_multiple_routes_execution(self, litestar_app):
        """Test execution of multiple routes."""
        config = RouteTestConfig(
            max_examples=2,
            exclude_patterns=["/health"],
        )
        runner = RouteTestRunner(litestar_app, config)

        extractor = get_extractor(litestar_app)
        routes = extractor.extract_routes(litestar_app)

        # Filter GET routes only for this test
        get_routes = [r for r in routes if "GET" in r.methods and r.path != "/health"]

        results = await runner.test_all_routes(get_routes[:2])
        assert len(results) == 2
        assert all(r["passed"] for r in results)


class TestRouteTestFailure:
    """Tests for RouteTestFailure error formatting."""

    def test_failure_format_basic(self):
        """Test basic failure message formatting."""
        failure = RouteTestFailure(
            route_path="/users/{user_id}",
            method="GET",
            status_code=500,
            expected_codes=[200, 201, 204],
            request_path="/users/123",
        )

        message = failure.format_message()

        assert "ROUTE TEST FAILURE" in message
        assert "GET" in message
        assert "/users/{user_id}" in message
        assert "500" in message

    def test_failure_format_with_params(self):
        """Test failure message with path parameters."""
        failure = RouteTestFailure(
            route_path="/users/{user_id}",
            method="GET",
            status_code=500,
            expected_codes=[200],
            request_path="/users/123",
            path_params={"user_id": 123},
        )

        message = failure.format_message()

        assert "Path Parameters" in message
        assert "user_id" in message
        assert "123" in message

    def test_failure_format_with_body(self):
        """Test failure message with request body."""
        failure = RouteTestFailure(
            route_path="/users",
            method="POST",
            status_code=422,
            expected_codes=[200, 201],
            request_path="/users",
            body={"name": "test", "email": "test@example.com"},
        )

        message = failure.format_message()

        assert "Request Body" in message
        assert "name" in message
        assert "email" in message

    def test_failure_format_with_response_body(self):
        """Test failure message with response body."""
        failure = RouteTestFailure(
            route_path="/users",
            method="POST",
            status_code=400,
            expected_codes=[200],
            request_path="/users",
            response_body='{"error": "Invalid input"}',
        )

        message = failure.format_message()

        assert "Response Body" in message
        assert "Invalid input" in message

    def test_failure_format_truncates_long_response(self):
        """Test that long response bodies are truncated."""
        long_response = "x" * 1000

        failure = RouteTestFailure(
            route_path="/users",
            method="GET",
            status_code=500,
            expected_codes=[200],
            request_path="/users",
            response_body=long_response,
        )

        message = failure.format_message()

        assert "..." in message
        assert len(message) < len(long_response)


class TestPluginConfiguration:
    """Tests for plugin configuration integration."""

    def test_config_from_defaults(self):
        """Test default configuration values."""
        config = RouteTestConfig()

        assert config.max_examples == 100
        assert config.timeout_per_route == 30.0
        assert config.fail_on_5xx is True
        assert "GET" in config.methods

    def test_config_with_custom_values(self):
        """Test configuration with custom values."""
        config = RouteTestConfig(
            max_examples=50,
            timeout_per_route=10.0,
            include_patterns=["/api/*"],
            exclude_patterns=["/internal/*"],
            methods=["GET", "POST"],
            fail_on_5xx=False,
        )

        assert config.max_examples == 50
        assert config.timeout_per_route == 10.0
        assert "/api/*" in config.include_patterns
        assert "/internal/*" in config.exclude_patterns
        assert config.fail_on_5xx is False

    def test_config_allowed_status_codes(self):
        """Test allowed status codes configuration."""
        config = RouteTestConfig(
            allowed_status_codes=[200, 201, 204, 400, 404],
        )

        assert 200 in config.allowed_status_codes
        assert 201 in config.allowed_status_codes
        assert 500 not in config.allowed_status_codes


class TestFrameworkAutoDetection:
    """Tests for framework auto-detection."""

    def test_litestar_detection(self, litestar_app):
        """Test Litestar app detection."""
        extractor = get_extractor(litestar_app)
        assert extractor.supports(litestar_app)
        assert "Litestar" in type(extractor).__name__

    def test_starlette_detection(self, starlette_app):
        """Test Starlette app detection."""
        extractor = get_extractor(starlette_app)
        assert extractor.supports(starlette_app)
        assert "Starlette" in type(extractor).__name__

    def test_fastapi_detection(self, fastapi_app):
        """Test FastAPI app detection (uses Starlette extractor)."""
        extractor = get_extractor(fastapi_app)
        assert extractor.supports(fastapi_app)
        # FastAPI uses Starlette extractor
        assert "Starlette" in type(extractor).__name__
