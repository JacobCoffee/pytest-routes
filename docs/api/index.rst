.. _api-reference:

=============
API Reference
=============

This section provides complete API documentation for pytest-routes, organized by
functional area. All public APIs are fully documented with type hints, examples,
and cross-references to related functionality.

.. contents:: On This Page
   :local:
   :depth: 2
   :backlinks: none


Quick Reference
===============

The most commonly used classes and functions, organized by task:

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Task
     - API
   * - Configure testing
     - :class:`~pytest_routes.config.RouteTestConfig`
   * - Extract routes
     - :class:`~pytest_routes.discovery.base.RouteInfo`, :func:`~pytest_routes.discovery.get_extractor`
   * - Generate test data
     - :func:`~pytest_routes.generation.strategies.strategy_for_type`, :func:`~pytest_routes.generation.strategies.register_strategy`
   * - Execute tests
     - :class:`~pytest_routes.execution.runner.RouteTestRunner`, :class:`~pytest_routes.execution.client.RouteTestClient`
   * - Validate responses
     - :class:`~pytest_routes.validation.response.StatusCodeValidator`, :class:`~pytest_routes.validation.response.CompositeValidator`


Usage Examples
==============

Importing the Public API
------------------------

All public APIs are exported from the top-level ``pytest_routes`` package:

.. code-block:: python

   from pytest_routes import (
       # Configuration
       RouteTestConfig,
       load_config_from_pyproject,
       merge_configs,

       # Discovery
       RouteInfo,
       RouteExtractor,
       get_extractor,

       # Execution
       RouteTestClient,
       RouteTestRunner,
       RouteTestFailure,

       # Strategy generation
       strategy_for_type,
       register_strategy,
       unregister_strategy,
       register_strategies,
       get_registered_types,
       strategy_provider,
       temporary_strategy,

       # Header generation
       generate_headers,
       generate_optional_headers,
       register_header_strategy,

       # Validation
       ResponseValidator,
       ValidationResult,
       StatusCodeValidator,
       ContentTypeValidator,
       JsonSchemaValidator,
       OpenAPIResponseValidator,
       CompositeValidator,
   )


Basic Usage Pattern
-------------------

Here is a typical workflow for using the pytest-routes API programmatically:

.. code-block:: python

   from pytest_routes import (
       RouteTestConfig,
       get_extractor,
       RouteTestRunner,
   )

   # 1. Configure testing parameters
   config = RouteTestConfig(
       max_examples=50,
       fail_on_5xx=True,
       exclude_patterns=["/health", "/metrics"],
   )

   # 2. Get the appropriate extractor for your app
   extractor = get_extractor(app)

   # 3. Extract routes from your application
   routes = extractor.extract_routes(app)

   # 4. Create a test runner
   runner = RouteTestRunner(app, config)

   # 5. Generate and execute tests
   for route in routes:
       test_func = runner.create_test(route)
       test_func()  # Run the Hypothesis-powered test


Registering Custom Strategies
-----------------------------

When your API uses custom types, register Hypothesis strategies for them:

.. code-block:: python

   from hypothesis import strategies as st
   from pytest_routes import register_strategy, temporary_strategy

   # Register a permanent strategy
   register_strategy(
       MyCustomType,
       st.builds(MyCustomType, name=st.text(min_size=1, max_size=50))
   )

   # Or use a temporary strategy for a specific test
   with temporary_strategy(MyCustomType, st.just(MyCustomType("test"))):
       # Strategy only active within this block
       result = strategy_for_type(MyCustomType).example()


Custom Response Validation
--------------------------

Combine multiple validators for comprehensive response checking:

.. code-block:: python

   from pytest_routes import (
       CompositeValidator,
       StatusCodeValidator,
       ContentTypeValidator,
       JsonSchemaValidator,
   )

   # Build a composite validator
   validator = CompositeValidator([
       StatusCodeValidator(allowed_codes=[200, 201, 204]),
       ContentTypeValidator(expected_types=["application/json"]),
       JsonSchemaValidator(schema={
           "type": "object",
           "required": ["id", "name"],
       }),
   ])

   # Use in your tests
   result = validator.validate(response, route)
   if not result.valid:
       print(f"Validation failed: {result.errors}")


API Modules
===========

The API is organized into the following modules:

.. toctree::
   :maxdepth: 2
   :caption: API Documentation

   config
   discovery
   generation
   execution
   validation


Module Overview
---------------

Configuration (:mod:`pytest_routes.config`)
    Controls test execution parameters including the number of examples,
    timeout settings, route filtering patterns, and validation options.
    See :doc:`config`.

Discovery (:mod:`pytest_routes.discovery`)
    Extracts route information from ASGI applications. Includes framework-specific
    extractors for Litestar, Starlette, FastAPI, and OpenAPI schemas.
    See :doc:`discovery`.

Generation (:mod:`pytest_routes.generation`)
    Creates Hypothesis strategies for generating test data including path
    parameters, query parameters, request bodies, and headers.
    See :doc:`generation`.

Execution (:mod:`pytest_routes.execution`)
    Runs property-based tests against routes using the generated data and
    validates responses according to configuration.
    See :doc:`execution`.

Validation (:mod:`pytest_routes.validation`)
    Validates HTTP responses against expected schemas, status codes, and
    content types. Supports OpenAPI schema validation.
    See :doc:`validation`.


Plugin Integration
==================

The pytest plugin module provides integration with pytest's collection and
execution hooks. This module is typically not used directly but is loaded
automatically when pytest-routes is installed.

.. automodule:: pytest_routes.plugin
   :members:
   :undoc-members:
   :show-inheritance:
   :exclude-members: pytest_addoption, pytest_configure, pytest_collection_modifyitems


Indices and Tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
