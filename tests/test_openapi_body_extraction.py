"""Tests for OpenAPI body type extraction."""

from __future__ import annotations

from dataclasses import MISSING, fields, is_dataclass

import pytest

from pytest_routes.discovery.openapi import OpenAPIExtractor


@pytest.fixture
def sample_openapi_schema():
    """Sample OpenAPI schema with various request body types."""
    return {
        "openapi": "3.0.0",
        "info": {"title": "Test API", "version": "1.0.0"},
        "paths": {
            "/users": {
                "post": {
                    "operationId": "create_user",
                    "requestBody": {
                        "required": True,
                        "content": {"application/json": {"schema": {"$ref": "#/components/schemas/UserCreate"}}},
                    },
                }
            },
            "/items": {
                "post": {
                    "operationId": "create_item",
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "name": {"type": "string"},
                                        "price": {"type": "number"},
                                        "in_stock": {"type": "boolean"},
                                    },
                                    "required": ["name", "price"],
                                }
                            }
                        },
                    },
                }
            },
            "/events": {
                "post": {
                    "operationId": "create_event",
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "event_id": {"type": "string", "format": "uuid"},
                                        "scheduled_date": {"type": "string", "format": "date"},
                                        "start_time": {"type": "string", "format": "date-time"},
                                    },
                                }
                            }
                        },
                    },
                }
            },
            "/tags": {
                "post": {
                    "operationId": "create_tags",
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "array",
                                    "items": {"type": "string"},
                                }
                            }
                        },
                    },
                }
            },
            "/status": {
                "post": {
                    "operationId": "update_status",
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "string",
                                    "enum": ["active", "inactive", "pending"],
                                }
                            }
                        },
                    },
                }
            },
            "/nested": {
                "post": {
                    "operationId": "create_nested",
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "name": {"type": "string"},
                                        "metadata": {
                                            "type": "object",
                                            "properties": {
                                                "version": {"type": "integer"},
                                                "author": {"type": "string"},
                                            },
                                        },
                                    },
                                }
                            }
                        },
                    },
                }
            },
        },
        "components": {
            "schemas": {
                "UserCreate": {
                    "type": "object",
                    "properties": {
                        "username": {"type": "string"},
                        "email": {"type": "string", "format": "email"},
                        "age": {"type": "integer"},
                        "is_active": {"type": "boolean"},
                    },
                    "required": ["username", "email"],
                }
            }
        },
    }


class TestOpenAPIBodyExtraction:
    """Tests for OpenAPI request body type extraction."""

    def test_extracts_body_type_from_ref(self, sample_openapi_schema):
        """Test extracting body type from $ref."""
        extractor = OpenAPIExtractor(schema=sample_openapi_schema)
        routes = extractor.extract_routes(None)

        user_route = next(r for r in routes if r.path == "/users")
        assert user_route.body_type is not None
        assert is_dataclass(user_route.body_type)

        # Check fields
        field_dict = {f.name: f.type for f in fields(user_route.body_type)}
        assert "username" in field_dict
        assert "email" in field_dict
        assert "age" in field_dict
        assert "is_active" in field_dict

        # Check required vs optional
        field_names_with_defaults = {f.name for f in fields(user_route.body_type) if f.default is not MISSING}
        assert "age" in field_names_with_defaults  # Optional field
        assert "is_active" in field_names_with_defaults  # Optional field

    def test_extracts_inline_object_body_type(self, sample_openapi_schema):
        """Test extracting inline object schema as body type."""
        extractor = OpenAPIExtractor(schema=sample_openapi_schema)
        routes = extractor.extract_routes(None)

        item_route = next(r for r in routes if r.path == "/items")
        assert item_route.body_type is not None
        assert is_dataclass(item_route.body_type)

        # Check fields
        field_dict = {f.name: f.type for f in fields(item_route.body_type)}
        assert "name" in field_dict
        assert "price" in field_dict
        assert "in_stock" in field_dict

        # Check types
        assert field_dict["name"] == str
        assert field_dict["price"] == float

    def test_extracts_format_types(self, sample_openapi_schema):
        """Test extracting format-specific types (uuid, date, datetime)."""
        extractor = OpenAPIExtractor(schema=sample_openapi_schema)
        routes = extractor.extract_routes(None)

        event_route = next(r for r in routes if r.path == "/events")
        assert event_route.body_type is not None
        assert is_dataclass(event_route.body_type)

        # Check format types
        field_dict = {f.name: f.type for f in fields(event_route.body_type)}
        # UUID format should map to uuid.UUID
        assert "UUID" in str(field_dict["event_id"])
        # Date format should map to date
        assert "date" in str(field_dict["scheduled_date"])
        # Date-time format should map to datetime
        assert "datetime" in str(field_dict["start_time"])

    def test_extracts_array_body_type(self, sample_openapi_schema):
        """Test extracting array types."""
        extractor = OpenAPIExtractor(schema=sample_openapi_schema)
        routes = extractor.extract_routes(None)

        tags_route = next(r for r in routes if r.path == "/tags")
        assert tags_route.body_type is not None
        # Array type should be list[str]
        assert "list" in str(tags_route.body_type).lower()

    def test_extracts_enum_body_type(self, sample_openapi_schema):
        """Test extracting enum types."""
        extractor = OpenAPIExtractor(schema=sample_openapi_schema)
        routes = extractor.extract_routes(None)

        status_route = next(r for r in routes if r.path == "/status")
        assert status_route.body_type is not None
        # Enum should map to str type
        assert status_route.body_type == str

    def test_extracts_nested_object_body_type(self, sample_openapi_schema):
        """Test extracting nested object schemas."""
        extractor = OpenAPIExtractor(schema=sample_openapi_schema)
        routes = extractor.extract_routes(None)

        nested_route = next(r for r in routes if r.path == "/nested")
        assert nested_route.body_type is not None
        assert is_dataclass(nested_route.body_type)

        # Check fields
        field_dict = {f.name: f.type for f in fields(nested_route.body_type)}
        assert "name" in field_dict
        assert "metadata" in field_dict

        # Metadata should also be a dataclass
        metadata_type = field_dict["metadata"]
        # Should be a dataclass or union with dataclass
        # (since it's optional, it might be Union[GeneratedModel, None])
        assert is_dataclass(metadata_type) or any(is_dataclass(arg) for arg in getattr(metadata_type, "__args__", []))

    def test_no_body_type_for_get_request(self):
        """Test that GET requests don't have body types."""
        schema = {
            "openapi": "3.0.0",
            "info": {"title": "Test API", "version": "1.0.0"},
            "paths": {
                "/users": {
                    "get": {
                        "operationId": "list_users",
                    }
                }
            },
        }

        extractor = OpenAPIExtractor(schema=schema)
        routes = extractor.extract_routes(None)

        user_route = next(r for r in routes if r.path == "/users")
        assert user_route.body_type is None

    def test_type_caching(self, sample_openapi_schema):
        """Test that referenced types are cached."""
        extractor = OpenAPIExtractor(schema=sample_openapi_schema)
        routes = extractor.extract_routes(None)

        # UserCreate should be in the cache
        assert "UserCreate" in extractor._type_cache

        # Multiple requests to the same schema should return the same type
        user_route = next(r for r in routes if r.path == "/users")
        cached_type = extractor._type_cache["UserCreate"]
        assert user_route.body_type == cached_type


class TestOpenAPIReferenceResolution:
    """Tests for $ref resolution."""

    def test_resolves_component_schema_ref(self):
        """Test resolving $ref to components/schemas."""
        schema = {
            "openapi": "3.0.0",
            "info": {"title": "Test API", "version": "1.0.0"},
            "paths": {},
            "components": {
                "schemas": {
                    "User": {
                        "type": "object",
                        "properties": {"name": {"type": "string"}},
                    }
                }
            },
        }

        extractor = OpenAPIExtractor(schema=schema)
        resolved = extractor._resolve_ref("#/components/schemas/User", schema)

        assert resolved["type"] == "object"
        assert "name" in resolved["properties"]

    def test_raises_on_external_ref(self):
        """Test that external refs raise an error."""
        schema = {"openapi": "3.0.0", "info": {"title": "Test API", "version": "1.0.0"}}

        extractor = OpenAPIExtractor(schema=schema)

        with pytest.raises(ValueError, match="Only local references are supported"):
            extractor._resolve_ref("https://example.com/schema.json", schema)

    def test_raises_on_missing_ref(self):
        """Test that missing refs raise an error."""
        schema = {
            "openapi": "3.0.0",
            "info": {"title": "Test API", "version": "1.0.0"},
            "components": {"schemas": {}},
        }

        extractor = OpenAPIExtractor(schema=schema)

        with pytest.raises(ValueError, match="Reference not found"):
            extractor._resolve_ref("#/components/schemas/MissingSchema", schema)


class TestBackwardCompatibility:
    """Tests for backward compatibility with simple _schema_to_type."""

    def test_simple_schema_to_type_still_works(self):
        """Test that the simple _schema_to_type method still works."""
        extractor = OpenAPIExtractor()

        assert extractor._schema_to_type({"type": "string"}) == str
        assert extractor._schema_to_type({"type": "integer"}) == int
        assert extractor._schema_to_type({"type": "number"}) == float
        assert extractor._schema_to_type({"type": "boolean"}) == bool
        assert extractor._schema_to_type({"type": "array"}) == list
        assert extractor._schema_to_type({"type": "object"}) == dict
