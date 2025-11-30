"""Tests for reporting module."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import pytest

from pytest_routes.discovery.base import RouteInfo
from pytest_routes.reporting.html import HTMLReportGenerator, ReportConfig
from pytest_routes.reporting.metrics import RouteMetrics, TestMetrics, aggregate_metrics
from pytest_routes.reporting.route_coverage import CoverageMetrics, RouteCoverage, calculate_coverage

if TYPE_CHECKING:
    pass


class TestRouteMetrics:
    """Tests for RouteMetrics."""

    def test_initial_state(self):
        metrics = RouteMetrics(route_path="/users", method="GET")
        assert metrics.route_path == "/users"
        assert metrics.method == "GET"
        assert metrics.total_requests == 0
        assert metrics.successful_requests == 0
        assert metrics.failed_requests == 0
        assert metrics.total_time_ms == 0.0
        assert metrics.avg_time_ms == 0.0

    def test_record_request_success(self):
        metrics = RouteMetrics(route_path="/users", method="GET")
        metrics.record_request(200, 50.0, success=True)

        assert metrics.total_requests == 1
        assert metrics.successful_requests == 1
        assert metrics.failed_requests == 0
        assert metrics.total_time_ms == 50.0
        assert metrics.min_time_ms == 50.0
        assert metrics.max_time_ms == 50.0
        assert metrics.status_codes == {200: 1}

    def test_record_request_failure(self):
        metrics = RouteMetrics(route_path="/users", method="GET")
        metrics.record_request(500, 100.0, success=False, error="Server error")

        assert metrics.total_requests == 1
        assert metrics.successful_requests == 0
        assert metrics.failed_requests == 1
        assert metrics.errors == ["Server error"]

    def test_multiple_requests(self):
        metrics = RouteMetrics(route_path="/users", method="GET")
        metrics.record_request(200, 50.0, success=True)
        metrics.record_request(200, 100.0, success=True)
        metrics.record_request(500, 25.0, success=False)

        assert metrics.total_requests == 3
        assert metrics.successful_requests == 2
        assert metrics.failed_requests == 1
        assert metrics.avg_time_ms == pytest.approx(58.33, rel=0.01)
        assert metrics.min_time_ms == 25.0
        assert metrics.max_time_ms == 100.0

    def test_success_rate(self):
        metrics = RouteMetrics(route_path="/users", method="GET")
        metrics.record_request(200, 50.0, success=True)
        metrics.record_request(200, 50.0, success=True)
        metrics.record_request(500, 50.0, success=False)

        assert metrics.success_rate == pytest.approx(66.67, rel=0.01)

    def test_passed_property(self):
        metrics = RouteMetrics(route_path="/users", method="GET")
        metrics.record_request(200, 50.0, success=True)
        assert metrics.passed is True

        metrics.record_request(500, 50.0, success=False)
        assert metrics.passed is False

    def test_to_dict(self):
        metrics = RouteMetrics(route_path="/users", method="GET")
        metrics.record_request(200, 50.0, success=True)

        result = metrics.to_dict()
        assert result["route_path"] == "/users"
        assert result["method"] == "GET"
        assert result["total_requests"] == 1
        assert result["passed"] is True


class TestTestMetrics:
    """Tests for TestMetrics."""

    def test_initial_state(self):
        metrics = TestMetrics()
        assert metrics.total_routes == 0
        assert metrics.passed_routes == 0
        assert metrics.failed_routes == 0
        assert metrics.skipped_routes == 0

    def test_get_or_create_route_metrics(self):
        metrics = TestMetrics()
        route = RouteInfo(
            path="/users",
            methods=["GET"],
            path_params={},
            query_params={},
            body_type=None,
        )

        rm = metrics.get_or_create_route_metrics(route)
        assert rm.route_path == "/users"
        assert rm.method == "GET"

        rm2 = metrics.get_or_create_route_metrics(route)
        assert rm is rm2

    def test_pass_rate(self):
        metrics = TestMetrics()
        route1 = RouteInfo(path="/users", methods=["GET"], path_params={}, query_params={}, body_type=None)
        route2 = RouteInfo(path="/users", methods=["POST"], path_params={}, query_params={}, body_type=None)

        rm1 = metrics.get_or_create_route_metrics(route1)
        rm1.record_request(200, 50.0, success=True)

        rm2 = metrics.get_or_create_route_metrics(route2)
        rm2.record_request(500, 50.0, success=False)

        assert metrics.pass_rate == 50.0

    def test_finish(self):
        metrics = TestMetrics()
        assert metrics.end_time is None

        metrics.finish()
        assert metrics.end_time is not None
        assert metrics.duration_seconds >= 0

    def test_to_dict(self):
        metrics = TestMetrics()
        metrics.finish()

        result = metrics.to_dict()
        assert "start_time" in result
        assert "end_time" in result
        assert "duration_seconds" in result
        assert "total_routes" in result
        assert "pass_rate" in result


class TestAggregrateMetrics:
    """Tests for aggregate_metrics function."""

    def test_aggregate_empty(self):
        result = aggregate_metrics([])
        assert result.total_routes == 0

    def test_aggregate_multiple(self):
        rm1 = RouteMetrics(route_path="/users", method="GET")
        rm1.record_request(200, 50.0, success=True)

        rm2 = RouteMetrics(route_path="/users", method="POST")
        rm2.record_request(500, 100.0, success=False)

        result = aggregate_metrics([rm1, rm2])
        assert result.total_routes == 2
        assert result.passed_routes == 1
        assert result.failed_routes == 1


class TestRouteCoverage:
    """Tests for RouteCoverage."""

    def test_initial_state(self):
        coverage = RouteCoverage(route_path="/users", method="GET")
        assert coverage.tested is False
        assert coverage.test_count == 0
        assert coverage.coverage_score == 0.0

    def test_mark_tested(self):
        coverage = RouteCoverage(route_path="/users", method="GET")
        coverage.mark_tested(200, parameters={"id"}, has_body=True)

        assert coverage.tested is True
        assert coverage.test_count == 1
        assert 200 in coverage.status_codes_seen
        assert "id" in coverage.parameters_tested
        assert coverage.body_tested is True

    def test_coverage_score_basic(self):
        coverage = RouteCoverage(route_path="/users", method="GET")
        coverage.mark_tested(200)

        assert coverage.coverage_score == 50.0

    def test_coverage_score_full(self):
        coverage = RouteCoverage(route_path="/users", method="GET")
        coverage.mark_tested(200, parameters={"id"}, has_body=True)
        coverage.mark_tested(400)

        assert coverage.coverage_score == 100.0

    def test_to_dict(self):
        coverage = RouteCoverage(route_path="/users", method="GET")
        coverage.mark_tested(200)

        result = coverage.to_dict()
        assert result["route_path"] == "/users"
        assert result["tested"] is True
        assert "coverage_score" in result


class TestCoverageMetrics:
    """Tests for CoverageMetrics."""

    def test_add_route(self):
        metrics = CoverageMetrics()
        route = RouteInfo(path="/users", methods=["GET"], path_params={}, query_params={}, body_type=None)

        coverage = metrics.add_route(route)
        assert metrics.total_routes == 1
        assert coverage.route_path == "/users"

    def test_coverage_percentage(self):
        metrics = CoverageMetrics()
        route1 = RouteInfo(path="/users", methods=["GET"], path_params={}, query_params={}, body_type=None)
        route2 = RouteInfo(path="/users", methods=["POST"], path_params={}, query_params={}, body_type=None)

        c1 = metrics.add_route(route1)
        metrics.add_route(route2)

        c1.mark_tested(200)

        assert metrics.coverage_percentage == 50.0
        assert metrics.tested_routes == 1

    def test_untested_routes(self):
        metrics = CoverageMetrics()
        route1 = RouteInfo(path="/users", methods=["GET"], path_params={}, query_params={}, body_type=None)
        route2 = RouteInfo(path="/users", methods=["POST"], path_params={}, query_params={}, body_type=None)

        c1 = metrics.add_route(route1)
        metrics.add_route(route2)

        c1.mark_tested(200)

        untested = metrics.untested_routes
        assert len(untested) == 1
        assert "POST /users" in untested


class TestCalculateCoverage:
    """Tests for calculate_coverage function."""

    def test_calculate_coverage(self):
        all_routes = [
            RouteInfo(path="/users", methods=["GET"], path_params={}, query_params={}, body_type=None),
            RouteInfo(path="/users", methods=["POST"], path_params={}, query_params={}, body_type=None),
        ]
        tested_routes = [
            RouteInfo(path="/users", methods=["GET"], path_params={}, query_params={}, body_type=None),
        ]

        metrics = calculate_coverage(all_routes, tested_routes)

        assert metrics.total_routes == 2
        assert metrics.tested_routes == 1
        assert metrics.coverage_percentage == 50.0


class TestHTMLReportGenerator:
    """Tests for HTMLReportGenerator."""

    def test_default_config(self):
        generator = HTMLReportGenerator()
        assert generator.config.title == "pytest-routes Test Report"
        assert generator.config.theme == "light"

    def test_custom_config(self):
        config = ReportConfig(title="Custom Report", theme="dark")
        generator = HTMLReportGenerator(config)
        assert generator.config.title == "Custom Report"
        assert generator.config.theme == "dark"

    def test_generate_html(self):
        metrics = TestMetrics()
        route = RouteInfo(path="/users", methods=["GET"], path_params={}, query_params={}, body_type=None)
        rm = metrics.get_or_create_route_metrics(route)
        rm.record_request(200, 50.0, success=True)
        metrics.finish()

        generator = HTMLReportGenerator()
        html = generator.generate(metrics)

        assert "pytest-routes Test Report" in html
        assert "/users" in html
        assert "GET" in html

    def test_generate_html_with_coverage(self):
        metrics = TestMetrics()
        coverage = CoverageMetrics()

        route = RouteInfo(path="/users", methods=["GET"], path_params={}, query_params={}, body_type=None)
        rm = metrics.get_or_create_route_metrics(route)
        rm.record_request(200, 50.0, success=True)

        c = coverage.add_route(route)
        c.mark_tested(200)

        metrics.finish()

        generator = HTMLReportGenerator()
        html = generator.generate(metrics, coverage)

        assert "Coverage" in html or "coverage" in html.lower()

    def test_write_report(self, tmp_path):
        metrics = TestMetrics()
        metrics.finish()

        config = ReportConfig(output_path=tmp_path / "report.html")
        generator = HTMLReportGenerator(config)
        report_path = generator.write(metrics)

        assert report_path.exists()
        content = report_path.read_text()
        assert "pytest-routes Test Report" in content

    def test_to_json(self):
        metrics = TestMetrics()
        metrics.finish()

        generator = HTMLReportGenerator()
        json_str = generator.to_json(metrics)

        data = json.loads(json_str)
        assert "generated_at" in data
        assert "metrics" in data

    def test_write_json(self, tmp_path):
        metrics = TestMetrics()
        metrics.finish()

        generator = HTMLReportGenerator()
        json_path = generator.write_json(metrics, output_path=tmp_path / "report.json")

        assert json_path.exists()
        data = json.loads(json_path.read_text())
        assert "metrics" in data
