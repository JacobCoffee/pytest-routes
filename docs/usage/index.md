# Usage Guide

This section covers how to use pytest-routes effectively in your projects.

```{toctree}
:maxdepth: 2
:caption: Contents

cli-options
configuration
authentication
frameworks/index
```

---

## Overview

pytest-routes provides property-based smoke testing for ASGI applications. It automatically:

1. **Discovers routes** from your application using framework-specific extractors
2. **Generates test inputs** using Hypothesis strategies based on parameter types
3. **Executes requests** against each route with randomized data
4. **Validates responses** ensuring no 5xx errors occur

```{tip}
New to pytest-routes? Start with the [Getting Started](../getting-started.md) guide,
then return here for in-depth usage patterns.
```

---

## How It Works

### Route Discovery

pytest-routes extracts routes directly from your ASGI application without requiring
an OpenAPI schema. Each framework has a dedicated extractor:

| Extractor | Framework | Description |
|-----------|-----------|-------------|
| `LitestarExtractor` | Litestar | Extracts from Litestar's route handler map with full type information |
| `StarletteExtractor` | FastAPI, Starlette | Extracts from Starlette/FastAPI route lists |
| `OpenAPIExtractor` | Any | Falls back to OpenAPI schema if available |

The appropriate extractor is automatically selected based on your application type.

```{note}
You can override auto-detection using the `framework` configuration option if needed.
See [Configuration](configuration.md) for details.
```

### Input Generation

For each discovered route, pytest-routes generates test inputs using Hypothesis:

**Path Parameters**
: Generated based on type hints (e.g., `int`, `str`, `UUID`). The extractor reads
  your route definitions to determine the correct types.

**Query Parameters**
: Extracted from handler signatures and generated with appropriate strategies.

**Request Bodies**
: Generated from Pydantic models or dataclasses defined in your handler signatures.

```python
# Example: pytest-routes understands these type annotations
from uuid import UUID
from pydantic import BaseModel

class CreateUser(BaseModel):
    name: str
    email: str
    age: int

# Path param: user_id will generate random UUIDs
# Body: data will generate random CreateUser instances
@post("/users/{user_id}")
async def create_user(user_id: UUID, data: CreateUser) -> User:
    ...
```

### Test Execution

Each route is tested with multiple randomized inputs. By default, **100 examples**
are generated per route. Tests validate that:

- The route does not return 5xx status codes (server errors)
- The response matches configured validation rules

```{warning}
Routes requiring authentication will return 401/403 by default. Either exclude
these routes or configure your test fixtures to provide authentication.
See [Frameworks](frameworks/index.md) for solutions.
```

### Shrinking

When a test fails, Hypothesis automatically "shrinks" the input to find the
**minimal example** that still causes the failure. This makes debugging significantly
easier by removing irrelevant complexity from the failing case.

```
# Before shrinking: Complex failing input
{"name": "aB7x_qR2mN...", "email": "test1234567@...", "age": 98234}

# After shrinking: Minimal failing input
{"name": "", "email": "x", "age": -1}
```

---

## Common Patterns

### Testing Only Specific Routes

Use include patterns to focus tests on certain routes:

```bash
# Test only API routes
pytest --routes --routes-app myapp:app --routes-include "/api/*"

# Test multiple path patterns
pytest --routes --routes-app myapp:app --routes-include "/users/*,/orders/*"

# Test versioned API routes with recursive matching
pytest --routes --routes-app myapp:app --routes-include "/api/v2/**"
```

```{tip}
Use `*` to match within a single path segment and `**` to match across multiple segments.
For example, `/api/*` matches `/api/users` but not `/api/users/123`, while
`/api/**` matches both.
```

### Excluding Routes

Exclude routes that should not be smoke tested:

```bash
# Exclude health and internal routes
pytest --routes --routes-app myapp:app --routes-exclude "/health,/internal/*"

# Exclude multiple patterns
pytest --routes --routes-app myapp:app --routes-exclude "/health,/metrics,/admin/*"

# Clear all default excludes (test everything)
pytest --routes --routes-app myapp:app --routes-exclude ""
```

```{note}
Default excluded routes: `/health`, `/metrics`, `/openapi*`, `/docs`, `/redoc`, `/schema`.
These are typically infrastructure endpoints that don't need smoke testing.
```

### Reproducible Tests

Use a seed for reproducible test runs - essential for debugging and CI:

```bash
# Use a specific seed
pytest --routes --routes-app myapp:app --routes-seed 12345

# Use CI run ID as seed for reproducibility
pytest --routes --routes-app myapp:app --routes-seed $GITHUB_RUN_ID
```

When a test fails, pytest-routes reports the seed used, allowing you to reproduce
the exact failure:

```
FAILED test_routes[GET /users/{id}] - AssertionError: Status 500
  Seed: 98765  # <-- Use this to reproduce
  Input: {"id": 42}
```

### Adjusting Test Intensity

Control how many examples are generated per route:

```bash
# Quick smoke test (fast feedback during development)
pytest --routes --routes-app myapp:app --routes-max-examples 10

# Standard testing (default)
pytest --routes --routes-app myapp:app --routes-max-examples 100

# Thorough testing (CI/CD or pre-release)
pytest --routes --routes-app myapp:app --routes-max-examples 500
```

```{tip}
Start with fewer examples during development (`--routes-max-examples 10`) for fast
feedback, then increase for CI/CD pipelines where thoroughness matters more than speed.
```

---

## Custom Strategies

You can register custom Hypothesis strategies for your domain types:

```python
# conftest.py
from hypothesis import strategies as st
from pytest_routes import register_strategy

from myapp.models import CustomId, EmailAddress, PhoneNumber

# Register a strategy that generates valid CustomId instances
register_strategy(
    CustomId,
    st.builds(CustomId, st.integers(min_value=1, max_value=10000))
)

# Generate email-like strings
register_strategy(
    EmailAddress,
    st.emails().map(EmailAddress)
)

# Generate phone numbers in a specific format
register_strategy(
    PhoneNumber,
    st.from_regex(r"\+1-[0-9]{3}-[0-9]{3}-[0-9]{4}", fullmatch=True).map(PhoneNumber)
)
```

```{note}
Custom strategies are especially useful for:
- Domain-specific value objects
- Types with validation constraints
- External IDs that must follow specific formats
```

See the [API Reference](../api/index.rst) for the full strategy registration API.

---

## Response Validation

pytest-routes supports multiple validation strategies that can be combined:

```python
# conftest.py
from pytest_routes import (
    StatusCodeValidator,
    ContentTypeValidator,
    CompositeValidator,
)

# Basic: Validate only status codes
status_validator = StatusCodeValidator(
    allowed_codes=[200, 201, 204, 400, 404]  # 5xx always fail
)

# Strict: Also validate content types
content_validator = ContentTypeValidator(
    allowed_types=["application/json", "application/xml"]
)

# Combined: Use multiple validators together
validator = CompositeValidator([
    status_validator,
    content_validator,
])
```

**Available Validators:**

| Validator | Purpose |
|-----------|---------|
| `StatusCodeValidator` | Validates HTTP status codes against allowed list |
| `ContentTypeValidator` | Validates response Content-Type header |
| `JsonSchemaValidator` | Validates response body against JSON schema |
| `OpenAPIValidator` | Validates response against OpenAPI specification |

---

## Integration with CI/CD

pytest-routes integrates seamlessly with CI/CD pipelines:

```yaml
# .github/workflows/test.yml
name: Smoke Tests

on: [push, pull_request]

jobs:
  smoke-test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@11bd71901bbe5b1630ceea73d27597364c9af683  # v4
        with:
          persist-credentials: false

      - uses: astral-sh/setup-uv@6b9c6063abd6010835644d4c2e1bef4cf5cd0fca  # v6
        with:
          python-version: "3.12"

      - name: Install dependencies
        run: uv sync --all-groups

      - name: Run smoke tests
        run: |
          uv run pytest --routes \
            --routes-app myapp:app \
            --routes-max-examples 200 \
            --routes-seed ${{ github.run_id }}
```

```{tip}
Using `${{ github.run_id }}` as the seed ensures reproducibility within a CI run
while still getting randomized tests across different runs.
```

### CI Configuration Example

For CI/CD, use a dedicated configuration profile:

```toml
# pyproject.toml
[tool.pytest-routes]
app = "myapp:app"
max_examples = 200
fail_on_5xx = true
allowed_status_codes = [200, 201, 204, 400, 401, 403, 404, 422]
exclude = ["/health", "/metrics"]
```

---

## Next Steps

- [CLI Options Reference](cli-options.md) - Complete list of command-line options
- [Configuration](configuration.md) - Detailed configuration options
- [Framework Support](frameworks/index.md) - Framework-specific guides and troubleshooting
