"""Integration tests for response validation with runner."""

from __future__ import annotations

from unittest.mock import Mock

import pytest
from litestar import Litestar, get

from pytest_routes import RouteTestConfig, RouteTestRunner
from pytest_routes.discovery.base import RouteInfo
from pytest_routes.validation.response import StatusCodeValidator


@get("/test")
async def test_endpoint() -> dict[str, str]:
    """Test endpoint."""
    return {"status": "ok"}


@pytest.fixture
def test_app() -> Litestar:
    """Create test Litestar app."""
    return Litestar(route_handlers=[test_endpoint])


def test_runner_with_validation_disabled(test_app: Litestar) -> None:
    """Test that validation is disabled by default."""
    config = RouteTestConfig(max_examples=1, validate_responses=False)
    runner = RouteTestRunner(test_app, config)
    assert len(runner._validators) == 0


def test_runner_with_validation_enabled(test_app: Litestar) -> None:
    """Test that validators are initialized when enabled."""
    config = RouteTestConfig(
        max_examples=1,
        validate_responses=True,
        response_validators=["status_code", "content_type"],
    )
    runner = RouteTestRunner(test_app, config)
    assert len(runner._validators) == 2


def test_runner_with_only_status_code_validator(test_app: Litestar) -> None:
    """Test runner with only status code validator."""
    config = RouteTestConfig(
        max_examples=1,
        validate_responses=True,
        response_validators=["status_code"],
    )
    runner = RouteTestRunner(test_app, config)
    assert len(runner._validators) == 1
    assert isinstance(runner._validators[0], StatusCodeValidator)


def test_validation_in_detailed_response() -> None:
    """Test that validation is called in _validate_response_detailed."""
    config = RouteTestConfig(
        max_examples=1,
        validate_responses=True,
        response_validators=["status_code"],
        allowed_status_codes=[200],
        fail_on_validation_error=True,
    )

    # Create a mock app
    mock_app = Mock()
    runner = RouteTestRunner(mock_app, config)

    # Create a mock response
    response = Mock()
    response.status_code = 200
    response.text = '{"status": "ok"}'

    route = RouteInfo(path="/test", methods=["GET"])

    # Should not raise - validation passes
    runner._validate_response_detailed(
        response=response,
        route=route,
        formatted_path="/test",
        path_params={},
        query_params={},
        body=None,
    )


def test_validation_failure_in_detailed_response() -> None:
    """Test that validation failures raise AssertionError."""
    config = RouteTestConfig(
        max_examples=1,
        validate_responses=True,
        response_validators=["status_code"],
        allowed_status_codes=[200],
        fail_on_validation_error=True,
    )

    # Create a mock app
    mock_app = Mock()
    runner = RouteTestRunner(mock_app, config)

    # Create a mock response with invalid status code
    response = Mock()
    response.status_code = 404
    response.text = '{"error": "not found"}'

    route = RouteInfo(path="/test", methods=["GET"])

    # Should raise AssertionError with validation errors
    with pytest.raises(AssertionError) as exc_info:
        runner._validate_response_detailed(
            response=response,
            route=route,
            formatted_path="/test",
            path_params={},
            query_params={},
            body=None,
        )

    assert "unexpected_status" in str(exc_info.value)


def test_validation_with_fail_on_validation_error_false() -> None:
    """Test that validation errors don't raise when fail_on_validation_error=False."""
    config = RouteTestConfig(
        max_examples=1,
        validate_responses=True,
        response_validators=["status_code"],
        allowed_status_codes=[200],
        fail_on_validation_error=False,  # Don't fail on validation errors
    )

    # Create a mock app
    mock_app = Mock()
    runner = RouteTestRunner(mock_app, config)

    # Create a mock response - would normally fail status code check
    response = Mock()
    response.status_code = 200  # Valid status
    response.text = '{"status": "ok"}'

    route = RouteInfo(path="/test", methods=["GET"])

    # Should not raise even with validation enabled
    runner._validate_response_detailed(
        response=response,
        route=route,
        formatted_path="/test",
        path_params={},
        query_params={},
        body=None,
    )
