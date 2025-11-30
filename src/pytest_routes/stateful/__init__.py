"""Stateful testing module for pytest-routes.

This module provides stateful API testing capabilities using Hypothesis RuleBasedStateMachine
and Schemathesis integration. Stateful testing enables testing API workflows and sequences
where responses from one endpoint are used as inputs to subsequent endpoints.

Key Components:
    - StatefulTestConfig: Configuration for stateful test execution
    - StatefulTestRunner: Orchestrates stateful test execution with state machines
    - LinkExtractor: Extracts OpenAPI links for state transitions
    - BundleManager: Manages value exchange between operations

Example:
    >>> from pytest_routes.stateful import StatefulTestConfig, StatefulTestRunner
    >>> config = StatefulTestConfig(
    ...     enabled=True,
    ...     step_count=50,
    ...     stateful_recursion_limit=5,
    ... )
    >>> runner = StatefulTestRunner(app, config)
    >>> results = await runner.run_stateful_tests()

Stateful Testing Modes:
    - "links": Use OpenAPI links to define state transitions (default)
    - "data_dependency": Infer dependencies from response/request schemas
    - "explicit": Use user-defined transition rules

Architecture:
    The stateful testing system is built on three layers:

    1. Configuration Layer (config.py):
       - StatefulTestConfig dataclass with all configuration options
       - LinkConfig for OpenAPI link customization
       - HookConfig for lifecycle hook settings

    2. State Machine Layer (state_machine.py):
       - APIStateMachine extending Hypothesis RuleBasedStateMachine
       - Rule generation from OpenAPI operations
       - Bundle management for value exchange

    3. Execution Layer (runner.py):
       - StatefulTestRunner coordinating test execution
       - Integration with existing RouteTestRunner
       - Metrics collection and reporting
"""

from __future__ import annotations

from pytest_routes.stateful.config import (
    HookConfig,
    LinkConfig,
    StatefulTestConfig,
    merge_stateful_configs,
)
from pytest_routes.stateful.runner import (
    StatefulTestFactory,
    StatefulTestResult,
    StatefulTestRunner,
    TransitionRecord,
)
from pytest_routes.stateful.state_machine import (
    APIStateMachine,
    BundleDefinition,
    OperationRule,
    build_api_state_machine,
)

__all__ = [
    # Config
    "HookConfig",
    "LinkConfig",
    "StatefulTestConfig",
    "merge_stateful_configs",
    # Runner
    "StatefulTestFactory",
    "StatefulTestResult",
    "StatefulTestRunner",
    "TransitionRecord",
    # State Machine
    "APIStateMachine",
    "BundleDefinition",
    "OperationRule",
    "build_api_state_machine",
]
