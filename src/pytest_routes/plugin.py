"""Pytest plugin for route smoke testing."""

from __future__ import annotations

import importlib
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pytest

from pytest_routes.config import (
    ReportConfig,
    RouteTestConfig,
    SchemathesisConfig,
    load_config_from_pyproject,
    merge_configs,
)
from pytest_routes.discovery import get_extractor
from pytest_routes.execution.runner import RouteTestRunner

if TYPE_CHECKING:
    from pytest_routes.discovery.base import RouteInfo

# Global storage for routes (set during collection)
_discovered_routes: list[RouteInfo] = []
_all_routes: list[RouteInfo] = []
_route_runner: RouteTestRunner | None = None
_routes_enabled: bool = False
_route_config: RouteTestConfig | None = None
_test_metrics: Any = None
_coverage_metrics: Any = None


def pytest_addoption(parser: pytest.Parser) -> None:
    """Add pytest command line options."""
    group = parser.getgroup("routes")
    group.addoption(
        "--routes",
        action="store_true",
        default=False,
        help="Run route smoke tests",
    )
    group.addoption(
        "--routes-app",
        action="store",
        help="Import path to ASGI app (e.g., 'myapp:app')",
    )
    group.addoption(
        "--routes-max-examples",
        type=int,
        default=100,
        help="Max examples per route (default: 100)",
    )
    group.addoption(
        "--routes-exclude",
        action="store",
        default="",
        help="Comma-separated patterns to exclude (e.g., '/health,/metrics')",
    )
    group.addoption(
        "--routes-include",
        action="store",
        default="",
        help="Comma-separated patterns to include (e.g., '/api/*')",
    )
    group.addoption(
        "--routes-methods",
        action="store",
        default="GET,POST,PUT,PATCH,DELETE",
        help="Comma-separated HTTP methods to test (default: GET,POST,PUT,PATCH,DELETE)",
    )
    group.addoption(
        "--routes-seed",
        type=int,
        default=None,
        help="Random seed for reproducibility",
    )
    group.addoption(
        "--routes-verbose",
        action="store_true",
        default=False,
        help="Show generated values for each request (path params, query params, body)",
    )
    group.addoption(
        "--routes-schemathesis",
        action="store_true",
        default=False,
        help="Enable Schemathesis integration for schema-based validation",
    )
    group.addoption(
        "--routes-schemathesis-schema-path",
        action="store",
        default="/openapi.json",
        help="Path to fetch OpenAPI schema from app (default: /openapi.json)",
    )
    group.addoption(
        "--routes-report",
        action="store",
        default=None,
        help="Generate HTML report at specified path (e.g., report.html)",
    )
    group.addoption(
        "--routes-report-json",
        action="store",
        default=None,
        help="Generate JSON report at specified path (e.g., report.json)",
    )
    group.addoption(
        "--routes-report-title",
        action="store",
        default="pytest-routes Test Report",
        help="Title for the HTML report",
    )
    group.addoption(
        "--routes-stateful",
        action="store_true",
        default=False,
        help="Enable stateful API testing via state machines",
    )
    group.addoption(
        "--routes-stateful-step-count",
        type=int,
        default=50,
        help="Maximum number of steps per stateful test sequence (default: 50)",
    )
    group.addoption(
        "--routes-stateful-max-examples",
        type=int,
        default=20,
        help="Maximum number of stateful test sequences to generate (default: 20)",
    )
    group.addoption(
        "--routes-stateful-seed",
        type=int,
        default=None,
        help="Random seed for stateful test reproducibility",
    )
    group.addoption(
        "--routes-websocket",
        action="store_true",
        default=False,
        help="Enable WebSocket route testing",
    )
    group.addoption(
        "--routes-ws-max-messages",
        type=int,
        default=10,
        help="Maximum messages per WebSocket test sequence (default: 10)",
    )
    group.addoption(
        "--routes-ws-timeout",
        type=float,
        default=30.0,
        help="WebSocket connection timeout in seconds (default: 30.0)",
    )


def pytest_configure(config: pytest.Config) -> None:
    """Register plugin markers and discover routes if enabled."""
    global _discovered_routes, _all_routes, _route_runner, _routes_enabled
    global _route_config, _test_metrics, _coverage_metrics

    config.addinivalue_line("markers", "routes: mark test as route smoke test")
    config.addinivalue_line("markers", "routes_app(app): specify ASGI app for route testing")
    config.addinivalue_line(
        "markers",
        "routes_skip(reason=None): skip route smoke testing for this test or route pattern",
    )
    config.addinivalue_line(
        "markers",
        "routes_auth(provider): specify authentication provider for route testing",
    )

    # Check if routes testing is enabled
    if not config.getoption("--routes", default=False):
        return

    _routes_enabled = True

    # Load configuration from pyproject.toml first
    try:
        # Try to find pyproject.toml in the project root
        rootdir = Path(config.rootpath) if hasattr(config, "rootpath") else Path.cwd()
        pyproject_path = rootdir / "pyproject.toml"
        file_config = load_config_from_pyproject(pyproject_path if pyproject_path.exists() else None)
    except (ImportError, ValueError) as e:
        # If we can't load from pyproject.toml, use defaults
        print(f"\npytest-routes: Warning - could not load pyproject.toml config: {e}")
        file_config = RouteTestConfig()

    # Build CLI config
    cli_exclude_patterns = []
    if exclude_str := config.getoption("--routes-exclude", default=""):
        cli_exclude_patterns = [p.strip() for p in exclude_str.split(",") if p.strip()]

    cli_include_patterns = []
    if include_str := config.getoption("--routes-include", default=""):
        cli_include_patterns = [p.strip() for p in include_str.split(",") if p.strip()]

    cli_methods_str = config.getoption("--routes-methods", default="GET,POST,PUT,PATCH,DELETE")
    cli_methods = [m.strip().upper() for m in cli_methods_str.split(",")]

    # Build schemathesis config from CLI
    schemathesis_enabled = config.getoption("--routes-schemathesis", default=False)
    schemathesis_config = SchemathesisConfig(
        enabled=schemathesis_enabled,
        schema_path=config.getoption("--routes-schemathesis-schema-path", default="/openapi.json"),
    )

    # Build report config from CLI
    report_path = config.getoption("--routes-report", default=None)
    report_config = ReportConfig(
        enabled=report_path is not None,
        output_path=report_path or "pytest-routes-report.html",
        json_output=config.getoption("--routes-report-json", default=None),
        title=config.getoption("--routes-report-title", default="pytest-routes Test Report"),
    )

    # Build stateful config from CLI
    stateful_enabled = config.getoption("--routes-stateful", default=False)
    stateful_config = None
    if stateful_enabled:
        from pytest_routes.stateful.config import StatefulTestConfig

        stateful_config = StatefulTestConfig(
            enabled=True,
            step_count=config.getoption("--routes-stateful-step-count", default=50),
            max_examples=config.getoption("--routes-stateful-max-examples", default=20),
            seed=config.getoption("--routes-stateful-seed", default=None),
        )

    # Build WebSocket config from CLI
    websocket_enabled = config.getoption("--routes-websocket", default=False)
    websocket_config = None
    if websocket_enabled:
        from pytest_routes.websocket.config import WebSocketTestConfig

        websocket_config = WebSocketTestConfig(
            enabled=True,
            max_messages=config.getoption("--routes-ws-max-messages", default=10),
            connection_timeout=config.getoption("--routes-ws-timeout", default=30.0),
        )

    # Create CLI config (only with values that were explicitly set)
    cli_config = RouteTestConfig(
        max_examples=config.getoption("--routes-max-examples", default=100),
        exclude_patterns=cli_exclude_patterns,
        include_patterns=cli_include_patterns,
        methods=cli_methods,
        seed=config.getoption("--routes-seed", default=None),
        verbose=config.getoption("--routes-verbose", default=False),
        schemathesis=schemathesis_config,
        report=report_config,
        stateful=stateful_config,
        websocket=websocket_config,
    )

    # Merge configs: CLI > pyproject.toml > defaults
    route_config = merge_configs(cli_config, file_config)

    # If exclude/include patterns are empty after merge, use sensible defaults
    if not route_config.exclude_patterns:
        route_config.exclude_patterns = ["/health", "/metrics", "/docs", "/schema*", "/openapi*"]

    # Load the app (check CLI first, then pyproject.toml)
    app_path = config.getoption("--routes-app")
    if not app_path:
        # Try to get from pyproject.toml
        try:
            rootdir = Path(config.rootpath) if hasattr(config, "rootpath") else Path.cwd()
            pyproject_path = rootdir / "pyproject.toml"
            if pyproject_path.exists():
                import sys

                if sys.version_info >= (3, 11):
                    import tomllib
                else:
                    try:
                        import tomli as tomllib  # type: ignore[import-untyped]
                    except ImportError:
                        tomllib = None  # type: ignore[assignment]

                if tomllib is not None:
                    with open(pyproject_path, "rb") as f:
                        data = tomllib.load(f)
                    app_path = data.get("tool", {}).get("pytest-routes", {}).get("app")
        except Exception:
            pass

    if not app_path:
        return

    try:
        module_path, attr = app_path.rsplit(":", 1)
        module = importlib.import_module(module_path)
        app = getattr(module, attr)
    except Exception as e:
        print(f"\npytest-routes: Failed to load app '{app_path}': {e}")
        return

    # Discover routes
    extractor = get_extractor(app)
    routes = extractor.extract_routes(app)
    _all_routes = routes.copy()

    # Filter routes
    for route in routes:
        # Check method filter
        if not any(m in route_config.methods for m in route.methods):
            continue

        # Check exclude patterns
        excluded = False
        for pattern in route_config.exclude_patterns:
            if _matches_pattern(route.path, pattern):
                excluded = True
                break
        if excluded:
            continue

        # Check include patterns (if specified)
        if route_config.include_patterns:
            included = False
            for pattern in route_config.include_patterns:
                if _matches_pattern(route.path, pattern):
                    included = True
                    break
            if not included:
                continue

        _discovered_routes.append(route)

    # Create runner
    _route_runner = RouteTestRunner(app, route_config)

    # Store config for later use
    _route_config = route_config

    # Initialize metrics if reporting is enabled
    if route_config.report.enabled:
        from pytest_routes.reporting.metrics import RunMetrics
        from pytest_routes.reporting.route_coverage import CoverageMetrics

        _test_metrics = RunMetrics()
        _coverage_metrics = CoverageMetrics()

        # Add all routes to coverage tracking
        for route in _all_routes:
            _coverage_metrics.add_route(route)

    # Print discovered routes
    print(f"\n{'=' * 60}")
    print("pytest-routes: Route Discovery")
    print(f"{'=' * 60}")
    print(f"App: {app_path}")
    print(f"Total routes found: {len(routes)}")
    print(f"Routes after filtering: {len(_discovered_routes)}")
    print(f"Max examples: {route_config.max_examples}")
    print(f"Methods: {', '.join(route_config.methods)}")
    if route_config.exclude_patterns:
        print(f"Exclude patterns: {', '.join(route_config.exclude_patterns)}")
    if route_config.include_patterns:
        print(f"Include patterns: {', '.join(route_config.include_patterns)}")
    if route_config.seed is not None:
        print(f"Random seed: {route_config.seed}")
    if route_config.schemathesis.enabled:
        print(f"Schemathesis: enabled (schema: {route_config.schemathesis.schema_path})")
    if route_config.stateful and route_config.stateful.enabled:
        steps = route_config.stateful.step_count
        examples = route_config.stateful.max_examples
        print(f"Stateful testing: enabled (steps: {steps}, examples: {examples})")
    if route_config.websocket and route_config.websocket.enabled:
        print(f"WebSocket testing: enabled (max messages: {route_config.websocket.max_messages})")
    if route_config.report.enabled:
        print(f"Report: {route_config.report.output_path}")
    print("\nRoutes to test:")
    for route in _discovered_routes:
        print(f"  {', '.join(route.methods):20} {route.path}")
    print(f"{'=' * 60}\n")


@pytest.fixture(scope="session")
def route_config(request: pytest.FixtureRequest) -> RouteTestConfig:
    """Build configuration from CLI options and pyproject.toml.

    Configuration priority (highest to lowest):
    1. CLI options
    2. pyproject.toml [tool.pytest-routes]
    3. Built-in defaults
    """
    config = request.config

    # Load from pyproject.toml first
    try:
        rootdir = Path(config.rootpath) if hasattr(config, "rootpath") else Path.cwd()
        pyproject_path = rootdir / "pyproject.toml"
        file_config = load_config_from_pyproject(pyproject_path if pyproject_path.exists() else None)
    except (ImportError, ValueError):
        file_config = RouteTestConfig()

    # Build CLI config
    cli_exclude_patterns = []
    if exclude_str := config.getoption("--routes-exclude", default=""):
        cli_exclude_patterns = [p.strip() for p in exclude_str.split(",") if p.strip()]

    cli_include_patterns = []
    if include_str := config.getoption("--routes-include", default=""):
        cli_include_patterns = [p.strip() for p in include_str.split(",") if p.strip()]

    cli_methods_str = config.getoption("--routes-methods", default="GET,POST,PUT,PATCH,DELETE")
    cli_methods = [m.strip().upper() for m in cli_methods_str.split(",")]

    cli_config = RouteTestConfig(
        max_examples=config.getoption("--routes-max-examples", default=100),
        exclude_patterns=cli_exclude_patterns,
        include_patterns=cli_include_patterns,
        methods=cli_methods,
        seed=config.getoption("--routes-seed", default=None),
    )

    # Merge configs: CLI > pyproject.toml > defaults
    merged = merge_configs(cli_config, file_config)

    # If exclude patterns are empty, use sensible defaults
    if not merged.exclude_patterns:
        merged.exclude_patterns = ["/health", "/metrics", "/docs", "/schema*", "/openapi*"]

    return merged


@pytest.fixture(scope="session")
def asgi_app(request: pytest.FixtureRequest) -> Any:
    """Load the ASGI application."""
    app_path = request.config.getoption("--routes-app")

    if app_path:
        module_path, attr = app_path.rsplit(":", 1)
        module = importlib.import_module(module_path)
        return getattr(module, attr)

    # Try to find from conftest or pytest fixture
    try:
        return request.getfixturevalue("app")
    except pytest.FixtureLookupError:
        pytest.skip("No ASGI app provided. Use --routes-app or define an 'app' fixture.")
        return None


@pytest.fixture(scope="session")
def discovered_routes(asgi_app: Any, route_config: RouteTestConfig) -> list[RouteInfo]:
    """Discover routes from the ASGI application."""
    extractor = get_extractor(asgi_app)
    routes = extractor.extract_routes(asgi_app)

    # Filter routes based on config
    filtered = []
    for route in routes:
        # Check method filter
        if not any(m in route_config.methods for m in route.methods):
            continue

        # Check exclude patterns
        excluded = False
        for pattern in route_config.exclude_patterns:
            if _matches_pattern(route.path, pattern):
                excluded = True
                break
        if excluded:
            continue

        # Check include patterns (if specified)
        if route_config.include_patterns:
            included = False
            for pattern in route_config.include_patterns:
                if _matches_pattern(route.path, pattern):
                    included = True
                    break
            if not included:
                continue

        filtered.append(route)

    return filtered


@pytest.fixture
def route_runner(asgi_app: Any, route_config: RouteTestConfig) -> RouteTestRunner:
    """Provide configured test runner."""
    return RouteTestRunner(asgi_app, route_config)


def _matches_pattern(path: str, pattern: str) -> bool:
    """Check if path matches a glob-like pattern."""
    import fnmatch

    return fnmatch.fnmatch(path, pattern)


class RouteTestItem(pytest.Item):
    """Custom pytest Item for individual route smoke tests.

    This class represents a single test case for a discovered route. Each RouteTestItem
    executes property-based tests against one route using Hypothesis to generate test data.
    The item is created during pytest's collection phase and executed during the test phase.

    Attributes:
        route: The RouteInfo object containing route metadata (path, methods, parameters).
        runner: The RouteTestRunner instance used to execute the route test.
    """

    def __init__(self, name: str, parent: pytest.Collector, route: RouteInfo, runner: RouteTestRunner) -> None:
        """Initialize a RouteTestItem.

        Args:
            name: The test item name (e.g., "test_GET_users_id").
            parent: The parent pytest Collector that owns this item.
            route: The RouteInfo object describing the route to test.
            runner: The RouteTestRunner instance for executing route tests.
        """
        super().__init__(name, parent)
        self.route = route
        self.runner = runner

    def runtest(self) -> None:
        """Execute the route smoke test.

        This pytest hook runs the actual test logic for this item. It executes
        the async route test using the RouteTestRunner, handling the async/sync
        boundary with asyncio. The test uses Hypothesis to generate multiple
        examples of valid requests and validates the route's responses.

        Raises:
            RouteTestError: If the route test fails (e.g., unexpected status code,
                validation error, or exception during test execution).
        """
        import asyncio

        # Run the test
        async def run_test() -> dict:
            return await self.runner.test_route_async(self.route)

        try:
            loop = asyncio.get_running_loop()
            import concurrent.futures

            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, run_test())
                result = future.result()
        except RuntimeError:
            result = asyncio.run(run_test())

        if not result["passed"]:
            raise RouteTestError(self.route, result.get("error", "Unknown error"))

    def repr_failure(
        self,
        excinfo: pytest.ExceptionInfo[BaseException],
        style: str | None = None,
    ) -> str:
        """Represent a test failure for reporting.

        This pytest hook formats the failure output shown to users when a test fails.
        For RouteTestError exceptions, it provides a custom formatted message with
        route details and error information. For other exceptions, it delegates to
        the default pytest failure representation.

        Args:
            excinfo: Exception information captured by pytest.
            style: Optional formatting style for the failure representation.

        Returns:
            A formatted string representation of the test failure.
        """
        if isinstance(excinfo.value, RouteTestError):
            return str(excinfo.value)
        result = super().repr_failure(excinfo, style=style)  # type: ignore[arg-type]
        return str(result)

    def reportinfo(self) -> tuple[str, int | None, str]:
        """Report test information for pytest's output.

        This pytest hook provides metadata about the test for reporting purposes,
        including the file path, line number (if applicable), and a human-readable
        description of what's being tested.

        Returns:
            A tuple of (file_path, line_number, description) where:
                - file_path: Path to the test file (str)
                - line_number: Line number in the file (None for synthetic tests)
                - description: Human-readable test description (e.g., "GET, POST /users/{id}")
        """
        return (
            str(self.path),
            None,
            f"{', '.join(self.route.methods)} {self.route.path}",
        )


class RouteTestError(Exception):
    """Exception raised when a route smoke test fails.

    This exception is raised by RouteTestItem.runtest() when a route test does not
    pass. It contains the route information and error details for reporting.

    Attributes:
        route: The RouteInfo object for the route that failed testing.
        error: A string describing what went wrong during the test.
    """

    def __init__(self, route: RouteInfo, error: str) -> None:
        """Initialize a RouteTestError.

        Args:
            route: The RouteInfo object for the route that failed.
            error: Description of the test failure (e.g., "Expected 200, got 500").
        """
        self.route = route
        self.error = error
        super().__init__(f"Route test failed: {', '.join(route.methods)} {route.path}\n{error}")


class StatefulTestItem(pytest.Item):
    """Custom pytest Item for stateful API testing.

    This item represents a stateful test execution using Hypothesis state machines
    to test API workflows and sequences.

    Attributes:
        runner: The StatefulTestRunner instance for executing stateful tests.
        config: The StatefulTestConfig with test parameters.
    """

    def __init__(
        self,
        name: str,
        parent: pytest.Collector,
        runner: Any,
        config: Any,
    ) -> None:
        """Initialize a StatefulTestItem.

        Args:
            name: The test item name.
            parent: The parent pytest Collector.
            runner: The StatefulTestRunner instance.
            config: The StatefulTestConfig instance.
        """
        super().__init__(name, parent)
        self.runner = runner
        self.config = config

    def runtest(self) -> None:
        """Execute the stateful test.

        Runs the state machine and collects results. Raises an exception
        if any test sequences fail.

        Raises:
            StatefulTestError: If any stateful test sequences fail.
        """
        import asyncio

        async def run_test() -> list[Any]:
            return await self.runner.run_stateful_tests()

        try:
            loop = asyncio.get_running_loop()
            import concurrent.futures

            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, run_test())
                results = future.result()
        except RuntimeError:
            results = asyncio.run(run_test())

        failures = [r for r in results if not r.passed]
        if failures:
            error_messages = []
            for result in failures:
                error_messages.append(f"\n{result.test_name}:")
                for error in result.errors:
                    error_messages.append(f"  - {error}")
            raise StatefulTestError("\n".join(error_messages))

    def repr_failure(
        self,
        excinfo: pytest.ExceptionInfo[BaseException],
        style: str | None = None,
    ) -> str:
        """Represent a test failure for reporting.

        Args:
            excinfo: Exception information captured by pytest.
            style: Optional formatting style for the failure representation.

        Returns:
            A formatted string representation of the test failure.
        """
        if isinstance(excinfo.value, StatefulTestError):
            return str(excinfo.value)
        result = super().repr_failure(excinfo, style=style)  # type: ignore[arg-type]
        return str(result)

    def reportinfo(self) -> tuple[str, int | None, str]:
        """Report test information for pytest's output.

        Returns:
            A tuple of (file_path, line_number, description).
        """
        return str(self.path), None, "stateful: API workflow testing"


class StatefulTestError(Exception):
    """Exception raised when stateful tests fail."""


class WebSocketTestItem(pytest.Item):
    """Custom pytest Item for WebSocket route testing.

    This item represents a WebSocket test execution for a single route.

    Attributes:
        route: The RouteInfo for the WebSocket route.
        runner: The WebSocketTestRunner instance.
    """

    def __init__(
        self,
        name: str,
        parent: pytest.Collector,
        route: RouteInfo,
        runner: Any,
    ) -> None:
        """Initialize a WebSocketTestItem.

        Args:
            name: The test item name.
            parent: The parent pytest Collector.
            route: The RouteInfo for the WebSocket route.
            runner: The WebSocketTestRunner instance.
        """
        super().__init__(name, parent)
        self.route = route
        self.runner = runner

    def runtest(self) -> None:
        """Execute the WebSocket test.

        Runs property-based tests against the WebSocket route.

        Raises:
            WebSocketTestError: If the WebSocket test fails.
        """
        import asyncio

        async def run_test() -> dict:
            return await self.runner.test_route_async(self.route)

        try:
            loop = asyncio.get_running_loop()
            import concurrent.futures

            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, run_test())
                result = future.result()
        except RuntimeError:
            result = asyncio.run(run_test())

        if not result["passed"]:
            raise WebSocketTestError(self.route, result.get("error", "Unknown error"))

    def repr_failure(
        self,
        excinfo: pytest.ExceptionInfo[BaseException],
        style: str | None = None,
    ) -> str:
        """Represent a test failure for reporting.

        Args:
            excinfo: Exception information captured by pytest.
            style: Optional formatting style for the failure representation.

        Returns:
            A formatted string representation of the test failure.
        """
        if isinstance(excinfo.value, WebSocketTestError):
            return str(excinfo.value)
        result = super().repr_failure(excinfo, style=style)  # type: ignore[arg-type]
        return str(result)

    def reportinfo(self) -> tuple[str, int | None, str]:
        """Report test information for pytest's output.

        Returns:
            A tuple of (file_path, line_number, description).
        """
        return str(self.path), None, f"websocket: {self.route.path}"


class WebSocketTestError(Exception):
    """Exception raised when a WebSocket test fails.

    Attributes:
        route: The RouteInfo for the route that failed.
        error: Description of the test failure.
    """

    def __init__(self, route: RouteInfo, error: str) -> None:
        """Initialize a WebSocketTestError.

        Args:
            route: The RouteInfo for the route that failed.
            error: Description of the test failure.
        """
        self.route = route
        self.error = error
        super().__init__(f"WebSocket test failed: {route.path}\n{error}")


class RouteTestCollector(pytest.Collector):
    """Pytest Collector for route smoke tests.

    This collector is responsible for discovering and creating RouteTestItem instances
    from the globally discovered routes. It's part of pytest's collection phase and
    generates test items based on the routes found during plugin configuration.

    Note:
        This collector is currently not actively used in favor of the
        pytest_collection_modifyitems hook, but is kept for potential future use
        or alternative collection strategies.
    """

    def __init__(self, name: str, parent: pytest.Collector) -> None:
        super().__init__(name, parent)

    def collect(self) -> list[RouteTestItem]:
        """Collect route tests from discovered routes.

        This pytest hook creates RouteTestItem instances for each discovered route.
        It's called during pytest's collection phase to gather all tests to be run.

        Returns:
            A list of RouteTestItem instances, one for each discovered route.
            Returns an empty list if route testing is disabled or no routes were
            discovered.
        """
        if not _routes_enabled or not _discovered_routes or not _route_runner:
            return []

        items = []
        for route in _discovered_routes:
            method = route.methods[0]
            path_name = route.path.replace("/", "_").replace("{", "").replace("}", "").replace(":", "_").strip("_")
            name = f"test_{method}_{path_name}" if path_name else f"test_{method}_root"
            items.append(RouteTestItem.from_parent(self, name=name, route=route, runner=_route_runner))
        return items


def pytest_collection_modifyitems(session: pytest.Session, config: pytest.Config, items: list[pytest.Item]) -> None:
    """Add route tests to the collection after standard test discovery.

    This pytest hook modifies the collected test items by adding RouteTestItem instances
    for each discovered route. It runs after pytest's normal collection phase and
    dynamically injects route smoke tests into the test suite.

    Args:
        session: The pytest Session object.
        config: The pytest Config object containing configuration and CLI options.
        items: The list of collected test items to modify (route tests are appended).

    Note:
        This hook uses a guard flag (_routes_collected) to ensure route tests are
        only added once, even if the hook is called multiple times.
    """
    if not _routes_enabled or not _route_config:
        return

    # Check if we already added route tests
    if hasattr(config, "_routes_collected"):
        return
    config._routes_collected = True  # type: ignore[attr-defined]

    # Create HTTP route test items
    if _discovered_routes and _route_runner:
        for route in _discovered_routes:
            method = route.methods[0]
            path_name = route.path.replace("/", "_").replace("{", "").replace("}", "").replace(":", "_").strip("_")
            name = f"test_{method}_{path_name}" if path_name else f"test_{method}_root"

            item = RouteTestItem.from_parent(session, name=name, route=route, runner=_route_runner)
            items.append(item)

    # Create stateful test item if enabled
    if _route_config.stateful and _route_config.stateful.enabled:
        try:
            from pytest_routes.stateful.runner import StatefulTestRunner

            # Get app from the route runner if available
            if _route_runner:
                app = _route_runner.app
                stateful_runner = StatefulTestRunner(app, _route_config.stateful, _route_config)
                stateful_item = StatefulTestItem.from_parent(
                    session,
                    name="test_stateful_api_workflows",
                    runner=stateful_runner,
                    config=_route_config.stateful,
                )
                items.append(stateful_item)
        except ImportError as e:
            print(f"\npytest-routes: Warning - Stateful testing enabled but import failed: {e}")

    # Create WebSocket test items if enabled
    if _route_config.websocket and _route_config.websocket.enabled:
        try:
            from pytest_routes.websocket.runner import WebSocketTestRunner

            # Filter for WebSocket routes
            ws_routes = [r for r in _all_routes if r.is_websocket]

            if ws_routes and _route_runner:
                app = _route_runner.app
                ws_runner = WebSocketTestRunner(app, _route_config)

                for route in ws_routes:
                    path_name = route.path.replace("/", "_").strip("_")
                    name = f"test_ws_{path_name}" if path_name else "test_ws_root"

                    ws_item = WebSocketTestItem.from_parent(
                        session,
                        name=name,
                        route=route,
                        runner=ws_runner,
                    )
                    items.append(ws_item)

                if ws_routes:
                    print(f"\npytest-routes: Added {len(ws_routes)} WebSocket test(s)")
        except ImportError as e:
            print(f"\npytest-routes: Warning - WebSocket testing enabled but import failed: {e}")


def pytest_unconfigure(config: pytest.Config) -> None:
    """Clean up plugin state after test run.

    This pytest hook resets the global state used by the plugin, ensuring that
    subsequent test runs start with a clean slate. It's called when pytest is
    shutting down or when a test session completes.

    Args:
        config: The pytest Config object.
    """
    global _discovered_routes, _all_routes, _route_runner, _routes_enabled
    global _route_config, _test_metrics, _coverage_metrics

    # Generate report if enabled
    if _route_config is not None and _route_config.report.enabled and _test_metrics is not None:
        from pytest_routes.reporting.html import HTMLReportGenerator
        from pytest_routes.reporting.html import ReportConfig as HTMLReportConfig

        _test_metrics.finish()

        report_config = HTMLReportConfig(
            output_path=_route_config.report.output_path,
            title=_route_config.report.title,
            theme=_route_config.report.theme,
        )

        generator = HTMLReportGenerator(report_config)
        report_path = generator.write(_test_metrics, _coverage_metrics)
        print(f"\npytest-routes: Report generated at {report_path}")

        if _route_config.report.json_output:
            json_path = generator.write_json(
                _test_metrics,
                _coverage_metrics,
                output_path=_route_config.report.json_output,
            )
            print(f"pytest-routes: JSON report generated at {json_path}")

    _discovered_routes = []
    _all_routes = []
    _route_runner = None
    _routes_enabled = False
    _route_config = None
    _test_metrics = None
    _coverage_metrics = None
