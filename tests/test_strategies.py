"""Tests for Hypothesis strategy generation."""

from __future__ import annotations

import uuid
from datetime import date, datetime

import pytest
from hypothesis import given
from hypothesis import strategies as st

from pytest_routes.generation.strategies import (
    get_registered_types,
    register_strategies,
    register_strategy,
    strategy_for_type,
    strategy_provider,
    temporary_strategy,
    unregister_strategy,
)


class TestStrategyForType:
    """Tests for type-to-strategy mapping."""

    def test_string_strategy(self):
        """Test string strategy generation."""
        strategy = strategy_for_type(str)

        @given(value=strategy)
        def check(value):
            assert isinstance(value, str)

        check()

    def test_int_strategy(self):
        """Test integer strategy generation."""
        strategy = strategy_for_type(int)

        @given(value=strategy)
        def check(value):
            assert isinstance(value, int)

        check()

    def test_float_strategy(self):
        """Test float strategy generation."""
        strategy = strategy_for_type(float)

        @given(value=strategy)
        def check(value):
            assert isinstance(value, float)

        check()

    def test_bool_strategy(self):
        """Test boolean strategy generation."""
        strategy = strategy_for_type(bool)

        @given(value=strategy)
        def check(value):
            assert isinstance(value, bool)

        check()

    def test_uuid_strategy(self):
        """Test UUID strategy generation."""
        strategy = strategy_for_type(uuid.UUID)

        @given(value=strategy)
        def check(value):
            assert isinstance(value, uuid.UUID)

        check()

    def test_datetime_strategy(self):
        """Test datetime strategy generation."""
        strategy = strategy_for_type(datetime)

        @given(value=strategy)
        def check(value):
            assert isinstance(value, datetime)

        check()

    def test_date_strategy(self):
        """Test date strategy generation."""
        strategy = strategy_for_type(date)

        @given(value=strategy)
        def check(value):
            assert isinstance(value, date)

        check()

    def test_optional_strategy(self):
        """Test Optional[T] strategy generation."""
        strategy = strategy_for_type(str | None)

        @given(value=strategy)
        def check(value):
            assert value is None or isinstance(value, str)

        check()

    def test_list_strategy(self):
        """Test List[T] strategy generation."""
        strategy = strategy_for_type(list[int])

        @given(value=strategy)
        def check(value):
            assert isinstance(value, list)
            assert all(isinstance(x, int) for x in value)

        check()

    def test_dict_strategy(self):
        """Test Dict[K, V] strategy generation."""
        strategy = strategy_for_type(dict[str, int])

        @given(value=strategy)
        def check(value):
            assert isinstance(value, dict)
            assert all(isinstance(k, str) for k in value.keys())
            assert all(isinstance(v, int) for v in value.values())

        check()


class TestRegisterStrategy:
    """Tests for custom strategy registration."""

    def test_register_custom_strategy(self):
        """Test registering a custom strategy."""

        class MyType:
            def __init__(self, value: int):
                self.value = value

        register_strategy(MyType, st.builds(MyType, st.integers()))

        strategy = strategy_for_type(MyType)

        @given(value=strategy)
        def check(value):
            assert isinstance(value, MyType)
            assert isinstance(value.value, int)

        check()

        # Clean up
        unregister_strategy(MyType)

    def test_register_strategy_raises_on_duplicate(self):
        """Test that registering duplicate strategy raises ValueError."""

        class MyType:
            pass

        register_strategy(MyType, st.builds(MyType))

        with pytest.raises(ValueError, match="already registered"):
            register_strategy(MyType, st.builds(MyType))

        # Clean up
        unregister_strategy(MyType)

    def test_register_strategy_override(self):
        """Test overriding an existing strategy."""

        class MyType:
            def __init__(self, value: int = 0):
                self.value = value

        # Register initial strategy
        register_strategy(MyType, st.builds(MyType, st.just(1)))

        # Override with new strategy
        register_strategy(MyType, st.builds(MyType, st.just(2)), override=True)

        strategy = strategy_for_type(MyType)

        @given(value=strategy)
        def check(value):
            assert isinstance(value, MyType)
            assert value.value == 2  # Should use the overridden strategy

        check()

        # Clean up
        unregister_strategy(MyType)


class TestUnregisterStrategy:
    """Tests for strategy unregistration."""

    def test_unregister_strategy(self):
        """Test unregistering a strategy."""

        class MyType:
            pass

        # Register and then unregister
        register_strategy(MyType, st.builds(MyType))
        result = unregister_strategy(MyType)

        assert result is True
        assert MyType not in get_registered_types()

    def test_unregister_nonexistent_strategy(self):
        """Test unregistering a strategy that doesn't exist."""

        class MyType:
            pass

        result = unregister_strategy(MyType)
        assert result is False


class TestGetRegisteredTypes:
    """Tests for getting registered types."""

    def test_get_registered_types(self):
        """Test getting list of registered types."""
        types = get_registered_types()

        # Should include built-in types
        assert str in types
        assert int in types
        assert float in types
        assert bool in types
        assert uuid.UUID in types
        assert datetime in types
        assert date in types

    def test_get_registered_types_includes_custom(self):
        """Test that custom types appear in registered types."""

        class MyType:
            pass

        register_strategy(MyType, st.builds(MyType))

        types = get_registered_types()
        assert MyType in types

        # Clean up
        unregister_strategy(MyType)


class TestStrategyProvider:
    """Tests for decorator-based strategy registration."""

    def test_strategy_provider_decorator(self):
        """Test using decorator to register strategy."""

        class MyType:
            def __init__(self, value: str):
                self.value = value

        @strategy_provider(MyType)
        def my_custom_strategy():
            return st.builds(MyType, st.just("test"))

        strategy = strategy_for_type(MyType)

        @given(value=strategy)
        def check(value):
            assert isinstance(value, MyType)
            assert value.value == "test"

        check()

        # Clean up
        unregister_strategy(MyType)

    def test_strategy_provider_returns_function(self):
        """Test that decorator returns the original function."""

        class MyType:
            pass

        @strategy_provider(MyType)
        def my_strategy():
            return st.builds(MyType)

        # Should return the original function
        assert callable(my_strategy)
        assert my_strategy.__name__ == "my_strategy"

        # Clean up
        unregister_strategy(MyType)


class TestTemporaryStrategy:
    """Tests for temporary strategy context manager."""

    def test_temporary_strategy_basic(self):
        """Test using temporary strategy in context."""
        original_strategy = strategy_for_type(str)

        with temporary_strategy(str, st.just("temporary")):
            temp_strategy = strategy_for_type(str)

            @given(value=temp_strategy)
            def check_temp(value):
                assert value == "temporary"

            check_temp()

        # Should restore original strategy
        restored_strategy = strategy_for_type(str)
        assert restored_strategy is original_strategy

    def test_temporary_strategy_for_new_type(self):
        """Test temporary strategy for a type that wasn't registered."""

        class MyType:
            def __init__(self, value: int):
                self.value = value

        assert MyType not in get_registered_types()

        with temporary_strategy(MyType, st.builds(MyType, st.just(42))):
            assert MyType in get_registered_types()
            strategy = strategy_for_type(MyType)

            @given(value=strategy)
            def check(value):
                assert isinstance(value, MyType)
                assert value.value == 42

            check()

        # Should be removed after context
        assert MyType not in get_registered_types()

    def test_temporary_strategy_exception_handling(self):
        """Test that temporary strategy is cleaned up even on exception."""

        class MyType:
            pass

        original_types = get_registered_types()

        with pytest.raises(RuntimeError):
            with temporary_strategy(MyType, st.builds(MyType)):
                assert MyType in get_registered_types()
                raise RuntimeError("Test exception")

        # Should still be cleaned up
        assert get_registered_types() == original_types


class TestRegisterStrategies:
    """Tests for batch strategy registration."""

    def test_register_strategies_batch(self):
        """Test registering multiple strategies at once."""

        class Type1:
            pass

        class Type2:
            pass

        class Type3:
            pass

        register_strategies(
            {
                Type1: st.builds(Type1),
                Type2: st.builds(Type2),
                Type3: st.builds(Type3),
            }
        )

        types = get_registered_types()
        assert Type1 in types
        assert Type2 in types
        assert Type3 in types

        # Clean up
        unregister_strategy(Type1)
        unregister_strategy(Type2)
        unregister_strategy(Type3)

    def test_register_strategies_raises_on_duplicate(self):
        """Test that batch registration raises on duplicate."""

        class MyType:
            pass

        register_strategy(MyType, st.builds(MyType))

        with pytest.raises(ValueError, match="already registered"):
            register_strategies({MyType: st.builds(MyType)})

        # Clean up
        unregister_strategy(MyType)

    def test_register_strategies_override(self):
        """Test batch registration with override."""

        class Type1:
            def __init__(self, value: int = 0):
                self.value = value

        class Type2:
            def __init__(self, value: int = 0):
                self.value = value

        # Register initial strategies
        register_strategies(
            {
                Type1: st.builds(Type1, st.just(1)),
                Type2: st.builds(Type2, st.just(2)),
            }
        )

        # Override with new strategies
        register_strategies(
            {
                Type1: st.builds(Type1, st.just(10)),
                Type2: st.builds(Type2, st.just(20)),
            },
            override=True,
        )

        strategy1 = strategy_for_type(Type1)
        strategy2 = strategy_for_type(Type2)

        @given(value1=strategy1, value2=strategy2)
        def check(value1, value2):
            assert value1.value == 10
            assert value2.value == 20

        check()

        # Clean up
        unregister_strategy(Type1)
        unregister_strategy(Type2)
