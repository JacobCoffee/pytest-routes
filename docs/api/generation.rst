.. _api-generation:

===================
Strategy Generation
===================

The generation module creates Hypothesis strategies for generating test data.
It provides type-to-strategy mapping, path parameter generation, request body
generation, and header generation.

.. currentmodule:: pytest_routes.generation

.. contents:: On This Page
   :local:
   :depth: 2
   :backlinks: none


Overview
========

pytest-routes uses `Hypothesis <https://hypothesis.readthedocs.io/>`_ for
property-based testing. The generation module bridges your application's
type system with Hypothesis strategies:

1. **Type Strategies** - Map Python types to Hypothesis strategies
2. **Path Parameters** - Generate valid path parameter values
3. **Request Bodies** - Generate request payloads from models
4. **Headers** - Generate HTTP headers for authentication, content-type, etc.


Quick Start
===========

Get a strategy for any type:

.. code-block:: python

   from pytest_routes import strategy_for_type
   from hypothesis import given

   # Built-in types work automatically
   int_strategy = strategy_for_type(int)
   str_strategy = strategy_for_type(str)

   # Use in Hypothesis tests
   @given(value=strategy_for_type(int))
   def test_with_integers(value: int):
       assert isinstance(value, int)


Register custom types:

.. code-block:: python

   from hypothesis import strategies as st
   from pytest_routes import register_strategy

   class UserId:
       def __init__(self, value: int):
           self.value = value

   register_strategy(
       UserId,
       st.builds(UserId, value=st.integers(min_value=1, max_value=1000000))
   )


Built-in Type Strategies
========================

The following types have pre-registered strategies:

.. list-table::
   :header-rows: 1
   :widths: 20 80

   * - Type
     - Strategy
   * - ``str``
     - ``st.text(min_size=1, max_size=100)``
   * - ``int``
     - ``st.integers(min_value=-1000, max_value=1000)``
   * - ``float``
     - ``st.floats(allow_nan=False, allow_infinity=False)``
   * - ``bool``
     - ``st.booleans()``
   * - ``uuid.UUID``
     - ``st.uuids()``
   * - ``datetime``
     - ``st.datetimes()``
   * - ``date``
     - ``st.dates()``
   * - ``bytes``
     - ``st.binary(min_size=1, max_size=100)``

Generic types are also supported:

.. code-block:: python

   from pytest_routes import strategy_for_type

   # Optional[str] -> st.none() | st.text()
   strategy_for_type(Optional[str])

   # list[int] -> st.lists(st.integers())
   strategy_for_type(list[int])

   # dict[str, int] -> st.dictionaries(st.text(), st.integers())
   strategy_for_type(dict[str, int])


API Reference
=============

Type Strategies
---------------

Strategy Registration Functions
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. autofunction:: pytest_routes.generation.strategies.register_strategy

   Register a permanent strategy for a type.

   .. rubric:: Example

   .. code-block:: python

      from hypothesis import strategies as st
      from pytest_routes import register_strategy

      # Register for a custom type
      register_strategy(
          MyType,
          st.builds(MyType, name=st.text(min_size=1))
      )

      # Override an existing strategy
      register_strategy(
          str,
          st.text(min_size=5, max_size=20),
          override=True
      )


.. autofunction:: pytest_routes.generation.strategies.unregister_strategy

.. autofunction:: pytest_routes.generation.strategies.register_strategies

   Register multiple strategies at once.

   .. rubric:: Example

   .. code-block:: python

      from hypothesis import strategies as st
      from pytest_routes import register_strategies

      register_strategies({
          UserId: st.builds(UserId, st.integers(min_value=1)),
          Email: st.emails(),
          PhoneNumber: st.from_regex(r"\+\d{10,15}"),
      })


.. autofunction:: pytest_routes.generation.strategies.get_registered_types


Strategy Helpers
~~~~~~~~~~~~~~~~

.. autofunction:: pytest_routes.generation.strategies.strategy_for_type

   The main function for getting a strategy for any type.

   .. rubric:: Type Resolution

   The function resolves types in this order:

   1. Direct lookup in the registry
   2. ``Optional[X]`` unwrapping
   3. ``list[X]`` and ``dict[K, V]`` handling
   4. Dataclass/Pydantic model detection
   5. Hypothesis ``from_type()`` fallback
   6. Text fallback for unknown types


.. autofunction:: pytest_routes.generation.strategies.strategy_provider

   Decorator for registering strategy provider functions.

   .. rubric:: Example

   .. code-block:: python

      from pytest_routes import strategy_provider
      from hypothesis import strategies as st

      @strategy_provider(MyComplexType)
      def my_complex_strategy():
          return st.builds(
              MyComplexType,
              field1=st.text(),
              field2=st.integers(),
          )


.. autofunction:: pytest_routes.generation.strategies.temporary_strategy

   Context manager for temporary strategy registration.

   .. rubric:: Example

   .. code-block:: python

      from pytest_routes import temporary_strategy, strategy_for_type
      from hypothesis import strategies as st

      # Normal str strategy
      normal = strategy_for_type(str).example()

      with temporary_strategy(str, st.just("fixed")):
          # Inside context, str always generates "fixed"
          assert strategy_for_type(str).example() == "fixed"

      # Original strategy restored


Path Parameters
---------------

.. automodule:: pytest_routes.generation.path
   :members:
   :undoc-members:
   :show-inheritance:

Path parameter generation handles URL path variables:

.. code-block:: python

   from pytest_routes.generation.path import generate_path_params, format_path

   # Generate values for path parameters
   path_params = {"user_id": int, "post_id": int}
   strategy = generate_path_params(path_params, "/users/{user_id}/posts/{post_id}")

   # Format a path with generated values
   values = {"user_id": 42, "post_id": 123}
   url = format_path("/users/{user_id}/posts/{post_id}", values)
   # Result: "/users/42/posts/123"


Request Bodies
--------------

.. automodule:: pytest_routes.generation.body
   :members:
   :undoc-members:
   :show-inheritance:

Request body generation creates payloads for POST/PUT/PATCH requests:

.. code-block:: python

   from pytest_routes.generation.body import generate_body
   from pydantic import BaseModel

   class CreateUserRequest(BaseModel):
       name: str
       email: str
       age: int

   # Generate valid request bodies
   body_strategy = generate_body(CreateUserRequest)
   example = body_strategy.example()
   # Result: {"name": "...", "email": "...", "age": ...}


Header Generation
-----------------

.. automodule:: pytest_routes.generation.headers
   :members:
   :undoc-members:
   :show-inheritance:

Header generation provides strategies for HTTP headers:

.. code-block:: python

   from pytest_routes import (
       generate_headers,
       generate_optional_headers,
       register_header_strategy,
   )

   # Generate required headers
   headers = generate_headers(["Authorization", "Content-Type"])

   # Generate optional headers (may or may not be present)
   optional = generate_optional_headers(["X-Request-ID", "X-Trace-ID"])

   # Register a custom header strategy
   from hypothesis import strategies as st
   register_header_strategy(
       "Authorization",
       st.just("Bearer test-token-12345")
   )


Advanced Usage
==============

Pydantic Model Strategies
-------------------------

pytest-routes automatically generates strategies for Pydantic models:

.. code-block:: python

   from pydantic import BaseModel, Field
   from pytest_routes import strategy_for_type

   class User(BaseModel):
       id: int = Field(ge=1)
       name: str = Field(min_length=1, max_length=100)
       email: str

   # Automatically creates a valid User strategy
   user_strategy = strategy_for_type(User)
   user = user_strategy.example()


Dataclass Strategies
--------------------

Dataclasses are also supported:

.. code-block:: python

   from dataclasses import dataclass
   from pytest_routes import strategy_for_type

   @dataclass
   class Point:
       x: float
       y: float

   point_strategy = strategy_for_type(Point)
   point = point_strategy.example()


Constrained Strategies
----------------------

For more control, register constrained strategies:

.. code-block:: python

   from hypothesis import strategies as st
   from pytest_routes import register_strategy

   # Positive integers only
   register_strategy(
       int,
       st.integers(min_value=0, max_value=10000),
       override=True
   )

   # Email-like strings
   class Email(str):
       pass

   register_strategy(
       Email,
       st.emails()
   )


See Also
========

* :doc:`discovery` - How routes and types are extracted
* :doc:`execution` - How generated data is used in tests
* `Hypothesis documentation <https://hypothesis.readthedocs.io/>`_ - Full Hypothesis docs
