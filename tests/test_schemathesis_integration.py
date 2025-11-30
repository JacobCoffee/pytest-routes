"""Tests for Schemathesis integration."""

from __future__ import annotations

from pytest_routes.discovery.base import RouteInfo
from pytest_routes.integrations.schemathesis import (
    SchemathesisAdapter,
    SchemathesisConfig,
    SchemathesisValidator,
    schemathesis_available,
)
from pytest_routes.validation.response import ValidationResult


class TestSchemathesisAvailable:
    """Tests for schemathesis_available function."""

    def test_schemathesis_available(self):
        result = schemathesis_available()
        assert result is True


class TestSchemathesisConfig:
    """Tests for SchemathesisConfig."""

    def test_default_values(self):
        config = SchemathesisConfig()
        assert config.enabled is False
        assert config.schema_path == "/openapi.json"
        assert config.validate_responses is True
        assert config.stateful == "none"
        assert "status_code_conformance" in config.checks
        assert "content_type_conformance" in config.checks
        assert "response_schema_conformance" in config.checks

    def test_custom_values(self):
        config = SchemathesisConfig(
            enabled=True,
            schema_path="/api/schema.json",
            validate_responses=False,
            stateful="links",
            checks=["status_code_conformance"],
        )
        assert config.enabled is True
        assert config.schema_path == "/api/schema.json"
        assert config.validate_responses is False
        assert config.stateful == "links"
        assert config.checks == ["status_code_conformance"]


class TestSchemathesisAdapter:
    """Tests for SchemathesisAdapter."""

    def test_initialization(self):
        app = object()
        adapter = SchemathesisAdapter(app)
        assert adapter.app is app
        assert adapter.schema_path == "/openapi.json"
        assert adapter.validate_responses is True

    def test_custom_initialization(self):
        app = object()
        adapter = SchemathesisAdapter(
            app,
            schema_path="/api/openapi.yaml",
            validate_responses=False,
            checks=["status_code_conformance"],
        )
        assert adapter.schema_path == "/api/openapi.yaml"
        assert adapter.validate_responses is False
        assert adapter.checks == ["status_code_conformance"]

    def test_available_property(self):
        adapter = SchemathesisAdapter(object())
        assert adapter.available is True

    def test_validate_response_when_disabled(self):
        adapter = SchemathesisAdapter(object(), validate_responses=False)
        route = RouteInfo(
            path="/users",
            methods=["GET"],
            path_params={},
            query_params={},
            body_type=None,
        )

        result = adapter.validate_response(object(), route)
        assert result.valid is True


class TestSchemathesisValidator:
    """Tests for SchemathesisValidator."""

    def test_initialization(self):
        adapter = SchemathesisAdapter(object())
        validator = SchemathesisValidator(adapter)
        assert validator.adapter is adapter
        assert validator.strict is False

    def test_strict_mode(self):
        adapter = SchemathesisAdapter(object())
        validator = SchemathesisValidator(adapter, strict=True)
        assert validator.strict is True

    def test_validate_with_available_adapter(self):
        adapter = SchemathesisAdapter(object(), validate_responses=False)
        validator = SchemathesisValidator(adapter)

        route = RouteInfo(
            path="/users",
            methods=["GET"],
            path_params={},
            query_params={},
            body_type=None,
        )

        result = validator.validate(object(), route)
        assert isinstance(result, ValidationResult)
        assert result.valid is True
