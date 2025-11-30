# Litestar

**Status:** First-class support

[Litestar](https://litestar.dev/) is the primary supported framework with full
type extraction from route handlers.

---

## Installation

::::{tab-set}

:::{tab-item} uv (recommended)
```bash
uv add "pytest-routes[litestar]"
```
:::

:::{tab-item} pip
```bash
pip install "pytest-routes[litestar]"
```
:::

::::

---

## Features

- Full path parameter type extraction from route definitions
- Query parameter extraction from handler signatures with types
- Request body type extraction (Pydantic models, dataclasses, TypedDicts)
- Handler metadata (tags, deprecated, description)
- OpenAPI schema fallback for edge cases

---

## Complete Example

```python
# myapp/main.py
from dataclasses import dataclass
from uuid import UUID

from litestar import Litestar, Controller, get, post, put, delete

@dataclass
class User:
    """User model with validation."""
    id: UUID
    name: str
    email: str
    is_active: bool = True

@dataclass
class CreateUser:
    """Input model for creating users."""
    name: str
    email: str

@dataclass
class UpdateUser:
    """Input model for updating users."""
    name: str | None = None
    email: str | None = None
    is_active: bool | None = None

class UserController(Controller):
    """User management endpoints."""

    path = "/users"
    tags = ["users"]

    @get("/")
    async def list_users(
        self,
        limit: int = 10,
        offset: int = 0,
        active_only: bool = False
    ) -> list[User]:
        """List all users with pagination."""
        return []

    @get("/{user_id:uuid}")
    async def get_user(self, user_id: UUID) -> User:
        """Get a specific user by ID."""
        return User(id=user_id, name="Test", email="test@example.com")

    @post("/")
    async def create_user(self, data: CreateUser) -> User:
        """Create a new user."""
        return User(id=UUID("..."), name=data.name, email=data.email)

    @put("/{user_id:uuid}")
    async def update_user(self, user_id: UUID, data: UpdateUser) -> User:
        """Update an existing user."""
        return User(id=user_id, name="Updated", email="updated@example.com")

    @delete("/{user_id:uuid}")
    async def delete_user(self, user_id: UUID) -> None:
        """Delete a user."""
        pass

app = Litestar(route_handlers=[UserController], debug=True)
```

---

## Running Tests

```bash
# Basic smoke test
pytest --routes --routes-app myapp.main:app

# With verbose output
pytest --routes --routes-app myapp.main:app -v

# Test only user endpoints
pytest --routes --routes-app myapp.main:app --routes-include "/users/*"
```

---

## What pytest-routes Extracts

For the example above, pytest-routes discovers:

```
GET  /users/              params: limit(int), offset(int), active_only(bool)
GET  /users/{user_id}     params: user_id(UUID)
POST /users/              body: CreateUser
PUT  /users/{user_id}     params: user_id(UUID), body: UpdateUser
DELETE /users/{user_id}   params: user_id(UUID)
```

---

## Tips

```{tip}
**Use dataclasses or Pydantic models for best results.** pytest-routes can
generate valid test data for these automatically.
```

```{tip}
**Litestar's path parameter syntax** (`{user_id:uuid}`) is fully supported.
The type hint after `:` is used for strategy selection.
```

```{warning}
**Guards and middleware** are executed during smoke tests. If you have
authentication guards, either exclude those routes or configure test auth.
```

---

## Handling Authentication

```python
# conftest.py
import pytest

@pytest.fixture
def app():
    """Create app with test authentication."""
    from myapp.main import app
    from myapp.auth import TestAuthMiddleware

    app.middleware = [TestAuthMiddleware()]
    return app
```
