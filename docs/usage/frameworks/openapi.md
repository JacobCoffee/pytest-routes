# OpenAPI Fallback

If framework-specific extraction fails, pytest-routes falls back to OpenAPI
schema extraction. This works with any ASGI framework that exposes an OpenAPI
schema.

## Features

- Schema-based route discovery
- Request body extraction from schema definitions
- Response schema validation (optional)
- Support for `$ref` schema references

## Usage

OpenAPI extraction is automatic when:
1. Framework-specific extraction fails or is unavailable
2. The app exposes an OpenAPI schema at `/openapi.json`, `/openapi.yaml`, or similar

## Manual Configuration

```toml
# pyproject.toml
[tool.pytest-routes]
framework = "openapi"
openapi_path = "/api/openapi.json"  # Custom schema path
```

## When to Use OpenAPI Extraction

```{tip}
**Use OpenAPI extraction when:**
- Your framework isn't directly supported
- You want schema-based validation
- Type extraction from code isn't working
```

```{warning}
**OpenAPI extraction requires a valid schema.** Make sure your app
generates an OpenAPI schema before running tests.
```
