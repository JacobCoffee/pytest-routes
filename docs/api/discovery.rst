.. _api-discovery:

===============
Route Discovery
===============

The discovery module extracts route information from ASGI applications.
It provides framework-specific extractors for Litestar, Starlette, FastAPI,
and can also extract routes from OpenAPI schemas.

.. currentmodule:: pytest_routes.discovery

.. contents:: On This Page
   :local:
   :depth: 2
   :backlinks: none


Overview
========

Route discovery is the first step in pytest-routes' testing pipeline:

1. **Detection** - Identify the framework (Litestar, FastAPI, Starlette)
2. **Extraction** - Pull route definitions from the application
3. **Normalization** - Convert to :class:`RouteInfo` objects with metadata

The :func:`get_extractor` factory function automatically selects the
appropriate extractor based on your application type.


Quick Start
===========

The simplest way to extract routes:

.. code-block:: python

   from pytest_routes import get_extractor, RouteInfo

   # Automatic framework detection
   extractor = get_extractor(app)

   # Extract all routes
   routes: list[RouteInfo] = extractor.extract_routes(app)

   for route in routes:
       print(f"{route.methods} {route.path}")
       print(f"  Path params: {route.path_params}")
       print(f"  Query params: {route.query_params}")


Architecture
============

.. code-block:: text

   +------------------+
   |  get_extractor() | -- Factory function
   +--------+---------+
            |
            v
   +------------------+     +-------------------+
   | RouteExtractor   |<----| LitestarExtractor |
   |   (Protocol)     |     +-------------------+
   +------------------+     +-------------------+
            ^         <-----| StarletteExtractor|
            |               +-------------------+
            |               +-------------------+
            +----------<----| OpenAPIExtractor  |
                            +-------------------+


API Reference
=============

Core Types
----------

RouteInfo
~~~~~~~~~

.. autoclass:: pytest_routes.discovery.base.RouteInfo
   :members:
   :undoc-members:
   :show-inheritance:

   The :class:`RouteInfo` dataclass is the normalized representation of a route,
   containing all information needed for test generation.

   .. rubric:: Attributes

   ``path``
       The URL path pattern (e.g., ``/users/{user_id}``)

   ``methods``
       List of HTTP methods (e.g., ``["GET", "POST"]``)

   ``name``
       Optional route name from the framework

   ``handler``
       Reference to the route handler function

   ``path_params``
       Dict mapping parameter names to their types

   ``query_params``
       Dict mapping query parameter names to their types

   ``body_type``
       The expected request body type (for POST/PUT/PATCH)

   ``tags``
       OpenAPI tags for categorization

   ``deprecated``
       Whether the route is marked deprecated

   ``description``
       Human-readable route description

   .. rubric:: Example

   .. code-block:: python

      route = RouteInfo(
          path="/users/{user_id}",
          methods=["GET"],
          name="get_user",
          path_params={"user_id": int},
          query_params={"include_posts": bool},
      )


RouteExtractor
~~~~~~~~~~~~~~

.. autoclass:: pytest_routes.discovery.base.RouteExtractor
   :members:
   :undoc-members:
   :show-inheritance:

   Abstract base class that all extractors must implement.


Factory Function
----------------

.. autofunction:: pytest_routes.discovery.get_extractor

   .. rubric:: Example

   .. code-block:: python

      from litestar import Litestar
      from pytest_routes import get_extractor

      app = Litestar(route_handlers=[...])
      extractor = get_extractor(app)  # Returns LitestarExtractor

      routes = extractor.extract_routes(app)


Framework Extractors
--------------------

Litestar Extractor
~~~~~~~~~~~~~~~~~~

.. automodule:: pytest_routes.discovery.litestar
   :members:
   :undoc-members:
   :show-inheritance:

The Litestar extractor provides first-class support for Litestar applications,
extracting full type information from route handlers including:

* Path parameters with type annotations
* Query parameters with defaults
* Request body models (Pydantic, dataclasses, msgspec)
* OpenAPI metadata (tags, deprecation, description)

.. code-block:: python

   from litestar import Litestar, get
   from pytest_routes.discovery.litestar import LitestarExtractor

   @get("/users/{user_id:int}")
   async def get_user(user_id: int) -> User:
       ...

   app = Litestar([get_user])
   extractor = LitestarExtractor()

   if extractor.supports(app):
       routes = extractor.extract_routes(app)


Starlette Extractor
~~~~~~~~~~~~~~~~~~~

.. automodule:: pytest_routes.discovery.starlette
   :members:
   :undoc-members:
   :show-inheritance:

The Starlette extractor works with both Starlette and FastAPI applications.
Since FastAPI is built on Starlette, this extractor handles both frameworks.

.. code-block:: python

   from fastapi import FastAPI
   from pytest_routes.discovery.starlette import StarletteExtractor

   app = FastAPI()

   @app.get("/users/{user_id}")
   async def get_user(user_id: int) -> dict:
       ...

   extractor = StarletteExtractor()
   routes = extractor.extract_routes(app)


OpenAPI Extractor
~~~~~~~~~~~~~~~~~

.. automodule:: pytest_routes.discovery.openapi
   :members:
   :undoc-members:
   :show-inheritance:

The OpenAPI extractor parses an OpenAPI specification (JSON or YAML) to
extract route information. This is useful for:

* Testing against an API specification before implementation
* Testing third-party APIs
* Framework-agnostic route extraction

.. code-block:: python

   from pytest_routes.discovery.openapi import OpenAPIExtractor

   openapi_schema = {
       "openapi": "3.0.0",
       "paths": {
           "/users/{user_id}": {
               "get": {
                   "parameters": [
                       {"name": "user_id", "in": "path", "schema": {"type": "integer"}}
                   ]
               }
           }
       }
   }

   extractor = OpenAPIExtractor(openapi_schema)
   routes = extractor.extract_routes(None)  # Schema-based, no app needed


Custom Extractors
=================

Implement custom extractors for unsupported frameworks:

.. code-block:: python

   from pytest_routes.discovery.base import RouteExtractor, RouteInfo
   from typing import Any

   class MyFrameworkExtractor(RouteExtractor):
       """Extractor for MyFramework applications."""

       def supports(self, app: Any) -> bool:
           """Check if this is a MyFramework app."""
           return hasattr(app, "my_framework_marker")

       def extract_routes(self, app: Any) -> list[RouteInfo]:
           """Extract routes from MyFramework app."""
           routes = []
           for route_def in app.get_routes():
               routes.append(RouteInfo(
                   path=route_def.path,
                   methods=route_def.methods,
                   path_params=self._extract_path_params(route_def),
                   query_params=self._extract_query_params(route_def),
                   body_type=route_def.body_model,
               ))
           return routes


See Also
========

* :doc:`generation` - How extracted routes are used for test generation
* :doc:`execution` - Running tests against discovered routes
* :ref:`api-reference` - Complete API overview
