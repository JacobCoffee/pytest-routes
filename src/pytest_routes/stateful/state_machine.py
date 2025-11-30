"""State machine implementation for stateful API testing.

This module provides the APIStateMachine class, a Hypothesis RuleBasedStateMachine
implementation for stateful API testing. It serves as a fallback when Schemathesis
is not available, or can be extended for custom stateful testing scenarios.

Architecture:
    The state machine is built dynamically based on:
    1. Discovered routes from the ASGI application
    2. OpenAPI schema (if available) for link relationships
    3. User-defined bundle configurations

    Each API operation becomes a rule in the state machine, with:
    - Input bundles for parameters that depend on previous responses
    - Output bundles for values extracted from responses
    - Preconditions based on required state

Example:
    >>> from pytest_routes.stateful.state_machine import build_api_state_machine
    >>> StateMachine = build_api_state_machine(app, config)
    >>> # Run with Hypothesis
    >>> run_state_machine_as_test(StateMachine)

Bundle System:
    Bundles are named collections of values that can be passed between rules.
    For REST APIs, common bundles include:
    - user_ids: IDs returned from POST /users
    - post_ids: IDs returned from POST /posts
    - auth_tokens: Tokens from POST /auth/login

    Example bundle flow:
        1. POST /users returns {"id": "123"}
        2. "123" is stored in user_ids bundle
        3. GET /users/{id} draws "123" from user_ids bundle
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Callable

    from pytest_routes.discovery.base import RouteInfo
    from pytest_routes.stateful.config import StatefulTestConfig


@dataclass
class BundleDefinition:
    """Definition of a bundle for value exchange between operations.

    Bundles store values from API responses that can be used as inputs
    to subsequent API calls. This enables testing of dependent operations
    like creating a resource then fetching it by ID.

    Attributes:
        name: Unique identifier for the bundle (e.g., "user_ids").
        value_type: Expected type of values in the bundle.
        extractor: Function to extract values from responses.
        filter_func: Optional function to filter which values to store.
        max_size: Maximum number of values to store (oldest are discarded).
        description: Human-readable description of what this bundle contains.

    Example:
        >>> user_id_bundle = BundleDefinition(
        ...     name="user_ids",
        ...     value_type=str,
        ...     extractor=lambda resp: resp.json().get("id"),
        ...     description="User IDs returned from user creation",
        ... )
    """

    name: str
    value_type: type = str
    extractor: Callable[[Any], Any] | None = None
    filter_func: Callable[[Any], bool] | None = None
    max_size: int = 100
    description: str = ""


@dataclass
class OperationRule:
    """Definition of a rule (API operation) in the state machine.

    Each OperationRule maps to a single API operation that can be
    executed as part of the state machine's test sequence.

    Attributes:
        operation_id: Unique identifier for the operation.
        route: The RouteInfo for this operation.
        method: HTTP method (GET, POST, etc.).
        path: API path pattern.
        input_bundles: Bundles to draw input parameters from.
        output_bundles: Bundles to store response values in.
        preconditions: Functions that must return True for rule to execute.
        weight: Relative weight for rule selection (higher = more likely).
        timeout: Timeout for this specific operation.

    Example:
        >>> get_user_rule = OperationRule(
        ...     operation_id="getUser",
        ...     route=user_route,
        ...     method="GET",
        ...     path="/users/{id}",
        ...     input_bundles={"id": "user_ids"},
        ...     preconditions=[lambda machine: len(machine.bundles["user_ids"]) > 0],
        ... )
    """

    operation_id: str
    route: RouteInfo
    method: str
    path: str
    input_bundles: dict[str, str] = field(default_factory=dict)
    output_bundles: dict[str, str] = field(default_factory=dict)
    preconditions: list[Callable[[Any], bool]] = field(default_factory=list)
    weight: float = 1.0
    timeout: float = 30.0


class APIStateMachine:
    """Base class for API state machines.

    This class provides the foundation for building Hypothesis RuleBasedStateMachine
    implementations for API testing. Subclasses or dynamic instances add rules
    for specific API operations.

    The state machine maintains:
    - Bundles: Collections of values from previous operations
    - Context: Shared state across all operations
    - History: Record of all transitions for debugging

    Attributes:
        bundles: Dictionary of named bundles containing values.
        context: Shared context dictionary for cross-operation state.
        history: List of operations executed in this run.
        config: StatefulTestConfig controlling behavior.

    Lifecycle Methods:
        - setup(): Called before the state machine starts
        - teardown(): Called after all steps complete
        - before_step(rule): Called before each step
        - after_step(rule, response): Called after each step

    Example:
        >>> class MyAPIStateMachine(APIStateMachine):
        ...     @rule()
        ...     def create_user(self):
        ...         response = self.call_api("POST", "/users", body={"name": "Alice"})
        ...         self.bundles["user_ids"].append(response.json()["id"])
        ...
        ...     @rule(target=consumes("user_ids"))
        ...     def get_user(self, user_id):
        ...         response = self.call_api("GET", f"/users/{user_id}")
        ...         assert response.status_code == 200
    """

    def __init__(self) -> None:
        """Initialize the state machine."""
        self.bundles: dict[str, list[Any]] = {}
        self.context: dict[str, Any] = {}
        self.history: list[dict[str, Any]] = []
        self._step_count = 0

    def setup(self) -> None:
        """Set up the state machine before running.

        Override this method to perform initialization tasks like:
        - Creating test fixtures
        - Authenticating
        - Populating initial bundles

        This method is called once before the first rule executes.
        """

    def teardown(self) -> None:
        """Clean up after the state machine completes.

        Override this method to perform cleanup tasks like:
        - Deleting test data
        - Logging out
        - Closing connections

        This method is called once after all rules have executed.
        """

    def before_step(self, rule_name: str) -> None:
        """Called before each step executes.

        Args:
            rule_name: Name of the rule about to execute.

        Override to add pre-step behavior like:
        - Logging
        - Metrics collection
        - State validation
        """
        self._step_count += 1

    def after_step(self, rule_name: str, response: Any) -> None:
        """Called after each step executes.

        Args:
            rule_name: Name of the rule that executed.
            response: Response from the API call.

        Override to add post-step behavior like:
        - Response validation
        - Bundle population
        - Error handling
        """

    def call_api(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        body: Any = None,
        headers: dict[str, str] | None = None,
        timeout: float | None = None,
    ) -> Any:
        """Make an API call through the test client.

        This method is the primary way rules interact with the API.
        It handles authentication, timeout, and response recording.

        Args:
            method: HTTP method (GET, POST, PUT, DELETE, etc.).
            path: API path to call.
            params: Query parameters.
            body: Request body (will be JSON-encoded).
            headers: Additional headers.
            timeout: Request timeout in seconds.

        Returns:
            The HTTP response object.

        Raises:
            TimeoutError: If the request exceeds the timeout.
            APIError: If the API returns an unexpected error.

        Example:
            >>> response = self.call_api(
            ...     "POST",
            ...     "/users",
            ...     body={"name": "Alice", "email": "alice@example.com"},
            ... )
            >>> assert response.status_code == 201
        """
        # TODO: Implement API call using RouteTestClient
        # This should:
        # 1. Apply authentication from context
        # 2. Make the request
        # 3. Record in history
        # 4. Return response

        raise NotImplementedError("API calls must be implemented by subclass or factory")

    def get_bundle_value(self, bundle_name: str) -> Any:
        """Get a random value from a bundle.

        Args:
            bundle_name: Name of the bundle to draw from.

        Returns:
            A value from the bundle.

        Raises:
            KeyError: If bundle doesn't exist.
            ValueError: If bundle is empty.
        """
        if bundle_name not in self.bundles:
            msg = f"Bundle '{bundle_name}' not found"
            raise KeyError(msg)

        bundle = self.bundles[bundle_name]
        if not bundle:
            msg = f"Bundle '{bundle_name}' is empty"
            raise ValueError(msg)

        # TODO: Use Hypothesis to draw from bundle
        # For now, just return the last value
        return bundle[-1]

    def add_to_bundle(self, bundle_name: str, value: Any) -> None:
        """Add a value to a bundle.

        Args:
            bundle_name: Name of the bundle.
            value: Value to add.
        """
        if bundle_name not in self.bundles:
            self.bundles[bundle_name] = []

        self.bundles[bundle_name].append(value)

    def clear_bundle(self, bundle_name: str) -> None:
        """Clear all values from a bundle.

        Args:
            bundle_name: Name of the bundle to clear.
        """
        if bundle_name in self.bundles:
            self.bundles[bundle_name] = []


def build_api_state_machine(
    app: Any,
    config: StatefulTestConfig,
    routes: list[RouteInfo] | None = None,
    openapi_schema: dict[str, Any] | None = None,
) -> type[APIStateMachine]:
    """Build a state machine class for the given application.

    Factory function that creates a customized APIStateMachine subclass
    with rules for each API operation.

    Args:
        app: The ASGI application to test.
        config: Configuration for stateful testing.
        routes: Optional list of routes (will be discovered if not provided).
        openapi_schema: Optional OpenAPI schema for link detection.

    Returns:
        A class extending APIStateMachine with rules for each operation.

    Example:
        >>> StateMachine = build_api_state_machine(app, config)
        >>> run_state_machine_as_test(StateMachine)

    Architecture Notes:
        The factory:
        1. Discovers routes if not provided
        2. Parses OpenAPI links for dependencies
        3. Creates bundles for each resource type
        4. Generates rules for each operation
        5. Sets up preconditions based on dependencies
    """

    from hypothesis.stateful import Bundle, RuleBasedStateMachine, rule

    from pytest_routes.execution.client import RouteTestClient

    if routes is None and openapi_schema:
        from pytest_routes.discovery.openapi import OpenAPIExtractor

        extractor = OpenAPIExtractor(schema=openapi_schema)
        routes = extractor.extract_routes(app)
    elif routes is None:
        routes = []

    bundles_dict, operation_rules = _extract_bundles_from_openapi(openapi_schema or {}, routes)

    hypothesis_bundles: dict[str, Any] = {}
    for bundle_name in bundles_dict:
        hypothesis_bundles[bundle_name] = Bundle(bundle_name)

    class GeneratedStateMachine(RuleBasedStateMachine):
        """Dynamically generated state machine for API testing."""

        def __init__(self) -> None:
            super().__init__()
            self.client = RouteTestClient(app)
            self.bundles_storage: dict[str, list[Any]] = {name: [] for name in bundles_dict}
            self.context: dict[str, Any] = config.initial_state.copy()
            self.history: list[dict[str, Any]] = []
            self._step_count = 0

    for bundle_name, bundle_obj in hypothesis_bundles.items():
        setattr(GeneratedStateMachine, bundle_name, bundle_obj)

    for op_id, operation_rule in operation_rules.items():
        rule_func = _create_rule_for_operation(operation_rule, config, bundles_dict, hypothesis_bundles)
        if rule_func:
            setattr(GeneratedStateMachine, f"rule_{op_id}", rule_func)

    if not operation_rules:
        if config.verbose:
            import logging

            logger = logging.getLogger(__name__)
            logger.warning("No operations found for state machine")

        @rule(target=None)
        def noop_rule(self: Any) -> None:
            """Placeholder rule when no operations are available."""

        setattr(GeneratedStateMachine, "noop_rule", noop_rule)  # noqa: B010

    return GeneratedStateMachine  # type: ignore[return-value]


def _create_rule_for_operation(
    operation: OperationRule,
    config: StatefulTestConfig,
    bundles: dict[str, BundleDefinition],
    hypothesis_bundles: dict[str, Any],
) -> Callable[..., Any] | None:
    """Create a Hypothesis rule for an API operation.

    Args:
        operation: The operation rule definition.
        config: Stateful test configuration.
        bundles: Available bundle definitions.
        hypothesis_bundles: Hypothesis Bundle objects by name.

    Returns:
        A rule function decorated with @rule, or None if operation should be skipped.
    """
    import asyncio

    from hypothesis import assume
    from hypothesis.stateful import consumes, rule

    if not config.should_include_operation(operation.operation_id):
        return None

    method = operation.method.upper()
    path = operation.path

    bundle_consumes: dict[str, Any] = {}
    for param_name, bundle_name in operation.input_bundles.items():
        if bundle_name in hypothesis_bundles:
            bundle_consumes[param_name] = consumes(hypothesis_bundles[bundle_name])

    target_bundle = None
    if operation.output_bundles:
        first_output = next(iter(operation.output_bundles.values()))
        if first_output in hypothesis_bundles:
            target_bundle = hypothesis_bundles[first_output]

    def rule_implementation(self: Any, **kwargs: Any) -> Any:
        """Execute API operation."""

        for precondition in operation.preconditions:
            assume(precondition(self))

        self._step_count += 1

        resolved_path = path
        path_params = {}
        for param_name, value in kwargs.items():
            if f"{{{param_name}}}" in resolved_path:
                path_params[param_name] = value
                resolved_path = resolved_path.replace(f"{{{param_name}}}", str(value))

        timeout = config.get_effective_timeout(self._step_count)

        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        try:
            response = loop.run_until_complete(
                self.client.request(
                    method=method,
                    path=resolved_path,
                    timeout=timeout,
                )
            )

            http_server_error = 500
            http_client_error = 400

            if response.status_code >= http_server_error:
                msg = f"Server error: {response.status_code}"
                raise AssertionError(msg)

            if operation.output_bundles and response.status_code < http_client_error:
                try:
                    response_data = response.json()
                    for field, bundle_name in operation.output_bundles.items():
                        if field in response_data:
                            value = response_data[field]
                            if bundle_name in self.bundles_storage:
                                self.bundles_storage[bundle_name].append(value)
                            return value
                except Exception:
                    pass

            self.history.append(
                {
                    "step": self._step_count,
                    "operation": operation.operation_id,
                    "method": method,
                    "path": resolved_path,
                    "status": response.status_code,
                }
            )

            return None

        except Exception as e:
            if config.fail_fast:
                raise
            if config.verbose:
                import logging

                logger = logging.getLogger(__name__)
                logger.warning("Error in %s: %s", operation.operation_id, e)
            return None

    rule_implementation.__name__ = f"rule_{operation.operation_id}"
    rule_implementation.__doc__ = f"Test {method} {path}"

    if target_bundle is not None:
        decorated_rule = rule(target=target_bundle, **bundle_consumes)(rule_implementation)
    else:
        decorated_rule = rule(**bundle_consumes)(rule_implementation)

    return decorated_rule


def _extract_bundles_from_openapi(
    openapi_schema: dict[str, Any],
    routes: list[RouteInfo],
) -> tuple[dict[str, BundleDefinition], dict[str, OperationRule]]:
    """Extract bundle definitions and operation rules from OpenAPI schema.

    Parses OpenAPI links to determine:
    - Which operations produce values (output bundles)
    - Which operations consume values (input bundles)
    - Dependencies between operations

    Args:
        openapi_schema: The OpenAPI specification.
        routes: List of discovered routes.

    Returns:
        Tuple of (bundle_definitions, operation_rules).

    Example OpenAPI Link:
        responses:
          '201':
            links:
              GetUserById:
                operationId: getUser
                parameters:
                  userId: '$response.body#/id'

        This creates:
        - Bundle: user_ids (produced by createUser)
        - Input: getUser.userId from user_ids
    """

    bundles: dict[str, BundleDefinition] = {}
    rules: dict[str, OperationRule] = {}

    if not openapi_schema or "paths" not in openapi_schema:
        routes_map = {(r.path, r.methods[0] if r.methods else "GET"): r for r in routes}
        for (path, method), route in routes_map.items():
            op_id = f"{method.lower()}_{path.replace('/', '_').strip('_')}"
            rules[op_id] = OperationRule(
                operation_id=op_id,
                route=route,
                method=method.upper(),
                path=path,
            )
        return bundles, rules

    paths = openapi_schema.get("paths", {})
    routes_map = {(r.path, r.methods[0].upper() if r.methods else "GET"): r for r in routes}

    link_map: dict[str, dict[str, Any]] = {}

    for path, path_item in paths.items():
        for method in ["get", "post", "put", "patch", "delete", "options", "head"]:
            if method not in path_item:
                continue

            operation = path_item[method]
            op_id = operation.get("operationId", f"{method}_{path.replace('/', '_').strip('_')}")

            route = routes_map.get((path, method.upper()))
            if not route:
                continue

            operation_rule = OperationRule(
                operation_id=op_id,
                route=route,
                method=method.upper(),
                path=path,
            )

            responses = operation.get("responses", {})
            for response_obj in responses.values():
                if not isinstance(response_obj, dict):
                    continue

                links = response_obj.get("links", {})
                for link_obj in links.values():
                    if not isinstance(link_obj, dict):
                        continue

                    target_op_id = link_obj.get("operationId")
                    if not target_op_id:
                        continue

                    if target_op_id not in link_map:
                        link_map[target_op_id] = {"inputs": {}}

                    parameters = link_obj.get("parameters", {})
                    for param_name, param_expr in parameters.items():
                        if isinstance(param_expr, str) and "$response.body#/" in param_expr:
                            field_path = param_expr.split("$response.body#/")[-1]
                            field_name = field_path.split("/")[0]

                            bundle_name = f"{field_name}_bundle"

                            if bundle_name not in bundles:
                                bundles[bundle_name] = BundleDefinition(
                                    name=bundle_name,
                                    value_type=str,
                                    description=f"Values from {field_name} field",
                                )

                            if field_name not in operation_rule.output_bundles:
                                operation_rule.output_bundles[field_name] = bundle_name

                            link_map[target_op_id]["inputs"][param_name] = bundle_name

            rules[op_id] = operation_rule

    for op_id, link_info in link_map.items():
        if op_id in rules:
            rules[op_id].input_bundles.update(link_info["inputs"])

            def make_precondition(bundle_name: str) -> Callable[[Any], bool]:
                def check(machine: Any) -> bool:
                    return len(machine.bundles_storage.get(bundle_name, [])) > 0

                return check

            for bundle_name in link_info["inputs"].values():
                rules[op_id].preconditions.append(make_precondition(bundle_name))

    return bundles, rules
