"""Hypothesis strategy generation for route testing."""

from __future__ import annotations

from pytest_routes.generation.headers import (
    ACCEPT_STRATEGY,
    AUTHORIZATION_STRATEGY,
    CONTENT_TYPE_STRATEGY,
    USER_AGENT_STRATEGY,
    generate_headers,
    generate_optional_headers,
    register_header_strategy,
)
from pytest_routes.generation.strategies import register_strategy, strategy_for_type

__all__ = [
    # Type strategies
    "register_strategy",
    "strategy_for_type",
    # Header generation
    "generate_headers",
    "generate_optional_headers",
    "register_header_strategy",
    # Standard header strategies
    "CONTENT_TYPE_STRATEGY",
    "ACCEPT_STRATEGY",
    "AUTHORIZATION_STRATEGY",
    "USER_AGENT_STRATEGY",
]
