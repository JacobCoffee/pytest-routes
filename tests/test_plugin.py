"""Tests for pytest plugin integration."""

from __future__ import annotations

from pytest_routes.config import RouteTestConfig
from pytest_routes.plugin import _matches_pattern


class TestMatchesPattern:
    """Tests for route pattern matching."""

    def test_exact_match(self):
        """Test exact path matching."""
        assert _matches_pattern("/health", "/health")
        assert not _matches_pattern("/health", "/healthz")

    def test_wildcard_match(self):
        """Test wildcard pattern matching."""
        assert _matches_pattern("/api/users", "/api/*")
        assert _matches_pattern("/api/users/123", "/api/*")
        assert not _matches_pattern("/users", "/api/*")

    def test_double_wildcard_match(self):
        """Test double wildcard pattern matching."""
        assert _matches_pattern("/api/v1/users", "/api/**")
        assert _matches_pattern("/api/v1/users/123/posts", "/api/**")

    def test_suffix_wildcard(self):
        """Test suffix wildcard matching."""
        assert _matches_pattern("/openapi.json", "/openapi*")
        assert _matches_pattern("/openapi", "/openapi*")
        assert not _matches_pattern("/api/openapi", "/openapi*")

    def test_question_mark_wildcard(self):
        """Test single character wildcard matching."""
        assert _matches_pattern("/v1", "/v?")
        assert _matches_pattern("/v2", "/v?")
        assert not _matches_pattern("/v10", "/v?")


class TestRouteConfigFixture:
    """Tests for route_config fixture."""

    def test_default_config_values(self):
        """Test default configuration values."""
        config = RouteTestConfig()

        assert config.max_examples == 100
        assert config.timeout_per_route == 30.0
        assert config.fail_on_5xx is True
        assert "GET" in config.methods
        assert "POST" in config.methods

    def test_exclude_patterns_default(self):
        """Test default exclude patterns."""
        config = RouteTestConfig()

        assert "/health" in config.exclude_patterns
        assert "/metrics" in config.exclude_patterns
        assert "/docs" in config.exclude_patterns

    def test_allowed_status_codes_default(self):
        """Test default allowed status codes."""
        config = RouteTestConfig()

        assert 200 in config.allowed_status_codes
        assert 404 in config.allowed_status_codes
        assert 500 not in config.allowed_status_codes

    def test_custom_config(self):
        """Test custom configuration."""
        config = RouteTestConfig(
            max_examples=50,
            timeout_per_route=10.0,
            include_patterns=["/api/*"],
            exclude_patterns=["/api/internal/*"],
            methods=["GET", "POST"],
        )

        assert config.max_examples == 50
        assert config.timeout_per_route == 10.0
        assert "/api/*" in config.include_patterns
        assert "/api/internal/*" in config.exclude_patterns
        assert config.methods == ["GET", "POST"]


class TestPluginMarkers:
    """Tests for pytest markers registration."""

    def test_routes_marker_registered(self, pytestconfig):
        """Test that routes marker is registered."""
        markers = list(pytestconfig.getini("markers"))
        marker_names = [m.split(":")[0] for m in markers]
        assert "routes" in marker_names or any("routes" in m for m in markers)


class TestRouteFiltering:
    """Tests for route filtering logic."""

    def test_method_filtering(self, litestar_app):
        """Test filtering routes by HTTP method."""
        from pytest_routes.discovery import get_extractor

        extractor = get_extractor(litestar_app)
        routes = extractor.extract_routes(litestar_app)

        config = RouteTestConfig(methods=["GET"])
        get_routes = [r for r in routes if any(m in config.methods for m in r.methods)]

        assert all("GET" in r.methods for r in get_routes)

    def test_exclude_filtering(self, litestar_app):
        """Test filtering routes by exclude patterns."""
        from pytest_routes.discovery import get_extractor

        extractor = get_extractor(litestar_app)
        routes = extractor.extract_routes(litestar_app)

        config = RouteTestConfig(exclude_patterns=["/health"])
        filtered = [r for r in routes if not any(_matches_pattern(r.path, p) for p in config.exclude_patterns)]

        assert not any(r.path == "/health" for r in filtered)

    def test_include_filtering(self, litestar_app):
        """Test filtering routes by include patterns."""
        from pytest_routes.discovery import get_extractor

        extractor = get_extractor(litestar_app)
        routes = extractor.extract_routes(litestar_app)

        config = RouteTestConfig(include_patterns=["/users/*"])
        filtered = [r for r in routes if any(_matches_pattern(r.path, p) for p in config.include_patterns)]

        assert all("users" in r.path for r in filtered)
