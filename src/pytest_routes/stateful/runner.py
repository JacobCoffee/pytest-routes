"""Stateful test runner for pytest-routes.

This module provides the StatefulTestRunner class that orchestrates stateful API testing
using Hypothesis RuleBasedStateMachine and optional Schemathesis integration.

Stateful testing enables testing API workflows where the output of one operation
becomes the input to subsequent operations, simulating real-world API usage patterns.

Architecture:
    StatefulTestRunner
        |
        +-- Uses Schemathesis (if available) for state machine generation
        |   `-- schema.as_state_machine()
        |
        +-- Falls back to custom RuleBasedStateMachine implementation
        |   `-- APIStateMachine (in state_machine.py)
        |
        +-- Integrates with RouteTestRunner for individual request execution
        |
        +-- Collects metrics via StatefulTestResult and TransitionRecord

Example:
    >>> runner = StatefulTestRunner(app, stateful_config)
    >>> results = await runner.run_stateful_tests()
    >>> for result in results:
    ...     print(f"{result.test_name}: {'PASSED' if result.passed else 'FAILED'}")
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Callable

    from pytest_routes.config import RouteTestConfig
    from pytest_routes.discovery.base import RouteInfo
    from pytest_routes.stateful.config import StatefulTestConfig


@dataclass
class TransitionRecord:
    """Record of a single state transition in the state machine.

    Captures details about each API call made during stateful testing,
    including timing, parameters used, and response received.

    Attributes:
        step_number: Sequential step number in the test run (1-indexed).
        operation_id: The OpenAPI operationId or generated operation name.
        method: HTTP method used (GET, POST, PUT, DELETE, etc.).
        path: The API path that was called.
        path_params: Path parameters used in the request.
        query_params: Query parameters used in the request.
        body: Request body (if any).
        status_code: HTTP status code of the response.
        response_body: Response body (may be truncated for large responses).
        duration_ms: Time taken for the request in milliseconds.
        bundle_values_used: Values from bundles that were used as inputs.
        bundle_values_produced: Values extracted and stored in bundles.
        error: Error message if the transition failed.
        timestamp: Unix timestamp when the transition occurred.

    Example:
        >>> record = TransitionRecord(
        ...     step_number=1,
        ...     operation_id="createUser",
        ...     method="POST",
        ...     path="/users",
        ...     body={"name": "Alice"},
        ...     status_code=201,
        ...     duration_ms=45.2,
        ...     bundle_values_produced={"user_id": "12345"},
        ... )
    """

    step_number: int
    operation_id: str
    method: str
    path: str
    path_params: dict[str, Any] = field(default_factory=dict)
    query_params: dict[str, Any] = field(default_factory=dict)
    body: Any = None
    status_code: int | None = None
    response_body: Any = None
    duration_ms: float = 0.0
    bundle_values_used: dict[str, Any] = field(default_factory=dict)
    bundle_values_produced: dict[str, Any] = field(default_factory=dict)
    error: str | None = None
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization.

        Returns:
            Dictionary representation suitable for JSON serialization.
        """
        return {
            "step_number": self.step_number,
            "operation_id": self.operation_id,
            "method": self.method,
            "path": self.path,
            "path_params": self.path_params,
            "query_params": self.query_params,
            "body": self.body,
            "status_code": self.status_code,
            "response_body": self.response_body,
            "duration_ms": self.duration_ms,
            "bundle_values_used": self.bundle_values_used,
            "bundle_values_produced": self.bundle_values_produced,
            "error": self.error,
            "timestamp": self.timestamp,
        }


@dataclass
class StatefulTestResult:
    """Result of a stateful test run.

    Captures the overall outcome of a stateful test execution, including
    all transitions that occurred and coverage metrics.

    Attributes:
        test_name: Name identifying this test run.
        passed: Whether the test passed.
        transitions: List of all transitions that occurred.
        total_steps: Total number of steps executed.
        successful_steps: Number of steps that succeeded.
        failed_steps: Number of steps that failed.
        duration_ms: Total test duration in milliseconds.
        errors: List of error messages encountered.
        coverage: State/transition coverage metrics.
        seed: Random seed used for reproducibility.

    Example:
        >>> result = StatefulTestResult(
        ...     test_name="test_user_crud_workflow",
        ...     passed=True,
        ...     transitions=[...],
        ...     total_steps=50,
        ...     successful_steps=50,
        ...     failed_steps=0,
        ...     duration_ms=1234.5,
        ... )
    """

    test_name: str
    passed: bool
    transitions: list[TransitionRecord] = field(default_factory=list)
    total_steps: int = 0
    successful_steps: int = 0
    failed_steps: int = 0
    duration_ms: float = 0.0
    errors: list[str] = field(default_factory=list)
    coverage: dict[str, Any] = field(default_factory=dict)
    seed: int | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization.

        Returns:
            Dictionary representation suitable for JSON serialization.
        """
        return {
            "test_name": self.test_name,
            "passed": self.passed,
            "transitions": [t.to_dict() for t in self.transitions],
            "total_steps": self.total_steps,
            "successful_steps": self.successful_steps,
            "failed_steps": self.failed_steps,
            "duration_ms": self.duration_ms,
            "errors": self.errors,
            "coverage": self.coverage,
            "seed": self.seed,
        }

    def add_transition(self, transition: TransitionRecord) -> None:
        """Add a transition record to this result.

        Args:
            transition: The transition to add.
        """
        self.transitions.append(transition)
        self.total_steps += 1
        if transition.error:
            self.failed_steps += 1
        else:
            self.successful_steps += 1


class StatefulTestRunner:
    """Orchestrates stateful API testing using state machines.

    The StatefulTestRunner coordinates stateful test execution by:
    1. Loading the OpenAPI schema (via Schemathesis or discovery)
    2. Building a state machine with operations as rules
    3. Managing bundles for value exchange between operations
    4. Executing the state machine with Hypothesis
    5. Collecting and reporting results

    This class integrates with Schemathesis when available but provides
    fallback functionality using Hypothesis RuleBasedStateMachine directly.

    Attributes:
        app: The ASGI application under test.
        config: StatefulTestConfig with test parameters.
        route_config: Optional RouteTestConfig for shared settings.
        _schema: Cached OpenAPI schema (loaded lazily).
        _state_machine_class: Generated state machine class.
        _results: Collected test results.

    Example:
        >>> from pytest_routes.stateful import StatefulTestConfig, StatefulTestRunner
        >>> config = StatefulTestConfig(enabled=True, step_count=50)
        >>> runner = StatefulTestRunner(app, config)
        >>> results = await runner.run_stateful_tests()

    Integration with Schemathesis:
        When Schemathesis is installed, the runner uses `schema.as_state_machine()`
        to generate the state machine. This provides:
        - Automatic OpenAPI link detection
        - Proper request/response validation
        - Bundle management based on response schemas

        Without Schemathesis, the runner falls back to a custom implementation
        that provides basic stateful testing capabilities.
    """

    def __init__(
        self,
        app: Any,
        config: StatefulTestConfig,
        route_config: RouteTestConfig | None = None,
    ) -> None:
        """Initialize the StatefulTestRunner.

        Args:
            app: The ASGI application to test.
            config: Configuration for stateful testing.
            route_config: Optional general route test configuration.
        """
        self.app = app
        self.config = config
        self.route_config = route_config
        self._schema: Any = None
        self._state_machine_class: type | None = None
        self._results: list[StatefulTestResult] = []
        self._context: dict[str, Any] = {}
        self._schemathesis_available: bool | None = None

    @property
    def schemathesis_available(self) -> bool:
        """Check if Schemathesis is available.

        Returns:
            True if Schemathesis is installed and can be used.
        """
        if self._schemathesis_available is None:
            try:
                import schemathesis  # noqa: F401

                self._schemathesis_available = True
            except ImportError:
                self._schemathesis_available = False
        return self._schemathesis_available

    def load_schema(self, schema_path: str = "/openapi.json") -> Any:
        """Load the OpenAPI schema from the application.

        Args:
            schema_path: Path to the OpenAPI schema endpoint.

        Returns:
            The loaded schema object (Schemathesis schema or dict).

        Raises:
            RuntimeError: If schema loading fails.

        Example:
            >>> runner = StatefulTestRunner(app, config)
            >>> schema = runner.load_schema("/openapi.json")
        """
        if self._schema is not None:
            return self._schema

        if self.schemathesis_available:
            try:
                import schemathesis.openapi

                self._schema = schemathesis.openapi.from_asgi(schema_path, app=self.app)
                return self._schema
            except Exception as e:
                msg = f"Failed to load schema via Schemathesis from {schema_path}: {e}"
                raise RuntimeError(msg) from e

        try:
            import json

            from pytest_routes.execution.client import RouteTestClient

            client = RouteTestClient(self.app)
            loop = asyncio.get_event_loop()
            response = loop.run_until_complete(client.get(schema_path))

            http_ok = 200
            if response.status_code != http_ok:
                msg = f"Failed to fetch schema from {schema_path}: HTTP {response.status_code}"
                raise RuntimeError(msg)

            self._schema = json.loads(response.text)
            return self._schema

        except Exception as e:
            msg = f"Failed to load OpenAPI schema from {schema_path}: {e}"
            raise RuntimeError(msg) from e

    def build_state_machine(self) -> type:
        """Build the Hypothesis RuleBasedStateMachine class.

        Creates a state machine class with rules for each API operation.
        Uses Schemathesis's `as_state_machine()` when available, otherwise
        builds a custom state machine.

        Returns:
            A class extending RuleBasedStateMachine.

        Raises:
            RuntimeError: If state machine cannot be built.

        Example:
            >>> runner = StatefulTestRunner(app, config)
            >>> StateMachine = runner.build_state_machine()
            >>> # StateMachine can now be run with Hypothesis

        Architecture Notes:
            The state machine includes:
            - A rule for each API operation that passes filters
            - Bundles for each resource type (based on OpenAPI schemas)
            - Invariants for state consistency checks
            - Setup/teardown for lifecycle management
        """
        if self._state_machine_class is not None:
            return self._state_machine_class

        schema = self.load_schema()

        if self.schemathesis_available and self.config.mode == "links":
            try:
                if hasattr(schema, "as_state_machine"):
                    self._state_machine_class = schema.as_state_machine()
                    return self._state_machine_class
            except Exception as e:
                if self.config.verbose:
                    import logging

                    logger = logging.getLogger(__name__)
                    logger.warning(
                        "Failed to build Schemathesis state machine: %s, falling back to custom implementation",
                        e,
                    )

        from pytest_routes.stateful.state_machine import build_api_state_machine

        openapi_schema = schema if isinstance(schema, dict) else None
        self._state_machine_class = build_api_state_machine(
            app=self.app,
            config=self.config,
            openapi_schema=openapi_schema,
        )

        return self._state_machine_class

    async def run_stateful_tests(self) -> list[StatefulTestResult]:
        """Execute stateful tests and return results.

        Runs the state machine with Hypothesis, collecting results for
        each test sequence generated.

        Returns:
            List of StatefulTestResult objects, one per test sequence.

        Raises:
            RuntimeError: If tests cannot be executed.

        Example:
            >>> runner = StatefulTestRunner(app, config)
            >>> results = await runner.run_stateful_tests()
            >>> passed = sum(1 for r in results if r.passed)
            >>> print(f"{passed}/{len(results)} test sequences passed")
        """
        if not self.config.enabled:
            return []

        self._results = []
        start_time = time.time()

        # Execute lifecycle setup hook
        if self.config.hook_config.enable_hooks and self.config.hook_config.setup_hook:
            await self._run_hook(self.config.hook_config.setup_hook, self._context)

        try:
            # TODO: Implement actual test execution
            # This involves:
            # 1. Building the state machine
            # 2. Running it with Hypothesis settings
            # 3. Capturing each transition
            # 4. Building results

            if self.schemathesis_available:
                results = await self._run_with_schemathesis()
            else:
                results = await self._run_with_hypothesis()

            self._results = results

        finally:
            # Execute lifecycle teardown hook
            if self.config.hook_config.enable_hooks and self.config.hook_config.teardown_hook:
                await self._run_hook(self.config.hook_config.teardown_hook, self._context)

        duration_ms = (time.time() - start_time) * 1000

        # Update total duration on results
        for result in self._results:
            if result.duration_ms == 0:
                result.duration_ms = duration_ms / max(len(self._results), 1)

        return self._results

    async def _run_with_schemathesis(self) -> list[StatefulTestResult]:
        """Run stateful tests using Schemathesis.

        Uses Schemathesis's state machine capabilities for comprehensive
        stateful testing with OpenAPI link support.

        Returns:
            List of StatefulTestResult objects.

        Note:
            This method requires Schemathesis to be installed.
        """
        from hypothesis import Phase, Verbosity, settings
        from hypothesis.stateful import run_state_machine_as_test

        results: list[StatefulTestResult] = []
        state_machine_class = self.build_state_machine()

        result = StatefulTestResult(
            test_name="stateful_test_schemathesis",
            passed=True,
            seed=self.config.seed,
        )

        start_time = time.time()

        try:
            test_settings = settings(
                max_examples=self.config.max_examples,
                stateful_step_count=self.config.step_count,
                deadline=None,
                suppress_health_check=list(Phase),
                verbosity=Verbosity.verbose if self.config.verbose else Verbosity.normal,
            )
            run_state_machine_as_test(state_machine_class, settings=test_settings)
            result.passed = True
        except Exception as e:
            result.passed = False
            result.errors.append(str(e))

        result.duration_ms = (time.time() - start_time) * 1000
        results.append(result)

        return results

    async def _run_with_hypothesis(self) -> list[StatefulTestResult]:
        """Run stateful tests using Hypothesis RuleBasedStateMachine directly.

        Fallback implementation when Schemathesis is not available.
        Provides basic stateful testing capabilities.

        Returns:
            List of StatefulTestResult objects.
        """
        from hypothesis import Phase, Verbosity, settings
        from hypothesis.stateful import run_state_machine_as_test

        results: list[StatefulTestResult] = []
        state_machine_class = self.build_state_machine()

        result = StatefulTestResult(
            test_name="stateful_test_hypothesis",
            passed=True,
            seed=self.config.seed,
        )

        start_time = time.time()

        try:
            test_settings = settings(
                max_examples=self.config.max_examples,
                stateful_step_count=self.config.step_count,
                deadline=None,
                suppress_health_check=list(Phase),
                verbosity=Verbosity.verbose if self.config.verbose else Verbosity.normal,
            )
            run_state_machine_as_test(state_machine_class, settings=test_settings)
            result.passed = True
        except Exception as e:
            result.passed = False
            result.errors.append(str(e))

        result.duration_ms = (time.time() - start_time) * 1000
        results.append(result)

        return results

    async def _run_hook(
        self,
        hook: Callable[..., Any],
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        """Execute a lifecycle hook with timeout handling.

        Args:
            hook: The hook function to execute.
            *args: Positional arguments for the hook.
            **kwargs: Keyword arguments for the hook.

        Returns:
            The hook's return value.

        Raises:
            asyncio.TimeoutError: If hook exceeds timeout.
        """
        timeout = self.config.hook_config.hook_timeout

        if asyncio.iscoroutinefunction(hook):
            return await asyncio.wait_for(hook(*args, **kwargs), timeout=timeout)

        # Run sync hook in executor
        loop = asyncio.get_event_loop()
        return await asyncio.wait_for(
            loop.run_in_executor(None, lambda: hook(*args, **kwargs)),
            timeout=timeout,
        )

    def create_transition_record(
        self,
        step_number: int,
        operation_id: str,
        method: str,
        path: str,
        **kwargs: Any,
    ) -> TransitionRecord:
        """Create a TransitionRecord for logging a state transition.

        Factory method for creating transition records with consistent defaults.

        Args:
            step_number: The step number in the test sequence.
            operation_id: The operation identifier.
            method: HTTP method.
            path: API path.
            **kwargs: Additional TransitionRecord fields.

        Returns:
            A new TransitionRecord instance.

        Example:
            >>> record = runner.create_transition_record(
            ...     step_number=1,
            ...     operation_id="createUser",
            ...     method="POST",
            ...     path="/users",
            ...     body={"name": "Alice"},
            ... )
        """
        return TransitionRecord(
            step_number=step_number,
            operation_id=operation_id,
            method=method,
            path=path,
            **kwargs,
        )

    def get_results(self) -> list[StatefulTestResult]:
        """Get the collected test results.

        Returns:
            List of StatefulTestResult objects from the last test run.
        """
        return self._results

    def get_coverage_metrics(self) -> dict[str, Any]:
        """Calculate coverage metrics from test results.

        Analyzes the transitions to determine:
        - Operation coverage: Which operations were tested
        - Transition coverage: Which state transitions were exercised
        - Link coverage: Which OpenAPI links were followed

        Returns:
            Dictionary with coverage metrics.

        Example:
            >>> runner = StatefulTestRunner(app, config)
            >>> await runner.run_stateful_tests()
            >>> coverage = runner.get_coverage_metrics()
            >>> print(f"Operation coverage: {coverage['operation_coverage_pct']}%")
        """
        if not self._results:
            return {
                "operation_coverage_pct": 0.0,
                "transition_coverage_pct": 0.0,
                "link_coverage_pct": 0.0,
                "operations_tested": [],
                "operations_untested": [],
                "transitions_count": 0,
            }

        operations_tested = set()
        transitions_count = 0
        transition_pairs = set()

        for result in self._results:
            prev_op = None
            for transition in result.transitions:
                operations_tested.add(transition.operation_id)
                transitions_count += 1

                if prev_op:
                    transition_pairs.add((prev_op, transition.operation_id))
                prev_op = transition.operation_id

        all_operations = self._get_all_operations_from_schema()
        operations_untested = all_operations - operations_tested

        operation_coverage_pct = (len(operations_tested) / len(all_operations) * 100) if all_operations else 0.0

        total_possible_transitions = len(all_operations) * len(all_operations) if all_operations else 1
        transition_coverage_pct = (len(transition_pairs) / total_possible_transitions * 100) if all_operations else 0.0

        links_count = self._count_openapi_links()
        links_followed = self._count_links_followed(transition_pairs)
        link_coverage_pct = (links_followed / links_count * 100) if links_count > 0 else 0.0

        return {
            "operation_coverage_pct": round(operation_coverage_pct, 2),
            "transition_coverage_pct": round(transition_coverage_pct, 2),
            "link_coverage_pct": round(link_coverage_pct, 2),
            "operations_tested": sorted(operations_tested),
            "operations_untested": sorted(operations_untested),
            "transitions_count": transitions_count,
            "unique_transitions": len(transition_pairs),
            "total_operations": len(all_operations),
            "total_links": links_count,
        }

    def _get_all_operations_from_schema(self) -> set[str]:
        """Extract all operation IDs from the OpenAPI schema."""
        operations = set()

        if not self._schema:
            return operations

        if isinstance(self._schema, dict):
            paths = self._schema.get("paths", {})
            for path, path_item in paths.items():
                for method in ["get", "post", "put", "patch", "delete", "options", "head", "trace"]:
                    if method in path_item:
                        operation = path_item[method]
                        op_id = operation.get("operationId", f"{method}_{path.replace('/', '_').strip('_')}")
                        if self.config.should_include_operation(op_id):
                            operations.add(op_id)

        return operations

    def _count_openapi_links(self) -> int:
        """Count total number of OpenAPI links in the schema."""
        if not isinstance(self._schema, dict):
            return 0

        link_count = 0
        paths = self._schema.get("paths", {})

        for path_item in paths.values():
            for method_data in path_item.values():
                if not isinstance(method_data, dict):
                    continue
                responses = method_data.get("responses", {})
                for response in responses.values():
                    if isinstance(response, dict) and "links" in response:
                        link_count += len(response["links"])

        return link_count

    def _count_links_followed(self, transition_pairs: set[tuple[str, str]]) -> int:
        """Count how many OpenAPI links were actually followed."""
        if not isinstance(self._schema, dict):
            return 0

        followed = 0
        paths = self._schema.get("paths", {})

        for path_item in paths.values():
            for method_data in path_item.values():
                if not isinstance(method_data, dict):
                    continue

                source_op_id = method_data.get("operationId")
                if not source_op_id:
                    continue

                responses = method_data.get("responses", {})
                for response in responses.values():
                    if not isinstance(response, dict):
                        continue

                    links = response.get("links", {})
                    for link in links.values():
                        if isinstance(link, dict):
                            target_op_id = link.get("operationId")
                            if target_op_id and (source_op_id, target_op_id) in transition_pairs:
                                followed += 1

        return followed

    def reset(self) -> None:
        """Reset the runner state for a new test run.

        Clears cached results and prepares for fresh test execution.
        """
        self._results = []
        self._context = {}


class StatefulTestFactory:
    """Factory for creating stateful test functions.

    Creates pytest-compatible test functions from the StatefulTestRunner
    for integration with pytest's collection and execution.

    This factory generates test items that can be collected by pytest
    and executed as part of the normal test run.

    Example:
        >>> factory = StatefulTestFactory(runner)
        >>> test_func = factory.create_test("test_user_workflow")
        >>> # test_func can now be collected by pytest
    """

    def __init__(self, runner: StatefulTestRunner) -> None:
        """Initialize the factory.

        Args:
            runner: The StatefulTestRunner to use for test execution.
        """
        self.runner = runner

    def create_test(self, name: str) -> Callable[[], None]:
        """Create a test function for stateful testing.

        Args:
            name: Name for the test function.

        Returns:
            A callable test function compatible with pytest.

        Example:
            >>> factory = StatefulTestFactory(runner)
            >>> test_func = factory.create_test("test_api_workflow")
            >>> test_func()  # Executes the stateful test
        """

        def test_stateful() -> None:
            """Execute stateful API tests."""
            # TODO: Implement test function
            # This runs the state machine synchronously for pytest compatibility

            # import asyncio
            # results = asyncio.run(runner.run_stateful_tests())
            # failures = [r for r in results if not r.passed]
            # if failures:
            #     error_msg = "\n".join(f"{r.test_name}: {r.errors}" for r in failures)
            #     raise AssertionError(f"Stateful tests failed:\n{error_msg}")

        test_stateful.__name__ = name
        test_stateful.__doc__ = f"Stateful API test: {name}"

        return test_stateful

    def create_tests_for_routes(
        self,
        routes: list[RouteInfo],
    ) -> list[Callable[[], None]]:
        """Create test functions for a list of routes.

        Generates stateful test functions that cover workflows
        involving the specified routes.

        Args:
            routes: List of routes to create tests for.

        Returns:
            List of test functions.

        Example:
            >>> factory = StatefulTestFactory(runner)
            >>> tests = factory.create_tests_for_routes(discovered_routes)
        """
        # TODO: Implement route-based test generation
        # This could:
        # 1. Group routes by resource type
        # 2. Create CRUD workflow tests for each resource
        # 3. Create cross-resource integration tests

        return []
