# Starlette

**Status:** Fully supported

[Starlette](https://www.starlette.io/) is the base ASGI framework that FastAPI
builds upon.

## Installation

::::{tab-set}

:::{tab-item} pip
```bash
pip install "pytest-routes[starlette]"
```
:::

:::{tab-item} uv
```bash
uv add "pytest-routes[starlette]"
```
:::

::::

## Features

- Route extraction from `app.routes`
- Path parameter extraction from URL patterns (`:int`, `:str`, `:uuid`, etc.)
- Support for `Route`, `Mount`, and `Router` classes
- Endpoint function introspection

## Complete Example

```python
# myapp/main.py
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route, Mount

async def homepage(request: Request) -> JSONResponse:
    return JSONResponse({"message": "Welcome to the API"})

async def list_users(request: Request) -> JSONResponse:
    limit = int(request.query_params.get("limit", 10))
    offset = int(request.query_params.get("offset", 0))
    return JSONResponse({"users": [], "limit": limit, "offset": offset})

async def get_user(request: Request) -> JSONResponse:
    user_id = request.path_params["user_id"]
    return JSONResponse({"id": user_id, "name": "Test User"})

async def create_user(request: Request) -> JSONResponse:
    body = await request.json()
    return JSONResponse({"id": 1, "name": body.get("name")}, status_code=201)

async def update_user(request: Request) -> JSONResponse:
    user_id = request.path_params["user_id"]
    body = await request.json()
    return JSONResponse({"id": user_id, "name": body.get("name", "Updated")})

async def delete_user(request: Request) -> JSONResponse:
    return JSONResponse(None, status_code=204)

routes = [
    Route("/", homepage, methods=["GET"]),
    Mount("/api", routes=[
        Route("/users", list_users, methods=["GET"]),
        Route("/users", create_user, methods=["POST"]),
        Route("/users/{user_id:int}", get_user, methods=["GET"]),
        Route("/users/{user_id:int}", update_user, methods=["PUT"]),
        Route("/users/{user_id:int}", delete_user, methods=["DELETE"]),
    ]),
]

app = Starlette(routes=routes, debug=True)
```

## Running Tests

```bash
# Basic smoke test
pytest --routes --routes-app myapp.main:app

# Include the root route
pytest --routes --routes-app myapp.main:app --routes-include "/*,/api/*"
```

## Tips

```{tip}
**Use path converters** like `{user_id:int}` for proper type extraction.
Without converters, parameters are treated as strings.
```

```{tip}
**Mount provides route grouping.** Routes under a `Mount` are discovered
with the mount path prefix.
```

```{warning}
**Query params have limited type info.** Starlette doesn't expose query
parameter types, so pytest-routes generates strings by default.
```

## Available Path Converters

```{list-table}
:header-rows: 1
:widths: 20 40 40

* - Converter
  - Pattern
  - Generated Strategy
* - `:str`
  - `{name:str}`
  - Random strings
* - `:int`
  - `{id:int}`
  - Random integers
* - `:float`
  - `{value:float}`
  - Random floats
* - `:uuid`
  - `{uuid:uuid}`
  - Random UUIDs
* - `:path`
  - `{path:path}`
  - Random path-like strings
```
