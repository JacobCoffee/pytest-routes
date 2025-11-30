"""Schemathesis integration for pytest-routes.

Provides contract testing capabilities when OpenAPI schema is available.
Falls back gracefully when Schemathesis is not installed.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Callable

    from pytest_routes.discovery.base import RouteInfo
    from pytest_routes.validation.response import ValidationResult


def schemathesis_available() -> bool:
    """Check if Schemathesis is installed and available."""
    try:
        import schemathesis  # noqa: F401

        return True
    except ImportError:
        return False


@dataclass
class SchemathesisConfig:
    """Configuration for Schemathesis integration.

    Attributes:
        enabled: Whether Schemathesis mode is enabled.
        schema_path: Path to fetch OpenAPI schema from the app.
        validate_responses: Whether to validate response bodies against schema.
        stateful: Stateful testing mode ('none', 'links').
        checks: List of Schemathesis checks to run.
    """

    enabled: bool = False
    schema_path: str = "/openapi.json"
    validate_responses: bool = True
    stateful: str = "none"
    checks: list[str] = field(
        default_factory=lambda: [
            "status_code_conformance",
            "content_type_conformance",
            "response_schema_conformance",
        ]
    )


class SchemathesisAdapter:
    """Adapter for Schemathesis integration.

    Provides contract testing capabilities when OpenAPI schema is available.
    Falls back gracefully when Schemathesis is not installed.
    """

    def __init__(
        self,
        app: Any,
        schema_path: str = "/openapi.json",
        *,
        validate_responses: bool = True,
        checks: list[str] | None = None,
    ) -> None:
        """Initialize the Schemathesis adapter.

        Args:
            app: The ASGI application.
            schema_path: Path to the OpenAPI schema endpoint.
            validate_responses: Whether to validate response bodies.
            checks: List of Schemathesis checks to run.
        """
        self.app = app
        self.schema_path = schema_path
        self.validate_responses = validate_responses
        self.checks = checks or [
            "status_code_conformance",
            "content_type_conformance",
            "response_schema_conformance",
        ]
        self._schema: Any = None
        self._available = schemathesis_available()

    @property
    def available(self) -> bool:
        """Check if Schemathesis is installed."""
        return self._available

    def load_schema(self) -> Any:
        """Load OpenAPI schema via Schemathesis.

        Returns:
            The loaded Schemathesis schema object.

        Raises:
            ImportError: If Schemathesis is not installed.
            RuntimeError: If schema loading fails.
        """
        if not self._available:
            msg = "Schemathesis is not installed. Install with: pip install pytest-routes[schemathesis]"
            raise ImportError(msg)

        import schemathesis.openapi  # type: ignore[import-untyped]

        try:
            self._schema = schemathesis.openapi.from_asgi(self.schema_path, app=self.app)
            return self._schema
        except Exception as e:
            msg = f"Failed to load OpenAPI schema from {self.schema_path}: {e}"
            raise RuntimeError(msg) from e

    def get_schema(self) -> Any:
        """Get the loaded schema, loading it if necessary.

        Returns:
            The Schemathesis schema object.
        """
        if self._schema is None:
            self.load_schema()
        return self._schema

    def create_contract_test(self, route: RouteInfo) -> Callable | None:
        """Create Schemathesis-powered contract test for a route.

        Args:
            route: The route to create a test for.

        Returns:
            A test function or None if the route is not found in schema.
        """
        if not self._available:
            return None

        schema = self.get_schema()
        operation = self._find_operation(route)

        if not operation:
            return None

        app = self.app
        checks = self._get_check_functions()

        def test_contract() -> None:
            for case in schema[route.path][route.methods[0].lower()].as_strategy():

                @schema.given(case)
                def run_case(case: Any) -> None:
                    response = case.call_asgi(app=app)
                    for check in checks:
                        check(response, case)

                run_case()

        return test_contract

    def _find_operation(self, route: RouteInfo) -> Any | None:
        """Find matching operation in schema.

        Args:
            route: The route to find.

        Returns:
            The operation or None if not found.
        """
        schema = self.get_schema()

        try:
            path_item = schema[route.path]
            method = route.methods[0].lower()
            if hasattr(path_item, method):
                return getattr(path_item, method)
        except (KeyError, AttributeError):
            pass

        return None

    def _get_check_functions(self) -> list[Callable]:
        """Get Schemathesis check functions based on config.

        Returns:
            List of check functions to run.
        """
        if not self._available:
            return []

        from schemathesis.specs.openapi import checks as schemathesis_checks

        check_map = {
            "status_code_conformance": schemathesis_checks.status_code_conformance,
            "content_type_conformance": schemathesis_checks.content_type_conformance,
            "response_schema_conformance": schemathesis_checks.response_schema_conformance,
        }

        return [check_map[name] for name in self.checks if name in check_map]

    def validate_response(self, response: Any, route: RouteInfo) -> ValidationResult:
        """Validate response using Schemathesis.

        Args:
            response: The HTTP response object.
            route: The route information.

        Returns:
            ValidationResult with validation status.
        """
        from pytest_routes.validation.response import ValidationResult

        if not self._available:
            return ValidationResult(
                valid=True,
                warnings=["Schemathesis not installed, skipping schema validation"],
            )

        if not self.validate_responses:
            return ValidationResult(valid=True)

        errors: list[str] = []
        warnings: list[str] = []

        try:
            self.get_schema()
            operation = self._find_operation(route)

            if not operation:
                warnings.append(f"No schema found for {route.methods[0]} {route.path}")
                return ValidationResult(valid=True, warnings=warnings)

            checks = self._get_check_functions()
            check_errors = []
            for check in checks:
                try:
                    check(response, operation)
                except AssertionError as e:
                    check_errors.append(str(e))
            errors.extend(check_errors)

        except Exception as e:
            errors.append(f"Schemathesis validation error: {e}")

        return ValidationResult(
            valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
        )


class SchemathesisValidator:
    """Response validator using Schemathesis schema validation.

    This validator integrates with the existing validation framework
    to provide schema-based response validation.
    """

    def __init__(
        self,
        adapter: SchemathesisAdapter,
        *,
        strict: bool = False,
    ) -> None:
        """Initialize the Schemathesis validator.

        Args:
            adapter: The SchemathesisAdapter instance.
            strict: If True, fail when Schemathesis is not available.
        """
        self.adapter = adapter
        self.strict = strict

    def validate(self, response: Any, route: RouteInfo) -> ValidationResult:
        """Validate response against OpenAPI schema.

        Args:
            response: The HTTP response object.
            route: The route information.

        Returns:
            ValidationResult with validation status.
        """
        from pytest_routes.validation.response import ValidationResult

        if not self.adapter.available:
            if self.strict:
                return ValidationResult(
                    valid=False,
                    errors=["Schemathesis is required but not installed"],
                )
            return ValidationResult(
                valid=True,
                warnings=["Schemathesis not available, skipping schema validation"],
            )

        return self.adapter.validate_response(response, route)
