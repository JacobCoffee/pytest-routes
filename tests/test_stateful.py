"""Tests for stateful testing module."""

from __future__ import annotations

import time
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from pytest_routes.stateful.config import HookConfig, LinkConfig, StatefulTestConfig, merge_stateful_configs
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
    _extract_bundles_from_openapi,
    build_api_state_machine,
)


class TestLinkConfig:
    """Tests for LinkConfig."""

    def test_link_config_defaults(self) -> None:
        config = LinkConfig()

        assert config.follow_links is True
        assert config.link_timeout == 30.0
        assert config.max_link_depth == 5
        assert config.link_filters == {}
        assert config.parameter_mapping == {}

    def test_link_config_custom_values(self) -> None:
        config = LinkConfig(
            follow_links=False,
            link_timeout=60.0,
            max_link_depth=10,
            link_filters={"include": ["Get*"], "exclude": ["*Admin*"]},
            parameter_mapping={"userId": "id"},
        )

        assert config.follow_links is False
        assert config.link_timeout == 60.0
        assert config.max_link_depth == 10
        assert config.link_filters == {"include": ["Get*"], "exclude": ["*Admin*"]}
        assert config.parameter_mapping == {"userId": "id"}


class TestHookConfig:
    """Tests for HookConfig."""

    def test_hook_config_defaults(self) -> None:
        config = HookConfig()

        assert config.enable_hooks is False
        assert config.setup_hook is None
        assert config.teardown_hook is None
        assert config.before_call_hook is None
        assert config.after_call_hook is None
        assert config.on_error_hook is None
        assert config.hook_timeout == 10.0

    def test_hook_config_with_hooks(self) -> None:
        def setup_hook(context: dict[str, Any]) -> None:
            context["initialized"] = True

        def teardown_hook(context: dict[str, Any]) -> None:
            context["cleaned_up"] = True

        config = HookConfig(
            enable_hooks=True,
            setup_hook=setup_hook,
            teardown_hook=teardown_hook,
            hook_timeout=20.0,
        )

        assert config.enable_hooks is True
        assert config.setup_hook is setup_hook
        assert config.teardown_hook is teardown_hook
        assert config.hook_timeout == 20.0


class TestStatefulTestConfig:
    """Tests for StatefulTestConfig."""

    def test_stateful_test_config_defaults(self) -> None:
        config = StatefulTestConfig()

        assert config.enabled is False
        assert config.mode == "links"
        assert config.step_count == 50
        assert config.stateful_recursion_limit == 5
        assert config.max_examples == 100
        assert config.seed is None
        assert config.timeout_per_step == 30.0
        assert config.timeout_total == 600.0
        assert config.fail_fast is False
        assert config.collect_coverage is True
        assert config.verbose is False
        assert config.auth is None
        assert isinstance(config.link_config, LinkConfig)
        assert isinstance(config.hook_config, HookConfig)
        assert config.include_operations == []
        assert config.exclude_operations == []
        assert config.bundle_strategies == {}
        assert config.initial_state == {}

    def test_stateful_test_config_custom_values(self) -> None:
        link_config = LinkConfig(follow_links=False)
        hook_config = HookConfig(enable_hooks=True)

        config = StatefulTestConfig(
            enabled=True,
            mode="data_dependency",
            step_count=100,
            stateful_recursion_limit=10,
            max_examples=200,
            seed=12345,
            timeout_per_step=60.0,
            timeout_total=1200.0,
            fail_fast=True,
            collect_coverage=False,
            verbose=True,
            link_config=link_config,
            hook_config=hook_config,
            include_operations=["create*", "get*"],
            exclude_operations=["*Admin*"],
            bundle_strategies={"users": "custom_strategy"},
            initial_state={"auth_token": "test-token"},
        )

        assert config.enabled is True
        assert config.mode == "data_dependency"
        assert config.step_count == 100
        assert config.stateful_recursion_limit == 10
        assert config.max_examples == 200
        assert config.seed == 12345
        assert config.timeout_per_step == 60.0
        assert config.timeout_total == 1200.0
        assert config.fail_fast is True
        assert config.collect_coverage is False
        assert config.verbose is True
        assert config.link_config is link_config
        assert config.hook_config is hook_config
        assert config.include_operations == ["create*", "get*"]
        assert config.exclude_operations == ["*Admin*"]
        assert config.bundle_strategies == {"users": "custom_strategy"}
        assert config.initial_state == {"auth_token": "test-token"}

    def test_should_include_operation_no_filters(self) -> None:
        config = StatefulTestConfig()
        assert config.should_include_operation("createUser") is True
        assert config.should_include_operation("getUser") is True
        assert config.should_include_operation("deleteAdminUser") is True

    def test_should_include_operation_with_include_patterns(self) -> None:
        config = StatefulTestConfig(include_operations=["create*", "get*"])

        assert config.should_include_operation("createUser") is True
        assert config.should_include_operation("getUser") is True
        assert config.should_include_operation("deleteUser") is False
        assert config.should_include_operation("updateUser") is False

    def test_should_include_operation_with_exclude_patterns(self) -> None:
        config = StatefulTestConfig(exclude_operations=["*Admin*", "*Internal*"])

        assert config.should_include_operation("createUser") is True
        assert config.should_include_operation("deleteAdminUser") is False
        assert config.should_include_operation("getInternalData") is False
        assert config.should_include_operation("getUserById") is True

    def test_should_include_operation_include_and_exclude(self) -> None:
        config = StatefulTestConfig(
            include_operations=["create*", "get*"],
            exclude_operations=["*Admin*"],
        )

        assert config.should_include_operation("createUser") is True
        assert config.should_include_operation("createAdminUser") is False
        assert config.should_include_operation("getUser") is True
        assert config.should_include_operation("deleteUser") is False

    def test_get_effective_timeout_first_step(self) -> None:
        config = StatefulTestConfig(timeout_per_step=30.0, timeout_total=100.0)
        timeout = config.get_effective_timeout(1)
        assert timeout == 30.0

    def test_get_effective_timeout_within_budget(self) -> None:
        config = StatefulTestConfig(timeout_per_step=30.0, timeout_total=100.0)
        timeout = config.get_effective_timeout(2)
        assert timeout == 30.0

    def test_get_effective_timeout_budget_exhausted(self) -> None:
        config = StatefulTestConfig(timeout_per_step=30.0, timeout_total=100.0)
        timeout = config.get_effective_timeout(4)
        assert timeout == 10.0

    def test_get_effective_timeout_minimum(self) -> None:
        config = StatefulTestConfig(timeout_per_step=30.0, timeout_total=50.0)
        timeout = config.get_effective_timeout(10)
        assert timeout == 1.0

    def test_from_dict_minimal(self) -> None:
        data: dict[str, Any] = {}
        config = StatefulTestConfig.from_dict(data)

        defaults = StatefulTestConfig()
        assert config.enabled == defaults.enabled
        assert config.mode == defaults.mode
        assert config.step_count == defaults.step_count

    def test_from_dict_full(self) -> None:
        data = {
            "enabled": True,
            "mode": "explicit",
            "step_count": 75,
            "stateful_recursion_limit": 8,
            "max_examples": 150,
            "seed": 99999,
            "timeout_per_step": 45.0,
            "timeout_total": 900.0,
            "fail_fast": True,
            "collect_coverage": False,
            "verbose": True,
            "include_operations": ["create*"],
            "exclude_operations": ["delete*"],
            "bundle_strategies": {"users": "strategy1"},
            "initial_state": {"token": "abc123"},
            "link_config": {
                "follow_links": False,
                "link_timeout": 40.0,
                "max_link_depth": 7,
                "link_filters": {"include": ["*"]},
                "parameter_mapping": {"id": "userId"},
            },
            "hook_config": {
                "enable_hooks": True,
                "hook_timeout": 15.0,
            },
        }

        config = StatefulTestConfig.from_dict(data)

        assert config.enabled is True
        assert config.mode == "explicit"
        assert config.step_count == 75
        assert config.stateful_recursion_limit == 8
        assert config.max_examples == 150
        assert config.seed == 99999
        assert config.timeout_per_step == 45.0
        assert config.timeout_total == 900.0
        assert config.fail_fast is True
        assert config.collect_coverage is False
        assert config.verbose is True
        assert config.include_operations == ["create*"]
        assert config.exclude_operations == ["delete*"]
        assert config.bundle_strategies == {"users": "strategy1"}
        assert config.initial_state == {"token": "abc123"}
        assert config.link_config.follow_links is False
        assert config.link_config.link_timeout == 40.0
        assert config.link_config.max_link_depth == 7
        assert config.hook_config.enable_hooks is True
        assert config.hook_config.hook_timeout == 15.0


class TestMergeStatefulConfigs:
    """Tests for merge_stateful_configs."""

    def test_merge_both_none(self) -> None:
        merged = merge_stateful_configs(None, None)
        defaults = StatefulTestConfig()
        assert merged.enabled == defaults.enabled
        assert merged.step_count == defaults.step_count

    def test_merge_only_file_config(self) -> None:
        file_config = StatefulTestConfig(enabled=True, step_count=75)
        merged = merge_stateful_configs(None, file_config)

        assert merged.enabled is True
        assert merged.step_count == 75

    def test_merge_only_cli_config(self) -> None:
        cli_config = StatefulTestConfig(enabled=True, max_examples=200)
        merged = merge_stateful_configs(cli_config, None)

        assert merged.enabled is True
        assert merged.max_examples == 200

    def test_merge_cli_overrides_file(self) -> None:
        file_config = StatefulTestConfig(enabled=True, step_count=50, max_examples=100)
        cli_config = StatefulTestConfig(enabled=True, step_count=100)

        merged = merge_stateful_configs(cli_config, file_config)

        assert merged.step_count == 100
        assert merged.max_examples == 100

    def test_merge_preserves_defaults(self) -> None:
        defaults = StatefulTestConfig()
        file_config = StatefulTestConfig(step_count=75)
        cli_config = StatefulTestConfig()

        merged = merge_stateful_configs(cli_config, file_config)

        assert merged.step_count == 75
        assert merged.enabled == defaults.enabled

    def test_merge_seed_handling(self) -> None:
        file_config = StatefulTestConfig(seed=123)
        cli_config = StatefulTestConfig(seed=None)

        merged = merge_stateful_configs(cli_config, file_config)
        assert merged.seed == 123

        cli_config_with_seed = StatefulTestConfig(seed=456)
        merged = merge_stateful_configs(cli_config_with_seed, file_config)
        assert merged.seed == 456

    def test_merge_bundle_strategies(self) -> None:
        file_config = StatefulTestConfig(bundle_strategies={"users": "strategy1", "posts": "strategy2"})
        cli_config = StatefulTestConfig(bundle_strategies={"users": "strategy3", "comments": "strategy4"})

        merged = merge_stateful_configs(cli_config, file_config)

        assert merged.bundle_strategies == {"users": "strategy3", "posts": "strategy2", "comments": "strategy4"}

    def test_merge_initial_state(self) -> None:
        file_config = StatefulTestConfig(initial_state={"token": "file-token", "user_id": "123"})
        cli_config = StatefulTestConfig(initial_state={"token": "cli-token", "role": "admin"})

        merged = merge_stateful_configs(cli_config, file_config)

        assert merged.initial_state == {"token": "cli-token", "user_id": "123", "role": "admin"}


class TestTransitionRecord:
    """Tests for TransitionRecord."""

    def test_transition_record_minimal(self) -> None:
        record = TransitionRecord(
            step_number=1,
            operation_id="createUser",
            method="POST",
            path="/users",
        )

        assert record.step_number == 1
        assert record.operation_id == "createUser"
        assert record.method == "POST"
        assert record.path == "/users"
        assert record.path_params == {}
        assert record.query_params == {}
        assert record.body is None
        assert record.status_code is None
        assert record.response_body is None
        assert record.duration_ms == 0.0
        assert record.bundle_values_used == {}
        assert record.bundle_values_produced == {}
        assert record.error is None
        assert record.timestamp > 0

    def test_transition_record_full(self) -> None:
        timestamp = time.time()
        record = TransitionRecord(
            step_number=5,
            operation_id="getUser",
            method="GET",
            path="/users/123",
            path_params={"id": "123"},
            query_params={"include": "posts"},
            body=None,
            status_code=200,
            response_body={"id": "123", "name": "Alice"},
            duration_ms=42.5,
            bundle_values_used={"user_id": "123"},
            bundle_values_produced={"user_name": "Alice"},
            error=None,
            timestamp=timestamp,
        )

        assert record.step_number == 5
        assert record.operation_id == "getUser"
        assert record.method == "GET"
        assert record.path == "/users/123"
        assert record.path_params == {"id": "123"}
        assert record.query_params == {"include": "posts"}
        assert record.status_code == 200
        assert record.response_body == {"id": "123", "name": "Alice"}
        assert record.duration_ms == 42.5
        assert record.bundle_values_used == {"user_id": "123"}
        assert record.bundle_values_produced == {"user_name": "Alice"}
        assert record.error is None
        assert record.timestamp == timestamp

    def test_transition_record_with_error(self) -> None:
        record = TransitionRecord(
            step_number=3,
            operation_id="deleteUser",
            method="DELETE",
            path="/users/999",
            status_code=404,
            error="User not found",
        )

        assert record.step_number == 3
        assert record.status_code == 404
        assert record.error == "User not found"

    def test_to_dict(self) -> None:
        timestamp = 1234567890.0
        record = TransitionRecord(
            step_number=2,
            operation_id="updateUser",
            method="PUT",
            path="/users/456",
            path_params={"id": "456"},
            query_params={},
            body={"name": "Bob"},
            status_code=200,
            response_body={"id": "456", "name": "Bob"},
            duration_ms=55.3,
            bundle_values_used={"user_id": "456"},
            bundle_values_produced={},
            error=None,
            timestamp=timestamp,
        )

        result = record.to_dict()

        assert result == {
            "step_number": 2,
            "operation_id": "updateUser",
            "method": "PUT",
            "path": "/users/456",
            "path_params": {"id": "456"},
            "query_params": {},
            "body": {"name": "Bob"},
            "status_code": 200,
            "response_body": {"id": "456", "name": "Bob"},
            "duration_ms": 55.3,
            "bundle_values_used": {"user_id": "456"},
            "bundle_values_produced": {},
            "error": None,
            "timestamp": timestamp,
        }


class TestStatefulTestResult:
    """Tests for StatefulTestResult."""

    def test_stateful_test_result_defaults(self) -> None:
        result = StatefulTestResult(test_name="test_workflow", passed=True)

        assert result.test_name == "test_workflow"
        assert result.passed is True
        assert result.transitions == []
        assert result.total_steps == 0
        assert result.successful_steps == 0
        assert result.failed_steps == 0
        assert result.duration_ms == 0.0
        assert result.errors == []
        assert result.coverage == {}
        assert result.seed is None

    def test_stateful_test_result_with_values(self) -> None:
        transitions = [
            TransitionRecord(1, "createUser", "POST", "/users"),
            TransitionRecord(2, "getUser", "GET", "/users/1"),
        ]
        result = StatefulTestResult(
            test_name="test_crud",
            passed=True,
            transitions=transitions,
            total_steps=2,
            successful_steps=2,
            failed_steps=0,
            duration_ms=123.4,
            errors=[],
            coverage={"operations": 5},
            seed=12345,
        )

        assert result.test_name == "test_crud"
        assert result.passed is True
        assert len(result.transitions) == 2
        assert result.total_steps == 2
        assert result.successful_steps == 2
        assert result.failed_steps == 0
        assert result.duration_ms == 123.4
        assert result.coverage == {"operations": 5}
        assert result.seed == 12345

    def test_add_transition_successful(self) -> None:
        result = StatefulTestResult(test_name="test", passed=True)
        transition = TransitionRecord(1, "createUser", "POST", "/users", status_code=201)

        result.add_transition(transition)

        assert len(result.transitions) == 1
        assert result.transitions[0] is transition
        assert result.total_steps == 1
        assert result.successful_steps == 1
        assert result.failed_steps == 0

    def test_add_transition_failed(self) -> None:
        result = StatefulTestResult(test_name="test", passed=True)
        transition = TransitionRecord(1, "createUser", "POST", "/users", error="Server error")

        result.add_transition(transition)

        assert len(result.transitions) == 1
        assert result.total_steps == 1
        assert result.successful_steps == 0
        assert result.failed_steps == 1

    def test_add_multiple_transitions(self) -> None:
        result = StatefulTestResult(test_name="test", passed=True)

        transition1 = TransitionRecord(1, "createUser", "POST", "/users")
        transition2 = TransitionRecord(2, "getUser", "GET", "/users/1", error="Not found")
        transition3 = TransitionRecord(3, "updateUser", "PUT", "/users/1")

        result.add_transition(transition1)
        result.add_transition(transition2)
        result.add_transition(transition3)

        assert len(result.transitions) == 3
        assert result.total_steps == 3
        assert result.successful_steps == 2
        assert result.failed_steps == 1

    def test_to_dict(self) -> None:
        transition = TransitionRecord(1, "createUser", "POST", "/users")
        result = StatefulTestResult(
            test_name="test_api",
            passed=False,
            transitions=[transition],
            total_steps=5,
            successful_steps=3,
            failed_steps=2,
            duration_ms=234.5,
            errors=["Error 1", "Error 2"],
            coverage={"ops": 10},
            seed=999,
        )

        data = result.to_dict()

        assert data["test_name"] == "test_api"
        assert data["passed"] is False
        assert len(data["transitions"]) == 1
        assert data["total_steps"] == 5
        assert data["successful_steps"] == 3
        assert data["failed_steps"] == 2
        assert data["duration_ms"] == 234.5
        assert data["errors"] == ["Error 1", "Error 2"]
        assert data["coverage"] == {"ops": 10}
        assert data["seed"] == 999


class TestStatefulTestRunner:
    """Tests for StatefulTestRunner."""

    def test_initialization(self) -> None:
        app = MagicMock()
        config = StatefulTestConfig()
        runner = StatefulTestRunner(app, config)

        assert runner.app is app
        assert runner.config is config
        assert runner.route_config is None
        assert runner._schema is None
        assert runner._state_machine_class is None
        assert runner._results == []

    def test_schemathesis_available_true(self) -> None:
        app = MagicMock()
        config = StatefulTestConfig()
        runner = StatefulTestRunner(app, config)

        runner._schemathesis_available = None

        with patch.dict("sys.modules", {"schemathesis": MagicMock()}):
            result = runner.schemathesis_available
            assert result is True

    def test_schemathesis_available_false(self) -> None:
        app = MagicMock()
        config = StatefulTestConfig()
        runner = StatefulTestRunner(app, config)
        runner._schemathesis_available = None

        with patch.dict("sys.modules", {"schemathesis": None}):
            with patch("builtins.__import__", side_effect=ImportError):
                result = runner.schemathesis_available
                assert result is False

    def test_create_transition_record(self) -> None:
        app = MagicMock()
        config = StatefulTestConfig()
        runner = StatefulTestRunner(app, config)

        record = runner.create_transition_record(
            step_number=3,
            operation_id="getUser",
            method="GET",
            path="/users/123",
            status_code=200,
        )

        assert isinstance(record, TransitionRecord)
        assert record.step_number == 3
        assert record.operation_id == "getUser"
        assert record.method == "GET"
        assert record.path == "/users/123"
        assert record.status_code == 200

    def test_get_results(self) -> None:
        app = MagicMock()
        config = StatefulTestConfig()
        runner = StatefulTestRunner(app, config)

        results = [
            StatefulTestResult("test1", True),
            StatefulTestResult("test2", False),
        ]
        runner._results = results

        assert runner.get_results() == results

    def test_reset(self) -> None:
        app = MagicMock()
        config = StatefulTestConfig()
        runner = StatefulTestRunner(app, config)

        runner._results = [StatefulTestResult("test", True)]
        runner._context = {"key": "value"}

        runner.reset()

        assert runner._results == []
        assert runner._context == {}

    def test_get_coverage_metrics_empty(self) -> None:
        app = MagicMock()
        config = StatefulTestConfig()
        runner = StatefulTestRunner(app, config)

        metrics = runner.get_coverage_metrics()

        assert metrics["operation_coverage_pct"] == 0.0
        assert metrics["transition_coverage_pct"] == 0.0
        assert metrics["link_coverage_pct"] == 0.0
        assert metrics["operations_tested"] == []
        assert metrics["operations_untested"] == []
        assert metrics["transitions_count"] == 0

    def test_get_coverage_metrics_with_results(self) -> None:
        app = MagicMock()
        config = StatefulTestConfig()
        runner = StatefulTestRunner(app, config)

        runner._schema = {
            "paths": {
                "/users": {
                    "get": {"operationId": "getUsers"},
                    "post": {"operationId": "createUser"},
                },
                "/users/{id}": {
                    "get": {"operationId": "getUser"},
                },
            }
        }

        result = StatefulTestResult("test", True)
        result.add_transition(TransitionRecord(1, "createUser", "POST", "/users"))
        result.add_transition(TransitionRecord(2, "getUser", "GET", "/users/1"))
        runner._results = [result]

        metrics = runner.get_coverage_metrics()

        assert metrics["operations_tested"] == ["createUser", "getUser"]
        assert metrics["operations_untested"] == ["getUsers"]
        assert metrics["total_operations"] == 3
        assert metrics["transitions_count"] == 2


class TestBundleDefinition:
    """Tests for BundleDefinition."""

    def test_bundle_definition_defaults(self) -> None:
        bundle = BundleDefinition(name="user_ids")

        assert bundle.name == "user_ids"
        assert bundle.value_type is str
        assert bundle.extractor is None
        assert bundle.filter_func is None
        assert bundle.max_size == 100
        assert bundle.description == ""

    def test_bundle_definition_with_extractor(self) -> None:
        def extract_id(response: Any) -> str:
            return response["id"]

        bundle = BundleDefinition(
            name="user_ids",
            value_type=str,
            extractor=extract_id,
            description="User IDs from creation",
        )

        assert bundle.name == "user_ids"
        assert bundle.extractor is extract_id
        assert bundle.description == "User IDs from creation"

    def test_bundle_definition_with_filter(self) -> None:
        def is_valid_id(value: Any) -> bool:
            return isinstance(value, str) and len(value) > 0

        bundle = BundleDefinition(
            name="user_ids",
            filter_func=is_valid_id,
            max_size=50,
        )

        assert bundle.filter_func is is_valid_id
        assert bundle.max_size == 50


class TestOperationRule:
    """Tests for OperationRule."""

    def test_operation_rule_minimal(self) -> None:
        route = MagicMock()
        rule = OperationRule(
            operation_id="getUser",
            route=route,
            method="GET",
            path="/users/{id}",
        )

        assert rule.operation_id == "getUser"
        assert rule.route is route
        assert rule.method == "GET"
        assert rule.path == "/users/{id}"
        assert rule.input_bundles == {}
        assert rule.output_bundles == {}
        assert rule.preconditions == []
        assert rule.weight == 1.0
        assert rule.timeout == 30.0

    def test_operation_rule_with_bundles(self) -> None:
        route = MagicMock()
        rule = OperationRule(
            operation_id="getUser",
            route=route,
            method="GET",
            path="/users/{id}",
            input_bundles={"id": "user_ids"},
            output_bundles={"name": "user_names"},
        )

        assert rule.input_bundles == {"id": "user_ids"}
        assert rule.output_bundles == {"name": "user_names"}

    def test_operation_rule_with_preconditions(self) -> None:
        route = MagicMock()

        def has_users(machine: Any) -> bool:
            return len(machine.bundles.get("user_ids", [])) > 0

        rule = OperationRule(
            operation_id="getUser",
            route=route,
            method="GET",
            path="/users/{id}",
            preconditions=[has_users],
            weight=2.0,
            timeout=60.0,
        )

        assert len(rule.preconditions) == 1
        assert rule.preconditions[0] is has_users
        assert rule.weight == 2.0
        assert rule.timeout == 60.0


class TestAPIStateMachine:
    """Tests for APIStateMachine."""

    def test_initialization(self) -> None:
        machine = APIStateMachine()

        assert machine.bundles == {}
        assert machine.context == {}
        assert machine.history == []
        assert machine._step_count == 0

    def test_setup(self) -> None:
        machine = APIStateMachine()
        machine.setup()

    def test_teardown(self) -> None:
        machine = APIStateMachine()
        machine.teardown()

    def test_before_step(self) -> None:
        machine = APIStateMachine()
        machine.before_step("test_rule")
        assert machine._step_count == 1

        machine.before_step("another_rule")
        assert machine._step_count == 2

    def test_after_step(self) -> None:
        machine = APIStateMachine()
        response = MagicMock()
        machine.after_step("test_rule", response)

    def test_get_bundle_value_not_found(self) -> None:
        machine = APIStateMachine()

        with pytest.raises(KeyError, match="Bundle 'nonexistent' not found"):
            machine.get_bundle_value("nonexistent")

    def test_get_bundle_value_empty(self) -> None:
        machine = APIStateMachine()
        machine.bundles["user_ids"] = []

        with pytest.raises(ValueError, match="Bundle 'user_ids' is empty"):
            machine.get_bundle_value("user_ids")

    def test_get_bundle_value_success(self) -> None:
        machine = APIStateMachine()
        machine.bundles["user_ids"] = ["123", "456", "789"]

        value = machine.get_bundle_value("user_ids")
        assert value == "789"

    def test_add_to_bundle_new(self) -> None:
        machine = APIStateMachine()
        machine.add_to_bundle("user_ids", "123")

        assert machine.bundles["user_ids"] == ["123"]

    def test_add_to_bundle_existing(self) -> None:
        machine = APIStateMachine()
        machine.bundles["user_ids"] = ["123"]
        machine.add_to_bundle("user_ids", "456")

        assert machine.bundles["user_ids"] == ["123", "456"]

    def test_clear_bundle(self) -> None:
        machine = APIStateMachine()
        machine.bundles["user_ids"] = ["123", "456"]
        machine.clear_bundle("user_ids")

        assert machine.bundles["user_ids"] == []

    def test_clear_bundle_nonexistent(self) -> None:
        machine = APIStateMachine()
        machine.clear_bundle("nonexistent")


class TestBuildAPIStateMachine:
    """Tests for build_api_state_machine."""

    def test_build_with_no_routes(self) -> None:
        app = MagicMock()
        config = StatefulTestConfig()

        state_machine_class = build_api_state_machine(app, config, routes=[])

        assert state_machine_class is not None
        assert hasattr(state_machine_class, "__init__")

    def test_build_with_routes(self) -> None:
        app = MagicMock()
        config = StatefulTestConfig()

        route = MagicMock()
        route.path = "/users"
        route.methods = ["GET"]
        routes = [route]

        state_machine_class = build_api_state_machine(app, config, routes=routes)

        assert state_machine_class is not None

    def test_build_with_openapi_schema(self) -> None:
        app = MagicMock()
        config = StatefulTestConfig()

        openapi_schema = {
            "paths": {
                "/users": {
                    "get": {
                        "operationId": "getUsers",
                        "responses": {"200": {"description": "Success"}},
                    },
                    "post": {
                        "operationId": "createUser",
                        "responses": {
                            "201": {
                                "description": "Created",
                                "links": {
                                    "GetUser": {
                                        "operationId": "getUser",
                                        "parameters": {"userId": "$response.body#/id"},
                                    }
                                },
                            }
                        },
                    },
                },
                "/users/{userId}": {
                    "get": {
                        "operationId": "getUser",
                        "responses": {"200": {"description": "Success"}},
                    }
                },
            }
        }

        route1 = MagicMock()
        route1.path = "/users"
        route1.methods = ["GET", "POST"]

        route2 = MagicMock()
        route2.path = "/users/{userId}"
        route2.methods = ["GET"]

        routes = [route1, route2]

        state_machine_class = build_api_state_machine(app, config, routes=routes, openapi_schema=openapi_schema)

        assert state_machine_class is not None


class TestExtractBundlesFromOpenAPI:
    """Tests for _extract_bundles_from_openapi."""

    def test_extract_no_schema(self) -> None:
        routes = []
        bundles, rules = _extract_bundles_from_openapi({}, routes)

        assert bundles == {}
        assert rules == {}
        assert isinstance(bundles, dict)
        assert isinstance(rules, dict)

    def test_extract_routes_only(self) -> None:
        route1 = MagicMock()
        route1.path = "/users"
        route1.methods = ["GET"]

        route2 = MagicMock()
        route2.path = "/posts"
        route2.methods = ["POST"]

        routes = [route1, route2]

        _bundles, rules = _extract_bundles_from_openapi({}, routes)

        assert len(rules) == 2
        assert "get_users" in rules
        assert "post_posts" in rules
        assert rules["get_users"].method == "GET"
        assert rules["post_posts"].method == "POST"

    def test_extract_with_openapi_links(self) -> None:
        openapi_schema = {
            "paths": {
                "/users": {
                    "post": {
                        "operationId": "createUser",
                        "responses": {
                            "201": {
                                "links": {
                                    "GetUser": {
                                        "operationId": "getUser",
                                        "parameters": {"userId": "$response.body#/id"},
                                    }
                                }
                            }
                        },
                    }
                },
                "/users/{userId}": {
                    "get": {
                        "operationId": "getUser",
                        "responses": {"200": {"description": "Success"}},
                    }
                },
            }
        }

        route1 = MagicMock()
        route1.path = "/users"
        route1.methods = ["POST"]

        route2 = MagicMock()
        route2.path = "/users/{userId}"
        route2.methods = ["GET"]

        routes = [route1, route2]

        bundles, rules = _extract_bundles_from_openapi(openapi_schema, routes)

        assert "id_bundle" in bundles
        assert bundles["id_bundle"].name == "id_bundle"
        assert "createUser" in rules
        assert "getUser" in rules
        assert rules["createUser"].output_bundles == {"id": "id_bundle"}
        assert rules["getUser"].input_bundles == {"userId": "id_bundle"}
        assert len(rules["getUser"].preconditions) == 1


class TestStatefulTestFactory:
    """Tests for StatefulTestFactory."""

    def test_initialization(self) -> None:
        runner = MagicMock()
        factory = StatefulTestFactory(runner)

        assert factory.runner is runner

    def test_create_test(self) -> None:
        runner = MagicMock()
        factory = StatefulTestFactory(runner)

        test_func = factory.create_test("test_workflow")

        assert callable(test_func)
        assert test_func.__name__ == "test_workflow"
        assert "Stateful API test: test_workflow" in test_func.__doc__

    def test_create_tests_for_routes_empty(self) -> None:
        runner = MagicMock()
        factory = StatefulTestFactory(runner)

        tests = factory.create_tests_for_routes([])

        assert tests == []


@pytest.mark.asyncio
class TestStatefulTestRunnerAsync:
    """Async tests for StatefulTestRunner."""

    async def test_run_stateful_tests_disabled(self) -> None:
        app = MagicMock()
        config = StatefulTestConfig(enabled=False)
        runner = StatefulTestRunner(app, config)

        results = await runner.run_stateful_tests()

        assert results == []

    async def test_run_hook_async(self) -> None:
        app = MagicMock()
        config = StatefulTestConfig()
        runner = StatefulTestRunner(app, config)

        async def async_hook(context: dict[str, Any]) -> None:
            context["called"] = True

        context: dict[str, Any] = {}
        await runner._run_hook(async_hook, context)

        assert context["called"] is True

    async def test_run_hook_sync(self) -> None:
        app = MagicMock()
        config = StatefulTestConfig()
        runner = StatefulTestRunner(app, config)

        def sync_hook(context: dict[str, Any]) -> None:
            context["called"] = True

        context: dict[str, Any] = {}
        await runner._run_hook(sync_hook, context)

        assert context["called"] is True

    async def test_run_hook_timeout(self) -> None:
        app = MagicMock()
        config = StatefulTestConfig(hook_config=HookConfig(hook_timeout=0.1))
        runner = StatefulTestRunner(app, config)

        async def slow_hook(context: dict[str, Any]) -> None:
            import asyncio

            await asyncio.sleep(1.0)

        context: dict[str, Any] = {}

        with pytest.raises(TimeoutError):
            await runner._run_hook(slow_hook, context)
