"""Tests for configuration loading and merging."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from pytest_routes.config import RouteTestConfig, load_config_from_pyproject, merge_configs

if TYPE_CHECKING:
    pass


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
