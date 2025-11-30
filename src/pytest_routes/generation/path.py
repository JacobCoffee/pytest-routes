"""Path parameter generation."""

from __future__ import annotations

from typing import Any

from hypothesis import strategies as st

from pytest_routes.generation.strategies import strategy_for_type


def generate_path_params(
    path_params: dict[str, type],
    path: str,  # noqa: ARG001 - kept for future context-aware generation
) -> st.SearchStrategy[dict[str, Any]]:
    """Generate valid path parameter combinations.

    Args:
        path_params: Mapping of parameter names to their types.
        path: The route path pattern (reserved for future context-aware generation).

    Returns:
        A Hypothesis strategy that generates dictionaries of path parameters.
    """
    if not path_params:
        return st.just({})

    strategies: dict[str, st.SearchStrategy[Any]] = {}

    for name, typ in path_params.items():
        if typ is str:
            # URL-safe strings for paths (no slashes, reasonable length)
            strategies[name] = st.text(
                alphabet=st.characters(whitelist_categories=("Ll", "Lu", "Nd"), whitelist_characters="-_"),
                min_size=1,
                max_size=50,
            )
        elif typ is int:
            # Positive integers common for IDs
            strategies[name] = st.integers(min_value=1, max_value=10000)
        elif typ is float:
            # Reasonable floats for paths
            strategies[name] = st.floats(min_value=0.0, max_value=10000.0, allow_nan=False, allow_infinity=False)
        else:
            strategies[name] = strategy_for_type(typ)

    return st.fixed_dictionaries(strategies)


def format_path(path: str, params: dict[str, Any]) -> str:
    """Format a path pattern with parameter values.

    Args:
        path: The path pattern with {param} placeholders.
        params: Dictionary of parameter values.

    Returns:
        The formatted path with parameters substituted.
    """
    result = path
    for name, value in params.items():
        # Handle both {param} and {param:type} patterns
        import re

        pattern = rf"\{{{name}(?::[^}}]+)?\}}"
        result = re.sub(pattern, str(value), result)
    return result
