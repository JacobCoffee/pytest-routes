"""pytest-routes: Property-based smoke testing for ASGI application routes."""

from __future__ import annotations

from pytest_routes.__metadata__ import __version__
from pytest_routes.auth import (
    APIKeyAuth,
    AuthProvider,
    BearerTokenAuth,
    CompositeAuth,
    NoAuth,
)
from pytest_routes.config import (
    ReportConfig,
    RouteOverride,
    RouteTestConfig,
    SchemathesisConfig,
    load_config_from_pyproject,
    merge_configs,
)
from pytest_routes.discovery import get_extractor
from pytest_routes.discovery.base import RouteExtractor, RouteInfo
from pytest_routes.execution.client import RouteTestClient
from pytest_routes.execution.runner import RouteTestFailure, RouteTestRunner
from pytest_routes.generation.headers import (
    generate_headers,
    generate_optional_headers,
    register_header_strategy,
)
from pytest_routes.generation.strategies import (
    get_registered_types,
    register_strategies,
    register_strategy,
    strategy_for_type,
    strategy_provider,
    temporary_strategy,
    unregister_strategy,
)
from pytest_routes.integrations.schemathesis import (
    SchemathesisAdapter,
    SchemathesisValidator,
    schemathesis_available,
)
from pytest_routes.reporting import (
    CoverageMetrics,
    HTMLReportGenerator,
    RouteCoverage,
    RouteMetrics,
    TestMetrics,
    aggregate_metrics,
    calculate_coverage,
)
from pytest_routes.validation.response import (
    CompositeValidator,
    ContentTypeValidator,
    JsonSchemaValidator,
    OpenAPIResponseValidator,
    ResponseValidator,
    StatusCodeValidator,
    ValidationResult,
)

__all__ = [
    "__version__",
    # Auth
    "APIKeyAuth",
    "AuthProvider",
    "BearerTokenAuth",
    "CompositeAuth",
    "NoAuth",
    # Config
    "ReportConfig",
    "RouteOverride",
    "RouteTestConfig",
    "SchemathesisConfig",
    "load_config_from_pyproject",
    "merge_configs",
    # Discovery
    "RouteExtractor",
    "RouteInfo",
    "get_extractor",
    # Execution
    "RouteTestClient",
    "RouteTestFailure",
    "RouteTestRunner",
    # Generation - Strategies
    "get_registered_types",
    "register_strategies",
    "register_strategy",
    "strategy_for_type",
    "strategy_provider",
    "temporary_strategy",
    "unregister_strategy",
    # Generation - Headers
    "generate_headers",
    "generate_optional_headers",
    "register_header_strategy",
    # Validation
    "CompositeValidator",
    "ContentTypeValidator",
    "JsonSchemaValidator",
    "OpenAPIResponseValidator",
    "ResponseValidator",
    "StatusCodeValidator",
    "ValidationResult",
    # Integrations
    "SchemathesisAdapter",
    "SchemathesisValidator",
    "schemathesis_available",
    # Reporting
    "CoverageMetrics",
    "HTMLReportGenerator",
    "RouteCoverage",
    "RouteMetrics",
    "TestMetrics",
    "aggregate_metrics",
    "calculate_coverage",
]
