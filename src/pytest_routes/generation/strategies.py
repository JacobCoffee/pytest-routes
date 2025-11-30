"""Type-to-strategy mapping for Hypothesis."""

from __future__ import annotations

import uuid
from contextlib import contextmanager
from datetime import date, datetime
from typing import TYPE_CHECKING, Any, Union, get_args, get_origin

from hypothesis import strategies as st

if TYPE_CHECKING:
    from collections.abc import Callable, Generator

    from hypothesis.strategies import SearchStrategy

# Global type to strategy registry
_TYPE_STRATEGIES: dict[type, Any] = {
    str: st.text(min_size=1, max_size=100),
    int: st.integers(min_value=-1000, max_value=1000),
    float: st.floats(allow_nan=False, allow_infinity=False),
    bool: st.booleans(),
    uuid.UUID: st.uuids(),
    datetime: st.datetimes(),
    date: st.dates(),
    bytes: st.binary(min_size=1, max_size=100),
}


def register_strategy(
    typ: type,
    strategy: SearchStrategy[Any],
    *,
    override: bool = False,
) -> None:
    """Register a custom strategy for a type.

    Args:
        typ: The Python type.
        strategy: The Hypothesis strategy to use for this type.
        override: If True, allow overriding an existing strategy. If False (default),
            raise ValueError if a strategy is already registered for this type.

    Raises:
        ValueError: If a strategy is already registered and override is False.

    Examples:
        >>> from hypothesis import strategies as st
        >>> register_strategy(MyType, st.builds(MyType))
        >>> register_strategy(MyType, st.builds(MyType, arg="new"), override=True)
    """
    if typ in _TYPE_STRATEGIES and not override:
        msg = f"Strategy for {typ} already registered. Use override=True to replace."
        raise ValueError(msg)
    _TYPE_STRATEGIES[typ] = strategy


def unregister_strategy(typ: type) -> bool:
    """Unregister a custom strategy.

    Args:
        typ: The Python type to unregister.

    Returns:
        True if the type was previously registered, False otherwise.

    Examples:
        >>> from hypothesis import strategies as st
        >>> register_strategy(MyType, st.builds(MyType))
        >>> unregister_strategy(MyType)
        True
        >>> unregister_strategy(MyType)
        False
    """
    return _TYPE_STRATEGIES.pop(typ, None) is not None


def get_registered_types() -> list[type]:
    """Get list of types with registered strategies.

    Returns:
        List of types that have custom strategies registered.

    Examples:
        >>> types = get_registered_types()
        >>> str in types
        True
    """
    return list(_TYPE_STRATEGIES.keys())


def strategy_provider(
    typ: type,
) -> Callable[[Callable[[], SearchStrategy[Any]]], Callable[[], SearchStrategy[Any]]]:
    """Decorator to register a strategy provider function.

    Args:
        typ: The Python type to register a strategy for.

    Returns:
        Decorator function that registers the strategy when applied.

    Examples:
        >>> from hypothesis import strategies as st
        >>> @strategy_provider(MyType)
        ... def my_custom_strategy():
        ...     return st.builds(MyType, field=st.text())
    """

    def decorator(
        func: Callable[[], SearchStrategy[Any]],
    ) -> Callable[[], SearchStrategy[Any]]:
        register_strategy(typ, func())
        return func

    return decorator


@contextmanager
def temporary_strategy(
    typ: type,
    strategy: SearchStrategy[Any],
) -> Generator[None, None, None]:
    """Temporarily register a strategy for the duration of a context.

    The original strategy (if any) is restored when the context exits.

    Args:
        typ: The Python type.
        strategy: The temporary Hypothesis strategy to use.

    Yields:
        None

    Examples:
        >>> from hypothesis import strategies as st
        >>> with temporary_strategy(str, st.just("test")):
        ...     # str strategy is now st.just("test")
        ...     result = strategy_for_type(str).example()
        >>> # Original str strategy is restored
    """
    old_strategy = _TYPE_STRATEGIES.get(typ)
    _TYPE_STRATEGIES[typ] = strategy
    try:
        yield
    finally:
        if old_strategy is not None:
            _TYPE_STRATEGIES[typ] = old_strategy
        else:
            _TYPE_STRATEGIES.pop(typ, None)


def register_strategies(
    mapping: dict[type, SearchStrategy[Any]],
    *,
    override: bool = False,
) -> None:
    """Register multiple strategies at once.

    Args:
        mapping: Dictionary mapping types to their strategies.
        override: If True, allow overriding existing strategies. If False (default),
            raise ValueError if any type already has a registered strategy.

    Raises:
        ValueError: If any type is already registered and override is False.

    Examples:
        >>> from hypothesis import strategies as st
        >>> register_strategies(
        ...     {
        ...         MyType1: st.builds(MyType1),
        ...         MyType2: st.builds(MyType2),
        ...     }
        ... )
    """
    for typ, strategy in mapping.items():
        register_strategy(typ, strategy, override=override)


def strategy_for_type(typ: type) -> SearchStrategy[Any]:  # noqa: PLR0911
    """Get a Hypothesis strategy for a Python type.

    Args:
        typ: The Python type to generate values for.

    Returns:
        A Hypothesis SearchStrategy for the type.
    """
    # Direct lookup
    if typ in _TYPE_STRATEGIES:
        return _TYPE_STRATEGIES[typ]

    # Handle Optional[X] (Union[X, None])
    origin = get_origin(typ)
    if origin is Union:
        args = get_args(typ)
        if type(None) in args:
            non_none = [a for a in args if a is not type(None)]
            if len(non_none) == 1:
                return st.none() | strategy_for_type(non_none[0])

    # Handle List[X]
    if origin is list:
        item_type = get_args(typ)[0] if get_args(typ) else Any
        if item_type is Any:
            return st.lists(st.text(), max_size=10)
        return st.lists(strategy_for_type(item_type), max_size=10)

    # Handle Dict[K, V]
    if origin is dict:
        args = get_args(typ)
        key_type = args[0] if args else str
        val_type = args[1] if len(args) > 1 else Any
        return st.dictionaries(
            strategy_for_type(key_type) if key_type is not Any else st.text(),
            strategy_for_type(val_type) if val_type is not Any else st.text(),
            max_size=10,
        )

    # Fallback to builds for dataclasses/pydantic models
    if hasattr(typ, "__dataclass_fields__") or hasattr(typ, "model_fields"):
        return st.builds(typ)

    # Try from_type as last resort
    try:
        return st.from_type(typ)
    except Exception:
        # Ultimate fallback to text
        return st.text(min_size=1, max_size=50)
