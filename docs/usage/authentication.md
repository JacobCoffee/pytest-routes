# Authentication

pytest-routes provides flexible authentication support for testing protected API endpoints.

```{contents}
:local:
:depth: 2
```

---

## Overview

Many APIs require authentication. pytest-routes supports:

- **Bearer Token Authentication** - JWT tokens, OAuth2 access tokens
- **API Key Authentication** - Header or query parameter-based keys
- **Composite Authentication** - Multiple auth methods combined
- **Per-Route Overrides** - Different auth for different routes

---

## Quick Start

### Bearer Token (Most Common)

```toml
# pyproject.toml
[tool.pytest-routes.auth]
bearer_token = "$API_TOKEN"  # Read from environment variable
```

```bash
# Set the environment variable and run tests
API_TOKEN=your-secret-token pytest --routes --routes-app myapp:app
```

### API Key

```toml
# pyproject.toml
[tool.pytest-routes.auth]
api_key = "$API_KEY"
header_name = "X-API-Key"
```

---

## Authentication Providers

### BearerTokenAuth

Adds an `Authorization: Bearer <token>` header to all requests.

**Configuration:**

```toml
[tool.pytest-routes.auth]
bearer_token = "your-token"

# Or from environment variable (recommended)
bearer_token = "$API_TOKEN"
```

**Programmatic Usage:**

```python
# conftest.py
import pytest
from pytest_routes import RouteTestConfig, BearerTokenAuth

@pytest.fixture
def routes_config():
    return RouteTestConfig(
        auth=BearerTokenAuth("your-secret-token"),
        max_examples=50,
    )
```

### APIKeyAuth

Sends an API key via header or query parameter.

**Header-based (default):**

```toml
[tool.pytest-routes.auth]
api_key = "$API_KEY"
header_name = "X-API-Key"  # Optional, defaults to X-API-Key
```

**Query parameter-based:**

```toml
[tool.pytest-routes.auth]
api_key = "$API_KEY"
query_param = "api_key"
```

**Programmatic Usage:**

```python
from pytest_routes import RouteTestConfig, APIKeyAuth

# Header-based
config = RouteTestConfig(
    auth=APIKeyAuth("my-api-key", header_name="X-API-Key"),
)

# Query parameter-based
config = RouteTestConfig(
    auth=APIKeyAuth("my-api-key", query_param="api_key"),
)
```

### CompositeAuth

Combine multiple authentication methods (e.g., Bearer token + tenant ID).

```python
# conftest.py
from pytest_routes import RouteTestConfig, BearerTokenAuth, APIKeyAuth, CompositeAuth

@pytest.fixture
def routes_config():
    return RouteTestConfig(
        auth=CompositeAuth([
            BearerTokenAuth("$JWT_TOKEN"),
            APIKeyAuth("tenant-123", header_name="X-Tenant-ID"),
        ]),
    )
```

This sends both:
- `Authorization: Bearer <token>`
- `X-Tenant-ID: tenant-123`

### NoAuth

Explicitly disable authentication (useful for overrides).

```python
from pytest_routes import RouteTestConfig, NoAuth

config = RouteTestConfig(auth=NoAuth())
```

---

## Environment Variables

Authentication tokens should **never** be hardcoded. Use environment variables:

```toml
[tool.pytest-routes.auth]
bearer_token = "$API_TOKEN"  # Reads from API_TOKEN env var
```

The `$` prefix tells pytest-routes to read from the environment.

**Example workflow:**

```bash
# Local development
export API_TOKEN=$(vault read -field=token secret/api)
pytest --routes

# CI/CD (GitHub Actions)
# Use repository secrets
```

```yaml
# .github/workflows/test.yml
env:
  API_TOKEN: ${{ secrets.API_TOKEN }}

steps:
  - run: pytest --routes --routes-app myapp:app
```

---

## Per-Route Overrides

Different routes may require different authentication. Use route overrides:

```toml
# pyproject.toml

# Default auth for most routes
[tool.pytest-routes.auth]
bearer_token = "$USER_TOKEN"

# Admin routes need admin credentials
[[tool.pytest-routes.routes]]
pattern = "/admin/*"
[tool.pytest-routes.routes.auth]
bearer_token = "$ADMIN_TOKEN"

# Public routes - skip auth
[[tool.pytest-routes.routes]]
pattern = "/public/*"
# No auth section = no authentication

# Internal routes - skip testing entirely
[[tool.pytest-routes.routes]]
pattern = "/internal/*"
skip = true
```

### Override Priority

1. Route-specific override (if pattern matches)
2. Global `[tool.pytest-routes.auth]`
3. No authentication

---

## Pytest Markers

Use markers for test-level authentication control:

### @pytest.mark.routes_skip

Skip route smoke testing for specific tests:

```python
import pytest

@pytest.mark.routes_skip(reason="Requires external service")
def test_external_integration():
    ...
```

### @pytest.mark.routes_auth

Specify authentication for specific tests:

```python
import pytest
from pytest_routes import BearerTokenAuth

@pytest.mark.routes_auth(BearerTokenAuth("special-token"))
def test_special_endpoint():
    ...
```

---

## Example: Testing an Authenticated API

Here's a complete example of testing a Litestar API with authentication:

**Application (`app.py`):**

```python
from litestar import Litestar, get
from litestar.middleware import AuthenticationMiddleware

@get("/public")
async def public_endpoint() -> dict:
    return {"message": "Public data"}

@get("/protected", guards=[require_auth])
async def protected_endpoint() -> dict:
    return {"message": "Protected data"}

@get("/admin", guards=[require_admin])
async def admin_endpoint() -> dict:
    return {"message": "Admin data"}

app = Litestar(
    route_handlers=[public_endpoint, protected_endpoint, admin_endpoint],
    middleware=[AuthenticationMiddleware],
)
```

**Configuration (`pyproject.toml`):**

```toml
[tool.pytest-routes]
app = "app:app"
max_examples = 50
exclude = ["/health", "/docs"]

# Default auth for protected routes
[tool.pytest-routes.auth]
bearer_token = "$USER_TOKEN"

# Admin routes need elevated privileges
[[tool.pytest-routes.routes]]
pattern = "/admin*"
[tool.pytest-routes.routes.auth]
bearer_token = "$ADMIN_TOKEN"

# Public routes - no auth needed
[[tool.pytest-routes.routes]]
pattern = "/public*"
# Omit auth = no authentication sent
```

**Running Tests:**

```bash
export USER_TOKEN=user-jwt-token
export ADMIN_TOKEN=admin-jwt-token
pytest --routes -v
```

---

## Troubleshooting

### 401 Unauthorized Errors

1. **Check token is set:**
   ```bash
   echo $API_TOKEN  # Should not be empty
   ```

2. **Verify auth header is sent:**
   ```bash
   pytest --routes --routes-verbose
   ```

3. **Check route pattern matching:**
   Route overrides use glob patterns - ensure your pattern matches.

### Environment Variable Not Found

If you see `ValueError: Environment variable 'X' is not set`:

1. Ensure the variable is exported: `export API_TOKEN=...`
2. Check for typos in the variable name
3. In CI, verify secrets are configured

### Wrong Auth for Route

Check route override patterns:

```toml
# Patterns are matched in order - first match wins
[[tool.pytest-routes.routes]]
pattern = "/api/v1/*"  # Matches /api/v1/users

[[tool.pytest-routes.routes]]
pattern = "/api/*"     # Would NOT match /api/v1/users if above matches first
```

---

## API Reference

See the [API documentation](../api/auth.md) for complete details on:

- `AuthProvider` - Base class for custom providers
- `BearerTokenAuth` - Bearer token implementation
- `APIKeyAuth` - API key implementation
- `CompositeAuth` - Combine multiple providers
- `NoAuth` - Explicit no-auth provider
