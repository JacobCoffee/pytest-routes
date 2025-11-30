"""Reporting module for pytest-routes."""

from __future__ import annotations

from pytest_routes.reporting.html import HTMLReportGenerator
from pytest_routes.reporting.metrics import (
    RouteMetrics,
    RunMetrics,
    aggregate_metrics,
)
from pytest_routes.reporting.route_coverage import (
    CoverageMetrics,
    RouteCoverage,
    calculate_coverage,
)

__all__ = [
    "CoverageMetrics",
    "HTMLReportGenerator",
    "RouteCoverage",
    "RouteMetrics",
    "RunMetrics",
    "aggregate_metrics",
    "calculate_coverage",
]
