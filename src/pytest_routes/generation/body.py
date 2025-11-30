"""Request body generation."""

from __future__ import annotations

import dataclasses
from typing import Any

from hypothesis import strategies as st


def generate_body(body_type: type | None) -> st.SearchStrategy[Any | None]:
    """Generate request body based on type annotation.

    Args:
        body_type: The expected request body type, or None if no body.

    Returns:
        A Hypothesis strategy that generates valid request bodies (as dicts).
    """
    if body_type is None:
        return st.none()

    # Check for Pydantic model - generate dict from model
    if _is_pydantic_model(body_type):
        return st.builds(body_type).map(_pydantic_to_dict)

    # Check for dataclass - generate dict from dataclass
    if hasattr(body_type, "__dataclass_fields__"):
        return st.builds(body_type).map(dataclasses.asdict)

    # Check for TypedDict
    if hasattr(body_type, "__annotations__") and hasattr(body_type, "__total__"):
        return _strategy_for_typed_dict(body_type)

    # Fallback to from_type
    try:
        return st.from_type(body_type)
    except Exception:
        return st.none()


def _pydantic_to_dict(model: Any) -> dict[str, Any]:
    """Convert Pydantic model to dict."""
    if hasattr(model, "model_dump"):
        return model.model_dump()  # Pydantic v2
    return model.dict()  # Pydantic v1


def _is_pydantic_model(typ: type) -> bool:
    """Check if type is a Pydantic model."""
    try:
        from pydantic import BaseModel

        return isinstance(typ, type) and issubclass(typ, BaseModel)
    except ImportError:
        return False


def _strategy_for_typed_dict(typed_dict: type) -> st.SearchStrategy[dict[str, Any]]:
    """Generate strategy for TypedDict."""
    from pytest_routes.generation.strategies import strategy_for_type

    annotations = getattr(typed_dict, "__annotations__", {})
    required_keys = getattr(typed_dict, "__required_keys__", set())

    strategies: dict[str, st.SearchStrategy[Any]] = {}
    optional_strategies: dict[str, st.SearchStrategy[Any]] = {}

    for key, typ in annotations.items():
        if key in required_keys:
            strategies[key] = strategy_for_type(typ)
        else:
            optional_strategies[key] = strategy_for_type(typ)

    base = st.fixed_dictionaries(strategies)

    if optional_strategies:
        optional = st.fixed_dictionaries(optional_strategies, optional=dict(optional_strategies))
        return st.builds(lambda a, b: {**a, **b}, base, optional)

    return base
