.. _api-reporting:

=========
Reporting
=========

The reporting module provides HTML report generation and metrics collection for
route smoke tests.


Metrics Classes
===============

RouteMetrics
------------

Collects metrics for a single route during testing.

.. autoclass:: pytest_routes.reporting.RouteMetrics
   :members:
   :undoc-members:
   :show-inheritance:


RunMetrics
-----------

Aggregates metrics across all routes for a test run.

.. autoclass:: pytest_routes.reporting.RunMetrics
   :members:
   :undoc-members:
   :show-inheritance:


Metrics Functions
-----------------

.. autofunction:: pytest_routes.reporting.aggregate_metrics


Coverage Classes
================

RouteCoverage
-------------

Tracks coverage for a single route.

.. autoclass:: pytest_routes.reporting.RouteCoverage
   :members:
   :undoc-members:
   :show-inheritance:


CoverageMetrics
---------------

Aggregates coverage across all routes.

.. autoclass:: pytest_routes.reporting.CoverageMetrics
   :members:
   :undoc-members:
   :show-inheritance:


Coverage Functions
------------------

.. autofunction:: pytest_routes.reporting.calculate_coverage


HTML Report Generation
======================

HTMLReportGenerator
-------------------

Generates HTML and JSON reports from test metrics.

.. autoclass:: pytest_routes.reporting.HTMLReportGenerator
   :members:
   :undoc-members:
   :show-inheritance:


ReportConfig
------------

Configuration for report generation.

.. autoclass:: pytest_routes.reporting.html.ReportConfig
   :members:
   :undoc-members:
   :show-inheritance:


Usage Examples
==============

Collecting Metrics
------------------

.. code-block:: python

   from pytest_routes.reporting import RunMetrics, RouteMetrics
   from pytest_routes.discovery.base import RouteInfo

   # Create test metrics container
   test_metrics = RunMetrics()

   # Get or create metrics for a route
   route = RouteInfo(
       path="/users",
       methods=["GET"],
       path_params={},
       query_params={},
       body_type=None,
   )
   route_metrics = test_metrics.get_or_create_route_metrics(route)

   # Record individual requests
   route_metrics.record_request(
       status_code=200,
       time_ms=12.5,
       success=True,
   )
   route_metrics.record_request(
       status_code=500,
       time_ms=45.0,
       success=False,
       error="Internal server error",
   )

   # Finish collecting metrics
   test_metrics.finish()

   # Access aggregate statistics
   print(f"Total routes: {test_metrics.total_routes}")
   print(f"Pass rate: {test_metrics.pass_rate}%")
   print(f"Duration: {test_metrics.duration_seconds}s")


Calculating Coverage
--------------------

.. code-block:: python

   from pytest_routes.reporting import calculate_coverage, CoverageMetrics
   from pytest_routes.discovery.base import RouteInfo

   # All routes in the application
   all_routes = [
       RouteInfo(path="/users", methods=["GET"], ...),
       RouteInfo(path="/users", methods=["POST"], ...),
       RouteInfo(path="/orders", methods=["GET"], ...),
   ]

   # Routes that were actually tested
   tested_routes = [
       RouteInfo(path="/users", methods=["GET"], ...),
       RouteInfo(path="/users", methods=["POST"], ...),
   ]

   # Calculate coverage
   coverage = calculate_coverage(all_routes, tested_routes)

   print(f"Coverage: {coverage.coverage_percentage}%")
   print(f"Untested routes: {len(coverage.untested_routes)}")


Generating Reports
------------------

.. code-block:: python

   from pytest_routes.reporting import HTMLReportGenerator, RunMetrics
   from pytest_routes.reporting.html import ReportConfig

   # Configure the report
   config = ReportConfig(
       title="API Smoke Test Report",
       include_coverage=True,
       include_timing=True,
       theme="dark",
   )

   # Create generator
   generator = HTMLReportGenerator(config)

   # Generate HTML
   html = generator.generate(test_metrics, coverage_metrics)

   # Write HTML report
   generator.write_report("report.html", test_metrics, coverage_metrics)

   # Write JSON report
   generator.write_json("results.json", test_metrics, coverage_metrics)


See Also
========

* :doc:`/usage/reports` - User guide for reports and metrics
* :doc:`/usage/cli-options` - CLI options for report generation
