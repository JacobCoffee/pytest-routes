"""Tests for configuration loading and merging."""

from __future__ import annotations

from pathlib import Path

import pytest

from pytest_routes.auth import BearerTokenAuth
from pytest_routes.config import RouteOverride, RouteTestConfig, load_config_from_pyproject, merge_configs


def test_route_test_config_defaults() -> None:
    """Test that RouteTestConfig has sensible defaults."""
    config = RouteTestConfig()

    assert config.max_examples == 100
    assert config.timeout_per_route == 30.0
    assert config.include_patterns == []
    assert config.exclude_patterns == ["/health", "/metrics", "/openapi*", "/docs", "/redoc", "/schema"]
    assert config.methods == ["GET", "POST", "PUT", "PATCH", "DELETE"]
    assert config.strategy == "hybrid"
    assert config.seed is None
    assert config.allowed_status_codes == list(range(200, 500))
    assert config.fail_on_5xx is True
    assert config.fail_on_validation_error is True
    assert config.framework == "auto"


def test_from_dict_with_all_fields() -> None:
    """Test creating config from dictionary with all fields."""
    data = {
        "max_examples": 50,
        "timeout": 15.0,
        "include": ["/api/*"],
        "exclude": ["/health", "/metrics"],
        "methods": ["GET", "POST"],
        "strategy": "openapi",
        "seed": 12345,
        "allowed_status_codes": [200, 201, 400, 404],
        "fail_on_5xx": False,
        "fail_on_validation_error": False,
        "validate_responses": True,
        "response_validators": ["status_code", "json_schema"],
        "framework": "litestar",
    }

    config = RouteTestConfig.from_dict(data)

    assert config.max_examples == 50
    assert config.timeout_per_route == 15.0
    assert config.include_patterns == ["/api/*"]
    assert config.exclude_patterns == ["/health", "/metrics"]
    assert config.methods == ["GET", "POST"]
    assert config.strategy == "openapi"
    assert config.seed == 12345
    assert config.allowed_status_codes == [200, 201, 400, 404]
    assert config.fail_on_5xx is False
    assert config.fail_on_validation_error is False
    assert config.validate_responses is True
    assert config.response_validators == ["status_code", "json_schema"]
    assert config.framework == "litestar"


def test_from_dict_with_partial_fields() -> None:
    """Test creating config from dictionary with only some fields (uses defaults for rest)."""
    data = {
        "max_examples": 25,
        "seed": 9999,
    }

    config = RouteTestConfig.from_dict(data)

    assert config.max_examples == 25
    assert config.seed == 9999
    # Defaults for unspecified fields
    assert config.timeout_per_route == 30.0
    assert config.methods == ["GET", "POST", "PUT", "PATCH", "DELETE"]


def test_from_dict_with_empty_dict() -> None:
    """Test creating config from empty dictionary (all defaults)."""
    config = RouteTestConfig.from_dict({})

    defaults = RouteTestConfig()
    assert config.max_examples == defaults.max_examples
    assert config.timeout_per_route == defaults.timeout_per_route
    assert config.methods == defaults.methods


def test_load_config_from_pyproject_file_not_found() -> None:
    """Test loading config when pyproject.toml doesn't exist."""
    config = load_config_from_pyproject(Path("/nonexistent/path/pyproject.toml"))

    # Should return defaults
    assert config.max_examples == 100
    assert config.timeout_per_route == 30.0


def test_load_config_from_pyproject_no_tool_section(tmp_path: Path) -> None:
    """Test loading config when pyproject.toml has no [tool.pytest-routes] section."""
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text("""
[project]
name = "test-project"
version = "0.1.0"
""")

    config = load_config_from_pyproject(pyproject)

    # Should return defaults
    assert config.max_examples == 100
    assert config.timeout_per_route == 30.0


def test_load_config_from_pyproject_with_config(tmp_path: Path) -> None:
    """Test loading config from pyproject.toml with [tool.pytest-routes] section."""
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text("""
[project]
name = "test-project"
version = "0.1.0"

[tool.pytest-routes]
app = "myapp:app"
max_examples = 50
timeout = 20.0
include = ["/api/*"]
exclude = ["/health", "/metrics"]
methods = ["GET", "POST"]
fail_on_5xx = false
allowed_status_codes = [200, 201, 204, 400, 401, 403, 404]
seed = 42
framework = "litestar"
""")

    config = load_config_from_pyproject(pyproject)

    assert config.max_examples == 50
    assert config.timeout_per_route == 20.0
    assert config.include_patterns == ["/api/*"]
    assert config.exclude_patterns == ["/health", "/metrics"]
    assert config.methods == ["GET", "POST"]
    assert config.fail_on_5xx is False
    assert config.allowed_status_codes == [200, 201, 204, 400, 401, 403, 404]
    assert config.seed == 42
    assert config.framework == "litestar"


def test_load_config_from_pyproject_invalid_toml(tmp_path: Path) -> None:
    """Test loading config from invalid TOML file."""
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text("invalid toml content [[[")

    with pytest.raises(ValueError, match=r"Failed to parse pyproject\.toml"):
        load_config_from_pyproject(pyproject)


def test_merge_configs_no_configs() -> None:
    """Test merging when no configs provided."""
    merged = merge_configs(None, None)

    defaults = RouteTestConfig()
    assert merged.max_examples == defaults.max_examples
    assert merged.timeout_per_route == defaults.timeout_per_route


def test_merge_configs_only_file_config() -> None:
    """Test merging with only file config."""
    file_config = RouteTestConfig(max_examples=50, seed=123)

    merged = merge_configs(None, file_config)

    assert merged.max_examples == 50
    assert merged.seed == 123


def test_merge_configs_only_cli_config() -> None:
    """Test merging with only CLI config."""
    cli_config = RouteTestConfig(max_examples=75, seed=456)

    merged = merge_configs(cli_config, None)

    assert merged.max_examples == 75
    assert merged.seed == 456


def test_merge_configs_cli_overrides_file() -> None:
    """Test that CLI config takes precedence over file config."""
    file_config = RouteTestConfig(max_examples=50, seed=123, timeout_per_route=15.0)
    # Override max_examples (diff from default), use file's seed
    cli_config = RouteTestConfig(max_examples=200, seed=None)

    merged = merge_configs(cli_config, file_config)

    assert merged.max_examples == 200  # From CLI (different from default)
    assert merged.seed == 123  # From file (CLI seed is None)
    assert merged.timeout_per_route == 15.0  # From file (CLI uses default)


def test_merge_configs_preserves_non_default_cli_values() -> None:
    """Test that non-default CLI values are preserved even when file has different values."""
    defaults = RouteTestConfig()
    file_config = RouteTestConfig(
        max_examples=50,
        include_patterns=["/api/*"],
        exclude_patterns=["/health"],
    )
    cli_config = RouteTestConfig(
        max_examples=200,  # Different from default
        include_patterns=["/custom/*"],  # Different from default
        exclude_patterns=defaults.exclude_patterns,  # Same as default, should use file's
    )

    merged = merge_configs(cli_config, file_config)

    assert merged.max_examples == 200  # CLI overrides (different from default)
    assert merged.include_patterns == ["/custom/*"]  # From CLI (different from default)
    assert merged.exclude_patterns == ["/health"]  # From file (CLI same as default)


def test_merge_configs_complex_scenario() -> None:
    """Test merging with complex mix of CLI and file values."""
    defaults = RouteTestConfig()
    file_config = RouteTestConfig(
        max_examples=50,
        timeout_per_route=20.0,
        include_patterns=["/api/*"],
        exclude_patterns=["/health", "/metrics"],
        methods=["GET", "POST"],
        seed=999,
        fail_on_5xx=False,
        framework="litestar",
    )

    cli_config = RouteTestConfig(
        max_examples=75,  # Override
        timeout_per_route=defaults.timeout_per_route,  # Default - use file's
        include_patterns=defaults.include_patterns,  # Default - use file's
        exclude_patterns=defaults.exclude_patterns,  # Default - use file's
        methods=defaults.methods,  # Default - use file's
        seed=12345,  # Override
        fail_on_5xx=defaults.fail_on_5xx,  # Default - use file's
        framework=defaults.framework,  # Default - use file's
    )

    merged = merge_configs(cli_config, file_config)

    # CLI overrides (different from defaults)
    assert merged.max_examples == 75
    assert merged.seed == 12345

    # From file (CLI uses defaults)
    assert merged.timeout_per_route == 20.0
    assert merged.include_patterns == ["/api/*"]
    assert merged.exclude_patterns == ["/health", "/metrics"]
    assert merged.methods == ["GET", "POST"]
    assert merged.fail_on_5xx is False
    assert merged.framework == "litestar"


def test_merge_configs_list_fields() -> None:
    """Test that list fields merge correctly (CLI takes precedence if different from default)."""
    defaults = RouteTestConfig()
    file_config = RouteTestConfig(
        include_patterns=["/api/*", "/v1/*"],
        exclude_patterns=["/health"],
        methods=["GET"],
    )
    cli_config = RouteTestConfig(
        include_patterns=["/api/v2/*"],  # Different from default
        exclude_patterns=defaults.exclude_patterns,  # Same as default
        methods=defaults.methods,  # Same as default
    )

    merged = merge_configs(cli_config, file_config)

    assert merged.include_patterns == ["/api/v2/*"]  # From CLI (different from default)
    assert merged.exclude_patterns == ["/health"]  # From file (CLI same as default)
    assert merged.methods == ["GET"]  # From file (CLI same as default)


class TestRouteOverride:
    """Tests for RouteOverride."""

    def test_route_override_with_all_fields(self) -> None:
        auth = BearerTokenAuth("test-token")
        override = RouteOverride(
            pattern="/api/admin/*",
            max_examples=50,
            timeout=10.0,
            auth=auth,
            skip=False,
            allowed_status_codes=[200, 201],
        )

        assert override.pattern == "/api/admin/*"
        assert override.max_examples == 50
        assert override.timeout == 10.0
        assert override.auth is auth
        assert override.skip is False
        assert override.allowed_status_codes == [200, 201]

    def test_route_override_defaults(self) -> None:
        override = RouteOverride(pattern="/api/*")

        assert override.pattern == "/api/*"
        assert override.max_examples is None
        assert override.timeout is None
        assert override.auth is None
        assert override.skip is False
        assert override.allowed_status_codes is None


class TestRouteTestConfigAuth:
    """Tests for auth-related config functionality."""

    def test_config_with_auth(self) -> None:
        auth = BearerTokenAuth("my-token")
        config = RouteTestConfig(auth=auth)
        assert config.auth is auth

    def test_config_with_route_overrides(self) -> None:
        overrides = [
            RouteOverride(pattern="/api/admin/*", skip=True),
            RouteOverride(pattern="/api/public/*", max_examples=50),
        ]
        config = RouteTestConfig(route_overrides=overrides)
        assert len(config.route_overrides) == 2

    def test_get_override_for_route_match(self) -> None:
        overrides = [
            RouteOverride(pattern="/api/admin/*", skip=True),
            RouteOverride(pattern="/api/public/*", max_examples=50),
        ]
        config = RouteTestConfig(route_overrides=overrides)

        override = config.get_override_for_route("/api/admin/users")
        assert override is not None
        assert override.skip is True

    def test_get_override_for_route_no_match(self) -> None:
        overrides = [
            RouteOverride(pattern="/api/admin/*", skip=True),
        ]
        config = RouteTestConfig(route_overrides=overrides)

        override = config.get_override_for_route("/api/public/data")
        assert override is None

    def test_get_effective_config_no_override(self) -> None:
        auth = BearerTokenAuth("base-token")
        config = RouteTestConfig(
            max_examples=100,
            timeout_per_route=30.0,
            auth=auth,
        )

        effective = config.get_effective_config_for_route("/some/path")
        assert effective["max_examples"] == 100
        assert effective["timeout"] == 30.0
        assert effective["auth"] is auth
        assert effective["skip"] is False

    def test_get_effective_config_with_override(self) -> None:
        base_auth = BearerTokenAuth("base-token")
        override_auth = BearerTokenAuth("override-token")
        overrides = [
            RouteOverride(
                pattern="/api/admin/*",
                max_examples=50,
                timeout=10.0,
                auth=override_auth,
                allowed_status_codes=[200, 201, 403],
            ),
        ]
        config = RouteTestConfig(
            max_examples=100,
            timeout_per_route=30.0,
            auth=base_auth,
            route_overrides=overrides,
        )

        effective = config.get_effective_config_for_route("/api/admin/users")
        assert effective["max_examples"] == 50
        assert effective["timeout"] == 10.0
        assert effective["auth"] is override_auth
        assert effective["allowed_status_codes"] == [200, 201, 403]
        assert effective["skip"] is False

    def test_get_effective_config_partial_override(self) -> None:
        base_auth = BearerTokenAuth("base-token")
        overrides = [
            RouteOverride(
                pattern="/api/*",
                max_examples=50,
            ),
        ]
        config = RouteTestConfig(
            max_examples=100,
            timeout_per_route=30.0,
            auth=base_auth,
            route_overrides=overrides,
        )

        effective = config.get_effective_config_for_route("/api/users")
        assert effective["max_examples"] == 50
        assert effective["timeout"] == 30.0
        assert effective["auth"] is base_auth


class TestConfigFromDictWithAuth:
    """Tests for loading config with auth from dictionary."""

    def test_from_dict_with_bearer_token(self) -> None:
        data = {
            "max_examples": 50,
            "auth": {"bearer_token": "my-secret-token"},
        }

        config = RouteTestConfig.from_dict(data)

        assert config.max_examples == 50
        assert config.auth is not None
        assert config.auth.get_headers() == {"Authorization": "Bearer my-secret-token"}

    def test_from_dict_with_api_key_header(self) -> None:
        data = {
            "auth": {
                "api_key": "my-api-key",
                "header_name": "X-Custom-Key",
            },
        }

        config = RouteTestConfig.from_dict(data)

        assert config.auth is not None
        assert config.auth.get_headers() == {"X-Custom-Key": "my-api-key"}

    def test_from_dict_with_api_key_query_param(self) -> None:
        data = {
            "auth": {
                "api_key": "my-api-key",
                "query_param": "api_key",
            },
        }

        config = RouteTestConfig.from_dict(data)

        assert config.auth is not None
        assert config.auth.get_query_params() == {"api_key": "my-api-key"}

    def test_from_dict_with_route_overrides(self) -> None:
        data = {
            "routes": [
                {"pattern": "/api/admin/*", "max_examples": 50, "skip": False},
                {"pattern": "/api/internal/*", "skip": True},
            ],
        }

        config = RouteTestConfig.from_dict(data)

        assert len(config.route_overrides) == 2
        assert config.route_overrides[0].pattern == "/api/admin/*"
        assert config.route_overrides[0].max_examples == 50
        assert config.route_overrides[1].pattern == "/api/internal/*"
        assert config.route_overrides[1].skip is True

    def test_from_dict_with_route_override_auth(self) -> None:
        data = {
            "routes": [
                {
                    "pattern": "/api/admin/*",
                    "auth": {"bearer_token": "admin-token"},
                },
            ],
        }

        config = RouteTestConfig.from_dict(data)

        assert len(config.route_overrides) == 1
        assert config.route_overrides[0].auth is not None
        assert config.route_overrides[0].auth.get_headers() == {"Authorization": "Bearer admin-token"}


class TestLoadConfigFromPyprojectWithAuth:
    """Tests for loading config with auth from pyproject.toml."""

    def test_load_with_bearer_token_auth(self, tmp_path: Path) -> None:
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text("""
[tool.pytest-routes]
max_examples = 50

[tool.pytest-routes.auth]
bearer_token = "my-secret-token"
""")

        config = load_config_from_pyproject(pyproject)

        assert config.max_examples == 50
        assert config.auth is not None
        assert config.auth.get_headers() == {"Authorization": "Bearer my-secret-token"}

    def test_load_with_api_key_auth(self, tmp_path: Path) -> None:
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text("""
[tool.pytest-routes]
max_examples = 50

[tool.pytest-routes.auth]
api_key = "my-api-key"
header_name = "X-API-Key"
""")

        config = load_config_from_pyproject(pyproject)

        assert config.auth is not None
        assert config.auth.get_headers() == {"X-API-Key": "my-api-key"}

    def test_load_with_route_overrides(self, tmp_path: Path) -> None:
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text("""
[tool.pytest-routes]
max_examples = 100

[[tool.pytest-routes.routes]]
pattern = "/api/admin/*"
max_examples = 25
skip = false

[[tool.pytest-routes.routes]]
pattern = "/api/internal/*"
skip = true
""")

        config = load_config_from_pyproject(pyproject)

        assert len(config.route_overrides) == 2
        assert config.route_overrides[0].pattern == "/api/admin/*"
        assert config.route_overrides[0].max_examples == 25
        assert config.route_overrides[1].pattern == "/api/internal/*"
        assert config.route_overrides[1].skip is True


class TestMergeConfigsWithAuth:
    """Tests for merging configs with auth."""

    def test_merge_cli_auth_overrides_file(self) -> None:
        file_auth = BearerTokenAuth("file-token")
        cli_auth = BearerTokenAuth("cli-token")

        file_config = RouteTestConfig(auth=file_auth)
        cli_config = RouteTestConfig(auth=cli_auth)

        merged = merge_configs(cli_config, file_config)

        assert merged.auth is cli_auth

    def test_merge_uses_file_auth_when_cli_none(self) -> None:
        file_auth = BearerTokenAuth("file-token")

        file_config = RouteTestConfig(auth=file_auth)
        cli_config = RouteTestConfig(auth=None)

        merged = merge_configs(cli_config, file_config)

        assert merged.auth is file_auth

    def test_merge_route_overrides_combined(self) -> None:
        file_overrides = [RouteOverride(pattern="/api/file/*", skip=True)]
        cli_overrides = [RouteOverride(pattern="/api/cli/*", max_examples=50)]

        file_config = RouteTestConfig(route_overrides=file_overrides)
        cli_config = RouteTestConfig(route_overrides=cli_overrides)

        merged = merge_configs(cli_config, file_config)

        assert len(merged.route_overrides) == 2
        assert merged.route_overrides[0].pattern == "/api/cli/*"
        assert merged.route_overrides[1].pattern == "/api/file/*"
