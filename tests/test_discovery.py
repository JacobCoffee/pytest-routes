"""Tests for route discovery."""

from __future__ import annotations

from pytest_routes.discovery import get_extractor


class TestLitestarExtractor:
    """Tests for Litestar route extraction."""

    def test_supports_litestar_app(self, litestar_app):
        """Test that extractor supports Litestar apps."""
        extractor = get_extractor(litestar_app)
        assert extractor.supports(litestar_app)

    def test_extracts_routes(self, litestar_app):
        """Test route extraction from Litestar app."""
        extractor = get_extractor(litestar_app)
        routes = extractor.extract_routes(litestar_app)

        assert len(routes) >= 3

        paths = [r.path for r in routes]
        assert "/" in paths
        assert "/users/{user_id:int}" in paths
        assert "/health" in paths

    def test_extracts_path_params(self, litestar_app):
        """Test path parameter extraction."""
        extractor = get_extractor(litestar_app)
        routes = extractor.extract_routes(litestar_app)

        user_route = next(r for r in routes if "user_id" in r.path)
        assert "user_id" in user_route.path_params

    def test_extracts_methods(self, litestar_app):
        """Test HTTP method extraction."""
        extractor = get_extractor(litestar_app)
        routes = extractor.extract_routes(litestar_app)

        get_routes = [r for r in routes if "GET" in r.methods]
        post_routes = [r for r in routes if "POST" in r.methods]

        assert len(get_routes) >= 2
        assert len(post_routes) >= 1


class TestStarletteExtractor:
    """Tests for Starlette route extraction."""

    def test_supports_starlette_app(self, starlette_app):
        """Test that extractor supports Starlette apps."""
        extractor = get_extractor(starlette_app)
        assert extractor.supports(starlette_app)

    def test_extracts_routes(self, starlette_app):
        """Test route extraction from Starlette app."""
        extractor = get_extractor(starlette_app)
        routes = extractor.extract_routes(starlette_app)

        assert len(routes) >= 2

        paths = [r.path for r in routes]
        assert "/" in paths

    def test_parses_path_params(self, starlette_app):
        """Test path parameter parsing."""
        extractor = get_extractor(starlette_app)
        routes = extractor.extract_routes(starlette_app)

        user_route = next((r for r in routes if "user_id" in r.path), None)
        if user_route:
            assert "user_id" in user_route.path_params
            assert user_route.path_params["user_id"] is int


class TestFastAPIExtractor:
    """Tests for FastAPI route extraction."""

    def test_supports_fastapi_app(self, fastapi_app):
        """Test that extractor supports FastAPI apps."""
        extractor = get_extractor(fastapi_app)
        assert extractor.supports(fastapi_app)

    def test_extracts_routes(self, fastapi_app):
        """Test route extraction from FastAPI app."""
        extractor = get_extractor(fastapi_app)
        routes = extractor.extract_routes(fastapi_app)

        assert len(routes) >= 2

        paths = [r.path for r in routes]
        assert "/" in paths
