"""Authentication providers for pytest-routes."""

from __future__ import annotations

from pytest_routes.auth.providers import (
    APIKeyAuth,
    AuthProvider,
    BearerTokenAuth,
    CompositeAuth,
    NoAuth,
)

__all__ = [
    "APIKeyAuth",
    "AuthProvider",
    "BearerTokenAuth",
    "CompositeAuth",
    "NoAuth",
]
