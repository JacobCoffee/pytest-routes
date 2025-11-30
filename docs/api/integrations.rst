.. _api-integrations:

============
Integrations
============

The integrations module provides adapters for external testing tools like Schemathesis.


Schemathesis Integration
========================

The Schemathesis integration provides OpenAPI contract testing capabilities.

.. autofunction:: pytest_routes.integrations.schemathesis_available


SchemathesisConfig
------------------

.. autoclass:: pytest_routes.integrations.schemathesis.SchemathesisConfig
   :members:
   :undoc-members:
   :show-inheritance:


SchemathesisAdapter
-------------------

.. autoclass:: pytest_routes.integrations.SchemathesisAdapter
   :members:
   :undoc-members:
   :show-inheritance:


SchemathesisValidator
---------------------

.. autoclass:: pytest_routes.integrations.SchemathesisValidator
   :members:
   :undoc-members:
   :show-inheritance:


Usage Examples
==============

Basic Usage
-----------

.. code-block:: python

   from pytest_routes.integrations import (
       SchemathesisAdapter,
       SchemathesisValidator,
       schemathesis_available,
   )

   # Check if Schemathesis is installed
   if schemathesis_available():
       # Create adapter for your ASGI app
       adapter = SchemathesisAdapter(
           app=your_app,
           schema_path="/openapi.json",
           validate_responses=True,
       )

       # Load the OpenAPI schema
       schema = adapter.load_schema()

       # Create a validator
       validator = SchemathesisValidator(adapter, strict=True)

       # Validate a response against the schema
       result = validator.validate(response, route_info)
       if not result.valid:
           print(f"Validation errors: {result.errors}")


Custom Checks Configuration
---------------------------

.. code-block:: python

   from pytest_routes.integrations import SchemathesisAdapter

   # Configure specific Schemathesis checks
   adapter = SchemathesisAdapter(
       app=your_app,
       schema_path="/api/openapi.json",
       validate_responses=True,
       checks=[
           "status_code_conformance",
           "content_type_conformance",
           "response_schema_conformance",
       ],
   )


See Also
========

* :doc:`/usage/schemathesis` - User guide for Schemathesis integration
* `Schemathesis Documentation <https://schemathesis.readthedocs.io/>`_ - Official Schemathesis docs
