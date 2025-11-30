# Query Parameter Extraction Implementation

This document describes the implementation of query parameter extraction for all framework extractors in pytest-routes.

## Overview

Query parameter extraction allows pytest-routes to automatically discover and validate query parameters from ASGI application routes. This is essential for property-based testing, as it enables the framework to generate valid query parameters for each route.

## Implementation Details

### 1. LitestarExtractor (`src/pytest_routes/discovery/litestar.py`)

**Changes:**
- Implemented `_extract_query_params()` method
- Uses `inspect.signature()` to analyze handler function parameters
- Extracts type hints using `get_type_hints()`
- Filters out:
  - Path parameters (from route definition)
  - Request body parameter (`data`)
  - Special parameters (`self`, `cls`, `scope`)
  - Litestar dependency injection types (`Request`, `State`, `ASGIConnection`)
- Handles `Optional` types by extracting the non-None type
- Defaults to `str` type when type hints are unavailable

**Example:**
```python
@get("/items/{item_id:int}")
async def get_item(item_id: int, q: str | None = None) -> dict:
    return {"item_id": item_id, "query": q}

# Extracted query_params: {'q': <class 'str'>}
```

### 2. StarletteExtractor (`src/pytest_routes/discovery/starlette.py`)

**Changes:**
- Implemented `_extract_query_params()` method
- Uses `inspect.signature()` and `get_type_hints()` to analyze endpoint parameters
- Filters out:
  - Path parameters
  - Request body parameter (`data`)
  - Framework parameters (`request`, `response`, `websocket`, `background_tasks`)
  - ASGI types (`Request`, `WebSocket`, `HTTPConnection`, `Response`)
  - Pydantic `BaseModel` subclasses (FastAPI request bodies)
  - FastAPI parameter annotations (`FieldInfo`, `Body`, `File`, `Form`)
- Handles both Starlette and FastAPI applications
- Handles `Optional` types by extracting the non-None type

**Example (FastAPI):**
```python
@app.get("/items/{item_id}")
async def get_item(item_id: int, q: str | None = None):
    return {"item_id": item_id, "query": q}

# Extracted query_params: {'q': <class 'str'>}
```

**Example (Starlette):**
```python
async def get_item(request):
    item_id = request.path_params["item_id"]
    q = request.query_params.get("q")
    return JSONResponse({"item_id": item_id, "query": q})

# Extracted query_params: {} (no type hints available)
```

### 3. OpenAPIExtractor (`src/pytest_routes/discovery/openapi.py`)

**Status:** Already implemented correctly
- Uses `_extract_params(operation, "query")` to extract query parameters from OpenAPI schema
- Converts JSON schema types to Python types
- Works with both Litestar and FastAPI OpenAPI schemas

## Type Handling

All extractors handle the following type scenarios:

1. **Typed parameters:** `q: str` → `{'q': str}`
2. **Optional parameters:** `q: str | None` → `{'q': str}`
3. **Union types:** `typing.Union[str, None]` → `{'q': str}`
4. **Untyped parameters:** Default to `str` type

## Filter Rules

Parameters are excluded from query_params if they are:

### Common to all frameworks:
- Path parameters (extracted separately)
- Request body parameters (named `data`)
- Class method parameters (`self`, `cls`)

### Litestar-specific:
- Dependency injection parameters (`Request`, `State`, `ASGIConnection`, `Scope`)
- Internal parameter `scope`

### Starlette/FastAPI-specific:
- Framework parameters (`request`, `response`, `websocket`, `background_tasks`)
- ASGI types (`Request`, `WebSocket`, `HTTPConnection`, `Response`)
- Pydantic models (FastAPI request bodies)
- FastAPI parameter annotations (`Body()`, `File()`, `Form()`)

## Test Coverage

Comprehensive tests added in `tests/test_query_params.py`:

- Query parameter extraction for Litestar
- Query parameter extraction for Starlette
- Query parameter extraction for FastAPI
- Query parameter extraction via OpenAPI
- Verification that path params are not confused with query params
- Verification that routes without query params return empty dict

Test fixtures updated in `tests/conftest.py` to include routes with query parameters.

## Code Quality

- All code passes `ruff` linting
- All code passes `ty` type checking
- All code is properly formatted with `ruff format`
- Complexity warnings suppressed with rationale (multiple edge cases to handle)
- Exception handling documented with comments

## Usage

```python
from pytest_routes.discovery import get_extractor

extractor = get_extractor(app)
routes = extractor.extract_routes(app)

for route in routes:
    print(f"{route.path}: {route.query_params}")
```

## Future Enhancements

Potential improvements for future iterations:

1. **Litestar `Query` parameter detection:** Detect parameters explicitly marked with `litestar.params.Query`
2. **FastAPI `Query` parameter metadata:** Extract constraints from `Query(...)` annotations
3. **Default value extraction:** Capture default values for optional query parameters
4. **Validation rules:** Extract validation constraints (min, max, pattern, etc.)
5. **Documentation extraction:** Parse docstrings for query parameter descriptions
