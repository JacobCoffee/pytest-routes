.. _api-validation:

===================
Response Validation
===================

The validation module provides validators for checking HTTP responses against
expected schemas, status codes, content types, and other criteria.

.. currentmodule:: pytest_routes.validation

.. contents:: On This Page
   :local:
   :depth: 2
   :backlinks: none


Overview
========

Response validation ensures your API responses conform to expectations:

* **Status Code Validation** - Check response status codes
* **Content Type Validation** - Verify Content-Type headers
* **JSON Schema Validation** - Validate response bodies against schemas
* **OpenAPI Validation** - Validate against OpenAPI specifications
* **Composite Validation** - Combine multiple validators


Quick Start
===========

Basic status code validation:

.. code-block:: python

   from pytest_routes import StatusCodeValidator, ValidationResult

   validator = StatusCodeValidator(allowed_codes=[200, 201, 204])
   result: ValidationResult = validator.validate(response, route)

   if result.valid:
       print("Response is valid!")
   else:
       print(f"Errors: {result.errors}")


Combine multiple validators:

.. code-block:: python

   from pytest_routes import (
       CompositeValidator,
       StatusCodeValidator,
       ContentTypeValidator,
       JsonSchemaValidator,
   )

   validator = CompositeValidator([
       StatusCodeValidator([200, 201]),
       ContentTypeValidator(["application/json"]),
       JsonSchemaValidator(schema={"type": "object"}),
   ])

   result = validator.validate(response, route)


Validator Hierarchy
===================

.. code-block:: text

   ResponseValidator (Protocol)
           |
           +-- StatusCodeValidator
           |
           +-- ContentTypeValidator
           |
           +-- JsonSchemaValidator
           |
           +-- OpenAPIResponseValidator
           |
           +-- CompositeValidator (combines others)


API Reference
=============

Core Types
----------

ValidationResult
~~~~~~~~~~~~~~~~

.. autoclass:: pytest_routes.validation.response.ValidationResult
   :members:
   :undoc-members:
   :show-inheritance:

   The result of a validation operation.

   .. rubric:: Attributes

   ``valid``
       Boolean indicating if validation passed

   ``errors``
       List of error messages (empty if valid)

   ``warnings``
       List of warning messages (non-fatal issues)

   .. rubric:: Example

   .. code-block:: python

      result = ValidationResult(
          valid=False,
          errors=["Status code 500 not in allowed codes"],
          warnings=["Response time exceeded 1s"],
      )

      if not result.valid:
          for error in result.errors:
              print(f"ERROR: {error}")


ResponseValidator Protocol
~~~~~~~~~~~~~~~~~~~~~~~~~~

.. autoclass:: pytest_routes.validation.response.ResponseValidator
   :members:
   :undoc-members:
   :show-inheritance:

   Protocol that all validators must implement.


Validators
----------

StatusCodeValidator
~~~~~~~~~~~~~~~~~~~

.. autoclass:: pytest_routes.validation.response.StatusCodeValidator
   :members:
   :undoc-members:
   :show-inheritance:

   Validates that response status codes are within an allowed set.

   .. rubric:: Example

   .. code-block:: python

      from pytest_routes import StatusCodeValidator

      # Allow success and client error codes
      validator = StatusCodeValidator(
          allowed_codes=[200, 201, 204, 400, 401, 403, 404, 422]
      )

      # Default: all 2xx-4xx codes (200-499)
      default_validator = StatusCodeValidator()


ContentTypeValidator
~~~~~~~~~~~~~~~~~~~~

.. autoclass:: pytest_routes.validation.response.ContentTypeValidator
   :members:
   :undoc-members:
   :show-inheritance:

   Validates the Content-Type header of responses.

   .. rubric:: Example

   .. code-block:: python

      from pytest_routes import ContentTypeValidator

      # JSON APIs
      json_validator = ContentTypeValidator(
          expected_types=["application/json"]
      )

      # Multiple content types
      multi_validator = ContentTypeValidator(
          expected_types=[
              "application/json",
              "application/xml",
              "text/html",
          ]
      )


JsonSchemaValidator
~~~~~~~~~~~~~~~~~~~

.. autoclass:: pytest_routes.validation.response.JsonSchemaValidator
   :members:
   :undoc-members:
   :show-inheritance:

   Validates response bodies against a JSON Schema.

   .. note::

      Requires the ``jsonschema`` package for full schema validation.
      Install with: ``pip install jsonschema``

   .. rubric:: Example

   .. code-block:: python

      from pytest_routes import JsonSchemaValidator

      schema = {
          "type": "object",
          "required": ["id", "name"],
          "properties": {
              "id": {"type": "integer"},
              "name": {"type": "string", "minLength": 1},
              "email": {"type": "string", "format": "email"},
          },
      }

      validator = JsonSchemaValidator(schema=schema, strict=True)
      result = validator.validate(response, route)

      if not result.valid:
          print(f"Schema errors: {result.errors}")


OpenAPIResponseValidator
~~~~~~~~~~~~~~~~~~~~~~~~

.. autoclass:: pytest_routes.validation.response.OpenAPIResponseValidator
   :members:
   :undoc-members:
   :show-inheritance:

   Validates responses against an OpenAPI specification.

   This validator automatically:

   * Finds the matching path in the OpenAPI spec
   * Looks up the expected response schema for the status code
   * Validates the response body against that schema

   .. rubric:: Example

   .. code-block:: python

      from pytest_routes import OpenAPIResponseValidator

      openapi_spec = {
          "openapi": "3.0.0",
          "paths": {
              "/users/{user_id}": {
                  "get": {
                      "responses": {
                          "200": {
                              "content": {
                                  "application/json": {
                                      "schema": {
                                          "type": "object",
                                          "properties": {
                                              "id": {"type": "integer"},
                                              "name": {"type": "string"},
                                          },
                                      }
                                  }
                              }
                          }
                      }
                  }
              }
          }
      }

      validator = OpenAPIResponseValidator(openapi_schema=openapi_spec)
      result = validator.validate(response, route)


CompositeValidator
~~~~~~~~~~~~~~~~~~

.. autoclass:: pytest_routes.validation.response.CompositeValidator
   :members:
   :undoc-members:
   :show-inheritance:

   Combines multiple validators into one.

   All validators are run in sequence, and their results are aggregated.
   The composite is valid only if all child validators pass.

   .. rubric:: Example

   .. code-block:: python

      from pytest_routes import (
          CompositeValidator,
          StatusCodeValidator,
          ContentTypeValidator,
          JsonSchemaValidator,
      )

      # Build a comprehensive validator
      validator = CompositeValidator([
          StatusCodeValidator([200, 201]),
          ContentTypeValidator(["application/json"]),
          JsonSchemaValidator(schema={
              "type": "object",
              "required": ["data"],
          }),
      ])

      result = validator.validate(response, route)

      # Result contains all errors from all validators
      if not result.valid:
          for error in result.errors:
              print(f"Validation error: {error}")

      # Warnings are also aggregated
      for warning in result.warnings:
          print(f"Warning: {warning}")


Enabling Validation
===================

Enable response validation in your configuration:

.. code-block:: python

   from pytest_routes import RouteTestConfig

   config = RouteTestConfig(
       validate_responses=True,
       response_validators=["status_code", "content_type"],
       fail_on_validation_error=True,
   )

Available validator names:

* ``"status_code"`` - :class:`StatusCodeValidator`
* ``"content_type"`` - :class:`ContentTypeValidator`


Custom Validators
=================

Create custom validators by implementing the :class:`ResponseValidator` protocol:

.. code-block:: python

   from typing import Any
   from pytest_routes import ValidationResult
   from pytest_routes.discovery.base import RouteInfo

   class ResponseTimeValidator:
       """Validate that responses are fast enough."""

       def __init__(self, max_seconds: float = 1.0):
           self.max_seconds = max_seconds

       def validate(self, response: Any, route: RouteInfo) -> ValidationResult:
           # Access response time if available
           elapsed = getattr(response, "elapsed", None)

           if elapsed is None:
               return ValidationResult(
                   valid=True,
                   warnings=["Response time not available"]
               )

           if elapsed.total_seconds() > self.max_seconds:
               return ValidationResult(
                   valid=False,
                   errors=[
                       f"Response took {elapsed.total_seconds():.2f}s, "
                       f"max allowed is {self.max_seconds}s"
                   ]
               )

           return ValidationResult(valid=True)


   class DeprecationHeaderValidator:
       """Check for deprecation warnings in headers."""

       def validate(self, response: Any, route: RouteInfo) -> ValidationResult:
           warnings = []

           if "Deprecation" in response.headers:
               warnings.append(
                   f"Route {route.path} is deprecated: "
                   f"{response.headers['Deprecation']}"
               )

           if "Sunset" in response.headers:
               warnings.append(
                   f"Route {route.path} will be removed: "
                   f"{response.headers['Sunset']}"
               )

           return ValidationResult(valid=True, warnings=warnings)


Use custom validators with :class:`CompositeValidator`:

.. code-block:: python

   from pytest_routes import CompositeValidator, StatusCodeValidator

   validator = CompositeValidator([
       StatusCodeValidator([200, 201]),
       ResponseTimeValidator(max_seconds=2.0),
       DeprecationHeaderValidator(),
   ])


See Also
========

* :doc:`config` - Configuration options for validation
* :doc:`execution` - How validation fits into test execution
* :ref:`api-reference` - Complete API overview
