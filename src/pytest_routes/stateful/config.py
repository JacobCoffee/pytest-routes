"""Configuration for stateful testing.

This module defines configuration dataclasses for stateful API testing with pytest-routes.
Stateful testing enables testing API workflows where responses from one operation
inform subsequent operations (e.g., POST /users returns an ID used in GET /users/{id}).

The configuration supports:
    - OpenAPI link-based state transitions
    - Custom lifecycle hooks (setup, teardown, before/after call)
    - Step limits and recursion depth control
    - Bundle filtering and transformation
    - Integration with Schemathesis state machines
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Literal

if TYPE_CHECKING:
    from collections.abc import Callable

    from pytest_routes.auth.providers import AuthProvider
    from pytest_routes.discovery.base import RouteInfo


@dataclass
class LinkConfig:
    """Configuration for OpenAPI link handling in stateful tests.

    OpenAPI links define relationships between operations, enabling pytest-routes
    to automatically build test sequences that mirror real API workflows.

    Attributes:
        follow_links: Whether to follow OpenAPI links for state transitions.
        link_timeout: Timeout for link traversal operations in seconds.
        max_link_depth: Maximum depth for following nested links.
        link_filters: Patterns to include/exclude specific links.
        parameter_mapping: Custom mapping of link parameters to values.

    Example:
        >>> link_config = LinkConfig(
        ...     follow_links=True,
        ...     max_link_depth=3,
        ...     link_filters={"include": ["GetUser*"], "exclude": ["*Admin*"]},
        ... )

    OpenAPI Link Example:
        In an OpenAPI spec, links define how response values map to subsequent requests::

            paths:
              /users:
                post:
                  responses:
                    201:
                      links:
                        GetUserById:
                          operationId: getUser
                          parameters:
                            userId: '$response.body#/id'
              /users/{userId}:
                get:
                  operationId: getUser

        This link tells pytest-routes that after POSTing a user, the returned ID
        should be used to test GET /users/{userId}.
    """

    follow_links: bool = True
    link_timeout: float = 30.0
    max_link_depth: int = 5
    link_filters: dict[str, list[str]] = field(default_factory=dict)
    parameter_mapping: dict[str, str] = field(default_factory=dict)


@dataclass
class HookConfig:
    """Configuration for stateful test lifecycle hooks.

    Lifecycle hooks allow custom behavior at key points during stateful test execution:
    - setup: Called once before the state machine starts
    - teardown: Called once after the state machine completes
    - before_call: Called before each API operation
    - after_call: Called after each API operation with the response

    Attributes:
        enable_hooks: Whether lifecycle hooks are enabled.
        setup_hook: Optional callable for state machine setup.
        teardown_hook: Optional callable for state machine teardown.
        before_call_hook: Optional callable before each API call.
        after_call_hook: Optional callable after each API call.
        on_error_hook: Optional callable when an error occurs.
        hook_timeout: Timeout for hook execution in seconds.

    Example:
        >>> def my_setup(context: dict) -> None:
        ...     context["auth_token"] = get_test_token()
        >>> def my_after_call(response: Any, context: dict) -> None:
        ...     if response.status_code == 401:
        ...         context["auth_token"] = refresh_token()
        >>> hook_config = HookConfig(
        ...     enable_hooks=True,
        ...     setup_hook=my_setup,
        ...     after_call_hook=my_after_call,
        ... )

    Hook Signatures:
        - setup_hook: (context: dict[str, Any]) -> None
        - teardown_hook: (context: dict[str, Any]) -> None
        - before_call_hook: (operation: str, params: dict, context: dict) -> dict | None
        - after_call_hook: (response: Any, operation: str, context: dict) -> None
        - on_error_hook: (error: Exception, operation: str, context: dict) -> None
    """

    enable_hooks: bool = False
    setup_hook: Callable[[dict[str, Any]], None] | None = None
    teardown_hook: Callable[[dict[str, Any]], None] | None = None
    before_call_hook: Callable[[str, dict[str, Any], dict[str, Any]], dict[str, Any] | None] | None = None
    after_call_hook: Callable[[Any, str, dict[str, Any]], None] | None = None
    on_error_hook: Callable[[Exception, str, dict[str, Any]], None] | None = None
    hook_timeout: float = 10.0


@dataclass
class StatefulTestConfig:
    """Configuration for stateful API testing.

    Stateful testing enables testing API workflows and sequences where responses
    from one endpoint are used as inputs to subsequent endpoints. This is essential
    for testing CRUD workflows, authentication flows, and complex API interactions.

    Attributes:
        enabled: Whether stateful testing is enabled.
        mode: Stateful testing mode ('links', 'data_dependency', 'explicit').
        step_count: Maximum number of steps (API calls) per test run.
        stateful_recursion_limit: Maximum depth for nested state transitions.
        max_examples: Number of test sequences to generate.
        seed: Random seed for reproducibility.
        timeout_per_step: Timeout for each step in seconds.
        timeout_total: Total timeout for the entire state machine run.
        fail_fast: Stop on first failure instead of collecting all failures.
        collect_coverage: Whether to track state/transition coverage.
        verbose: Enable detailed logging of state machine execution.
        auth: Authentication provider for all operations.
        link_config: Configuration for OpenAPI link handling.
        hook_config: Configuration for lifecycle hooks.
        include_operations: Operation IDs/patterns to include.
        exclude_operations: Operation IDs/patterns to exclude.
        bundle_strategies: Custom Hypothesis strategies for bundles.
        initial_state: Initial state values for the state machine.

    Example:
        >>> config = StatefulTestConfig(
        ...     enabled=True,
        ...     mode="links",
        ...     step_count=50,
        ...     max_examples=100,
        ...     stateful_recursion_limit=5,
        ...     fail_fast=False,
        ...     collect_coverage=True,
        ...     verbose=True,
        ... )

    Stateful Testing Workflow:
        1. Parse OpenAPI schema to identify operations and links
        2. Build Hypothesis RuleBasedStateMachine with operations as rules
        3. Create bundles for each resource type (users, posts, etc.)
        4. Generate test sequences that:
           - Create resources (POST) and store IDs in bundles
           - Retrieve resources (GET) using IDs from bundles
           - Update resources (PUT/PATCH) using stored IDs
           - Delete resources (DELETE) using stored IDs
        5. Validate responses and state consistency at each step

    Integration with Schemathesis:
        When Schemathesis is available, this config enables integration with
        Schemathesis's state machine capabilities via `schema.as_state_machine()`.
        The config options map to Schemathesis settings while providing
        additional pytest-routes specific features.
    """

    enabled: bool = False
    mode: Literal["links", "data_dependency", "explicit"] = "links"
    step_count: int = 50
    stateful_recursion_limit: int = 5
    max_examples: int = 100
    seed: int | None = None
    timeout_per_step: float = 30.0
    timeout_total: float = 600.0
    fail_fast: bool = False
    collect_coverage: bool = True
    verbose: bool = False
    auth: AuthProvider | None = None
    link_config: LinkConfig = field(default_factory=LinkConfig)
    hook_config: HookConfig = field(default_factory=HookConfig)
    include_operations: list[str] = field(default_factory=list)
    exclude_operations: list[str] = field(default_factory=list)
    bundle_strategies: dict[str, Any] = field(default_factory=dict)
    initial_state: dict[str, Any] = field(default_factory=dict)

    def should_include_operation(self, operation_id: str, route: RouteInfo | None = None) -> bool:
        """Check if an operation should be included in stateful testing.

        Applies include/exclude filters to determine if an operation should
        be part of the state machine.

        Args:
            operation_id: The OpenAPI operationId or generated operation name.
            route: Optional RouteInfo for additional filtering context.

        Returns:
            True if the operation should be included, False otherwise.

        Example:
            >>> config = StatefulTestConfig(
            ...     include_operations=["create*", "get*"],
            ...     exclude_operations=["*Admin*"],
            ... )
            >>> config.should_include_operation("createUser")
            True
            >>> config.should_include_operation("deleteAdminUser")
            False
        """
        import fnmatch

        if self.exclude_operations and any(
            fnmatch.fnmatch(operation_id, pattern) for pattern in self.exclude_operations
        ):
            return False

        if self.include_operations:
            return any(fnmatch.fnmatch(operation_id, pattern) for pattern in self.include_operations)

        return True

    def get_effective_timeout(self, step_number: int) -> float:
        """Calculate effective timeout for a step considering total timeout.

        Args:
            step_number: The current step number (1-indexed).

        Returns:
            Timeout in seconds for this step, adjusted for remaining budget.

        Example:
            >>> config = StatefulTestConfig(timeout_per_step=30.0, timeout_total=100.0)
            >>> config.get_effective_timeout(1)  # First step: full budget
            30.0
            >>> # Later steps may have reduced timeout if total budget is consumed
        """
        remaining_budget = self.timeout_total - (step_number - 1) * self.timeout_per_step
        return min(self.timeout_per_step, max(1.0, remaining_budget))

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> StatefulTestConfig:
        """Create StatefulTestConfig from a dictionary.

        Parses configuration from pyproject.toml or other dictionary sources.

        Args:
            data: Dictionary containing stateful test configuration.

        Returns:
            StatefulTestConfig instance.

        Example config in pyproject.toml::

            [tool.pytest - routes.stateful]
            enabled = true
            mode = "links"
            step_count = 50
            max_examples = 100
            stateful_recursion_limit = 5

            [tool.pytest - routes.stateful.link_config]
            follow_links = true
            max_link_depth = 3

            [tool.pytest - routes.stateful.hook_config]
            enable_hooks = false
        """
        defaults = cls()

        link_data = data.get("link_config", {})
        link_config = LinkConfig(
            follow_links=link_data.get("follow_links", defaults.link_config.follow_links),
            link_timeout=link_data.get("link_timeout", defaults.link_config.link_timeout),
            max_link_depth=link_data.get("max_link_depth", defaults.link_config.max_link_depth),
            link_filters=link_data.get("link_filters", defaults.link_config.link_filters),
            parameter_mapping=link_data.get("parameter_mapping", defaults.link_config.parameter_mapping),
        )

        hook_data = data.get("hook_config", {})
        hook_config = HookConfig(
            enable_hooks=hook_data.get("enable_hooks", defaults.hook_config.enable_hooks),
            hook_timeout=hook_data.get("hook_timeout", defaults.hook_config.hook_timeout),
        )

        return cls(
            enabled=data.get("enabled", defaults.enabled),
            mode=data.get("mode", defaults.mode),
            step_count=data.get("step_count", defaults.step_count),
            stateful_recursion_limit=data.get("stateful_recursion_limit", defaults.stateful_recursion_limit),
            max_examples=data.get("max_examples", defaults.max_examples),
            seed=data.get("seed", defaults.seed),
            timeout_per_step=data.get("timeout_per_step", defaults.timeout_per_step),
            timeout_total=data.get("timeout_total", defaults.timeout_total),
            fail_fast=data.get("fail_fast", defaults.fail_fast),
            collect_coverage=data.get("collect_coverage", defaults.collect_coverage),
            verbose=data.get("verbose", defaults.verbose),
            link_config=link_config,
            hook_config=hook_config,
            include_operations=data.get("include_operations", defaults.include_operations),
            exclude_operations=data.get("exclude_operations", defaults.exclude_operations),
            bundle_strategies=data.get("bundle_strategies", defaults.bundle_strategies),
            initial_state=data.get("initial_state", defaults.initial_state),
        )


def merge_stateful_configs(
    cli_config: StatefulTestConfig | None,
    file_config: StatefulTestConfig | None,
) -> StatefulTestConfig:
    """Merge CLI and file stateful configs with CLI taking precedence.

    Args:
        cli_config: Configuration from CLI options.
        file_config: Configuration from pyproject.toml.

    Returns:
        Merged StatefulTestConfig with CLI options taking precedence.

    Example:
        >>> file_cfg = StatefulTestConfig(step_count=50, max_examples=100)
        >>> cli_cfg = StatefulTestConfig(step_count=25)  # Override step_count
        >>> merged = merge_stateful_configs(cli_cfg, file_cfg)
        >>> merged.step_count
        25
        >>> merged.max_examples
        100
    """
    defaults = StatefulTestConfig()

    if cli_config is None and file_config is None:
        return defaults

    if cli_config is None:
        return file_config or defaults

    if file_config is None:
        return cli_config

    return StatefulTestConfig(
        enabled=cli_config.enabled if cli_config.enabled != defaults.enabled else file_config.enabled,
        mode=cli_config.mode if cli_config.mode != defaults.mode else file_config.mode,
        step_count=cli_config.step_count if cli_config.step_count != defaults.step_count else file_config.step_count,
        stateful_recursion_limit=(
            cli_config.stateful_recursion_limit
            if cli_config.stateful_recursion_limit != defaults.stateful_recursion_limit
            else file_config.stateful_recursion_limit
        ),
        max_examples=(
            cli_config.max_examples if cli_config.max_examples != defaults.max_examples else file_config.max_examples
        ),
        seed=cli_config.seed if cli_config.seed is not None else file_config.seed,
        timeout_per_step=(
            cli_config.timeout_per_step
            if cli_config.timeout_per_step != defaults.timeout_per_step
            else file_config.timeout_per_step
        ),
        timeout_total=(
            cli_config.timeout_total
            if cli_config.timeout_total != defaults.timeout_total
            else file_config.timeout_total
        ),
        fail_fast=cli_config.fail_fast if cli_config.fail_fast != defaults.fail_fast else file_config.fail_fast,
        collect_coverage=(
            cli_config.collect_coverage
            if cli_config.collect_coverage != defaults.collect_coverage
            else file_config.collect_coverage
        ),
        verbose=cli_config.verbose if cli_config.verbose != defaults.verbose else file_config.verbose,
        auth=cli_config.auth if cli_config.auth is not None else file_config.auth,
        link_config=(
            cli_config.link_config if cli_config.link_config != defaults.link_config else file_config.link_config
        ),
        hook_config=(
            cli_config.hook_config if cli_config.hook_config != defaults.hook_config else file_config.hook_config
        ),
        include_operations=cli_config.include_operations or file_config.include_operations,
        exclude_operations=cli_config.exclude_operations or file_config.exclude_operations,
        bundle_strategies={**file_config.bundle_strategies, **cli_config.bundle_strategies},
        initial_state={**file_config.initial_state, **cli_config.initial_state},
    )
