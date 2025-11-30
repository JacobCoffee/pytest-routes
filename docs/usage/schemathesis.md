# Schemathesis Integration

pytest-routes integrates with [Schemathesis](https://schemathesis.readthedocs.io/) to provide
OpenAPI contract testing capabilities. This allows you to validate that your API responses
conform to your OpenAPI schema specification.

```{contents}
:local:
:depth: 2
```

---

## Installation

Schemathesis is an optional dependency. Install it with:

```bash
pip install pytest-routes[schemathesis]

# Or with uv
uv add "pytest-routes[schemathesis]"
```

---

## Quick Start

Enable Schemathesis validation with the `--routes-schemathesis` flag:

```bash
pytest --routes --routes-app myapp:app --routes-schemathesis
```

This will:
1. Load your OpenAPI schema from `/openapi.json` (configurable)
2. Validate all responses against the schema
3. Report any conformance violations

---

## Configuration

### CLI Options

| Option | Default | Description |
|--------|---------|-------------|
| `--routes-schemathesis` | `false` | Enable Schemathesis validation |
| `--routes-schemathesis-schema-path` | `/openapi.json` | Path to OpenAPI schema endpoint |

### pyproject.toml Configuration

```toml
[tool.pytest-routes.schemathesis]
enabled = true
schema_path = "/openapi.json"
validate_responses = true
stateful = "none"  # or "links" for stateful testing
checks = [
    "status_code_conformance",
    "content_type_conformance",
    "response_schema_conformance",
]
```

---

## What Gets Validated

When Schemathesis is enabled, it validates:

### Status Code Conformance

Ensures that the response status code is one of the documented status codes in your
OpenAPI schema for that endpoint.

```yaml
# OpenAPI schema
paths:
  /users:
    get:
      responses:
        200:
          description: Success
        404:
          description: Not found
```

If the endpoint returns a `500` status code, the validation fails because it's not
documented in the schema.

### Content-Type Conformance

Ensures that the response `Content-Type` header matches what's documented in the schema.

```yaml
# OpenAPI schema
paths:
  /users:
    get:
      responses:
        200:
          content:
            application/json:
              schema:
                type: array
```

If the endpoint returns `text/plain` instead of `application/json`, the validation fails.

### Response Schema Conformance

Validates that the response body structure matches the JSON Schema defined in your
OpenAPI specification.

```yaml
# OpenAPI schema
components:
  schemas:
    User:
      type: object
      required:
        - id
        - name
      properties:
        id:
          type: integer
        name:
          type: string
        email:
          type: string
```

If a response is missing the required `id` field, the validation fails.

---

## Framework-Specific Schema Paths

Different frameworks expose OpenAPI schemas at different paths:

### Litestar

```bash
# Default Litestar schema path
pytest --routes --routes-app myapp:app --routes-schemathesis \
    --routes-schemathesis-schema-path /schema/openapi.json
```

### FastAPI

```bash
# Default FastAPI schema path
pytest --routes --routes-app myapp:app --routes-schemathesis \
    --routes-schemathesis-schema-path /openapi.json
```

### Starlette

Starlette doesn't have built-in OpenAPI support. You'll need to use a library like
`starlette-openapi` and configure the schema path accordingly.

---

## Programmatic Usage

You can also use the Schemathesis integration programmatically:

```python
from pytest_routes.integrations import SchemathesisAdapter, SchemathesisValidator

# Create the adapter
adapter = SchemathesisAdapter(
    app=your_app,
    schema_path="/openapi.json",
    validate_responses=True,
    checks=[
        "status_code_conformance",
        "content_type_conformance",
        "response_schema_conformance",
    ],
)

# Check if Schemathesis is available
if adapter.available:
    # Load the schema
    schema = adapter.load_schema()

    # Create a validator
    validator = SchemathesisValidator(adapter, strict=True)

    # Validate a response
    result = validator.validate(response, route)
    if not result.valid:
        print(f"Validation errors: {result.errors}")
```

---

## Troubleshooting

### Schema Not Found

```
RuntimeError: Failed to load OpenAPI schema from /openapi.json
```

**Solution:** Ensure your application serves an OpenAPI schema at the configured path.
Check your framework's documentation for how to enable OpenAPI schema generation.

### Schemathesis Not Installed

```
ImportError: Schemathesis is not installed. Install with: pip install pytest-routes[schemathesis]
```

**Solution:** Install the Schemathesis optional dependency:

```bash
pip install pytest-routes[schemathesis]
```

### Validation Failures

When Schemathesis reports validation failures, it means your API response doesn't match
your OpenAPI schema. Common causes:

1. **Missing fields:** Required fields not included in response
2. **Wrong types:** Field types don't match schema (e.g., string instead of integer)
3. **Undocumented status codes:** Response status code not in schema
4. **Wrong content type:** Response Content-Type doesn't match schema

---

## Best Practices

1. **Keep your OpenAPI schema up to date** - Schemathesis validates against your schema,
   so outdated schemas will cause false positives/negatives.

2. **Document all status codes** - Include error responses (4xx, 5xx) in your schema
   to avoid validation failures for legitimate error responses.

3. **Use strict validation in CI** - Enable Schemathesis in CI pipelines to catch
   schema drift early.

4. **Start with basic checks** - Begin with `status_code_conformance` and add more
   checks as your schema matures.

---

## See Also

- [CLI Options Reference](cli-options.md) - All command-line options
- [Configuration](configuration.md) - pyproject.toml configuration
- [Schemathesis Documentation](https://schemathesis.readthedocs.io/) - Full Schemathesis docs
