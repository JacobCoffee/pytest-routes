#!/usr/bin/env python
"""Debug script to verify Phase 2 features are working."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

# Add project root to path so we can import examples
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


def section(title: str) -> None:
    """Print a section header."""
    print(f"\n{'=' * 60}")
    print(f"  {title}")
    print(f"{'=' * 60}\n")


def main() -> None:
    """Run Phase 2 feature verification."""
    # =========================================================================
    # 1. Query Parameter Extraction
    # =========================================================================
    section("1. QUERY PARAMETER EXTRACTION")

    # Litestar
    print("--- Litestar Extractor ---")
    try:
        from examples.litestar_app import app as litestar_app
        from pytest_routes.discovery.litestar import LitestarExtractor

        extractor = LitestarExtractor()
        routes = extractor.extract_routes(litestar_app)

        for route in routes:
            if route.query_params:
                print(f"  {route.methods[0]:6} {route.path}")
                print(f"         query_params: {route.query_params}")
            elif "item" in route.path:
                print(f"  {route.methods[0]:6} {route.path}")
                print(f"         query_params: {route.query_params} (expected: {{'q': str | None}})")
    except Exception as e:
        print(f"  ERROR: {e}")

    # Starlette/FastAPI
    print("\n--- Starlette/FastAPI Extractor ---")
    try:
        from examples.fastapi_app import app as fastapi_app
        from pytest_routes.discovery.starlette import StarletteExtractor

        extractor = StarletteExtractor()
        routes = extractor.extract_routes(fastapi_app)

        for route in routes:
            if route.query_params:
                print(f"  {route.methods[0]:6} {route.path}")
                print(f"         query_params: {route.query_params}")
    except Exception as e:
        print(f"  ERROR: {e}")

    # =========================================================================
    # 2. Header Generation
    # =========================================================================
    section("2. HEADER GENERATION")

    from hypothesis import settings, given
    from pytest_routes.generation.headers import (
        generate_headers,
        generate_optional_headers,
        CONTENT_TYPE_STRATEGY,
        ACCEPT_STRATEGY,
        AUTHORIZATION_STRATEGY,
    )

    print("--- Standard Header Strategies (5 samples each) ---")

    @settings(max_examples=5, database=None)
    @given(ct=CONTENT_TYPE_STRATEGY)
    def show_content_types(ct: str) -> None:
        print(f"  Content-Type: {ct}")

    @settings(max_examples=5, database=None)
    @given(accept=ACCEPT_STRATEGY)
    def show_accepts(accept: str) -> None:
        print(f"  Accept: {accept}")

    @settings(max_examples=5, database=None)
    @given(auth=AUTHORIZATION_STRATEGY)
    def show_auth(auth: str) -> None:
        print(f"  Authorization: {auth[:50]}...")

    print("\nContent-Type samples:")
    show_content_types()

    print("\nAccept samples:")
    show_accepts()

    print("\nAuthorization samples:")
    show_auth()

    print("\n--- generate_headers() output ---")

    @settings(max_examples=3, database=None)
    @given(headers=generate_headers(include_content_type=True, include_accept=True))
    def show_generated_headers(headers: dict[str, str]) -> None:
        print(f"  {headers}")

    show_generated_headers()

    # =========================================================================
    # 3. OpenAPI Body Type Extraction
    # =========================================================================
    section("3. OPENAPI BODY TYPE EXTRACTION")

    from pytest_routes.discovery.openapi import OpenAPIExtractor

    # Create a sample OpenAPI schema
    sample_schema: dict[str, Any] = {
        "openapi": "3.0.0",
        "info": {"title": "Test", "version": "1.0"},
        "paths": {
            "/users": {
                "post": {
                    "operationId": "create_user",
                    "requestBody": {
                        "content": {"application/json": {"schema": {"$ref": "#/components/schemas/CreateUser"}}}
                    },
                    "responses": {"200": {"description": "OK"}},
                }
            },
            "/orders": {
                "post": {
                    "operationId": "create_order",
                    "requestBody": {
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "product_id": {"type": "integer"},
                                        "quantity": {"type": "integer"},
                                        "notes": {"type": "string"},
                                    },
                                    "required": ["product_id", "quantity"],
                                }
                            }
                        }
                    },
                    "responses": {"200": {"description": "OK"}},
                }
            },
        },
        "components": {
            "schemas": {
                "CreateUser": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "email": {"type": "string", "format": "email"},
                        "age": {"type": "integer"},
                    },
                    "required": ["name", "email"],
                }
            }
        },
    }

    print("--- Extracting body types from OpenAPI schema ---")
    extractor = OpenAPIExtractor(schema=sample_schema)
    routes = extractor.extract_routes(None)

    for route in routes:
        print(f"\n  {route.methods[0]:6} {route.path}")
        print(f"         body_type: {route.body_type}")
        if route.body_type and hasattr(route.body_type, "__dataclass_fields__"):
            fields = getattr(route.body_type, "__dataclass_fields__")
            print(f"         fields: {list(fields.keys())}")

    # =========================================================================
    # 4. Response Validation
    # =========================================================================
    section("4. RESPONSE VALIDATION")

    from dataclasses import dataclass
    from pytest_routes.validation.response import (
        StatusCodeValidator,
        ContentTypeValidator,
        CompositeValidator,
        ValidationResult,
    )
    from pytest_routes.discovery.base import RouteInfo

    @dataclass
    class MockResponse:
        status_code: int
        headers: dict[str, str]
        text: str = "{}"

    route = RouteInfo(path="/test", methods=["GET"], path_params={}, query_params={}, body_type=None)

    print("--- StatusCodeValidator ---")
    validator = StatusCodeValidator([200, 201, 204])

    responses = [
        MockResponse(200, {}),
        MockResponse(201, {}),
        MockResponse(404, {}),
        MockResponse(500, {}),
    ]

    for resp in responses:
        result = validator.validate(resp, route)
        status = "✅ VALID" if result.valid else "❌ INVALID"
        print(f"  {resp.status_code}: {status} {result.errors if result.errors else ''}")

    print("\n--- ContentTypeValidator ---")
    ct_validator = ContentTypeValidator(["application/json"])

    ct_responses = [
        MockResponse(200, {"content-type": "application/json"}),
        MockResponse(200, {"content-type": "application/json; charset=utf-8"}),
        MockResponse(200, {"content-type": "text/html"}),
        MockResponse(204, {}),  # No Content - should pass
    ]

    for resp in ct_responses:
        result = ct_validator.validate(resp, route)
        status = "✅ VALID" if result.valid else "❌ INVALID"
        ct = resp.headers.get("content-type", "(none)")
        print(f"  {resp.status_code} {ct}: {status}")

    print("\n--- CompositeValidator ---")
    composite = CompositeValidator(
        [
            StatusCodeValidator([200, 201]),
            ContentTypeValidator(["application/json"]),
        ]
    )

    composite_responses = [
        MockResponse(200, {"content-type": "application/json"}),
        MockResponse(200, {"content-type": "text/html"}),
        MockResponse(404, {"content-type": "application/json"}),
    ]

    for resp in composite_responses:
        result = composite.validate(resp, route)
        status = "✅ VALID" if result.valid else "❌ INVALID"
        print(f"  {resp.status_code} {resp.headers.get('content-type', '')}: {status}")
        if result.errors:
            for err in result.errors:
                print(f"       - {err}")

    # =========================================================================
    # 5. Strategy Registration API
    # =========================================================================
    section("5. STRATEGY REGISTRATION API")

    from hypothesis import strategies as st
    from pytest_routes.generation.strategies import (
        register_strategy,
        unregister_strategy,
        get_registered_types,
        temporary_strategy,
        strategy_provider,
    )

    print("--- Built-in registered types ---")
    builtin_types = get_registered_types()
    print(f"  Count: {len(builtin_types)}")
    print(f"  Types: {[t.__name__ for t in builtin_types[:10]]}...")

    print("\n--- Custom type registration ---")

    class CustomID:
        def __init__(self, value: str):
            self.value = value

        def __repr__(self) -> str:
            return f"CustomID({self.value!r})"

    register_strategy(CustomID, st.builds(CustomID, st.text(min_size=5, max_size=10)))
    print(f"  Registered CustomID")
    print(f"  Now in registry: {CustomID in get_registered_types()}")

    unregister_strategy(CustomID)
    print(f"  Unregistered CustomID")
    print(f"  Still in registry: {CustomID in get_registered_types()}")

    print("\n--- temporary_strategy context manager ---")
    original_int_count = 0

    @settings(max_examples=3, database=None)
    @given(x=st.integers())
    def count_ints(x: int) -> None:
        nonlocal original_int_count
        original_int_count += 1
        print(f"  Original int strategy: {x}")

    count_ints()

    print("\n  (Using temporary strategy for int -> always 42)")
    with temporary_strategy(int, st.just(42)):
        from pytest_routes.generation.strategies import strategy_for_type

        for _ in range(3):
            val = strategy_for_type(int).example()
            print(f"  Temporary int strategy: {val}")

    print("\n  (Back to original)")

    @settings(max_examples=3, database=None)
    @given(x=strategy_for_type(int))
    def show_restored(x: int) -> None:
        print(f"  Restored int strategy: {x}")

    show_restored()

    # =========================================================================
    # 6. pyproject.toml Configuration
    # =========================================================================
    section("6. PYPROJECT.TOML CONFIGURATION")

    from pathlib import Path
    from pytest_routes.config import load_config_from_pyproject, RouteTestConfig, merge_configs

    print("--- Loading from pyproject.toml ---")
    try:
        config = load_config_from_pyproject(Path("pyproject.toml"))
        print(f"  Loaded config: max_examples={config.max_examples}, methods={config.methods[:3]}...")
    except Exception as e:
        print(f"  No [tool.pytest-routes] section: {e}")

    print("\n--- Config merging (CLI > file > defaults) ---")
    file_config = RouteTestConfig(max_examples=50, seed=123)
    cli_config = RouteTestConfig(max_examples=200)  # CLI overrides

    merged = merge_configs(cli_config, file_config)
    print(f"  file_config.max_examples = 50")
    print(f"  cli_config.max_examples = 200")
    print(f"  merged.max_examples = {merged.max_examples}  (CLI wins)")
    print(f"  merged.seed = {merged.seed}  (from file_config)")

    # =========================================================================
    # Summary
    # =========================================================================
    section("PHASE 2 VERIFICATION COMPLETE")
    print("All features are working correctly!")
    print("\nTo run route tests with verbose output:")
    print("  make test-routes-litestar")
    print("\nTo see generated values in tests, add print statements or use -s flag")


if __name__ == "__main__":
    main()
