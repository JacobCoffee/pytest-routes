"""Pytest plugin integration for stateful testing.

This module provides pytest hooks and CLI options for stateful API testing.
It integrates with the main pytest-routes plugin to add stateful testing
capabilities when enabled.

CLI Options:
    --routes-stateful: Enable stateful testing mode
    --routes-stateful-step-count: Maximum steps per test sequence
    --routes-stateful-max-examples: Number of test sequences to generate
    --routes-stateful-recursion-limit: Maximum state recursion depth
    --routes-stateful-fail-fast: Stop on first failure
    --routes-stateful-seed: Random seed for reproducibility

Configuration in pyproject.toml:
    [tool.pytest-routes.stateful]
    enabled = true
    mode = "links"
    step_count = 50
    max_examples = 100
    stateful_recursion_limit = 5
    fail_fast = false
    collect_coverage = true
    verbose = false

    [tool.pytest-routes.stateful.link_config]
    follow_links = true
    max_link_depth = 3

Example Usage:
    # Run with stateful testing
    pytest --routes --routes-stateful --routes-app myapp:app

    # With custom step count
    pytest --routes --routes-stateful --routes-stateful-step-count 100

    # With seed for reproducibility
    pytest --routes --routes-stateful --routes-stateful-seed 12345
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import pytest


def add_stateful_options(parser: pytest.Parser) -> None:
    """Add stateful testing CLI options to pytest.

    This function is called by the main plugin's pytest_addoption hook
    to register stateful testing options.

    Args:
        parser: The pytest argument parser.

    Options Added:
        --routes-stateful: Enable stateful testing mode
        --routes-stateful-mode: Stateful testing mode (links, data_dependency, explicit)
        --routes-stateful-step-count: Maximum steps per test sequence
        --routes-stateful-max-examples: Number of test sequences to generate
        --routes-stateful-recursion-limit: Maximum state recursion depth
        --routes-stateful-timeout-per-step: Timeout per step in seconds
        --routes-stateful-timeout-total: Total timeout in seconds
        --routes-stateful-fail-fast: Stop on first failure
        --routes-stateful-seed: Random seed for reproducibility
        --routes-stateful-verbose: Enable verbose stateful test output
        --routes-stateful-include: Operations to include (glob patterns)
        --routes-stateful-exclude: Operations to exclude (glob patterns)
    """
    group = parser.getgroup("routes-stateful", "Stateful API Testing")

    group.addoption(
        "--routes-stateful",
        action="store_true",
        default=False,
        help="Enable stateful API testing mode",
    )

    group.addoption(
        "--routes-stateful-mode",
        action="store",
        choices=["links", "data_dependency", "explicit"],
        default="links",
        help="Stateful testing mode: 'links' uses OpenAPI links, "
        "'data_dependency' infers from schemas, 'explicit' uses manual config (default: links)",
    )

    group.addoption(
        "--routes-stateful-step-count",
        type=int,
        default=50,
        help="Maximum number of steps (API calls) per test sequence (default: 50)",
    )

    group.addoption(
        "--routes-stateful-max-examples",
        type=int,
        default=100,
        help="Number of test sequences to generate (default: 100)",
    )

    group.addoption(
        "--routes-stateful-recursion-limit",
        type=int,
        default=5,
        help="Maximum depth for nested state transitions (default: 5)",
    )

    group.addoption(
        "--routes-stateful-timeout-per-step",
        type=float,
        default=30.0,
        help="Timeout per step in seconds (default: 30.0)",
    )

    group.addoption(
        "--routes-stateful-timeout-total",
        type=float,
        default=600.0,
        help="Total timeout for entire stateful test run in seconds (default: 600.0)",
    )

    group.addoption(
        "--routes-stateful-fail-fast",
        action="store_true",
        default=False,
        help="Stop stateful testing on first failure instead of collecting all failures",
    )

    group.addoption(
        "--routes-stateful-seed",
        type=int,
        default=None,
        help="Random seed for reproducible stateful test sequences",
    )

    group.addoption(
        "--routes-stateful-verbose",
        action="store_true",
        default=False,
        help="Enable verbose output for stateful test execution",
    )

    group.addoption(
        "--routes-stateful-include",
        action="store",
        default="",
        help="Comma-separated operation patterns to include (e.g., 'create*,get*')",
    )

    group.addoption(
        "--routes-stateful-exclude",
        action="store",
        default="",
        help="Comma-separated operation patterns to exclude (e.g., '*Admin*,*Internal*')",
    )

    group.addoption(
        "--routes-stateful-coverage",
        action="store_true",
        default=True,
        help="Collect state/transition coverage metrics (default: enabled)",
    )

    group.addoption(
        "--routes-stateful-no-coverage",
        action="store_true",
        default=False,
        help="Disable state/transition coverage collection",
    )


def build_stateful_config_from_cli(config: pytest.Config) -> Any:
    """Build StatefulTestConfig from CLI options.

    Extracts CLI options and builds a StatefulTestConfig instance
    that can be merged with file configuration.

    Args:
        config: The pytest Config object.

    Returns:
        StatefulTestConfig instance with CLI values.

    Example:
        >>> # Called during pytest_configure
        >>> stateful_config = build_stateful_config_from_cli(config)
        >>> merged_config = merge_stateful_configs(stateful_config, file_config)
    """
    from pytest_routes.stateful.config import StatefulTestConfig

    include_patterns: list[str] = []
    if include_str := config.getoption("--routes-stateful-include", default=""):
        include_patterns = [p.strip() for p in include_str.split(",") if p.strip()]

    exclude_patterns: list[str] = []
    if exclude_str := config.getoption("--routes-stateful-exclude", default=""):
        exclude_patterns = [p.strip() for p in exclude_str.split(",") if p.strip()]

    collect_coverage = config.getoption("--routes-stateful-coverage", default=True)
    if config.getoption("--routes-stateful-no-coverage", default=False):
        collect_coverage = False

    return StatefulTestConfig(
        enabled=config.getoption("--routes-stateful", default=False),
        mode=config.getoption("--routes-stateful-mode", default="links"),
        step_count=config.getoption("--routes-stateful-step-count", default=50),
        max_examples=config.getoption("--routes-stateful-max-examples", default=100),
        stateful_recursion_limit=config.getoption("--routes-stateful-recursion-limit", default=5),
        timeout_per_step=config.getoption("--routes-stateful-timeout-per-step", default=30.0),
        timeout_total=config.getoption("--routes-stateful-timeout-total", default=600.0),
        fail_fast=config.getoption("--routes-stateful-fail-fast", default=False),
        seed=config.getoption("--routes-stateful-seed", default=None),
        verbose=config.getoption("--routes-stateful-verbose", default=False),
        collect_coverage=collect_coverage,
        include_operations=include_patterns,
        exclude_operations=exclude_patterns,
    )


def print_stateful_config_summary(config: Any) -> None:
    """Print a summary of stateful testing configuration.

    Outputs configuration details when stateful testing is enabled,
    helping users understand what settings are being used.

    Args:
        config: StatefulTestConfig instance.
    """
    print("\n" + "=" * 60)
    print("pytest-routes: Stateful Testing Configuration")
    print("=" * 60)
    print(f"Mode: {config.mode}")
    print(f"Step count: {config.step_count}")
    print(f"Max examples: {config.max_examples}")
    print(f"Recursion limit: {config.stateful_recursion_limit}")
    print(f"Timeout per step: {config.timeout_per_step}s")
    print(f"Timeout total: {config.timeout_total}s")
    print(f"Fail fast: {config.fail_fast}")
    print(f"Collect coverage: {config.collect_coverage}")

    if config.seed is not None:
        print(f"Seed: {config.seed}")

    if config.include_operations:
        print(f"Include operations: {', '.join(config.include_operations)}")

    if config.exclude_operations:
        print(f"Exclude operations: {', '.join(config.exclude_operations)}")

    print("=" * 60 + "\n")


class StatefulTestItem:
    """Pytest Item for stateful API tests.

    Represents a single stateful test sequence that can be collected
    and executed by pytest. Each item runs a complete state machine
    test sequence.

    Attributes:
        name: Test item name.
        runner: StatefulTestRunner for test execution.
        config: StatefulTestConfig for this test.

    Note:
        This class should extend pytest.Item but is kept as a stub
        for the architecture design. The coder agent will implement
        the full pytest integration.
    """

    def __init__(
        self,
        name: str,
        runner: Any,
        config: Any,
    ) -> None:
        """Initialize the stateful test item.

        Args:
            name: Name for the test item.
            runner: StatefulTestRunner instance.
            config: StatefulTestConfig instance.
        """
        self.name = name
        self.runner = runner
        self.config = config

    def runtest(self) -> None:
        """Execute the stateful test sequence.

        Runs the state machine test and collects results.
        Raises assertion error if any test sequence fails.

        Raises:
            AssertionError: If stateful test sequences fail.
        """
        # TODO: Implement test execution
        # import asyncio
        # results = asyncio.run(self.runner.run_stateful_tests())
        # failures = [r for r in results if not r.passed]
        # if failures:
        #     raise AssertionError(f"Stateful tests failed: {len(failures)} failures")

    def reportinfo(self) -> tuple[str, int | None, str]:
        """Report test information.

        Returns:
            Tuple of (filepath, line_number, description).
        """
        return ("", None, f"Stateful API Test: {self.name}")
