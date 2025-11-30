.. _api-execution:

==============
Test Execution
==============

The execution module runs property-based tests against routes using generated
data and validates responses according to configuration.

.. currentmodule:: pytest_routes.execution


Overview
========

Test execution is the final stage of the pytest-routes pipeline:

1. **Route Discovery** - Extract routes from your application
2. **Strategy Generation** - Create Hypothesis strategies for parameters
3. **Test Creation** - Build Hypothesis-powered test functions
4. **Execution** - Run tests with generated data
5. **Validation** - Check responses against expected criteria


Quick Start
===========

Create and run tests programmatically:

.. code-block:: python

   from pytest_routes import (
       RouteTestConfig,
       RouteTestRunner,
       get_extractor,
   )

   # Configure testing
   config = RouteTestConfig(max_examples=50)

   # Extract routes
   extractor = get_extractor(app)
   routes = extractor.extract_routes(app)

   # Create runner and execute tests
   runner = RouteTestRunner(app, config)

   for route in routes:
       test_func = runner.create_test(route)
       try:
           test_func()
           print(f"PASS: {route}")
       except AssertionError as e:
           print(f"FAIL: {route}")
           print(e)


Architecture
============

.. code-block:: text

   +------------------+
   | RouteTestRunner  |
   +--------+---------+
            |
            | creates
            v
   +------------------+     +-------------------+
   |  Hypothesis Test |---->| RouteTestClient   |
   |  (@given)        |     | (ASGI client)     |
   +------------------+     +-------------------+
            |                        |
            | on failure             | HTTP request
            v                        v
   +------------------+     +-------------------+
   | RouteTestFailure |     | ASGI Application  |
   | (detailed error) |     +-------------------+
   +------------------+


API Reference
=============

Test Runner
-----------

RouteTestRunner
~~~~~~~~~~~~~~~

.. autoclass:: pytest_routes.execution.runner.RouteTestRunner
   :members:
   :undoc-members:
   :show-inheritance:

   The main test runner that orchestrates test creation and execution.

   .. rubric:: Example

   .. code-block:: python

      from pytest_routes import RouteTestRunner, RouteTestConfig

      config = RouteTestConfig(
          max_examples=100,
          fail_on_5xx=True,
          verbose=True,
      )

      runner = RouteTestRunner(app, config)

      # Create a test for a specific route
      test = runner.create_test(route)
      test()  # Runs 100 Hypothesis examples

      # Or test all routes asynchronously
      import asyncio
      results = asyncio.run(runner.test_all_routes(routes))


RouteTestFailure
~~~~~~~~~~~~~~~~

.. autoclass:: pytest_routes.execution.runner.RouteTestFailure
   :members:
   :undoc-members:
   :show-inheritance:

   Detailed information about a test failure, including the shrunk example
   from Hypothesis.

   .. rubric:: Attributes

   ``route_path``
       The original route pattern (e.g., ``/users/{user_id}``)

   ``method``
       HTTP method that failed

   ``status_code``
       Actual status code received

   ``expected_codes``
       List of allowed status codes

   ``request_path``
       The actual request URL with parameters filled in

   ``path_params``
       Path parameter values that caused the failure (shrunk)

   ``query_params``
       Query parameter values that caused the failure (shrunk)

   ``body``
       Request body that caused the failure (shrunk)

   ``response_body``
       Response body from the server (truncated)

   ``error_type``
       Type of error: ``"server_error_5xx"``, ``"unexpected_status"``, or ``"validation_error"``

   .. rubric:: Example Output

   .. code-block:: text

      ============================================================
      ROUTE TEST FAILURE: GET /users/{user_id}
      ============================================================

      Error Type:
        unexpected_status

      Request Details:
        Method: GET
        Path: /users/0
        Status Code: 404
        Expected: [200, 201, 204, 400, 401, 403, 422]

      Path Parameters (shrunk example):
        user_id: 0

      Response Body (truncated):
        {"detail": "User not found"}

      ============================================================


Test Client
-----------

RouteTestClient
~~~~~~~~~~~~~~~

.. autoclass:: pytest_routes.execution.client.RouteTestClient
   :members:
   :undoc-members:
   :show-inheritance:

   An async ASGI test client wrapper for making requests to your application.

   .. rubric:: Example

   .. code-block:: python

      from pytest_routes import RouteTestClient

      async def test_endpoint():
          client = RouteTestClient(app)

          response = await client.request(
              method="GET",
              path="/users/123",
              params={"include_posts": "true"},
              timeout=30.0,
          )

          assert response.status_code == 200


Understanding Test Creation
===========================

The :meth:`RouteTestRunner.create_test` method creates a Hypothesis-decorated
test function:

.. code-block:: python

   # What create_test() generates internally:

   @settings(
       max_examples=config.max_examples,
       suppress_health_check=[HealthCheck.too_slow],
       deadline=None,
   )
   @given(
       path_params=generate_path_params(route.path_params, route.path),
       query_params=st.fixed_dictionaries({...}),
       body=generate_body(route.body_type),
   )
   def test_route(path_params, query_params, body):
       # Format path with generated params
       formatted_path = format_path(route.path, path_params)

       # Make request
       response = client.request(
           method=route.methods[0],
           path=formatted_path,
           params=query_params,
           json=body,
       )

       # Validate response
       validate_response(response, route)


Async Execution
===============

For async test execution, use the async methods:

.. code-block:: python

   import asyncio
   from pytest_routes import RouteTestRunner, RouteTestConfig, get_extractor

   async def run_smoke_tests():
       config = RouteTestConfig(max_examples=25)
       runner = RouteTestRunner(app, config)
       extractor = get_extractor(app)
       routes = extractor.extract_routes(app)

       # Test single route
       result = await runner.test_route_async(routes[0])
       print(f"Route: {result['route']}, Passed: {result['passed']}")

       # Test all routes
       results = await runner.test_all_routes(routes)

       passed = sum(1 for r in results if r["passed"])
       failed = len(results) - passed
       print(f"Results: {passed} passed, {failed} failed")

   asyncio.run(run_smoke_tests())


Verbose Mode
============

Enable verbose output for debugging:

.. code-block:: python

   config = RouteTestConfig(verbose=True)
   runner = RouteTestRunner(app, config)

   # Output during test execution:
   #   -> GET /users/42
   #     path_params: {'user_id': 42}
   #     query_params: {'include_posts': True}
   #   <- 200


Error Handling
==============

The runner distinguishes between different error types:

**Server Errors (5xx)**
    Caught when ``fail_on_5xx=True`` (default). These indicate bugs in your
    application.

**Unexpected Status Codes**
    When the response status is not in ``allowed_status_codes``. Configure
    this list based on your API's expected behavior.

**Validation Errors**
    When ``validate_responses=True`` and validators fail. See :doc:`validation`
    for details.

.. code-block:: python

   config = RouteTestConfig(
       fail_on_5xx=True,                    # Fail on server errors
       allowed_status_codes=[200, 201, 204, 400, 404, 422],  # Expected codes
       validate_responses=True,             # Enable response validation
       fail_on_validation_error=True,       # Fail on validation errors
   )


See Also
========

* :doc:`config` - Configuration options for test execution
* :doc:`discovery` - How routes are extracted for testing
* :doc:`generation` - How test data is generated
* :doc:`validation` - Response validation details
