# FastAPI

**Status:** Fully supported (via Starlette extractor)

[FastAPI](https://fastapi.tiangolo.com/) is built on Starlette, so pytest-routes
uses the Starlette extractor with FastAPI-specific enhancements.

---

## Installation

::::{tab-set}

:::{tab-item} uv (recommended)
```bash
uv add "pytest-routes[fastapi]"
```
:::

:::{tab-item} pip
```bash
pip install "pytest-routes[fastapi]"
```
:::

::::

---

## Features

- Path parameter extraction from route patterns
- Query parameter extraction from endpoint signatures
- Pydantic model body extraction with full validation
- Automatic type inference from annotations
- Response model extraction for validation

---

## Complete Example

```python
# myapp/main.py
from uuid import UUID
from typing import Annotated

from fastapi import FastAPI, Query, Path, Body
from pydantic import BaseModel, EmailStr, Field

class UserBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    email: EmailStr

class UserCreate(UserBase):
    password: str = Field(..., min_length=8)

class UserUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=100)
    email: EmailStr | None = None
    is_active: bool | None = None

class User(UserBase):
    id: UUID
    is_active: bool = True

    class Config:
        from_attributes = True

app = FastAPI(title="User API", version="1.0.0")

@app.get("/users/", response_model=list[User], tags=["users"])
async def list_users(
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 10,
    active_only: Annotated[bool, Query()] = False,
) -> list[User]:
    """List all users with pagination."""
    return []

@app.get("/users/{user_id}", response_model=User, tags=["users"])
async def get_user(user_id: Annotated[UUID, Path()]) -> User:
    """Get a specific user by ID."""
    return User(id=user_id, name="Test", email="test@example.com")

@app.post("/users/", response_model=User, status_code=201, tags=["users"])
async def create_user(user: Annotated[UserCreate, Body()]) -> User:
    """Create a new user."""
    return User(id=UUID("12345678-1234-1234-1234-123456789012"),
                name=user.name, email=user.email)

@app.put("/users/{user_id}", response_model=User, tags=["users"])
async def update_user(
    user_id: Annotated[UUID, Path()],
    user: Annotated[UserUpdate, Body()],
) -> User:
    """Update an existing user."""
    return User(id=user_id, name=user.name or "Updated",
                email=user.email or "updated@example.com")

@app.delete("/users/{user_id}", status_code=204, tags=["users"])
async def delete_user(user_id: Annotated[UUID, Path()]) -> None:
    """Delete a user."""
    pass
```

---

## Running Tests

```bash
# Basic smoke test
pytest --routes --routes-app myapp.main:app

# Test with more examples
pytest --routes --routes-app myapp.main:app --routes-max-examples 200

# Test only GET endpoints (safe for real data)
pytest --routes --routes-app myapp.main:app --routes-methods GET
```

---

## Tips

```{tip}
**Use Pydantic models with constraints.** FastAPI's `Field()` constraints
(min_length, ge, le, etc.) help pytest-routes generate valid data.
```

```{tip}
**Annotated types are fully supported.** Use `Annotated[int, Query(ge=0)]`
for better documentation and constraint extraction.
```

```{warning}
**Dependency injection is not automatically invoked.** For routes with complex
dependencies (database sessions, auth), configure overrides in your test fixture.
```

---

## Handling Dependencies

```python
# conftest.py
import pytest

@pytest.fixture
def app():
    """Create app with dependency overrides."""
    from myapp.main import app
    from myapp.deps import get_db, get_current_user
    from myapp.testing import TestDatabase, TestUser

    app.dependency_overrides[get_db] = lambda: TestDatabase()
    app.dependency_overrides[get_current_user] = lambda: TestUser()

    yield app

    app.dependency_overrides.clear()
```
