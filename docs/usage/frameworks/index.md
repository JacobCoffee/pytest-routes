# Framework Support

pytest-routes works with any ASGI framework. Each framework has a dedicated
extractor that understands its routing patterns.

```{toctree}
:maxdepth: 1

litestar
fastapi
starlette
openapi
```

---

## Framework Comparison

```{list-table} Feature Support by Framework
:header-rows: 1
:widths: 25 25 25 25

* - Feature
  - Litestar
  - FastAPI
  - Starlette
* - Path parameters
  - Full type extraction
  - Full type extraction
  - Full type extraction
* - Query parameters
  - Full type extraction
  - Full type extraction
  - Limited (no types)
* - Request bodies
  - Full (Pydantic, dataclasses)
  - Full (Pydantic)
  - Limited (manual)
* - Handler metadata
  - Full (tags, deprecated)
  - Partial
  - Limited
* - OpenAPI schema
  - Built-in
  - Built-in
  - Manual setup
* - Status
  - First-class support
  - Fully supported
  - Fully supported
```

---

## Framework Auto-Detection

pytest-routes automatically detects your framework based on the application class:

```python
def get_extractor(app: Any) -> RouteExtractor:
    """Get the appropriate extractor for an app."""

    # Check for Litestar
    if hasattr(app, "__class__") and app.__class__.__name__ == "Litestar":
        return LitestarExtractor()

    # Check for Starlette/FastAPI (FastAPI is a Starlette subclass)
    if hasattr(app, "routes") and hasattr(app, "middleware_stack"):
        return StarletteExtractor()

    # Fall back to OpenAPI
    return OpenAPIExtractor()
```

Override auto-detection when needed:

```toml
[tool.pytest-routes]
# Force a specific extractor
framework = "litestar"  # or "fastapi", "starlette", "openapi"
```

---

## Custom Extractors

Create custom extractors for unsupported frameworks:

```python
# myapp/extractor.py
from typing import Any
from pytest_routes.discovery.base import RouteExtractor, RouteInfo

class MyFrameworkExtractor(RouteExtractor):
    """Custom extractor for MyFramework."""

    def supports(self, app: Any) -> bool:
        """Check if this extractor supports the given app."""
        return isinstance(app, MyFramework)

    def extract_routes(self, app: Any) -> list[RouteInfo]:
        """Extract routes from a MyFramework application."""
        routes = []

        for route in app.get_routes():
            routes.append(RouteInfo(
                path=route.path,
                methods=route.methods,
                name=route.name,
                handler=route.handler,
                path_params=self._extract_path_params(route),
                query_params=self._extract_query_params(route),
                body_type=self._extract_body_type(route),
            ))

        return routes
```

---

## Troubleshooting

### Routes Not Discovered

**Symptom:** pytest-routes reports 0 routes found.

**Solutions:**

1. **Verify app import path:**
   ```bash
   python -c "from myapp.main import app; print(app)"
   ```

2. **Check routes are registered before app creation**

3. **Try explicit framework hint:**
   ```bash
   pytest --routes --routes-app myapp:app --routes-framework litestar
   ```

### Type Extraction Fails

**Symptom:** Parameters generate as strings instead of proper types.

**Solutions:**

1. Add type hints to handlers
2. Use proper Pydantic/dataclass models
3. Register custom strategies for custom types

### Authentication Errors

**Symptom:** Routes return 401/403 during smoke tests.

**Solutions:**

1. Exclude auth routes: `--routes-exclude "/auth/*"`
2. Configure test authentication in fixture
3. Accept auth failures: `allowed_status_codes = [200, 401, 403]`
