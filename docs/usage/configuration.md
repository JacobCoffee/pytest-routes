# Configuration

pytest-routes can be configured via command-line options or `pyproject.toml`.
CLI options always take precedence over file configuration.

```{contents}
:local:
:depth: 2
```

---

## Complete Configuration Example

Here's a complete `pyproject.toml` configuration showing all available options:

```toml
# pyproject.toml

[tool.pytest-routes]
# ============================================================================
# Application Settings
# ============================================================================

# Import path to your ASGI application (required if not using app fixture)
app = "myapp.main:application"

# Framework hint - usually auto-detected
# Options: "auto", "litestar", "fastapi", "starlette"
framework = "auto"

# ============================================================================
# Test Execution
# ============================================================================

# Maximum Hypothesis examples per route (higher = more thorough, slower)
max_examples = 100

# Timeout in seconds for each route test
timeout = 30.0

# Random seed for reproducible tests (omit for random each run)
# seed = 12345

# ============================================================================
# Route Filtering
# ============================================================================

# Glob patterns for routes to include (empty = include all)
include = []

# Glob patterns for routes to exclude
exclude = [
    "/health",
    "/metrics",
    "/openapi*",
    "/docs",
    "/redoc",
    "/schema",
]

# HTTP methods to test
methods = ["GET", "POST", "PUT", "PATCH", "DELETE"]

# ============================================================================
# Response Validation
# ============================================================================

# Fail tests on 5xx status codes
fail_on_5xx = true

# Status codes considered passing (in addition to 2xx)
allowed_status_codes = [200, 201, 204, 400, 401, 403, 404, 422]

# Enable response body validation
validate_responses = false

# Validators to use when validate_responses is enabled
# Options: "status_code", "content_type", "json_schema", "openapi"
response_validators = ["status_code"]

# ============================================================================
# Output
# ============================================================================

# Enable verbose output during test collection
verbose = false
```

---

## Configuration Options Reference

### Application Settings

#### `app`

Import path to your ASGI application.

Type
: `str`

Default
: `None` (uses `app` fixture from conftest.py)

```toml
[tool.pytest-routes]
# Simple module
app = "myapp:app"

# Nested module
app = "myapp.main:application"

# Factory function
app = "myapp.factory:create_app()"
```

```{tip}
If your application requires initialization (database connections, config loading),
use an `app` fixture in `conftest.py` instead of the config option.
```

#### `framework`

Framework hint for route extraction. Auto-detection works in most cases.

Type
: `str`

Default
: `"auto"`

Options
: `"auto"`, `"litestar"`, `"fastapi"`, `"starlette"`

```toml
[tool.pytest-routes]
# Let pytest-routes detect the framework
framework = "auto"

# Force Litestar extractor
framework = "litestar"
```

```{note}
Use explicit framework hints when auto-detection fails or when using
a framework that wraps another (e.g., a custom framework built on Starlette).
```

---

### Test Execution Settings

#### `max_examples`

Maximum number of Hypothesis examples to generate per route.

Type
: `int`

Default
: `100`

```toml
[tool.pytest-routes]
# Quick testing
max_examples = 10

# Standard testing
max_examples = 100

# Thorough testing
max_examples = 500
```

```{warning}
Higher values significantly increase test runtime. For 50 routes with
`max_examples = 500`, pytest-routes generates 25,000 test cases.
```

#### `timeout`

Timeout in seconds for each route test.

Type
: `float`

Default
: `30.0`

```toml
[tool.pytest-routes]
# Shorter timeout for fast endpoints
timeout = 10.0

# Longer timeout for slow endpoints
timeout = 60.0
```

#### `seed`

Random seed for reproducible test runs.

Type
: `int | None`

Default
: `None` (random seed each run)

```toml
[tool.pytest-routes]
# Fixed seed for reproducibility
seed = 12345
```

```{tip}
For CI/CD, pass the seed via CLI using the run ID: `--routes-seed $GITHUB_RUN_ID`.
This gives reproducibility within a run while varying inputs across runs.
```

---

### Route Filtering Settings

#### `include`

Glob patterns for routes to include. Only routes matching at least one pattern
will be tested.

Type
: `list[str]`

Default
: `[]` (include all routes)

```toml
[tool.pytest-routes]
# Test only API routes
include = ["/api/*"]

# Test multiple patterns
include = ["/api/*", "/v2/**"]

# Test specific endpoints
include = ["/users/*", "/orders/*", "/products/*"]
```

#### `exclude`

Glob patterns for routes to exclude.

Type
: `list[str]`

Default
: `["/health", "/metrics", "/openapi*", "/docs", "/redoc", "/schema"]`

```toml
[tool.pytest-routes]
# Exclude infrastructure endpoints
exclude = ["/health", "/metrics"]

# Exclude internal routes
exclude = ["/health", "/metrics", "/internal/*", "/admin/*"]

# Clear all excludes
exclude = []
```

#### `methods`

HTTP methods to test.

Type
: `list[str]`

Default
: `["GET", "POST", "PUT", "PATCH", "DELETE"]`

```toml
[tool.pytest-routes]
# Test only read operations
methods = ["GET"]

# Test only write operations
methods = ["POST", "PUT", "PATCH", "DELETE"]

# Include all methods
methods = ["GET", "HEAD", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"]
```

---

### Response Validation Settings

#### `fail_on_5xx`

Whether to fail tests on 5xx status codes (server errors).

Type
: `bool`

Default
: `true`

```toml
[tool.pytest-routes]
# Fail on any server error (recommended)
fail_on_5xx = true

# Allow 5xx responses (not recommended for smoke tests)
fail_on_5xx = false
```

#### `allowed_status_codes`

List of status codes considered passing.

Type
: `list[int]`

Default
: All 2xx-4xx codes (any non-5xx)

```toml
[tool.pytest-routes]
# Explicit allowed codes
allowed_status_codes = [200, 201, 204, 400, 401, 403, 404, 422]

# Allow only success codes
allowed_status_codes = [200, 201, 204]
```

#### `validate_responses`

Enable response body validation beyond status codes.

Type
: `bool`

Default
: `false`

```toml
[tool.pytest-routes]
validate_responses = true
```

#### `response_validators`

List of validators to use when `validate_responses` is enabled.

Type
: `list[str]`

Default
: `["status_code"]`

Options
: `"status_code"`, `"content_type"`, `"json_schema"`, `"openapi"`

```toml
[tool.pytest-routes]
validate_responses = true
response_validators = ["status_code", "content_type"]
```

**Available validators:**

```{list-table}
:header-rows: 1
:widths: 20 80

* - Validator
  - Description
* - `status_code`
  - Validates status codes against `allowed_status_codes`
* - `content_type`
  - Validates Content-Type header matches expected types
* - `json_schema`
  - Validates response body against JSON schema (requires schema)
* - `openapi`
  - Validates response against OpenAPI specification
```

---

### Output Settings

#### `verbose`

Enable verbose output during test collection and execution.

Type
: `bool`

Default
: `false`

```toml
[tool.pytest-routes]
verbose = true
```

---

## Configuration Precedence

Configuration is merged from multiple sources with this precedence (highest first):

1. **CLI options** - Always take precedence
2. **pyproject.toml** - File-based configuration
3. **Built-in defaults** - Fallback values

**Example of precedence:**

```toml
# pyproject.toml
[tool.pytest-routes]
max_examples = 50
exclude = ["/health", "/metrics"]
```

```bash
# CLI overrides max_examples, but uses exclude from file
pytest --routes --routes-app myapp:app --routes-max-examples 100

# Result: max_examples=100, exclude=["/health", "/metrics"]
```

---

## Environment Variables

```{note}
Currently, pytest-routes does not read configuration directly from environment
variables. Use CLI options for dynamic configuration in CI/CD pipelines.
```

**Workaround for CI/CD:**

```bash
# Use shell variable expansion in CLI
pytest --routes \
    --routes-app myapp:app \
    --routes-seed ${GITHUB_RUN_ID:-42} \
    --routes-max-examples ${SMOKE_TEST_EXAMPLES:-100}
```

**GitHub Actions example:**

```yaml
env:
  SMOKE_TEST_EXAMPLES: 200

steps:
  - run: |
      pytest --routes \
        --routes-app myapp:app \
        --routes-max-examples $SMOKE_TEST_EXAMPLES \
        --routes-seed ${{ github.run_id }}
```

---

## Configuration Profiles

### Development Profile

Quick feedback during local development:

```toml
# pyproject.toml - Development defaults
[tool.pytest-routes]
max_examples = 10
exclude = ["/health", "/metrics", "/docs", "/openapi*"]
verbose = true
timeout = 10.0
```

```{tip}
Override in CI with CLI: `--routes-max-examples 200`
```

### CI/CD Profile

Thorough testing in continuous integration:

```toml
# pyproject.toml - CI defaults
[tool.pytest-routes]
max_examples = 200
fail_on_5xx = true
allowed_status_codes = [200, 201, 204, 400, 401, 403, 404, 422]
timeout = 30.0
```

### Production Validation Profile

Pre-deployment smoke test with response validation:

```toml
# pyproject.toml - Pre-deployment
[tool.pytest-routes]
max_examples = 100
exclude = ["/health"]
validate_responses = true
response_validators = ["status_code", "content_type"]
fail_on_5xx = true
```

### Read-Only Profile

Safe testing against production-like data:

```toml
# pyproject.toml - Read-only testing
[tool.pytest-routes]
methods = ["GET", "HEAD"]
max_examples = 50
exclude = ["/admin/*", "/internal/*"]
```

---

## Fixture-Based Configuration

For complex setups, use a `conftest.py` fixture instead of or in addition to
file configuration:

```python
# conftest.py
import pytest
from myapp import create_app
from myapp.config import TestConfig

@pytest.fixture
def app():
    """Create a configured test application.

    This fixture is automatically used by pytest-routes when
    --routes-app is not specified.
    """
    # Create app with test configuration
    application = create_app(config=TestConfig())

    # Set up test database
    with application.database.begin():
        yield application

    # Cleanup happens automatically
```

```{tip}
The `app` fixture approach is recommended when your application needs:
- Database connections or migrations
- Configuration loading from environment
- Dependency injection setup
- Authentication/authorization configuration
```
