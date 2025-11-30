"""HTML report generation for pytest-routes."""

from __future__ import annotations

import html
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from pytest_routes.reporting.metrics import RunMetrics
    from pytest_routes.reporting.route_coverage import CoverageMetrics


def _jinja2_available() -> bool:
    """Check if Jinja2 is available."""
    try:
        import jinja2  # noqa: F401

        return True
    except ImportError:
        return False


@dataclass
class ReportConfig:
    """Configuration for HTML report generation.

    Attributes:
        output_path: Path to write the HTML report.
        title: Title for the report.
        include_charts: Whether to include charts.
        include_details: Whether to include detailed route info.
        theme: Color theme ('light' or 'dark').
    """

    output_path: Path | str = "pytest-routes-report.html"
    title: str = "pytest-routes Test Report"
    include_charts: bool = True
    include_details: bool = True
    theme: str = "light"

    def __post_init__(self) -> None:
        if isinstance(self.output_path, str):
            self.output_path = Path(self.output_path)


_REPORT_TEMPLATE = """<!DOCTYPE html>
<html lang="en" data-theme="{{ theme }}">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ title }}</title>
    <style>
        :root {
            --bg-color: #ffffff;
            --text-color: #1a1a1a;
            --card-bg: #f8f9fa;
            --border-color: #dee2e6;
            --success-color: #28a745;
            --danger-color: #dc3545;
            --warning-color: #ffc107;
            --info-color: #17a2b8;
            --primary-color: #dc2626;
        }
        [data-theme="dark"] {
            --bg-color: #1a1a1a;
            --text-color: #f0f0f0;
            --card-bg: #2d2d2d;
            --border-color: #404040;
        }
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: var(--bg-color);
            color: var(--text-color);
            line-height: 1.6;
            padding: 2rem;
        }
        .container { max-width: 1200px; margin: 0 auto; }
        header {
            text-align: center;
            margin-bottom: 2rem;
            padding-bottom: 1rem;
            border-bottom: 2px solid var(--primary-color);
        }
        h1 { font-size: 2rem; color: var(--primary-color); }
        .meta { color: #666; font-size: 0.9rem; margin-top: 0.5rem; }
        .summary {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 1rem;
            margin-bottom: 2rem;
        }
        .card {
            background: var(--card-bg);
            border-radius: 8px;
            padding: 1.5rem;
            border: 1px solid var(--border-color);
        }
        .card h3 { font-size: 0.9rem; color: #666; text-transform: uppercase; }
        .card .value {
            font-size: 2rem;
            font-weight: 700;
            margin-top: 0.5rem;
        }
        .card.success .value { color: var(--success-color); }
        .card.danger .value { color: var(--danger-color); }
        .card.info .value { color: var(--info-color); }
        .progress-bar {
            height: 8px;
            background: var(--border-color);
            border-radius: 4px;
            overflow: hidden;
            margin-top: 1rem;
        }
        .progress-bar .fill {
            height: 100%;
            background: var(--primary-color);
            transition: width 0.3s;
        }
        table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 1rem;
        }
        th, td {
            padding: 0.75rem;
            text-align: left;
            border-bottom: 1px solid var(--border-color);
        }
        th { background: var(--card-bg); font-weight: 600; }
        tr:hover { background: var(--card-bg); }
        .status {
            display: inline-block;
            padding: 0.25rem 0.75rem;
            border-radius: 4px;
            font-size: 0.8rem;
            font-weight: 600;
        }
        .status.passed { background: #d4edda; color: #155724; }
        .status.failed { background: #f8d7da; color: #721c24; }
        .status.skipped { background: #fff3cd; color: #856404; }
        [data-theme="dark"] .status.passed { background: #1e4620; color: #a3d9a5; }
        [data-theme="dark"] .status.failed { background: #4a1a1a; color: #f5a5a5; }
        [data-theme="dark"] .status.skipped { background: #4a3f1a; color: #f5d9a5; }
        .method {
            font-family: monospace;
            font-weight: 600;
            padding: 0.2rem 0.5rem;
            border-radius: 3px;
            font-size: 0.85rem;
        }
        .method.GET { background: #61affe; color: white; }
        .method.POST { background: #49cc90; color: white; }
        .method.PUT { background: #fca130; color: white; }
        .method.DELETE { background: #f93e3e; color: white; }
        .method.PATCH { background: #50e3c2; color: white; }
        .path { font-family: monospace; }
        .timing { font-family: monospace; color: #666; }
        section { margin-bottom: 2rem; }
        section h2 {
            font-size: 1.25rem;
            margin-bottom: 1rem;
            padding-bottom: 0.5rem;
            border-bottom: 1px solid var(--border-color);
        }
        .chart-container {
            display: flex;
            justify-content: center;
            gap: 2rem;
            margin: 1rem 0;
        }
        .pie-chart {
            width: 150px;
            height: 150px;
            border-radius: 50%;
            position: relative;
        }
        .pie-legend {
            display: flex;
            flex-direction: column;
            justify-content: center;
            gap: 0.5rem;
        }
        .pie-legend-item {
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }
        .pie-legend-color {
            width: 12px;
            height: 12px;
            border-radius: 2px;
        }
        footer {
            text-align: center;
            margin-top: 2rem;
            padding-top: 1rem;
            border-top: 1px solid var(--border-color);
            color: #666;
            font-size: 0.85rem;
        }
        footer a { color: var(--primary-color); text-decoration: none; }
        .collapsible { cursor: pointer; }
        .collapsible:after { content: ' ▼'; font-size: 0.7em; }
        .collapsible.active:after { content: ' ▲'; }
        .details { display: none; padding: 1rem; background: var(--card-bg); }
        .details.show { display: block; }
        .errors { color: var(--danger-color); font-family: monospace; font-size: 0.85rem; }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>{{ title }}</h1>
            <p class="meta">Generated on {{ generated_at }} | Duration: {{ duration }}s</p>
        </header>

        <section class="summary">
            <div class="card {% if passed_routes == total_routes %}success{% elif failed_routes > 0 %}danger{% else %}info{% endif %}">
                <h3>Pass Rate</h3>
                <div class="value">{{ pass_rate }}%</div>
                <div class="progress-bar">
                    <div class="fill" style="width: {{ pass_rate }}%"></div>
                </div>
            </div>
            <div class="card success">
                <h3>Passed Routes</h3>
                <div class="value">{{ passed_routes }}</div>
            </div>
            <div class="card {% if failed_routes > 0 %}danger{% endif %}">
                <h3>Failed Routes</h3>
                <div class="value">{{ failed_routes }}</div>
            </div>
            <div class="card info">
                <h3>Total Requests</h3>
                <div class="value">{{ total_requests }}</div>
            </div>
        </section>

        {% if coverage %}
        <section>
            <h2>Coverage Metrics</h2>
            <div class="summary">
                <div class="card">
                    <h3>Route Coverage</h3>
                    <div class="value">{{ coverage.coverage_percentage }}%</div>
                    <div class="progress-bar">
                        <div class="fill" style="width: {{ coverage.coverage_percentage }}%"></div>
                    </div>
                </div>
                <div class="card">
                    <h3>Tested Routes</h3>
                    <div class="value">{{ coverage.tested_routes }} / {{ coverage.total_routes }}</div>
                </div>
                <div class="card">
                    <h3>Avg Coverage Score</h3>
                    <div class="value">{{ coverage.average_coverage_score }}</div>
                </div>
            </div>
            {% if coverage.untested_routes %}
            <details>
                <summary style="cursor: pointer; color: var(--warning-color);">
                    {{ coverage.untested_routes|length }} untested routes
                </summary>
                <ul style="margin-top: 0.5rem; padding-left: 1.5rem;">
                {% for route in coverage.untested_routes %}
                    <li class="path">{{ route }}</li>
                {% endfor %}
                </ul>
            </details>
            {% endif %}
        </section>
        {% endif %}

        <section>
            <h2>Route Results</h2>
            <table>
                <thead>
                    <tr>
                        <th>Method</th>
                        <th>Path</th>
                        <th>Status</th>
                        <th>Requests</th>
                        <th>Avg Time</th>
                        <th>Success Rate</th>
                    </tr>
                </thead>
                <tbody>
                {% for route in routes %}
                    <tr>
                        <td><span class="method {{ route.method }}">{{ route.method }}</span></td>
                        <td class="path">{{ route.route_path }}</td>
                        <td><span class="status {% if route.passed %}passed{% else %}failed{% endif %}">
                            {% if route.passed %}PASSED{% else %}FAILED{% endif %}
                        </span></td>
                        <td>{{ route.total_requests }}</td>
                        <td class="timing">{{ route.avg_time_ms }}ms</td>
                        <td>{{ route.success_rate }}%</td>
                    </tr>
                    {% if route.errors %}
                    <tr>
                        <td colspan="6" class="errors">
                            {% for error in route.errors[:3] %}
                            <div>{{ error }}</div>
                            {% endfor %}
                            {% if route.errors|length > 3 %}
                            <div>... and {{ route.errors|length - 3 }} more errors</div>
                            {% endif %}
                        </td>
                    </tr>
                    {% endif %}
                {% endfor %}
                </tbody>
            </table>
        </section>

        <footer>
            <p>Generated by <a href="https://github.com/JacobCoffee/pytest-routes">pytest-routes</a></p>
        </footer>
    </div>
</body>
</html>
"""

_SIMPLE_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
        body {{ font-family: sans-serif; padding: 2rem; max-width: 1200px; margin: 0 auto; }}
        h1 {{ color: #dc2626; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 1rem; }}
        th, td {{ padding: 0.5rem; text-align: left; border-bottom: 1px solid #ddd; }}
        th {{ background: #f5f5f5; }}
        .passed {{ color: green; }}
        .failed {{ color: red; }}
        .summary {{ display: flex; gap: 2rem; margin: 1rem 0; }}
        .stat {{ padding: 1rem; background: #f5f5f5; border-radius: 8px; }}
        .stat-value {{ font-size: 2rem; font-weight: bold; }}
    </style>
</head>
<body>
    <h1>{title}</h1>
    <p>Generated on {generated_at} | Duration: {duration}s</p>
    <div class="summary">
        <div class="stat"><div class="stat-value">{pass_rate}%</div>Pass Rate</div>
        <div class="stat"><div class="stat-value passed">{passed_routes}</div>Passed</div>
        <div class="stat"><div class="stat-value failed">{failed_routes}</div>Failed</div>
        <div class="stat"><div class="stat-value">{total_requests}</div>Requests</div>
    </div>
    <table>
        <tr><th>Method</th><th>Path</th><th>Status</th><th>Requests</th><th>Avg Time</th></tr>
        {rows}
    </table>
    <p style="margin-top: 2rem; color: #666;">
        Generated by <a href="https://github.com/JacobCoffee/pytest-routes">pytest-routes</a>
    </p>
</body>
</html>
"""


class HTMLReportGenerator:
    """Generate HTML reports for pytest-routes test results."""

    def __init__(self, config: ReportConfig | None = None) -> None:
        """Initialize the report generator.

        Args:
            config: Report configuration options.
        """
        self.config = config or ReportConfig()
        self._use_jinja = _jinja2_available()

    def generate(
        self,
        metrics: RunMetrics,
        coverage: CoverageMetrics | None = None,
    ) -> str:
        """Generate HTML report.

        Args:
            metrics: Test metrics to include.
            coverage: Optional coverage metrics.

        Returns:
            HTML content as a string.
        """
        if self._use_jinja:
            return self._generate_with_jinja(metrics, coverage)
        return self._generate_simple(metrics, coverage)

    def write(
        self,
        metrics: RunMetrics,
        coverage: CoverageMetrics | None = None,
    ) -> Path:
        """Generate and write HTML report to file.

        Args:
            metrics: Test metrics to include.
            coverage: Optional coverage metrics.

        Returns:
            Path to the written file.
        """
        content = self.generate(metrics, coverage)
        output_path = Path(self.config.output_path)
        output_path.write_text(content, encoding="utf-8")
        return output_path

    def _generate_with_jinja(
        self,
        metrics: RunMetrics,
        coverage: CoverageMetrics | None,
    ) -> str:
        """Generate report using Jinja2 templates."""
        from jinja2 import Environment

        env = Environment(autoescape=True)
        template = env.from_string(_REPORT_TEMPLATE)

        routes = sorted(
            [rm.to_dict() for rm in metrics.routes.values()],
            key=lambda r: (not r["passed"], r["route_path"]),
        )

        context = {
            "title": self.config.title,
            "theme": self.config.theme,
            "generated_at": datetime.now(tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
            "duration": round(metrics.duration_seconds, 2),
            "pass_rate": round(metrics.pass_rate, 1),
            "passed_routes": metrics.passed_routes,
            "failed_routes": metrics.failed_routes,
            "total_routes": metrics.total_routes,
            "total_requests": metrics.total_requests,
            "routes": routes,
            "coverage": coverage.to_dict() if coverage else None,
        }

        return template.render(**context)

    def _generate_simple(
        self,
        metrics: RunMetrics,
        coverage: CoverageMetrics | None,
    ) -> str:
        """Generate simple HTML report without Jinja2."""
        routes = sorted(
            metrics.routes.values(),
            key=lambda r: (not r.passed, r.route_path),
        )

        rows = []
        for rm in routes:
            status_class = "passed" if rm.passed else "failed"
            status_text = "PASSED" if rm.passed else "FAILED"
            row = (
                f"<tr><td>{html.escape(rm.method)}</td>"
                f"<td>{html.escape(rm.route_path)}</td>"
                f'<td class="{status_class}">{status_text}</td>'
                f"<td>{rm.total_requests}</td>"
                f"<td>{round(rm.avg_time_ms, 2)}ms</td></tr>"
            )
            rows.append(row)

        return _SIMPLE_TEMPLATE.format(
            title=html.escape(self.config.title),
            generated_at=datetime.now(tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
            duration=round(metrics.duration_seconds, 2),
            pass_rate=round(metrics.pass_rate, 1),
            passed_routes=metrics.passed_routes,
            failed_routes=metrics.failed_routes,
            total_requests=metrics.total_requests,
            rows="\n".join(rows),
        )

    def to_json(
        self,
        metrics: RunMetrics,
        coverage: CoverageMetrics | None = None,
    ) -> str:
        """Export metrics as JSON.

        Args:
            metrics: Test metrics to export.
            coverage: Optional coverage metrics.

        Returns:
            JSON string.
        """
        data: dict[str, Any] = {
            "generated_at": datetime.now(tz=timezone.utc).isoformat(),
            "metrics": metrics.to_dict(),
        }
        if coverage:
            data["coverage"] = coverage.to_dict()
        return json.dumps(data, indent=2)

    def write_json(
        self,
        metrics: RunMetrics,
        coverage: CoverageMetrics | None = None,
        output_path: Path | str | None = None,
    ) -> Path:
        """Write metrics as JSON file.

        Args:
            metrics: Test metrics to export.
            coverage: Optional coverage metrics.
            output_path: Path to write to (defaults to report path with .json).

        Returns:
            Path to the written file.
        """
        if output_path is None:
            output_path = Path(self.config.output_path).with_suffix(".json")
        elif isinstance(output_path, str):
            output_path = Path(output_path)

        content = self.to_json(metrics, coverage)
        output_path.write_text(content, encoding="utf-8")
        return output_path
