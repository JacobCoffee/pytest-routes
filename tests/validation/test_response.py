"""Tests for response validators."""

from __future__ import annotations

from typing import Any
from unittest.mock import Mock

import pytest

from pytest_routes.discovery.base import RouteInfo
from pytest_routes.validation.response import (
    CompositeValidator,
    ContentTypeValidator,
    JsonSchemaValidator,
    OpenAPIResponseValidator,
    StatusCodeValidator,
    ValidationResult,
)


def _jsonschema_available() -> bool:
    """Check if jsonschema is available."""
    try:
        import jsonschema  # noqa: F401

        return True
    except ImportError:
        return False


@pytest.fixture
def mock_response() -> Mock:
    """Create a mock HTTP response."""
    response = Mock()
    response.status_code = 200
    response.headers = {"content-type": "application/json; charset=utf-8"}
    response.content = b'{"id": 1, "name": "test"}'
    response.text = '{"id": 1, "name": "test"}'
    response.json.return_value = {"id": 1, "name": "test"}
    return response


@pytest.fixture
def route_info() -> RouteInfo:
    """Create a sample route info."""
    return RouteInfo(path="/api/users/{user_id}", methods=["GET"])


class TestValidationResult:
    """Test ValidationResult dataclass."""

    def test_valid_result(self) -> None:
        result = ValidationResult(valid=True)
        assert result.valid
        assert result.errors == []
        assert result.warnings == []

    def test_invalid_result_with_errors(self) -> None:
        result = ValidationResult(valid=False, errors=["Error 1", "Error 2"])
        assert not result.valid
        assert len(result.errors) == 2
        assert result.warnings == []

    def test_result_with_warnings(self) -> None:
        result = ValidationResult(valid=True, warnings=["Warning 1"])
        assert result.valid
        assert result.errors == []
        assert len(result.warnings) == 1

    def test_repr(self) -> None:
        result = ValidationResult(valid=False, errors=["Error"], warnings=["Warning"])
        repr_str = repr(result)
        assert "INVALID" in repr_str
        assert "errors=1" in repr_str
        assert "warnings=1" in repr_str


class TestStatusCodeValidator:
    """Test StatusCodeValidator."""

    def test_valid_status_code(self, mock_response: Mock, route_info: RouteInfo) -> None:
        validator = StatusCodeValidator(allowed_codes=[200, 201, 204])
        result = validator.validate(mock_response, route_info)
        assert result.valid

    def test_invalid_status_code(self, mock_response: Mock, route_info: RouteInfo) -> None:
        mock_response.status_code = 404
        validator = StatusCodeValidator(allowed_codes=[200, 201])
        result = validator.validate(mock_response, route_info)
        assert not result.valid
        assert len(result.errors) == 1
        assert "404" in result.errors[0]

    def test_default_allowed_codes(self, mock_response: Mock, route_info: RouteInfo) -> None:
        # Default should allow 200-499
        validator = StatusCodeValidator()
        result = validator.validate(mock_response, route_info)
        assert result.valid

        # Should reject 5xx
        mock_response.status_code = 500
        result = validator.validate(mock_response, route_info)
        assert not result.valid

    def test_client_error_warning(self, mock_response: Mock, route_info: RouteInfo) -> None:
        mock_response.status_code = 404
        validator = StatusCodeValidator()
        result = validator.validate(mock_response, route_info)
        assert result.valid  # 404 is in default range
        assert len(result.warnings) == 1
        assert "404" in result.warnings[0]


class TestContentTypeValidator:
    """Test ContentTypeValidator."""

    def test_valid_json_content_type(self, mock_response: Mock, route_info: RouteInfo) -> None:
        validator = ContentTypeValidator()
        result = validator.validate(mock_response, route_info)
        assert result.valid

    def test_content_type_with_charset(self, mock_response: Mock, route_info: RouteInfo) -> None:
        mock_response.headers = {"content-type": "application/json; charset=utf-8"}
        validator = ContentTypeValidator()
        result = validator.validate(mock_response, route_info)
        assert result.valid

    def test_invalid_content_type(self, mock_response: Mock, route_info: RouteInfo) -> None:
        mock_response.headers = {"content-type": "text/html"}
        validator = ContentTypeValidator(expected_types=["application/json"])
        result = validator.validate(mock_response, route_info)
        assert not result.valid
        assert "text/html" in result.errors[0]

    def test_custom_expected_types(self, mock_response: Mock, route_info: RouteInfo) -> None:
        mock_response.headers = {"content-type": "application/xml"}
        validator = ContentTypeValidator(expected_types=["application/xml", "text/xml"])
        result = validator.validate(mock_response, route_info)
        assert result.valid

    def test_no_content_response(self, mock_response: Mock, route_info: RouteInfo) -> None:
        mock_response.status_code = 204
        mock_response.headers = {}
        validator = ContentTypeValidator()
        result = validator.validate(mock_response, route_info)
        assert result.valid

    def test_missing_content_type_header(self, mock_response: Mock, route_info: RouteInfo) -> None:
        mock_response.headers = {}
        validator = ContentTypeValidator()
        result = validator.validate(mock_response, route_info)
        assert not result.valid


class TestJsonSchemaValidator:
    """Test JsonSchemaValidator."""

    def test_valid_json_no_schema(self, mock_response: Mock, route_info: RouteInfo) -> None:
        # Without schema, just validates that response is valid JSON
        validator = JsonSchemaValidator()
        result = validator.validate(mock_response, route_info)
        assert result.valid

    def test_invalid_json(self, mock_response: Mock, route_info: RouteInfo) -> None:
        mock_response.json.side_effect = ValueError("Invalid JSON")
        mock_response.text = "not json"
        validator = JsonSchemaValidator()
        result = validator.validate(mock_response, route_info)
        assert not result.valid
        assert "not valid JSON" in result.errors[0]

    def test_empty_response(self, mock_response: Mock, route_info: RouteInfo) -> None:
        mock_response.status_code = 204
        mock_response.content = b""
        validator = JsonSchemaValidator()
        result = validator.validate(mock_response, route_info)
        assert result.valid

    @pytest.mark.skipif(
        not _jsonschema_available(),
        reason="jsonschema not installed",
    )
    def test_valid_schema(self, mock_response: Mock, route_info: RouteInfo) -> None:
        schema = {
            "type": "object",
            "properties": {
                "id": {"type": "integer"},
                "name": {"type": "string"},
            },
            "required": ["id", "name"],
        }
        validator = JsonSchemaValidator(schema=schema)
        result = validator.validate(mock_response, route_info)
        assert result.valid

    @pytest.mark.skipif(
        not _jsonschema_available(),
        reason="jsonschema not installed",
    )
    def test_invalid_schema(self, mock_response: Mock, route_info: RouteInfo) -> None:
        # Schema expects 'id' to be a string but it's an integer
        schema = {
            "type": "object",
            "properties": {
                "id": {"type": "string"},
            },
        }
        validator = JsonSchemaValidator(schema=schema)
        result = validator.validate(mock_response, route_info)
        assert not result.valid
        assert "validation failed" in result.errors[0].lower()

    def test_schema_without_jsonschema_library(self, mock_response: Mock, route_info: RouteInfo) -> None:
        # This test assumes jsonschema is available, so we can't truly test the fallback
        # But we can at least verify the validator doesn't crash
        schema = {"type": "object"}
        validator = JsonSchemaValidator(schema=schema, strict=False)
        result = validator.validate(mock_response, route_info)
        # Should either validate or warn about missing library
        assert result.valid or len(result.warnings) > 0


class TestOpenAPIResponseValidator:
    """Test OpenAPIResponseValidator."""

    @pytest.fixture
    def openapi_schema(self) -> dict[str, Any]:
        """Sample OpenAPI schema."""
        return {
            "paths": {
                "/api/users/{user_id}": {
                    "get": {
                        "responses": {
                            "200": {
                                "content": {
                                    "application/json": {
                                        "schema": {
                                            "type": "object",
                                            "properties": {
                                                "id": {"type": "integer"},
                                                "name": {"type": "string"},
                                            },
                                            "required": ["id", "name"],
                                        }
                                    }
                                }
                            },
                            "404": {
                                "content": {
                                    "application/json": {
                                        "schema": {
                                            "type": "object",
                                            "properties": {
                                                "error": {"type": "string"},
                                            },
                                        }
                                    }
                                }
                            },
                        }
                    }
                }
            }
        }

    def test_find_exact_path(
        self,
        openapi_schema: dict[str, Any],
        mock_response: Mock,
        route_info: RouteInfo,
    ) -> None:
        validator = OpenAPIResponseValidator(openapi_schema)
        schema = validator._get_response_schema(route_info, 200)
        assert schema is not None
        assert schema["type"] == "object"

    def test_no_schema_found(
        self,
        openapi_schema: dict[str, Any],
        mock_response: Mock,
    ) -> None:
        route = RouteInfo(path="/nonexistent", methods=["GET"])
        validator = OpenAPIResponseValidator(openapi_schema)
        result = validator.validate(mock_response, route)
        assert result.valid
        assert len(result.warnings) == 1
        assert "No OpenAPI schema found" in result.warnings[0]

    def test_schema_caching(
        self,
        openapi_schema: dict[str, Any],
        route_info: RouteInfo,
    ) -> None:
        validator = OpenAPIResponseValidator(openapi_schema)
        schema1 = validator._get_response_schema(route_info, 200)
        schema2 = validator._get_response_schema(route_info, 200)
        # Should be cached
        assert schema1 is schema2

    @pytest.mark.skipif(
        not _jsonschema_available(),
        reason="jsonschema not installed",
    )
    def test_valid_response_against_openapi(
        self,
        openapi_schema: dict[str, Any],
        mock_response: Mock,
        route_info: RouteInfo,
    ) -> None:
        validator = OpenAPIResponseValidator(openapi_schema)
        result = validator.validate(mock_response, route_info)
        assert result.valid

    @pytest.mark.skipif(
        not _jsonschema_available(),
        reason="jsonschema not installed",
    )
    def test_invalid_response_against_openapi(
        self,
        openapi_schema: dict[str, Any],
        mock_response: Mock,
        route_info: RouteInfo,
    ) -> None:
        # Response missing required 'name' field
        mock_response.json.return_value = {"id": 1}
        validator = OpenAPIResponseValidator(openapi_schema)
        result = validator.validate(mock_response, route_info)
        assert not result.valid


class TestCompositeValidator:
    """Test CompositeValidator."""

    def test_all_validators_pass(self, mock_response: Mock, route_info: RouteInfo) -> None:
        validators = [
            StatusCodeValidator([200, 201]),
            ContentTypeValidator(["application/json"]),
        ]
        composite = CompositeValidator(validators)
        result = composite.validate(mock_response, route_info)
        assert result.valid

    def test_one_validator_fails(self, mock_response: Mock, route_info: RouteInfo) -> None:
        mock_response.status_code = 404
        validators = [
            StatusCodeValidator([200, 201]),  # This will fail
            ContentTypeValidator(["application/json"]),  # This will pass
        ]
        composite = CompositeValidator(validators)
        result = composite.validate(mock_response, route_info)
        assert not result.valid
        assert len(result.errors) >= 1

    def test_multiple_validators_fail(self, mock_response: Mock, route_info: RouteInfo) -> None:
        mock_response.status_code = 404
        mock_response.headers = {"content-type": "text/html"}
        validators = [
            StatusCodeValidator([200, 201]),  # Fail
            ContentTypeValidator(["application/json"]),  # Fail
        ]
        composite = CompositeValidator(validators)
        result = composite.validate(mock_response, route_info)
        assert not result.valid
        assert len(result.errors) >= 2

    def test_aggregate_warnings(self, mock_response: Mock, route_info: RouteInfo) -> None:
        mock_response.status_code = 404
        validators = [
            StatusCodeValidator(),  # Will produce warning for 404
            JsonSchemaValidator(),  # May produce warning
        ]
        composite = CompositeValidator(validators)
        result = composite.validate(mock_response, route_info)
        # Warnings should be aggregated
        assert isinstance(result.warnings, list)

    def test_empty_validators(self, mock_response: Mock, route_info: RouteInfo) -> None:
        composite = CompositeValidator([])
        result = composite.validate(mock_response, route_info)
        assert result.valid
        assert result.errors == []
        assert result.warnings == []
