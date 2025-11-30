"""Configuration for pytest-routes."""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal

# Python 3.11+ has tomllib, earlier versions need tomli
if sys.version_info >= (3, 11):
    import tomllib
else:
    try:
        import tomli as tomllib  # type: ignore[import-untyped]
    except ImportError:
        tomllib = None  # type: ignore[assignment]

if TYPE_CHECKING:
    from pytest_routes.auth.providers import AuthProvider


@dataclass
class RouteOverride:
    """Per-route configuration overrides.

    Allows customizing test behavior for specific routes by path pattern.
    All fields are optional; only specified fields will override the base config.

    Args:
        pattern: Glob pattern to match routes (e.g., "/api/admin/*").
        max_examples: Override max examples for matching routes.
        timeout: Override timeout for matching routes.
        auth: Override authentication provider for matching routes.
        skip: If True, skip testing for matching routes.
        allowed_status_codes: Override allowed status codes for matching routes.

    Example:
        >>> override = RouteOverride(
        ...     pattern="/api/admin/*",
        ...     auth=BearerTokenAuth("admin-token"),
        ...     max_examples=50,
        ... )
    """

    pattern: str
    max_examples: int | None = None
    timeout: float | None = None
    auth: AuthProvider | None = None
    skip: bool = False
    allowed_status_codes: list[int] | None = None


@dataclass
class SchemathesisConfig:
    """Configuration for Schemathesis integration.

    Attributes:
        enabled: Whether Schemathesis mode is enabled.
        schema_path: Path to fetch OpenAPI schema from the app.
        validate_responses: Whether to validate response bodies against schema.
        stateful: Stateful testing mode ('none', 'links').
        checks: List of Schemathesis checks to run.
    """

    enabled: bool = False
    schema_path: str = "/openapi.json"
    validate_responses: bool = True
    stateful: str = "none"
    checks: list[str] = field(
        default_factory=lambda: [
            "status_code_conformance",
            "content_type_conformance",
            "response_schema_conformance",
        ]
    )


@dataclass
class ReportConfig:
    """Configuration for test reporting.

    Attributes:
        enabled: Whether to generate reports.
        output_path: Path to write HTML report.
        json_output: Path to write JSON report (None to skip).
        title: Title for the HTML report.
        include_coverage: Whether to include coverage metrics.
        include_timing: Whether to include timing metrics.
        theme: Color theme ('light' or 'dark').
    """

    enabled: bool = False
    output_path: str = "pytest-routes-report.html"
    json_output: str | None = None
    title: str = "pytest-routes Test Report"
    include_coverage: bool = True
    include_timing: bool = True
    theme: str = "light"


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

    # Authentication
    auth: AuthProvider | None = None

    # Per-route overrides
    route_overrides: list[RouteOverride] = field(default_factory=list)

    # Schemathesis integration
    schemathesis: SchemathesisConfig = field(default_factory=SchemathesisConfig)

    # Reporting
    report: ReportConfig = field(default_factory=ReportConfig)

    def get_override_for_route(self, path: str) -> RouteOverride | None:
        """Get the matching override for a route path.

        Finds the first RouteOverride whose pattern matches the given path.
        Uses glob-style pattern matching.

        Args:
            path: The route path to match.

        Returns:
            The first matching RouteOverride, or None if no match.
        """
        import fnmatch

        for override in self.route_overrides:
            if fnmatch.fnmatch(path, override.pattern):
                return override
        return None

    def get_effective_config_for_route(self, path: str) -> dict[str, Any]:
        """Get effective configuration for a specific route.

        Merges the base config with any matching route override.

        Args:
            path: The route path to get config for.

        Returns:
            Dictionary with effective configuration values.
        """
        override = self.get_override_for_route(path)
        config: dict[str, Any] = {
            "max_examples": self.max_examples,
            "timeout": self.timeout_per_route,
            "auth": self.auth,
            "allowed_status_codes": self.allowed_status_codes,
            "skip": False,
        }

        if override:
            if override.max_examples is not None:
                config["max_examples"] = override.max_examples
            if override.timeout is not None:
                config["timeout"] = override.timeout
            if override.auth is not None:
                config["auth"] = override.auth
            if override.allowed_status_codes is not None:
                config["allowed_status_codes"] = override.allowed_status_codes
            config["skip"] = override.skip

        return config

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

        # Parse auth configuration if present
        auth = _parse_auth_config(data.get("auth"))

        # Parse route overrides if present
        route_overrides = _parse_route_overrides(data.get("routes", []))

        # Parse schemathesis configuration if present
        schemathesis = _parse_schemathesis_config(data.get("schemathesis", {}))

        # Parse report configuration if present
        report = _parse_report_config(data.get("report", {}))

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
            auth=auth,
            route_overrides=route_overrides,
            schemathesis=schemathesis,
            report=report,
        )


def _parse_auth_config(auth_data: dict[str, Any] | None) -> AuthProvider | None:
    """Parse authentication configuration from dictionary.

    Supports the following auth types:
    - bearer_token: Bearer token authentication
    - api_key: API key authentication (header or query param)

    Args:
        auth_data: Authentication configuration dictionary.

    Returns:
        Configured AuthProvider or None if no auth specified.

    Example config in pyproject.toml::

        [tool.pytest - routes.auth]
        bearer_token = "$API_TOKEN"  # From environment variable

        # OR

        [tool.pytest - routes.auth]
        api_key = "my-key"
        header_name = "X-API-Key"

        # OR

        [tool.pytest - routes.auth]
        api_key = "$API_KEY"
        query_param = "api_key"
    """
    if not auth_data:
        return None

    # Import here to avoid circular imports
    from pytest_routes.auth.providers import APIKeyAuth, BearerTokenAuth

    # Bearer token auth
    if "bearer_token" in auth_data:
        return BearerTokenAuth(auth_data["bearer_token"])

    # API key auth
    if "api_key" in auth_data:
        return APIKeyAuth(
            auth_data["api_key"],
            header_name=auth_data.get("header_name"),
            query_param=auth_data.get("query_param"),
        )

    return None


def _parse_route_overrides(routes_data: list[dict[str, Any]]) -> list[RouteOverride]:
    """Parse route override configurations.

    Args:
        routes_data: List of route override dictionaries.

    Returns:
        List of RouteOverride instances.

    Example config in pyproject.toml::

        [[tool.pytest - routes.routes]]
        pattern = "/api/admin/*"
        max_examples = 50
        skip = false

        [[tool.pytest - routes.routes]]
        pattern = "/api/internal/*"
        skip = true
    """
    if not routes_data:
        return []

    overrides = []
    for route_data in routes_data:
        if "pattern" not in route_data:
            continue

        # Parse auth for this route if specified
        auth = _parse_auth_config(route_data.get("auth"))

        override = RouteOverride(
            pattern=route_data["pattern"],
            max_examples=route_data.get("max_examples"),
            timeout=route_data.get("timeout"),
            auth=auth,
            skip=route_data.get("skip", False),
            allowed_status_codes=route_data.get("allowed_status_codes"),
        )
        overrides.append(override)

    return overrides


def _parse_schemathesis_config(data: dict[str, Any]) -> SchemathesisConfig:
    """Parse Schemathesis configuration from dictionary.

    Args:
        data: Schemathesis configuration dictionary.

    Returns:
        SchemathesisConfig instance.

    Example config in pyproject.toml::

        [tool.pytest - routes.schemathesis]
        enabled = true
        schema_path = "/openapi.json"
        validate_responses = true
        stateful = "links"
        checks = ["status_code_conformance", "response_schema_conformance"]
    """
    defaults = SchemathesisConfig()

    return SchemathesisConfig(
        enabled=data.get("enabled", defaults.enabled),
        schema_path=data.get("schema_path", defaults.schema_path),
        validate_responses=data.get("validate_responses", defaults.validate_responses),
        stateful=data.get("stateful", defaults.stateful),
        checks=data.get("checks", defaults.checks),
    )


def _parse_report_config(data: dict[str, Any]) -> ReportConfig:
    """Parse report configuration from dictionary.

    Args:
        data: Report configuration dictionary.

    Returns:
        ReportConfig instance.

    Example config in pyproject.toml::

        [tool.pytest - routes.report]
        enabled = true
        output_path = "pytest-routes-report.html"
        json_output = "pytest-routes-report.json"
        title = "API Route Tests"
        include_coverage = true
        include_timing = true
        theme = "dark"
    """
    defaults = ReportConfig()

    return ReportConfig(
        enabled=data.get("enabled", defaults.enabled),
        output_path=data.get("output_path", defaults.output_path),
        json_output=data.get("json_output", defaults.json_output),
        title=data.get("title", defaults.title),
        include_coverage=data.get("include_coverage", defaults.include_coverage),
        include_timing=data.get("include_timing", defaults.include_timing),
        theme=data.get("theme", defaults.theme),
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
        # Auth: CLI takes precedence if set
        auth=cli_config.auth if cli_config.auth is not None else file_config.auth,
        # Route overrides: merge both lists (CLI overrides first for pattern matching priority)
        route_overrides=cli_config.route_overrides + file_config.route_overrides,
        # Schemathesis: CLI takes precedence if enabled
        schemathesis=_merge_schemathesis_config(cli_config.schemathesis, file_config.schemathesis),
        # Report: CLI takes precedence if enabled
        report=_merge_report_config(cli_config.report, file_config.report),
    )


def _merge_schemathesis_config(
    cli_config: SchemathesisConfig,
    file_config: SchemathesisConfig,
) -> SchemathesisConfig:
    """Merge schemathesis configs with CLI taking precedence."""
    defaults = SchemathesisConfig()

    enabled = cli_config.enabled if cli_config.enabled != defaults.enabled else file_config.enabled
    schema_path = cli_config.schema_path if cli_config.schema_path != defaults.schema_path else file_config.schema_path
    validate_responses = (
        cli_config.validate_responses
        if cli_config.validate_responses != defaults.validate_responses
        else file_config.validate_responses
    )
    stateful = cli_config.stateful if cli_config.stateful != defaults.stateful else file_config.stateful
    checks = cli_config.checks if cli_config.checks != defaults.checks else file_config.checks

    return SchemathesisConfig(
        enabled=enabled,
        schema_path=schema_path,
        validate_responses=validate_responses,
        stateful=stateful,
        checks=checks,
    )


def _merge_report_config(
    cli_config: ReportConfig,
    file_config: ReportConfig,
) -> ReportConfig:
    """Merge report configs with CLI taking precedence."""
    defaults = ReportConfig()

    enabled = cli_config.enabled if cli_config.enabled != defaults.enabled else file_config.enabled
    output_path = cli_config.output_path if cli_config.output_path != defaults.output_path else file_config.output_path
    json_output = cli_config.json_output if cli_config.json_output is not None else file_config.json_output
    title = cli_config.title if cli_config.title != defaults.title else file_config.title
    include_coverage = (
        cli_config.include_coverage
        if cli_config.include_coverage != defaults.include_coverage
        else file_config.include_coverage
    )
    include_timing = (
        cli_config.include_timing
        if cli_config.include_timing != defaults.include_timing
        else file_config.include_timing
    )
    theme = cli_config.theme if cli_config.theme != defaults.theme else file_config.theme

    return ReportConfig(
        enabled=enabled,
        output_path=output_path,
        json_output=json_output,
        title=title,
        include_coverage=include_coverage,
        include_timing=include_timing,
        theme=theme,
    )
