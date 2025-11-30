# pytest-routes

```{rst-class} lead
Property-based smoke testing for ASGI application routes with first-class Litestar support.
```

pytest-routes automatically discovers routes from your ASGI application and performs
randomized smoke testing using [Hypothesis](https://hypothesis.works/). It works with
any ASGI framework, with first-class support for [Litestar](https://litestar.dev/).

---

::::{grid} 1 2 2 3
:gutter: 3

:::{grid-item-card} {octicon}`download` Installation
:link: getting-started
:link-type: doc
:class-card: sd-border-0

Get started with pytest-routes in minutes. Install with pip or uv and run your first smoke test.
:::

:::{grid-item-card} {octicon}`book` Usage Guide
:link: usage/index
:link-type: doc
:class-card: sd-border-0

Learn how to configure pytest-routes, filter routes, customize strategies, and integrate with CI/CD.
:::

:::{grid-item-card} {octicon}`code` API Reference
:link: api/index
:link-type: doc
:class-card: sd-border-0

Complete API documentation for all public classes, functions, and configuration options.
:::

::::

---

## Key Features

::::{grid} 1 2 2 3
:gutter: 3

:::{grid-item-card} Automatic Discovery
:class-card: sd-border-0

Extracts routes directly from your ASGI app - no OpenAPI schema required.
Works with Litestar, FastAPI, Starlette, and any ASGI framework.
:::

:::{grid-item-card} Property-Based Testing
:class-card: sd-border-0

Uses Hypothesis to generate diverse, randomized test inputs that find
edge cases you never thought to test.
:::

:::{grid-item-card} Zero Configuration
:class-card: sd-border-0

Works out of the box with sensible defaults. Just add `--routes` to your
pytest command and start testing.
:::

:::{grid-item-card} Framework Aware
:class-card: sd-border-0

Deep integration with Litestar for full type extraction. Automatic support
for FastAPI and Starlette route patterns.
:::

:::{grid-item-card} Configurable
:class-card: sd-border-0

Filter routes by pattern, customize HTTP methods, set examples per route,
and configure validation rules.
:::

:::{grid-item-card} Response Validation
:class-card: sd-border-0

Built-in validators for status codes, content types, and JSON schemas.
Optional OpenAPI response validation.
:::

::::

---

## Quick Start

### Installation

```bash
# Using uv (recommended)
uv add pytest-routes

# Using pip
pip install pytest-routes

# With framework extras
uv add "pytest-routes[litestar]"
uv add "pytest-routes[fastapi]"
```

### Basic Usage

Run smoke tests on your ASGI application:

```bash
# Specify app via CLI
pytest --routes --routes-app myapp:app

# With options
pytest --routes --routes-app myapp:app --routes-max-examples 50
```

Or define your app as a pytest fixture:

```python
# conftest.py
import pytest
from myapp import create_app

@pytest.fixture(scope="session")
def app():
    return create_app()
```

```bash
# App is discovered from fixture
pytest --routes
```

### What It Does

1. **Discovery** - Extracts routes from your ASGI application
2. **Generation** - Creates Hypothesis strategies based on route parameter types
3. **Execution** - Runs property-based tests against each route
4. **Validation** - Checks that responses meet smoke test criteria (no 5xx errors)

---

## Example Output

```text
$ pytest --routes --routes-app examples.litestar_app:app -v

tests/test_routes.py::test_route[GET /] PASSED
tests/test_routes.py::test_route[GET /users] PASSED
tests/test_routes.py::test_route[POST /users] PASSED
tests/test_routes.py::test_route[GET /users/{user_id}] PASSED
tests/test_routes.py::test_route[PUT /users/{user_id}] PASSED
tests/test_routes.py::test_route[DELETE /users/{user_id}] PASSED

========================= 6 passed in 2.34s =========================
```

Each route is tested with multiple randomized inputs. If a route returns a 5xx error,
the test fails with a minimal reproducing example.

---

## Supported Frameworks

| Framework | Status | Notes |
|-----------|--------|-------|
| [Litestar](https://litestar.dev/) | First-class | Full type extraction from handlers |
| [FastAPI](https://fastapi.tiangolo.com/) | Supported | Via Starlette extractor |
| [Starlette](https://www.starlette.io/) | Supported | Base ASGI support |

---

```{toctree}
:maxdepth: 2
:caption: Learn
:hidden:

getting-started
usage/index
```

```{toctree}
:maxdepth: 2
:caption: Reference
:hidden:

api/index
```

```{toctree}
:caption: Project
:hidden:

changelog
GitHub <https://github.com/JacobCoffee/pytest-routes>
PyPI <https://pypi.org/project/pytest-routes/>
Discord <https://discord.gg/litestar>
```

---

## License

pytest-routes is released under the [MIT License](https://github.com/JacobCoffee/pytest-routes/blob/main/LICENSE).

---

## Indices and Tables

- {ref}`genindex`
- {ref}`modindex`
- {ref}`search`
