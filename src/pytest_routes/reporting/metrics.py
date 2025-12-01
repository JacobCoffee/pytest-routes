"""Performance and test metrics for pytest-routes."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from pytest_routes.discovery.base import RouteInfo


@dataclass
class RouteMetrics:
    """Performance and test metrics for a single route.

    Attributes:
        route_path: The route path.
        method: HTTP method.
        total_requests: Total number of requests made.
        successful_requests: Number of successful requests (2xx-4xx).
        failed_requests: Number of failed requests (5xx or unexpected).
        total_time_ms: Total time spent testing this route in milliseconds.
        min_time_ms: Minimum request time in milliseconds.
        max_time_ms: Maximum request time in milliseconds.
        avg_time_ms: Average request time in milliseconds.
        status_codes: Distribution of status codes.
        errors: List of error messages encountered.
    """

    route_path: str
    method: str
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    total_time_ms: float = 0.0
    min_time_ms: float = float("inf")
    max_time_ms: float = 0.0
    status_codes: dict[int, int] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)

    @property
    def avg_time_ms(self) -> float:
        """Calculate average request time."""
        if self.total_requests == 0:
            return 0.0
        return self.total_time_ms / self.total_requests

    @property
    def success_rate(self) -> float:
        """Calculate success rate as a percentage."""
        if self.total_requests == 0:
            return 0.0
        return (self.successful_requests / self.total_requests) * 100

    @property
    def passed(self) -> bool:
        """Check if all requests were successful."""
        return self.failed_requests == 0 and self.total_requests > 0

    def record_request(
        self,
        status_code: int,
        elapsed_ms: float,
        *,
        success: bool = True,
        error: str | None = None,
    ) -> None:
        """Record metrics for a single request.

        Args:
            status_code: HTTP status code returned.
            elapsed_ms: Time taken for the request in milliseconds.
            success: Whether the request was successful.
            error: Error message if the request failed.
        """
        self.total_requests += 1
        self.total_time_ms += elapsed_ms

        self.min_time_ms = min(self.min_time_ms, elapsed_ms)
        self.max_time_ms = max(self.max_time_ms, elapsed_ms)

        self.status_codes[status_code] = self.status_codes.get(status_code, 0) + 1

        if success:
            self.successful_requests += 1
        else:
            self.failed_requests += 1
            if error:
                self.errors.append(error)

    def to_dict(self) -> dict[str, Any]:
        """Convert metrics to dictionary for serialization."""
        return {
            "route_path": self.route_path,
            "method": self.method,
            "total_requests": self.total_requests,
            "successful_requests": self.successful_requests,
            "failed_requests": self.failed_requests,
            "total_time_ms": round(self.total_time_ms, 2),
            "min_time_ms": round(self.min_time_ms, 2) if self.min_time_ms != float("inf") else 0,
            "max_time_ms": round(self.max_time_ms, 2),
            "avg_time_ms": round(self.avg_time_ms, 2),
            "success_rate": round(self.success_rate, 1),
            "passed": self.passed,
            "status_codes": self.status_codes,
            "errors": self.errors,
        }


@dataclass
class RunMetrics:
    """Aggregate test metrics across all routes.

    Attributes:
        start_time: When testing started (Unix timestamp).
        end_time: When testing ended (Unix timestamp).
        routes: Metrics for individual routes.
        total_routes: Total number of routes tested.
        passed_routes: Number of routes that passed.
        failed_routes: Number of routes that failed.
        skipped_routes: Number of routes that were skipped.
    """

    start_time: float = field(default_factory=time.time)
    end_time: float | None = None
    routes: dict[str, RouteMetrics] = field(default_factory=dict)
    skipped_routes: int = 0

    @property
    def total_routes(self) -> int:
        """Total number of routes tested."""
        return len(self.routes)

    @property
    def passed_routes(self) -> int:
        """Number of routes that passed."""
        return sum(1 for m in self.routes.values() if m.passed)

    @property
    def failed_routes(self) -> int:
        """Number of routes that failed."""
        return sum(1 for m in self.routes.values() if not m.passed)

    @property
    def total_requests(self) -> int:
        """Total requests across all routes."""
        return sum(m.total_requests for m in self.routes.values())

    @property
    def total_time_ms(self) -> float:
        """Total time spent testing in milliseconds."""
        return sum(m.total_time_ms for m in self.routes.values())

    @property
    def duration_seconds(self) -> float:
        """Total test duration in seconds."""
        if self.end_time is None:
            return time.time() - self.start_time
        return self.end_time - self.start_time

    @property
    def pass_rate(self) -> float:
        """Percentage of routes that passed."""
        if self.total_routes == 0:
            return 0.0
        return (self.passed_routes / self.total_routes) * 100

    def get_or_create_route_metrics(self, route: RouteInfo) -> RouteMetrics:
        """Get or create metrics for a route.

        Args:
            route: The route to get metrics for.

        Returns:
            RouteMetrics instance for the route.
        """
        key = f"{route.methods[0]}:{route.path}"
        if key not in self.routes:
            self.routes[key] = RouteMetrics(
                route_path=route.path,
                method=route.methods[0],
            )
        return self.routes[key]

    def finish(self) -> None:
        """Mark testing as finished."""
        self.end_time = time.time()

    def to_dict(self) -> dict[str, Any]:
        """Convert metrics to dictionary for serialization."""
        return {
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration_seconds": round(self.duration_seconds, 2),
            "total_routes": self.total_routes,
            "passed_routes": self.passed_routes,
            "failed_routes": self.failed_routes,
            "skipped_routes": self.skipped_routes,
            "pass_rate": round(self.pass_rate, 1),
            "total_requests": self.total_requests,
            "total_time_ms": round(self.total_time_ms, 2),
            "routes": {k: v.to_dict() for k, v in self.routes.items()},
        }


def aggregate_metrics(route_metrics: list[RouteMetrics]) -> RunMetrics:
    """Aggregate individual route metrics into test metrics.

    Args:
        route_metrics: List of RouteMetrics to aggregate.

    Returns:
        Aggregated RunMetrics.
    """
    metrics = RunMetrics()
    for rm in route_metrics:
        key = f"{rm.method}:{rm.route_path}"
        metrics.routes[key] = rm
    metrics.finish()
    return metrics
