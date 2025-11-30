"""Response validation for pytest-routes."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Protocol

if TYPE_CHECKING:
    from pytest_routes.discovery.base import RouteInfo

# HTTP status code constants
HTTP_STATUS_NO_CONTENT = 204
HTTP_STATUS_CLIENT_ERROR_MIN = 400
HTTP_STATUS_SERVER_ERROR_MIN = 500

# Display limits
MAX_DISPLAYED_CODES = 10


@dataclass
class ValidationResult:
    """Result of response validation.

    Attributes:
        valid: Whether the validation passed.
        errors: List of validation error messages.
        warnings: List of validation warning messages.
    """

    valid: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def __repr__(self) -> str:
        status = "VALID" if self.valid else "INVALID"
        error_count = len(self.errors)
        warning_count = len(self.warnings)
        return f"ValidationResult({status}, errors={error_count}, warnings={warning_count})"


class ResponseValidator(Protocol):
    """Protocol for response validation.

    Response validators check that HTTP responses conform to expected
    schemas, status codes, content types, and other criteria.
    """

    def validate(self, response: Any, route: RouteInfo) -> ValidationResult:
        """Validate a response against expected schema.

        Args:
            response: The HTTP response object (typically httpx.Response).
            route: The route information for context.

        Returns:
            ValidationResult indicating success or failure with details.
        """
        ...


class StatusCodeValidator:
    """Validate response status codes.

    Checks that the response status code is within the allowed set.
    This is the most basic form of response validation.

    Example:
        >>> validator = StatusCodeValidator(allowed_codes=[200, 201, 204])
        >>> result = validator.validate(response, route)
        >>> assert result.valid
    """

    def __init__(self, allowed_codes: list[int] | None = None) -> None:
        """Initialize status code validator.

        Args:
            allowed_codes: List of allowed HTTP status codes.
                Defaults to all 2xx-4xx codes (200-499).
        """
        self.allowed_codes = allowed_codes or list(range(200, 500))

    def validate(self, response: Any, route: RouteInfo) -> ValidationResult:
        """Validate response status code.

        Args:
            response: The HTTP response object.
            route: The route information.

        Returns:
            ValidationResult with status code validation.
        """
        status_code = response.status_code

        if status_code not in self.allowed_codes:
            max_display = MAX_DISPLAYED_CODES
            codes_display = (
                f"{self.allowed_codes[:max_display]}{'...' if len(self.allowed_codes) > max_display else ''}"
            )
            return ValidationResult(
                valid=False,
                errors=[f"Status code {status_code} not in allowed codes. Expected one of: {codes_display}"],
            )

        # Add warning for client errors (4xx)
        warnings = []
        if HTTP_STATUS_CLIENT_ERROR_MIN <= status_code < HTTP_STATUS_SERVER_ERROR_MIN:
            warnings.append(f"Client error status code: {status_code}")

        return ValidationResult(valid=True, warnings=warnings)


class ContentTypeValidator:
    """Validate response content type.

    Checks that the response Content-Type header matches expected types.
    Useful for ensuring APIs return the correct media type.

    Example:
        >>> validator = ContentTypeValidator(expected_types=["application/json"])
        >>> result = validator.validate(response, route)
        >>> assert result.valid
    """

    def __init__(self, expected_types: list[str] | None = None) -> None:
        """Initialize content type validator.

        Args:
            expected_types: List of expected content types (e.g., ["application/json"]).
                Defaults to ["application/json"].
        """
        self.expected_types = expected_types or ["application/json"]

    def validate(self, response: Any, route: RouteInfo) -> ValidationResult:
        """Validate response content type.

        Args:
            response: The HTTP response object.
            route: The route information.

        Returns:
            ValidationResult with content type validation.
        """
        content_type = response.headers.get("content-type", "")

        # Handle empty responses (like 204 No Content)
        if not content_type and response.status_code == HTTP_STATUS_NO_CONTENT:
            return ValidationResult(valid=True)

        # Extract media type (ignore charset, boundary, etc.)
        media_type = content_type.split(";")[0].strip()

        # Check if media type matches any expected type
        for expected in self.expected_types:
            if media_type == expected or media_type.startswith(expected):
                return ValidationResult(valid=True)

        return ValidationResult(
            valid=False,
            errors=[
                f"Content-Type '{media_type}' not in expected types: {self.expected_types}. Full header: {content_type}"
            ],
        )


class JsonSchemaValidator:
    """Validate response body against JSON schema.

    Uses jsonschema library (if available) to validate response bodies
    against a provided JSON Schema. Falls back to basic JSON validation
    if jsonschema is not installed.

    Example:
        >>> schema = {"type": "object", "properties": {"id": {"type": "integer"}}}
        >>> validator = JsonSchemaValidator(schema=schema)
        >>> result = validator.validate(response, route)
        >>> assert result.valid
    """

    def __init__(self, schema: dict[str, Any] | None = None, *, strict: bool = False) -> None:
        """Initialize JSON schema validator.

        Args:
            schema: JSON Schema dictionary. If None, only validates JSON parsing.
            strict: If True, require jsonschema library. If False, degrade gracefully.
        """
        self.schema = schema
        self.strict = strict
        self._validator = None

        # Try to import jsonschema
        if schema is not None:
            try:
                from jsonschema import Draft7Validator  # type: ignore[import-not-found]

                self._validator = Draft7Validator(schema)
            except ImportError as e:
                if strict:
                    msg = "jsonschema library required for schema validation. Install with: pip install jsonschema"
                    raise ImportError(msg) from e

    def validate(self, response: Any, route: RouteInfo) -> ValidationResult:
        """Validate response body against JSON schema.

        Args:
            response: The HTTP response object.
            route: The route information.

        Returns:
            ValidationResult with JSON schema validation.
        """
        # Skip validation for empty responses
        if response.status_code == HTTP_STATUS_NO_CONTENT or not response.content:
            return ValidationResult(valid=True)

        # Try to parse JSON
        try:
            data = response.json()
        except (json.JSONDecodeError, ValueError) as e:
            return ValidationResult(
                valid=False,
                errors=[f"Response body is not valid JSON: {e}"],
            )

        # If no schema provided, just check that it's valid JSON
        if self.schema is None:
            return ValidationResult(valid=True)

        # If jsonschema is available, validate against schema
        if self._validator is not None:
            errors = []
            for error in self._validator.iter_errors(data):
                # Format the error message with path
                path = ".".join(str(p) for p in error.path) if error.path else "root"
                errors.append(f"{path}: {error.message}")

            if errors:
                return ValidationResult(
                    valid=False,
                    errors=[f"JSON Schema validation failed: {'; '.join(errors)}"],
                )

            return ValidationResult(valid=True)

        # Fallback: just check basic type
        return ValidationResult(
            valid=True,
            warnings=["jsonschema library not available, skipping schema validation"],
        )


class OpenAPIResponseValidator:
    """Validate response against OpenAPI schema.

    Extracts expected response schemas from an OpenAPI specification
    and validates responses against them. This is the most comprehensive
    form of validation for OpenAPI-based APIs.

    Example:
        >>> validator = OpenAPIResponseValidator(openapi_schema=openapi_spec)
        >>> result = validator.validate(response, route)
        >>> assert result.valid
    """

    def __init__(self, openapi_schema: dict[str, Any]) -> None:
        """Initialize OpenAPI response validator.

        Args:
            openapi_schema: Full OpenAPI specification dictionary.
        """
        self.schema = openapi_schema
        self._path_cache: dict[tuple[str, str, int], dict[str, Any] | None] = {}

    def _find_path_in_openapi(self, path: str) -> str | None:
        """Find matching path in OpenAPI spec.

        OpenAPI paths may contain path parameters like /users/{user_id}
        while the actual route might be /users/123.

        Args:
            path: The actual route path (may contain {param} syntax).

        Returns:
            The matching OpenAPI path or None.
        """
        paths = self.schema.get("paths", {})

        # First try exact match
        if path in paths:
            return path

        # Try pattern matching for parameterized paths
        for openapi_path in paths:
            # Convert OpenAPI path pattern to regex
            # {param} -> [^/]+
            pattern = re.sub(r"\{[^}]+\}", r"[^/]+", openapi_path)
            pattern = f"^{pattern}$"

            if re.match(pattern, path):
                return openapi_path

        return None

    def _get_response_schema(self, route: RouteInfo, status_code: int) -> dict[str, Any] | None:
        """Get expected response schema from OpenAPI spec.

        Args:
            route: The route information.
            status_code: The HTTP status code to look up.

        Returns:
            JSON Schema for the response or None if not found.
        """
        cache_key = (route.path, route.methods[0], status_code)
        if cache_key in self._path_cache:
            return self._path_cache[cache_key]

        # Find the matching path in OpenAPI spec
        openapi_path = self._find_path_in_openapi(route.path)
        if not openapi_path:
            self._path_cache[cache_key] = None
            return None

        # Get the method spec
        method = route.methods[0].lower()
        path_item = self.schema["paths"].get(openapi_path, {})
        operation = path_item.get(method, {})

        if not operation:
            self._path_cache[cache_key] = None
            return None

        # Get response spec for this status code
        responses = operation.get("responses", {})

        # Try exact status code first
        response_spec = responses.get(str(status_code))

        # Fall back to wildcard patterns (2XX, 4XX, etc.)
        if not response_spec:
            status_pattern = f"{str(status_code)[0]}XX"
            response_spec = responses.get(status_pattern)

        # Fall back to default
        if not response_spec:
            response_spec = responses.get("default")

        if not response_spec:
            self._path_cache[cache_key] = None
            return None

        # Extract schema from content
        content = response_spec.get("content", {})

        # Try application/json first
        json_content = content.get("application/json", {})
        schema = json_content.get("schema")

        if not schema:
            # Try any other content type
            for content_type_data in content.values():
                schema = content_type_data.get("schema")
                if schema:
                    break

        self._path_cache[cache_key] = schema
        return schema

    def validate(self, response: Any, route: RouteInfo) -> ValidationResult:
        """Validate response against OpenAPI schema.

        Args:
            response: The HTTP response object.
            route: The route information.

        Returns:
            ValidationResult with OpenAPI validation.
        """
        status_code = response.status_code

        # Get expected schema for this response
        schema = self._get_response_schema(route, status_code)

        if schema is None:
            return ValidationResult(
                valid=True,
                warnings=[f"No OpenAPI schema found for {route.methods[0]} {route.path} with status {status_code}"],
            )

        # Use JsonSchemaValidator to validate the response body
        validator = JsonSchemaValidator(schema=schema)
        return validator.validate(response, route)


class CompositeValidator:
    """Run multiple validators in sequence.

    Combines multiple validators into a single validator that runs all
    of them and aggregates their results. Useful for applying multiple
    validation rules to a single response.

    Example:
        >>> validators = [
        ...     StatusCodeValidator([200, 201]),
        ...     ContentTypeValidator(["application/json"]),
        ...     JsonSchemaValidator(schema=my_schema),
        ... ]
        >>> composite = CompositeValidator(validators)
        >>> result = composite.validate(response, route)
        >>> assert result.valid
    """

    def __init__(self, validators: list[ResponseValidator]) -> None:
        """Initialize composite validator.

        Args:
            validators: List of validators to run.
        """
        self.validators = validators

    def validate(self, response: Any, route: RouteInfo) -> ValidationResult:
        """Run all validators and aggregate results.

        Args:
            response: The HTTP response object.
            route: The route information.

        Returns:
            ValidationResult with aggregated errors and warnings.
        """
        all_errors: list[str] = []
        all_warnings: list[str] = []

        for validator in self.validators:
            result = validator.validate(response, route)
            all_errors.extend(result.errors)
            all_warnings.extend(result.warnings)

        return ValidationResult(
            valid=len(all_errors) == 0,
            errors=all_errors,
            warnings=all_warnings,
        )
