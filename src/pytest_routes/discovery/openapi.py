"""OpenAPI schema-based route extraction."""

from __future__ import annotations

import uuid
from dataclasses import make_dataclass
from datetime import date, datetime
from typing import Any, Union

from pytest_routes.discovery.base import RouteExtractor, RouteInfo

# Mapping of OpenAPI format strings to Python types
FORMAT_TYPE_MAP: dict[str, type] = {
    "date-time": datetime,
    "date": date,
    "uuid": uuid.UUID,
    "email": str,  # Could enhance with email validation strategy
    "uri": str,
    "hostname": str,
    "ipv4": str,
    "ipv6": str,
}


class OpenAPIExtractor(RouteExtractor):
    """Extract routes from an OpenAPI schema.

    This extractor provides framework-agnostic route discovery by parsing OpenAPI
    (Swagger) schemas. It supports both pre-loaded schemas and runtime schema
    extraction from Litestar and FastAPI applications.

    The extractor provides comprehensive type conversion from JSON Schema to Python
    types, including primitive types (string, integer, number, boolean), complex types
    (objects converted to dataclasses), container types (arrays with item types),
    reference resolution ($ref support), format-based types (date-time, uuid, email),
    and schema composition (allOf, oneOf, anyOf).

    Example:
        >>> from fastapi import FastAPI
        >>> from pydantic import BaseModel
        >>>
        >>> app = FastAPI()
        >>>
        >>> class User(BaseModel):
        ...     name: str
        ...     email: str
        >>>
        >>> @app.post("/users/{user_id}")
        >>> async def update_user(user_id: int, user: User):
        ...     return {"id": user_id, "name": user.name}
        >>>
        >>> extractor = OpenAPIExtractor()
        >>> routes = extractor.extract_routes(app)
        >>> route = routes[0]
        >>> route.path_params
        {'user_id': <class 'int'>}
        >>> route.body_type.__name__
        'User'

    Attributes:
        schema: Pre-loaded OpenAPI schema dict (optional)
        _type_cache: Cache of generated dataclass types by name
        _generated_type_counter: Counter for unique auto-generated type names

    Note:
        Caches generated dataclass types to avoid duplicates. Supports OpenAPI 3.0+
        schemas. Falls back to framework schema extraction if no schema provided.
    """

    def __init__(self, schema: dict[str, Any] | None = None) -> None:
        """Initialize the OpenAPI extractor with an optional pre-loaded schema.

        Args:
            schema: An optional pre-loaded OpenAPI schema dictionary. If not provided,
                the extractor will attempt to extract the schema from the application
                at runtime using framework-specific methods (Litestar's openapi_schema
                or FastAPI's openapi()).

        Example:
            >>> # Using pre-loaded schema
            >>> schema = {
            ...     "openapi": "3.0.0",
            ...     "paths": {
            ...         "/users/{user_id}": {
            ...             "get": {
            ...                 "parameters": [
            ...                     {"name": "user_id", "in": "path", "schema": {"type": "integer"}}
            ...                 ]
            ...             }
            ...         }
            ...     },
            ... }
            >>> extractor = OpenAPIExtractor(schema=schema)
            >>>
            >>> # Using runtime extraction
            >>> extractor = OpenAPIExtractor()
            >>> routes = extractor.extract_routes(app)  # Schema extracted from app
        """
        self.schema = schema
        self._type_cache: dict[str, type] = {}  # Cache for generated types
        self._generated_type_counter = 0  # Counter for unique generated type names

    def supports(self, app: Any) -> bool:
        """Check if an OpenAPI schema can be extracted from the application.

        This method checks if the extractor can work with the given application by:
            1. Checking if a pre-loaded schema was provided during initialization
            2. Checking if the app has an 'openapi_schema' attribute (Litestar)
            3. Checking if the app has an 'openapi' method (FastAPI)

        Args:
            app: The ASGI application to check for OpenAPI schema support.

        Returns:
            True if an OpenAPI schema is available or can be extracted, False otherwise.

        Example:
            >>> from fastapi import FastAPI
            >>> from litestar import Litestar
            >>>
            >>> # FastAPI support
            >>> fastapi_app = FastAPI()
            >>> extractor = OpenAPIExtractor()
            >>> extractor.supports(fastapi_app)
            True
            >>>
            >>> # Litestar support
            >>> litestar_app = Litestar(route_handlers=[])
            >>> extractor.supports(litestar_app)
            True
            >>>
            >>> # Pre-loaded schema
            >>> schema = {"openapi": "3.0.0", "paths": {}}
            >>> extractor_with_schema = OpenAPIExtractor(schema=schema)
            >>> extractor_with_schema.supports(None)  # Any app works with pre-loaded schema
            True

        Note:
            Always returns True if a schema was provided during initialization,
            regardless of the application type.
        """
        return bool(self.schema or hasattr(app, "openapi_schema") or hasattr(app, "openapi"))

    def extract_routes(self, app: Any) -> list[RouteInfo]:
        """Extract all routes from an OpenAPI schema.

        This method parses the OpenAPI schema's paths section and converts each
        operation into a RouteInfo object. It handles parameter extraction,
        request body type generation, and metadata extraction.

        Args:
            app: The ASGI application to extract routes from. If a pre-loaded schema
                was provided during initialization, this parameter is ignored and the
                pre-loaded schema is used instead.

        Returns:
            A list of RouteInfo objects containing complete route metadata:
            path (route path pattern), methods (HTTP method), name (operation ID),
            handler (always None for schema-based extraction), path_params (parameter
            name to type mapping), query_params (query parameter mapping), body_type
            (dataclass representing request body), tags (OpenAPI tags), deprecated
            (deprecation flag), and description (operation summary).

        Raises:
            ValueError: If no schema was provided and the app doesn't support
                OpenAPI schema extraction.

        Example:
            >>> from fastapi import FastAPI
            >>> from pydantic import BaseModel
            >>>
            >>> app = FastAPI()
            >>>
            >>> class CreateUser(BaseModel):
            ...     name: str
            ...     email: str
            >>>
            >>> @app.post("/users", tags=["users"], deprecated=False)
            >>> async def create_user(user: CreateUser):
            ...     return {"name": user.name}
            >>>
            >>> @app.get("/users/{user_id}", summary="Get a user")
            >>> async def get_user(user_id: int, include_posts: bool = False):
            ...     return {"id": user_id}
            >>>
            >>> extractor = OpenAPIExtractor()
            >>> routes = extractor.extract_routes(app)
            >>> len(routes)
            2
            >>> post_route = routes[0]
            >>> post_route.methods
            ['POST']
            >>> post_route.tags
            ['users']
            >>> post_route.body_type.__name__
            'CreateUser'
            >>> get_route = routes[1]
            >>> get_route.path_params
            {'user_id': <class 'int'>}
            >>> get_route.query_params
            {'include_posts': <class 'bool'>}
            >>> get_route.description
            'Get a user'

        Note:
            Only extracts standard HTTP methods (GET, POST, PUT, PATCH, DELETE).
            Schema references ($ref) are automatically resolved. Complex request
            body schemas are converted to dataclasses. Generated dataclass types
            are cached to avoid duplicates. Uses pre-loaded schema if available,
            otherwise extracts from app.
        """
        schema = self.schema or self._get_schema(app)
        routes: list[RouteInfo] = []

        for path, methods in schema.get("paths", {}).items():
            for method, operation in methods.items():
                method_upper = method.upper()
                if method_upper not in {"GET", "POST", "PUT", "PATCH", "DELETE"}:
                    continue

                routes.append(
                    RouteInfo(
                        path=path,
                        methods=[method_upper],
                        name=operation.get("operationId"),
                        handler=None,
                        path_params=self._extract_params(operation, "path", schema),
                        query_params=self._extract_params(operation, "query", schema),
                        body_type=self._extract_body_type(operation, schema),
                        tags=operation.get("tags", []),
                        deprecated=operation.get("deprecated", False),
                        description=operation.get("summary") or operation.get("description"),
                    )
                )

        return routes

    def _get_schema(self, app: Any) -> dict[str, Any]:
        """Extract OpenAPI schema from an app."""
        # Litestar
        if hasattr(app, "openapi_schema") and app.openapi_schema is not None:
            return app.openapi_schema.to_schema()

        # FastAPI
        if hasattr(app, "openapi"):
            return app.openapi()

        msg = "Cannot extract OpenAPI schema from app"
        raise ValueError(msg)

    def _extract_params(self, operation: dict[str, Any], location: str, full_schema: dict[str, Any]) -> dict[str, type]:
        """Extract parameters of a specific location from operation."""
        params: dict[str, type] = {}

        for param in operation.get("parameters", []):
            if param.get("in") == location:
                name = param.get("name")
                schema = param.get("schema", {})
                param_type = self._schema_to_type_complex(schema, full_schema)
                if name:
                    params[name] = param_type

        return params

    def _extract_body_type(self, operation: dict[str, Any], full_schema: dict[str, Any]) -> type | None:
        """Extract request body type from operation.

        Args:
            operation: OpenAPI operation object
            full_schema: Full OpenAPI schema for reference resolution

        Returns:
            Python type representing the request body, or None if no body
        """
        request_body = operation.get("requestBody", {})
        content = request_body.get("content", {})
        json_content = content.get("application/json", {})
        body_schema = json_content.get("schema", {})

        if not body_schema:
            return None

        # Handle $ref - preserve the ref name for caching
        if "$ref" in body_schema:
            ref_name = body_schema["$ref"].split("/")[-1]
            # Check cache first
            if ref_name in self._type_cache:
                return self._type_cache[ref_name]
            resolved_schema = self._resolve_ref(body_schema["$ref"], full_schema)
            # Use the ref name for caching
            return self._schema_to_dataclass(ref_name, resolved_schema, full_schema)

        return self._schema_to_type_complex(body_schema, full_schema)

    def _resolve_ref(self, ref: str, schema: dict[str, Any]) -> dict[str, Any]:
        """Resolve $ref to actual schema.

        Args:
            ref: Reference string (e.g., "#/components/schemas/User")
            schema: Full OpenAPI schema

        Returns:
            Resolved schema object
        """
        if not ref.startswith("#/"):
            msg = f"Only local references are supported: {ref}"
            raise ValueError(msg)

        # Split reference path (e.g., "#/components/schemas/User" -> ["components", "schemas", "User"])
        path_parts = ref[2:].split("/")

        # Navigate through schema
        current = schema
        for part in path_parts:
            if part not in current:
                msg = f"Reference not found: {ref}"
                raise ValueError(msg)
            current = current[part]

        return current

    def _schema_to_type(self, schema: dict[str, Any]) -> type:
        """Convert JSON schema to Python type (simple version for backward compatibility).

        Args:
            schema: JSON schema object

        Returns:
            Python type
        """
        schema_type = schema.get("type", "string")

        type_map: dict[str, type] = {
            "string": str,
            "integer": int,
            "number": float,
            "boolean": bool,
            "array": list,
            "object": dict,
        }

        return type_map.get(schema_type, str)

    def _schema_to_type_complex(self, schema: dict[str, Any], full_schema: dict[str, Any]) -> type:  # noqa: C901, PLR0911, PLR0912
        """Convert JSON schema to Python type with full support for complex types.

        Args:
            schema: JSON schema object
            full_schema: Full OpenAPI schema for reference resolution

        Returns:
            Python type (primitive, dataclass, or container type)
        """
        # Handle $ref
        if "$ref" in schema:
            ref_name = schema["$ref"].split("/")[-1]
            # Check cache first
            if ref_name in self._type_cache:
                return self._type_cache[ref_name]
            resolved_schema = self._resolve_ref(schema["$ref"], full_schema)
            # Pass the ref_name to _schema_to_dataclass for caching
            return self._schema_to_dataclass(ref_name, resolved_schema, full_schema)

        # Handle enum (use first enum type or string)
        if "enum" in schema:
            enum_values = schema["enum"]
            if enum_values:
                # Use type of first value if available
                first_val = enum_values[0]
                return type(first_val) if first_val is not None else str
            return str

        # Handle allOf (simplified: use first schema)
        if "allOf" in schema:
            all_schemas = schema["allOf"]
            if all_schemas:
                # Merge properties from all schemas (simplified)
                merged: dict[str, Any] = {"type": "object", "properties": {}}
                for sub_schema in all_schemas:
                    resolved = (
                        self._resolve_ref(sub_schema["$ref"], full_schema) if "$ref" in sub_schema else sub_schema
                    )
                    if "properties" in resolved:
                        merged["properties"].update(resolved["properties"])
                return self._schema_to_dataclass("AllOf", merged, full_schema)
            return dict

        # Handle oneOf/anyOf (simplified: use first schema)
        if "oneOf" in schema or "anyOf" in schema:
            schemas = schema.get("oneOf") or schema.get("anyOf", [])
            if schemas:
                first_schema = (
                    self._resolve_ref(schemas[0]["$ref"], full_schema) if "$ref" in schemas[0] else schemas[0]
                )
                return self._schema_to_type_complex(first_schema, full_schema)
            return dict

        schema_type = schema.get("type", "string")

        # Handle format
        if "format" in schema:
            format_type = FORMAT_TYPE_MAP.get(schema["format"])
            if format_type:
                return format_type

        # Handle array
        if schema_type == "array":
            items_schema = schema.get("items", {})
            if items_schema:
                item_type = self._schema_to_type_complex(items_schema, full_schema)
                return list[item_type]  # type: ignore[valid-type]
            return list

        # Handle object (create dataclass)
        if schema_type == "object":
            properties = schema.get("properties")
            if properties:
                # Generate a name from the schema title or a unique generated name
                if "title" in schema:
                    name = schema["title"]
                else:
                    self._generated_type_counter += 1
                    name = f"GeneratedModel{self._generated_type_counter}"
                return self._schema_to_dataclass(name, schema, full_schema)
            return dict

        # Handle primitives
        type_map: dict[str, type] = {
            "string": str,
            "integer": int,
            "number": float,
            "boolean": bool,
        }

        return type_map.get(schema_type, str)

    def _schema_to_dataclass(self, name: str, schema: dict[str, Any], full_schema: dict[str, Any]) -> type:
        """Create a dataclass from JSON schema.

        Args:
            name: Name for the generated dataclass
            schema: JSON schema object
            full_schema: Full OpenAPI schema for reference resolution

        Returns:
            Dynamically generated dataclass type
        """
        # Check cache
        if name in self._type_cache:
            return self._type_cache[name]

        properties = schema.get("properties", {})
        required = set(schema.get("required", []))

        # Build field definitions
        fields: list[tuple[str, type] | tuple[str, type, Any]] = []
        for field_name, field_schema in properties.items():
            field_type = self._schema_to_type_complex(field_schema, full_schema)
            is_required = field_name in required

            if is_required:
                fields.append((field_name, field_type))
            else:
                # Optional fields get None default
                optional_type = Union[field_type, None]  # type: ignore[valid-type]  # noqa: UP007
                fields.append((field_name, optional_type, None))  # type: ignore[arg-type]

        # Create dataclass
        dataclass_type = make_dataclass(name, fields if fields else [])

        # Cache the type
        self._type_cache[name] = dataclass_type

        return dataclass_type
