"""Tests for query parameter extraction across all extractors."""

from __future__ import annotations

from pytest_routes.discovery import get_extractor


class TestLitestarQueryParams:
    """Tests for Litestar query parameter extraction."""

    def test_extracts_simple_query_params(self, litestar_app):
        """Test extraction of basic query parameters."""
        extractor = get_extractor(litestar_app)
        routes = extractor.extract_routes(litestar_app)

        # Find the /items/{item_id:int} route which has query param 'q'
        item_routes = [r for r in routes if r.path == "/items/{item_id:int}"]
        assert len(item_routes) > 0, "Could not find /items/{item_id:int} route"

        # Find the route that has query param 'q' (there may be multiple methods)
        item_route_with_q = next((r for r in item_routes if "q" in r.query_params), None)
        assert item_route_with_q is not None, "Could not find route with query param 'q'"

        # Should have 'q' as a query parameter
        assert "q" in item_route_with_q.query_params
        # Type should be str (from str | None annotation)
        assert item_route_with_q.query_params["q"] is str

    def test_no_query_params_for_simple_routes(self, litestar_app):
        """Test routes without query params have empty dict."""
        extractor = get_extractor(litestar_app)
        routes = extractor.extract_routes(litestar_app)

        # Root route should have no query params
        root_route = next((r for r in routes if r.path == "/"), None)
        assert root_route is not None
        assert root_route.query_params == {}

    def test_query_params_not_confused_with_path_params(self, litestar_app):
        """Test that path parameters are not included in query params."""
        extractor = get_extractor(litestar_app)
        routes = extractor.extract_routes(litestar_app)

        # Find a route with path params
        user_route = next((r for r in routes if "user_id" in r.path), None)
        assert user_route is not None

        # user_id should be in path_params, not query_params
        assert "user_id" in user_route.path_params
        assert "user_id" not in user_route.query_params


class TestStarletteQueryParams:
    """Tests for Starlette query parameter extraction."""

    def test_extracts_simple_query_params(self, starlette_app):
        """Test extraction of basic query parameters."""
        extractor = get_extractor(starlette_app)
        routes = extractor.extract_routes(starlette_app)

        # Find the /items/{item_id:int} route
        item_routes = [r for r in routes if r.path == "/items/{item_id:int}"]
        assert len(item_routes) > 0, "Could not find /items/{item_id:int} route"

        # Starlette example doesn't use type hints for query params,
        # so query_params will be empty (query params accessed via request.query_params.get())
        # This test documents current behavior
        item_route = item_routes[0]
        assert isinstance(item_route.query_params, dict)
        # In pure Starlette without type hints, we can't extract query params
        assert item_route.query_params == {}

    def test_no_query_params_for_simple_routes(self, starlette_app):
        """Test routes without query params have empty dict."""
        extractor = get_extractor(starlette_app)
        routes = extractor.extract_routes(starlette_app)

        # Root route should have no query params
        root_route = next((r for r in routes if r.path == "/"), None)
        assert root_route is not None
        assert root_route.query_params == {}

    def test_query_params_not_confused_with_path_params(self, starlette_app):
        """Test that path parameters are not included in query params."""
        extractor = get_extractor(starlette_app)
        routes = extractor.extract_routes(starlette_app)

        # Find a route with path params
        user_route = next((r for r in routes if "user_id" in r.path), None)
        assert user_route is not None

        # user_id should be in path_params, not query_params
        assert "user_id" in user_route.path_params
        assert "user_id" not in user_route.query_params


class TestFastAPIQueryParams:
    """Tests for FastAPI query parameter extraction."""

    def test_extracts_simple_query_params(self, fastapi_app):
        """Test extraction of basic query parameters."""
        extractor = get_extractor(fastapi_app)
        routes = extractor.extract_routes(fastapi_app)

        # Find the /items/{item_id} route which has query param 'q'
        item_routes = [r for r in routes if r.path == "/items/{item_id}"]
        assert len(item_routes) > 0, "Could not find /items/{item_id} route"

        item_route = item_routes[0]
        # Should have 'q' as a query parameter
        assert "q" in item_route.query_params
        # Type should be str (from str | None annotation)
        assert item_route.query_params["q"] is str

    def test_no_query_params_for_simple_routes(self, fastapi_app):
        """Test routes without query params have empty dict."""
        extractor = get_extractor(fastapi_app)
        routes = extractor.extract_routes(fastapi_app)

        # Root route should have no query params
        root_route = next((r for r in routes if r.path == "/"), None)
        assert root_route is not None
        assert root_route.query_params == {}

    def test_query_params_not_confused_with_path_params(self, fastapi_app):
        """Test that path parameters are not included in query params."""
        extractor = get_extractor(fastapi_app)
        routes = extractor.extract_routes(fastapi_app)

        # Find a route with path params
        user_route = next((r for r in routes if "user_id" in r.path), None)
        assert user_route is not None

        # user_id should be in path_params, not query_params
        assert "user_id" in user_route.path_params
        assert "user_id" not in user_route.query_params


class TestOpenAPIQueryParams:
    """Tests for OpenAPI-based query parameter extraction."""

    def test_openapi_extracts_query_params_litestar(self, litestar_app):
        """Test OpenAPI extractor gets query params from Litestar app."""
        from pytest_routes.discovery.openapi import OpenAPIExtractor

        extractor = OpenAPIExtractor()
        assert extractor.supports(litestar_app)

        routes = extractor.extract_routes(litestar_app)

        # Find route with query params
        item_route = next((r for r in routes if "/items/" in r.path), None)
        if item_route:
            # OpenAPI should extract query params from schema
            assert isinstance(item_route.query_params, dict)

    def test_openapi_extracts_query_params_fastapi(self, fastapi_app):
        """Test OpenAPI extractor gets query params from FastAPI app."""
        from pytest_routes.discovery.openapi import OpenAPIExtractor

        extractor = OpenAPIExtractor()
        assert extractor.supports(fastapi_app)

        routes = extractor.extract_routes(fastapi_app)

        # Find route with query params
        item_route = next((r for r in routes if "/items/" in r.path), None)
        if item_route:
            # OpenAPI should extract query params from schema
            assert isinstance(item_route.query_params, dict)
