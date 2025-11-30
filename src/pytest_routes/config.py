"""Configuration for pytest-routes."""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

# Python 3.11+ has tomllib, earlier versions need tomli
if sys.version_info >= (3, 11):
    import tomllib
else:
    try:
        import tomli as tomllib  # type: ignore[import-untyped]
    except ImportError:
        tomllib = None  # type: ignore[assignment]


@dataclass
class RouteTestConfig:
    """Configuration for route smoke testing."""

    # Test execution
    max_examples: int = 100
    timeout_per_route: float = 30.0

    # Route filtering
    include_patterns: list[str] = field(default_factory=list)
    exclude_patterns: list[str] = field(
        default_factory=lambda: ["/health", "/metrics", "/openapi*", "/docs", "/redoc", "/schema"]
    )
    methods: list[str] = field(default_factory=lambda: ["GET", "POST", "PUT", "PATCH", "DELETE"])

    # Generation strategy
    strategy: Literal["random", "openapi", "hybrid"] = "hybrid"
    seed: int | None = None

    # Validation
    allowed_status_codes: list[int] = field(default_factory=lambda: list(range(200, 500)))
    fail_on_5xx: bool = True
    fail_on_validation_error: bool = True

    # Response validation
    validate_responses: bool = False
    response_validators: list[str] = field(default_factory=lambda: ["status_code"])

    # Framework hints
    framework: Literal["auto", "litestar", "fastapi", "starlette"] | None = "auto"

    # Output verbosity
    verbose: bool = False

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> RouteTestConfig:
        """Create config from dictionary (e.g., from pyproject.toml).

        Args:
            data: Dictionary containing configuration values.

        Returns:
            RouteTestConfig instance with values from dictionary.

        Examples:
            >>> config_data = {
            ...     "max_examples": 50,
            ...     "timeout": 30.0,
            ...     "include": ["/api/*"],
            ...     "exclude": ["/health", "/metrics"],
            ...     "methods": ["GET", "POST"],
            ...     "fail_on_5xx": True,
            ...     "allowed_status_codes": [200, 201, 400, 404],
            ...     "seed": 12345,
            ...     "framework": "litestar",
            ... }
            >>> config = RouteTestConfig.from_dict(config_data)
            >>> config.max_examples
            50
        """
        # Use defaults for missing values
        defaults = cls()

        return cls(
            max_examples=data.get("max_examples", defaults.max_examples),
            timeout_per_route=data.get("timeout", defaults.timeout_per_route),
            include_patterns=data.get("include", defaults.include_patterns),
            exclude_patterns=data.get("exclude", defaults.exclude_patterns),
            methods=data.get("methods", defaults.methods),
            strategy=data.get("strategy", defaults.strategy),
            seed=data.get("seed", defaults.seed),
            allowed_status_codes=data.get("allowed_status_codes", defaults.allowed_status_codes),
            fail_on_5xx=data.get("fail_on_5xx", defaults.fail_on_5xx),
            fail_on_validation_error=data.get("fail_on_validation_error", defaults.fail_on_validation_error),
            validate_responses=data.get("validate_responses", defaults.validate_responses),
            response_validators=data.get("response_validators", defaults.response_validators),
            framework=data.get("framework", defaults.framework),
            verbose=data.get("verbose", defaults.verbose),
        )


def load_config_from_pyproject(path: Path | None = None) -> RouteTestConfig:
    """Load configuration from pyproject.toml [tool.pytest-routes] section.

    Args:
        path: Path to pyproject.toml file. If None, looks in current working directory.

    Returns:
        RouteTestConfig instance loaded from file, or defaults if file not found.

    Raises:
        ImportError: If tomllib/tomli is not available (Python < 3.11 and tomli not installed).
        ValueError: If pyproject.toml contains invalid configuration.

    Examples:
        >>> # Load from default location (./pyproject.toml)
        >>> config = load_config_from_pyproject()
        >>> # Load from specific path
        >>> config = load_config_from_pyproject(Path("/path/to/pyproject.toml"))
    """
    if tomllib is None:
        msg = "tomllib is not available. For Python < 3.11, install tomli: pip install tomli"
        raise ImportError(msg)

    if path is None:
        path = Path.cwd() / "pyproject.toml"

    if not path.exists():
        # Return defaults if file doesn't exist
        return RouteTestConfig()

    try:
        with path.open("rb") as f:
            data = tomllib.load(f)
    except Exception as e:
        msg = f"Failed to parse pyproject.toml: {e}"
        raise ValueError(msg) from e

    # Extract [tool.pytest-routes] section
    config_data = data.get("tool", {}).get("pytest-routes", {})

    if not config_data:
        # No configuration section found, return defaults
        return RouteTestConfig()

    return RouteTestConfig.from_dict(config_data)


def merge_configs(
    cli_config: RouteTestConfig | None = None,
    file_config: RouteTestConfig | None = None,
) -> RouteTestConfig:
    """Merge CLI and file configs, with CLI taking precedence.

    Priority order (highest to lowest):
    1. CLI options (if provided and not default)
    2. pyproject.toml values
    3. Built-in defaults

    Args:
        cli_config: Configuration from CLI options.
        file_config: Configuration from pyproject.toml.

    Returns:
        Merged configuration with CLI options taking precedence.

    Examples:
        >>> file_cfg = RouteTestConfig(max_examples=50, seed=123)
        >>> cli_cfg = RouteTestConfig(max_examples=100)  # Override max_examples
        >>> merged = merge_configs(cli_cfg, file_cfg)
        >>> merged.max_examples  # From CLI
        100
        >>> merged.seed  # From file
        123
    """
    # Start with defaults
    defaults = RouteTestConfig()

    # If no configs provided, return defaults
    if cli_config is None and file_config is None:
        return defaults

    # If only file config, return it
    if cli_config is None:
        return file_config or defaults

    # If only CLI config, return it
    if file_config is None:
        return cli_config

    # Helper to check if a list is the "default" value (empty list)
    def _is_default_list(value: list, default: list) -> bool:
        """Check if a list value is considered a default."""
        # For include_patterns, default is []
        # For exclude_patterns, default is ["/health", ...]
        # For methods, default is ["GET", "POST", ...]
        # Empty list is only "default" for include_patterns
        if not value:  # Empty list
            return not default  # Empty is default only if default is also empty
        return value == default

    # Merge: CLI takes precedence over file, file over defaults
    # For each field, use CLI if it differs from default, otherwise use file
    return RouteTestConfig(
        max_examples=(
            cli_config.max_examples if cli_config.max_examples != defaults.max_examples else file_config.max_examples
        ),
        timeout_per_route=(
            cli_config.timeout_per_route
            if cli_config.timeout_per_route != defaults.timeout_per_route
            else file_config.timeout_per_route
        ),
        include_patterns=(
            cli_config.include_patterns
            if not _is_default_list(cli_config.include_patterns, defaults.include_patterns)
            else file_config.include_patterns
        ),
        exclude_patterns=(
            cli_config.exclude_patterns
            if not _is_default_list(cli_config.exclude_patterns, defaults.exclude_patterns)
            else file_config.exclude_patterns
        ),
        methods=(
            cli_config.methods if not _is_default_list(cli_config.methods, defaults.methods) else file_config.methods
        ),
        strategy=(cli_config.strategy if cli_config.strategy != defaults.strategy else file_config.strategy),
        seed=cli_config.seed if cli_config.seed is not None else file_config.seed,
        allowed_status_codes=(
            cli_config.allowed_status_codes
            if not _is_default_list(cli_config.allowed_status_codes, defaults.allowed_status_codes)
            else file_config.allowed_status_codes
        ),
        fail_on_5xx=(
            cli_config.fail_on_5xx if cli_config.fail_on_5xx != defaults.fail_on_5xx else file_config.fail_on_5xx
        ),
        fail_on_validation_error=(
            cli_config.fail_on_validation_error
            if cli_config.fail_on_validation_error != defaults.fail_on_validation_error
            else file_config.fail_on_validation_error
        ),
        validate_responses=(
            cli_config.validate_responses
            if cli_config.validate_responses != defaults.validate_responses
            else file_config.validate_responses
        ),
        response_validators=(
            cli_config.response_validators
            if not _is_default_list(cli_config.response_validators, defaults.response_validators)
            else file_config.response_validators
        ),
        framework=(cli_config.framework if cli_config.framework != defaults.framework else file_config.framework),
        verbose=cli_config.verbose if cli_config.verbose != defaults.verbose else file_config.verbose,
    )
