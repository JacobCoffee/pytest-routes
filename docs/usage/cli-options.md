# CLI Options Reference

pytest-routes adds several command-line options to pytest for controlling smoke test behavior.

```{contents}
:local:
:depth: 2
```

---

## Quick Reference

The following table summarizes all available CLI options:

```{list-table} CLI Options Summary
:header-rows: 1
:widths: 25 15 60

* - Option
  - Default
  - Description
* - `--routes`
  - `false`
  - Enable route smoke testing
* - `--routes-app`
  - `None`
  - Import path to ASGI application (`module:attribute`)
* - `--routes-max-examples`
  - `100`
  - Maximum Hypothesis examples per route
* - `--routes-include`
  - `[]`
  - Comma-separated glob patterns for routes to include
* - `--routes-exclude`
  - See below
  - Comma-separated glob patterns for routes to exclude
* - `--routes-methods`
  - `GET,POST,PUT,PATCH,DELETE`
  - HTTP methods to test
* - `--routes-seed`
  - `None`
  - Random seed for reproducible tests
```

---

## Core Options

### `--routes`

Enable route smoke testing. **Required** - without this flag, pytest-routes does not run any tests.

```bash
# Enable smoke testing
pytest --routes

# Combine with other pytest options
pytest --routes -v --tb=short
```

```{note}
This flag exists to prevent pytest-routes from running during normal test runs.
Add it only when you specifically want to run smoke tests.
```

### `--routes-app`

Specify the import path to your ASGI application.

**Format:** `module:attribute` or `module.submodule:attribute`

**Default:** `None` (uses `app` fixture from conftest.py)

```bash
# Simple module import
pytest --routes --routes-app myapp:app

# Nested module import
pytest --routes --routes-app myapp.main:application

# Package with factory function
pytest --routes --routes-app "myapp.factory:create_app()"
```

**Example import paths:**

```{list-table}
:header-rows: 1
:widths: 40 60

* - Import Path
  - Python Equivalent
* - `myapp:app`
  - `from myapp import app`
* - `myapp.main:application`
  - `from myapp.main import application`
* - `myapp.factory:create_app()`
  - `from myapp.factory import create_app; app = create_app()`
```

```{tip}
If you don't specify `--routes-app`, pytest-routes looks for an `app` fixture in
your `conftest.py`. This is useful for applications that require setup before use.
```

---

## Test Intensity Options

### `--routes-max-examples`

Maximum number of Hypothesis examples to generate per route.

**Default:** `100`

```bash
# Quick smoke test (10 examples per route)
pytest --routes --routes-app myapp:app --routes-max-examples 10

# Standard testing (100 examples per route)
pytest --routes --routes-app myapp:app --routes-max-examples 100

# Thorough testing (500 examples per route)
pytest --routes --routes-app myapp:app --routes-max-examples 500
```

**Recommendations by use case:**

```{list-table}
:header-rows: 1
:widths: 25 15 60

* - Use Case
  - Examples
  - Rationale
* - Development
  - `5-10`
  - Fast feedback loop, catch obvious issues
* - Pre-commit
  - `25-50`
  - Balance between speed and coverage
* - CI/CD
  - `100-200`
  - Thorough testing, acceptable runtime
* - Pre-release
  - `500+`
  - Maximum coverage before deployment
```

```{warning}
Higher values significantly increase test runtime. For an app with 50 routes,
`--routes-max-examples 500` generates 25,000 total test cases.
```

---

## Route Filtering Options

### `--routes-include`

Comma-separated list of glob patterns for routes to include. Only routes matching
at least one pattern will be tested.

**Default:** `[]` (empty - include all routes)

**Glob syntax:**
- `*` matches any characters within a single path segment
- `**` matches any characters including path separators (recursive)

```bash
# Test only API routes (single segment)
pytest --routes --routes-app myapp:app --routes-include "/api/*"
# Matches: /api/users, /api/orders
# Does NOT match: /api/users/123, /api/v2/users

# Test API routes recursively
pytest --routes --routes-app myapp:app --routes-include "/api/**"
# Matches: /api/users, /api/users/123, /api/v2/users/456

# Test multiple path patterns
pytest --routes --routes-app myapp:app --routes-include "/users/*,/orders/*"

# Test all v2 API routes
pytest --routes --routes-app myapp:app --routes-include "/api/v2/**"
```

### `--routes-exclude`

Comma-separated list of glob patterns for routes to exclude. Routes matching any
pattern will be skipped.

**Default:** `/health,/metrics,/openapi*,/docs,/redoc,/schema`

```bash
# Exclude specific routes
pytest --routes --routes-app myapp:app --routes-exclude "/health,/metrics"

# Exclude internal routes
pytest --routes --routes-app myapp:app --routes-exclude "/internal/*,/admin/*"

# Exclude auth routes that require setup
pytest --routes --routes-app myapp:app --routes-exclude "/auth/*,/login,/logout"

# Clear default excludes (test everything)
pytest --routes --routes-app myapp:app --routes-exclude ""
```

```{note}
When both `--routes-include` and `--routes-exclude` are specified, a route must:
1. Match at least one include pattern, AND
2. NOT match any exclude pattern
```

**Example: Testing API routes except internal ones:**

```bash
pytest --routes --routes-app myapp:app \
    --routes-include "/api/**" \
    --routes-exclude "/api/internal/*"
```

---

## HTTP Method Options

### `--routes-methods`

Comma-separated list of HTTP methods to test.

**Default:** `GET,POST,PUT,PATCH,DELETE`

```bash
# Test only GET requests (safe, read-only)
pytest --routes --routes-app myapp:app --routes-methods "GET"

# Test only write operations
pytest --routes --routes-app myapp:app --routes-methods "POST,PUT,DELETE"

# Include HEAD requests
pytest --routes --routes-app myapp:app --routes-methods "GET,HEAD"

# Test all methods including OPTIONS
pytest --routes --routes-app myapp:app --routes-methods "GET,HEAD,POST,PUT,PATCH,DELETE,OPTIONS"
```

**Common method combinations:**

```{list-table}
:header-rows: 1
:widths: 30 70

* - Methods
  - Use Case
* - `GET`
  - Read-only smoke test, safe for production-like data
* - `GET,POST`
  - Test reads and creates, skip updates/deletes
* - `POST,PUT,PATCH,DELETE`
  - Test only write operations
* - `GET,HEAD,OPTIONS`
  - Test metadata endpoints
```

---

## Reproducibility Options

### `--routes-seed`

Set a random seed for reproducible test runs. Essential for debugging failures
and consistent CI/CD behavior.

**Default:** `None` (random seed each run)

```bash
# Use a specific seed
pytest --routes --routes-app myapp:app --routes-seed 12345

# Reproduce a failing test from CI
pytest --routes --routes-app myapp:app --routes-seed 98765

# Use CI run ID for reproducibility
pytest --routes --routes-app myapp:app --routes-seed $GITHUB_RUN_ID
```

When a test fails, pytest-routes reports the seed used:

```
FAILED test_routes[GET /users/{id}] - AssertionError: Status 500
  Seed: 98765
  Input: {"id": 42, "include_deleted": true}

To reproduce:
  pytest --routes --routes-app myapp:app --routes-seed 98765
```

```{tip}
In CI/CD, use the run ID or commit SHA as the seed. This gives you reproducibility
within a run while still getting varied test inputs across different runs.
```

---

## Combining Options

Options can be combined for fine-grained control:

```bash
# Full example with all options
pytest --routes \
    --routes-app myapp:app \
    --routes-max-examples 50 \
    --routes-include "/api/*" \
    --routes-exclude "/api/internal/*,/api/admin/*" \
    --routes-methods "GET,POST" \
    --routes-seed 12345
```

---

## Configuration File Alternative

All CLI options can also be configured in `pyproject.toml`. CLI options always
take precedence over file configuration.

```toml
# pyproject.toml
[tool.pytest-routes]
app = "myapp:app"
max_examples = 50
include = ["/api/*"]
exclude = ["/health", "/metrics", "/api/internal/*"]
methods = ["GET", "POST"]
seed = 12345
```

See [Configuration](configuration.md) for complete details.

---

## Usage Examples

### Development: Quick Validation

Fast smoke test during local development:

```bash
pytest --routes \
    --routes-app myapp:app \
    --routes-max-examples 5 \
    -x  # Stop on first failure
```

### CI Pipeline: Thorough Testing

Comprehensive testing in CI with reproducibility:

```bash
pytest --routes \
    --routes-app myapp:app \
    --routes-max-examples 200 \
    --routes-seed $GITHUB_RUN_ID \
    --tb=short  # Shorter tracebacks
```

### Feature Development: Testing New Routes

Test only routes in a specific module:

```bash
pytest --routes \
    --routes-app myapp:app \
    --routes-include "/api/v2/users/*" \
    --routes-max-examples 100 \
    -v  # Verbose output
```

### Pre-Deployment: Comprehensive Check

Full smoke test before deployment:

```bash
pytest --routes \
    --routes-app myapp:app \
    --routes-max-examples 500 \
    --routes-exclude "/health" \
    --routes-seed $(date +%s)  # Timestamp seed for reproducibility
```

### Read-Only Testing: Safe for Production Data

Test only GET endpoints (safe with real data):

```bash
pytest --routes \
    --routes-app myapp:app \
    --routes-methods "GET" \
    --routes-exclude "/admin/*"
```
