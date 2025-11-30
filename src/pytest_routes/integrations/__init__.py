"""Optional integrations for pytest-routes."""

from __future__ import annotations

from pytest_routes.integrations.schemathesis import (
    SchemathesisAdapter,
    SchemathesisValidator,
    schemathesis_available,
)

__all__ = [
    "SchemathesisAdapter",
    "SchemathesisValidator",
    "schemathesis_available",
]
