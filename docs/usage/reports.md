# Reports and Metrics

pytest-routes can generate comprehensive HTML and JSON reports with detailed metrics
about your route smoke tests. Reports include test results, coverage statistics,
and performance timing data.

## Quick Start

Generate an HTML report with the `--routes-report` flag:

```bash
pytest --routes --routes-app myapp:app --routes-report pytest-routes-report.html
```

This creates a standalone HTML file with:
- Test summary (pass/fail counts)
- Route-by-route results
- Performance metrics per route
- Coverage statistics

## Report Types

### HTML Reports

HTML reports provide a visual, interactive view of your test results.

```bash
# Generate HTML report
pytest --routes --routes-app myapp:app --routes-report report.html

# With custom title
pytest --routes --routes-app myapp:app \
    --routes-report report.html \
    --routes-report-title "API Smoke Tests - Production"
```

**Features:**
- Responsive design (works on desktop and mobile)
- Light and dark theme support
- Sortable and filterable route table
- Color-coded pass/fail status
- Performance metrics visualization

### JSON Reports

JSON reports are ideal for CI/CD integration and programmatic analysis.

```bash
# Generate JSON report
pytest --routes --routes-app myapp:app --routes-report-json results.json

# Generate both HTML and JSON
pytest --routes --routes-app myapp:app \
    --routes-report report.html \
    --routes-report-json results.json
```

**JSON Structure:**

```json
{
  "title": "pytest-routes Report",
  "generated_at": "2025-01-15T10:30:00Z",
  "duration_seconds": 45.3,
  "summary": {
    "total_routes": 25,
    "passed_routes": 23,
    "failed_routes": 2,
    "skipped_routes": 0,
    "pass_rate": 92.0
  },
  "coverage": {
    "total_routes": 30,
    "tested_routes": 25,
    "coverage_percentage": 83.3,
    "untested_routes": [
      {"path": "/admin/settings", "method": "PUT"},
      {"path": "/internal/health", "method": "GET"}
    ]
  },
  "routes": [
    {
      "route_path": "/users",
      "method": "GET",
      "passed": true,
      "total_requests": 100,
      "successful_requests": 100,
      "failed_requests": 0,
      "success_rate": 100.0,
      "avg_time_ms": 12.5,
      "min_time_ms": 5.2,
      "max_time_ms": 45.8,
      "status_codes": {"200": 100}
    }
  ]
}
```

## Configuration

### CLI Options

| Option | Default | Description |
|--------|---------|-------------|
| `--routes-report` | `None` | Path for HTML report |
| `--routes-report-json` | `None` | Path for JSON report |
| `--routes-report-title` | `pytest-routes Report` | Custom report title |

### pyproject.toml Configuration

```toml
[tool.pytest-routes.report]
enabled = true
output_path = "pytest-routes-report.html"
json_output = "pytest-routes-report.json"
title = "API Route Tests"
include_coverage = true
include_timing = true
theme = "light"  # or "dark"
```

## Metrics Collected

### Route Metrics

For each tested route, the following metrics are collected:

| Metric | Description |
|--------|-------------|
| `total_requests` | Total number of test requests made |
| `successful_requests` | Requests that passed validation |
| `failed_requests` | Requests that failed validation |
| `success_rate` | Percentage of successful requests |
| `avg_time_ms` | Average response time in milliseconds |
| `min_time_ms` | Minimum response time |
| `max_time_ms` | Maximum response time |
| `status_codes` | Count of each HTTP status code received |
| `errors` | List of error messages for failed requests |

### Test Metrics

Aggregate metrics for the entire test run:

| Metric | Description |
|--------|-------------|
| `total_routes` | Total number of routes tested |
| `passed_routes` | Routes with no failures |
| `failed_routes` | Routes with at least one failure |
| `skipped_routes` | Routes that were skipped |
| `pass_rate` | Percentage of routes that passed |
| `start_time` | Test run start timestamp |
| `end_time` | Test run end timestamp |
| `duration_seconds` | Total test run duration |

### Coverage Metrics

Route coverage statistics:

| Metric | Description |
|--------|-------------|
| `total_routes` | Total routes in application |
| `tested_routes` | Routes that were tested |
| `untested_routes` | Routes that were not tested |
| `coverage_percentage` | Percentage of routes tested |

## Programmatic Usage

You can use the reporting module programmatically:

```python
from pytest_routes.reporting import (
    HTMLReportGenerator,
    RouteMetrics,
    TestMetrics,
    CoverageMetrics,
    calculate_coverage,
)
from pytest_routes.reporting.html import ReportConfig

# Configure the report
config = ReportConfig(
    title="My API Tests",
    include_coverage=True,
    include_timing=True,
    theme="dark",
)

# Create test metrics
test_metrics = TestMetrics()

# Record route metrics during testing
route = RouteInfo(path="/users", methods=["GET"], ...)
route_metrics = test_metrics.get_or_create_route_metrics(route)
route_metrics.record_request(
    status_code=200,
    time_ms=12.5,
    success=True,
)

# Finish and calculate totals
test_metrics.finish()

# Calculate coverage
all_routes = [...]  # All discovered routes
tested_routes = [...]  # Routes that were tested
coverage = calculate_coverage(all_routes, tested_routes)

# Generate the report
generator = HTMLReportGenerator(config)
html = generator.generate(test_metrics, coverage)

# Write to file
generator.write_report("report.html", test_metrics, coverage)
generator.write_json("results.json", test_metrics, coverage)
```

## CI/CD Integration

### GitHub Actions

```yaml
- name: Run smoke tests with report
  run: |
    pytest --routes \
      --routes-app myapp:app \
      --routes-report pytest-routes-report.html \
      --routes-report-json pytest-routes-results.json

- name: Upload test report
  uses: actions/upload-artifact@v4
  if: always()
  with:
    name: pytest-routes-report
    path: |
      pytest-routes-report.html
      pytest-routes-results.json

- name: Check pass rate
  run: |
    PASS_RATE=$(jq '.summary.pass_rate' pytest-routes-results.json)
    if (( $(echo "$PASS_RATE < 95" | bc -l) )); then
      echo "Pass rate $PASS_RATE% is below threshold of 95%"
      exit 1
    fi
```

### GitLab CI

```yaml
smoke_tests:
  script:
    - pytest --routes --routes-app myapp:app \
        --routes-report pytest-routes-report.html \
        --routes-report-json pytest-routes-results.json
  artifacts:
    paths:
      - pytest-routes-report.html
      - pytest-routes-results.json
    reports:
      junit: pytest-routes-results.json
```

## Customization

### Custom Report Title

```bash
pytest --routes --routes-app myapp:app \
    --routes-report report.html \
    --routes-report-title "Production API - Smoke Tests v2.0"
```

### Theme Selection

Configure the theme in `pyproject.toml`:

```toml
[tool.pytest-routes.report]
theme = "dark"  # Options: "light", "dark"
```

### Selective Metrics

Control which metrics are included:

```toml
[tool.pytest-routes.report]
include_coverage = true   # Include coverage statistics
include_timing = true     # Include performance timing
```

## See Also

- [CLI Options Reference](cli-options.md) - All command-line options
- [Configuration](configuration.md) - pyproject.toml configuration
- [Schemathesis Integration](schemathesis.md) - OpenAPI contract testing
