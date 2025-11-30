"""Example demonstrating custom strategy registration API."""

from __future__ import annotations

from dataclasses import dataclass

from hypothesis import strategies as st

from pytest_routes import (
    get_registered_types,
    register_strategies,
    register_strategy,
    strategy_for_type,
    strategy_provider,
    temporary_strategy,
    unregister_strategy,
)


# Example 1: Basic registration
@dataclass
class User:
    """User model."""

    username: str
    email: str
    age: int


def example_basic_registration() -> None:
    """Demonstrate basic strategy registration."""
    print("\n=== Example 1: Basic Registration ===")

    # Register a strategy for the User type
    register_strategy(
        User,
        st.builds(
            User,
            username=st.text(min_size=3, max_size=20),
            email=st.emails(),
            age=st.integers(min_value=18, max_value=100),
        ),
    )

    # Get and use the strategy
    strategy = strategy_for_type(User)
    example_user = strategy.example()
    print(f"Generated user: {example_user}")

    # Clean up
    unregister_strategy(User)


# Example 2: Override protection
def example_override_protection() -> None:
    """Demonstrate override protection."""
    print("\n=== Example 2: Override Protection ===")

    @dataclass
    class Product:
        """Product model."""

        name: str
        price: float

    # Register initial strategy
    register_strategy(Product, st.builds(Product, name=st.just("Original")))

    # This would raise ValueError
    try:
        register_strategy(Product, st.builds(Product, name=st.just("Override")))
    except ValueError as e:
        print(f"Error (expected): {e}")

    # This works with override=True
    register_strategy(
        Product, st.builds(Product, name=st.just("Override")), override=True
    )
    print("Successfully overrode strategy")

    # Clean up
    unregister_strategy(Product)


# Example 3: Decorator-based registration
@dataclass
class Order:
    """Order model."""

    order_id: str
    quantity: int


@strategy_provider(Order)
def order_strategy():
    """Strategy for Order type."""
    return st.builds(
        Order,
        order_id=st.uuids().map(str),
        quantity=st.integers(min_value=1, max_value=100),
    )


def example_decorator_registration() -> None:
    """Demonstrate decorator-based registration."""
    print("\n=== Example 3: Decorator Registration ===")

    strategy = strategy_for_type(Order)
    example_order = strategy.example()
    print(f"Generated order: {example_order}")

    # Clean up
    unregister_strategy(Order)


# Example 4: Temporary strategies
def example_temporary_strategies() -> None:
    """Demonstrate temporary strategy context manager."""
    print("\n=== Example 4: Temporary Strategies ===")

    # Get original string strategy behavior
    original_strategy = strategy_for_type(str)
    print(f"Original string: {original_strategy.example()}")

    # Temporarily override string strategy
    with temporary_strategy(str, st.just("TEMPORARY")):
        temp_strategy = strategy_for_type(str)
        print(f"Temporary string: {temp_strategy.example()}")

    # Original strategy is restored
    restored_strategy = strategy_for_type(str)
    print(f"Restored string: {restored_strategy.example()}")


# Example 5: Batch registration
def example_batch_registration() -> None:
    """Demonstrate batch strategy registration."""
    print("\n=== Example 5: Batch Registration ===")

    @dataclass
    class Address:
        """Address model."""

        street: str
        city: str
        zip_code: str

    @dataclass
    class Company:
        """Company model."""

        name: str
        employees: int

    @dataclass
    class Invoice:
        """Invoice model."""

        invoice_id: str
        amount: float

    # Register multiple strategies at once
    register_strategies(
        {
            Address: st.builds(
                Address,
                street=st.text(min_size=5),
                city=st.text(min_size=3),
                zip_code=st.from_regex(r"\d{5}"),
            ),
            Company: st.builds(
                Company,
                name=st.text(min_size=3, max_size=50),
                employees=st.integers(min_value=1, max_value=10000),
            ),
            Invoice: st.builds(
                Invoice,
                invoice_id=st.uuids().map(str),
                amount=st.floats(min_value=0, max_value=100000),
            ),
        }
    )

    print("Registered strategies for Address, Company, and Invoice")

    # Generate examples
    print(f"Address: {strategy_for_type(Address).example()}")
    print(f"Company: {strategy_for_type(Company).example()}")
    print(f"Invoice: {strategy_for_type(Invoice).example()}")

    # Clean up
    unregister_strategy(Address)
    unregister_strategy(Company)
    unregister_strategy(Invoice)


# Example 6: Inspecting registered types
def example_inspect_registered_types() -> None:
    """Demonstrate inspecting registered types."""
    print("\n=== Example 6: Inspect Registered Types ===")

    @dataclass
    class CustomType1:
        """Custom type 1."""

        value: int

    @dataclass
    class CustomType2:
        """Custom type 2."""

        value: str

    # Register some custom types
    register_strategies(
        {
            CustomType1: st.builds(CustomType1),
            CustomType2: st.builds(CustomType2),
        }
    )

    # Get all registered types
    registered = get_registered_types()
    print(f"Total registered types: {len(registered)}")

    # Check if custom types are registered
    print(f"CustomType1 registered: {CustomType1 in registered}")
    print(f"CustomType2 registered: {CustomType2 in registered}")

    # Built-in types are also registered
    print(f"str registered: {str in registered}")
    print(f"int registered: {int in registered}")

    # Clean up
    unregister_strategy(CustomType1)
    unregister_strategy(CustomType2)


def main() -> None:
    """Run all examples."""
    print("Custom Strategy Registration API Examples")
    print("=" * 50)

    example_basic_registration()
    example_override_protection()
    example_decorator_registration()
    example_temporary_strategies()
    example_batch_registration()
    example_inspect_registered_types()

    print("\n" + "=" * 50)
    print("All examples completed!")


if __name__ == "__main__":
    main()
