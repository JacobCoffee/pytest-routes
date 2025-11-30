"""Route coverage metrics for pytest-routes."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from pytest_routes.discovery.base import RouteInfo


@dataclass
class RouteCoverage:
    """Coverage information for a single route.

    Attributes:
        route_path: The route path.
        method: HTTP method.
        tested: Whether this route was tested.
        test_count: Number of tests run against this route.
        status_codes_seen: Status codes returned during testing.
        parameters_tested: Parameter names that were tested.
        body_tested: Whether request body was tested.
    """

    route_path: str
    method: str
    tested: bool = False
    test_count: int = 0
    status_codes_seen: set[int] = field(default_factory=set)
    parameters_tested: set[str] = field(default_factory=set)
    body_tested: bool = False

    @property
    def coverage_score(self) -> float:
        """Calculate coverage score (0-100)."""
        if not self.tested:
            return 0.0

        score = 50.0

        if len(self.status_codes_seen) > 1:
            score += 20.0

        if self.parameters_tested:
            score += 15.0

        if self.body_tested:
            score += 15.0

        return min(score, 100.0)

    def mark_tested(
        self,
        status_code: int,
        parameters: set[str] | None = None,
        *,
        has_body: bool = False,
    ) -> None:
        """Mark this route as tested.

        Args:
            status_code: Status code returned.
            parameters: Parameters that were tested.
            has_body: Whether request body was included.
        """
        self.tested = True
        self.test_count += 1
        self.status_codes_seen.add(status_code)
        if parameters:
            self.parameters_tested.update(parameters)
        if has_body:
            self.body_tested = True

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "route_path": self.route_path,
            "method": self.method,
            "tested": self.tested,
            "test_count": self.test_count,
            "status_codes_seen": sorted(self.status_codes_seen),
            "parameters_tested": sorted(self.parameters_tested),
            "body_tested": self.body_tested,
            "coverage_score": round(self.coverage_score, 1),
        }


@dataclass
class CoverageMetrics:
    """Aggregate coverage metrics across all routes.

    Attributes:
        total_routes: Total number of routes in the application.
        tested_routes: Number of routes that were tested.
        untested_routes: List of routes that were not tested.
        route_coverage: Coverage information per route.
    """

    total_routes: int = 0
    route_coverage: dict[str, RouteCoverage] = field(default_factory=dict)

    @property
    def tested_routes(self) -> int:
        """Number of routes tested."""
        return sum(1 for rc in self.route_coverage.values() if rc.tested)

    @property
    def untested_routes(self) -> list[str]:
        """List of routes that were not tested."""
        return [f"{rc.method} {rc.route_path}" for rc in self.route_coverage.values() if not rc.tested]

    @property
    def coverage_percentage(self) -> float:
        """Overall route coverage as a percentage."""
        if self.total_routes == 0:
            return 0.0
        return (self.tested_routes / self.total_routes) * 100

    @property
    def average_coverage_score(self) -> float:
        """Average coverage score across all tested routes."""
        tested = [rc for rc in self.route_coverage.values() if rc.tested]
        if not tested:
            return 0.0
        return sum(rc.coverage_score for rc in tested) / len(tested)

    def add_route(self, route: RouteInfo) -> RouteCoverage:
        """Add a route to track coverage.

        Args:
            route: The route to track.

        Returns:
            RouteCoverage instance for the route.
        """
        key = f"{route.methods[0]}:{route.path}"
        if key not in self.route_coverage:
            self.route_coverage[key] = RouteCoverage(
                route_path=route.path,
                method=route.methods[0],
            )
            self.total_routes += 1
        return self.route_coverage[key]

    def get_route_coverage(self, route: RouteInfo) -> RouteCoverage | None:
        """Get coverage for a specific route.

        Args:
            route: The route to get coverage for.

        Returns:
            RouteCoverage or None if not tracked.
        """
        key = f"{route.methods[0]}:{route.path}"
        return self.route_coverage.get(key)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "total_routes": self.total_routes,
            "tested_routes": self.tested_routes,
            "untested_routes": self.untested_routes,
            "coverage_percentage": round(self.coverage_percentage, 1),
            "average_coverage_score": round(self.average_coverage_score, 1),
            "routes": {k: v.to_dict() for k, v in self.route_coverage.items()},
        }


def calculate_coverage(
    all_routes: list[RouteInfo],
    tested_routes: list[RouteInfo],
) -> CoverageMetrics:
    """Calculate coverage metrics.

    Args:
        all_routes: All routes in the application.
        tested_routes: Routes that were actually tested.

    Returns:
        CoverageMetrics with coverage information.
    """
    metrics = CoverageMetrics()

    for route in all_routes:
        metrics.add_route(route)

    tested_keys = {f"{r.methods[0]}:{r.path}" for r in tested_routes}
    for key in tested_keys:
        if key in metrics.route_coverage:
            metrics.route_coverage[key].tested = True

    return metrics
