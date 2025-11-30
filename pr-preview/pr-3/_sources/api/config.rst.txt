.. _api-config:

=============
Configuration
=============

The configuration module provides the :class:`RouteTestConfig` dataclass and
related utilities for controlling pytest-routes behavior.

.. currentmodule:: pytest_routes.config


Overview
========

Configuration in pytest-routes follows a layered approach:

1. **Built-in defaults** - Sensible defaults for common use cases
2. **pyproject.toml** - Project-level configuration in ``[tool.pytest-routes]``
3. **CLI options** - Command-line overrides for specific test runs

The :func:`merge_configs` function handles combining these layers with
appropriate precedence.


Quick Start
===========

Basic configuration for most projects:

.. code-block:: python

   from pytest_routes import RouteTestConfig

   # Use defaults for most options
   config = RouteTestConfig(
       max_examples=50,           # Fewer examples for faster tests
       exclude_patterns=[         # Skip health and docs endpoints
           "/health",
           "/metrics",
           "/docs",
       ],
   )

Loading from pyproject.toml:

.. code-block:: python

   from pytest_routes import load_config_from_pyproject
   from pathlib import Path

   # Load from default location (./pyproject.toml)
   config = load_config_from_pyproject()

   # Or from a specific path
   config = load_config_from_pyproject(Path("/path/to/pyproject.toml"))


Configuration Options
=====================

The following table summarizes all available configuration options:

.. list-table::
   :header-rows: 1
   :widths: 25 15 60

   * - Option
     - Default
     - Description
   * - ``max_examples``
     - 100
     - Maximum Hypothesis examples per route
   * - ``timeout_per_route``
     - 30.0
     - Timeout in seconds for each route test
   * - ``include_patterns``
     - []
     - Route patterns to include (empty = all)
   * - ``exclude_patterns``
     - ["/health", ...]
     - Route patterns to exclude
   * - ``methods``
     - ["GET", "POST", ...]
     - HTTP methods to test
   * - ``strategy``
     - "hybrid"
     - Data generation strategy
   * - ``seed``
     - None
     - Random seed for reproducibility
   * - ``allowed_status_codes``
     - [200-499]
     - Status codes that pass tests
   * - ``fail_on_5xx``
     - True
     - Fail tests on server errors
   * - ``validate_responses``
     - False
     - Enable response validation
   * - ``framework``
     - "auto"
     - Framework hint for route extraction


pyproject.toml Example
======================

Configure pytest-routes in your project's ``pyproject.toml``:

.. code-block:: toml

   [tool.pytest-routes]
   max_examples = 50
   timeout = 30.0
   include = ["/api/*"]
   exclude = ["/health", "/metrics", "/docs", "/openapi*"]
   methods = ["GET", "POST", "PUT", "DELETE"]
   strategy = "hybrid"
   fail_on_5xx = true
   allowed_status_codes = [200, 201, 204, 400, 401, 403, 404, 422]
   framework = "litestar"
   verbose = false


API Reference
=============

RouteTestConfig
---------------

.. autoclass:: pytest_routes.config.RouteTestConfig
   :members:
   :undoc-members:
   :show-inheritance:
   :member-order: bysource

   .. rubric:: Example

   .. code-block:: python

      from pytest_routes import RouteTestConfig

      config = RouteTestConfig(
          max_examples=100,
          timeout_per_route=30.0,
          exclude_patterns=["/health", "/metrics"],
          fail_on_5xx=True,
          allowed_status_codes=list(range(200, 500)),
      )


Configuration Functions
-----------------------

.. autofunction:: pytest_routes.config.load_config_from_pyproject

.. autofunction:: pytest_routes.config.merge_configs


See Also
========

* :doc:`/usage/index` - Usage guide with configuration examples
* :doc:`execution` - How configuration affects test execution
* :doc:`validation` - Response validation configuration
