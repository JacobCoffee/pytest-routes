"""Tests for route test runner."""

from __future__ import annotations

import pytest

from pytest_routes.config import RouteTestConfig
from pytest_routes.discovery.base import RouteInfo
from pytest_routes.execution.runner import RouteTestRunner


class TestRouteTestRunner:
    """Tests for RouteTestRunner."""

    def test_runner_initialization(self, litestar_app):
        """Test runner initialization."""
        config = RouteTestConfig(max_examples=10)
        runner = RouteTestRunner(litestar_app, config)

        assert runner.app is litestar_app
        assert runner.config is config
        assert runner.client is not None

    def test_create_test_function(self, litestar_app):
        """Test creating a test function for a route."""
        config = RouteTestConfig(max_examples=5)
        runner = RouteTestRunner(litestar_app, config)

        route = RouteInfo(
            path="/",
            methods=["GET"],
            path_params={},
            query_params={},
        )

        test_func = runner.create_test(route)

        assert callable(test_func)
        assert "test_" in test_func.__name__
        assert test_func.__doc__ is not None

    def test_create_test_with_path_params(self, litestar_app):
        """Test creating a test for a route with path parameters."""
        config = RouteTestConfig(max_examples=5)
        runner = RouteTestRunner(litestar_app, config)

        route = RouteInfo(
            path="/users/{user_id:int}",
            methods=["GET"],
            path_params={"user_id": int},
            query_params={},
        )

        test_func = runner.create_test(route)

        assert callable(test_func)
        assert "user_id" in test_func.__name__ or "users" in test_func.__name__

    @pytest.mark.asyncio
    async def test_test_route_async(self, litestar_app):
        """Test async route testing."""
        config = RouteTestConfig(max_examples=3)
        runner = RouteTestRunner(litestar_app, config)

        route = RouteInfo(
            path="/",
            methods=["GET"],
            path_params={},
            query_params={},
        )

        result = await runner.test_route_async(route)

        assert "route" in result
        assert "passed" in result
        assert "error" in result

    @pytest.mark.asyncio
    async def test_test_all_routes(self, litestar_app):
        """Test testing all routes."""
        config = RouteTestConfig(max_examples=3)
        runner = RouteTestRunner(litestar_app, config)

        routes = [
            RouteInfo(path="/", methods=["GET"], path_params={}, query_params={}),
            RouteInfo(path="/health", methods=["GET"], path_params={}, query_params={}),
        ]

        results = await runner.test_all_routes(routes)

        assert len(results) == 2
        assert all("passed" in r for r in results)


class TestResponseValidation:
    """Tests for response validation."""

    def test_validate_5xx_fails(self, litestar_app):
        """Test that 5xx responses fail validation."""
        from unittest.mock import MagicMock

        config = RouteTestConfig(fail_on_5xx=True)
        runner = RouteTestRunner(litestar_app, config)

        mock_response = MagicMock()
        mock_response.status_code = 500

        route = RouteInfo(path="/", methods=["GET"], path_params={}, query_params={})

        with pytest.raises(AssertionError, match="5xx"):
            runner._validate_response(mock_response, route)

    def test_validate_5xx_allowed(self, litestar_app):
        """Test that 5xx responses pass when fail_on_5xx is False."""
        from unittest.mock import MagicMock

        config = RouteTestConfig(fail_on_5xx=False, allowed_status_codes=list(range(200, 600)))
        runner = RouteTestRunner(litestar_app, config)

        mock_response = MagicMock()
        mock_response.status_code = 500

        route = RouteInfo(path="/", methods=["GET"], path_params={}, query_params={})

        # Should not raise
        runner._validate_response(mock_response, route)

    def test_validate_unexpected_status(self, litestar_app):
        """Test that unexpected status codes fail validation."""
        from unittest.mock import MagicMock

        config = RouteTestConfig(allowed_status_codes=[200, 201])
        runner = RouteTestRunner(litestar_app, config)

        mock_response = MagicMock()
        mock_response.status_code = 418  # I'm a teapot

        route = RouteInfo(path="/", methods=["GET"], path_params={}, query_params={})

        with pytest.raises(AssertionError, match="unexpected status"):
            runner._validate_response(mock_response, route)


class TestTestNaming:
    """Tests for test function naming."""

    def test_test_name_includes_method(self, litestar_app):
        """Test that generated test name includes HTTP method."""
        config = RouteTestConfig(max_examples=1)
        runner = RouteTestRunner(litestar_app, config)

        route = RouteInfo(path="/users", methods=["POST"], path_params={}, query_params={})
        test_func = runner.create_test(route)

        assert "POST" in test_func.__name__

    def test_test_name_includes_path(self, litestar_app):
        """Test that generated test name includes sanitized path."""
        config = RouteTestConfig(max_examples=1)
        runner = RouteTestRunner(litestar_app, config)

        route = RouteInfo(path="/users/profile", methods=["GET"], path_params={}, query_params={})
        test_func = runner.create_test(route)

        assert "users" in test_func.__name__
        assert "profile" in test_func.__name__

    def test_test_docstring_descriptive(self, litestar_app):
        """Test that generated test has descriptive docstring."""
        config = RouteTestConfig(max_examples=1)
        runner = RouteTestRunner(litestar_app, config)

        route = RouteInfo(path="/users", methods=["GET"], path_params={}, query_params={})
        test_func = runner.create_test(route)

        assert "GET" in test_func.__doc__
        assert "/users" in test_func.__doc__
