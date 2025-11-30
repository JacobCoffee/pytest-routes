"""Example Litestar application for pytest-routes demonstration."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from litestar import Controller, Litestar, delete, get, patch, post

if TYPE_CHECKING:
    pass


@dataclass
class User:
    """User model."""

    id: int
    name: str
    email: str


@dataclass
class CreateUser:
    """Create user request body."""

    name: str
    email: str


@dataclass
class UpdateUser:
    """Update user request body."""

    name: str | None = None
    email: str | None = None


# In-memory "database"
users_db: dict[int, User] = {
    1: User(id=1, name="Alice", email="alice@example.com"),
    2: User(id=2, name="Bob", email="bob@example.com"),
}
next_id = 3


@get("/")
async def root() -> dict[str, str]:
    """Root endpoint."""
    return {"message": "Welcome to the pytest-routes example API!"}


@get("/health")
async def health() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "healthy"}


class UsersController(Controller):
    """Users resource controller."""

    path = "/users"
    tags = ["users"]

    @get("/")
    async def list_users(self) -> list[User]:
        """List all users."""
        return list(users_db.values())

    @get("/{user_id:int}")
    async def get_user(self, user_id: int) -> User:
        """Get a user by ID."""
        if user_id not in users_db:
            from litestar.exceptions import NotFoundException

            raise NotFoundException(f"User {user_id} not found")
        return users_db[user_id]

    @post("/")
    async def create_user(self, data: CreateUser) -> User:
        """Create a new user."""
        global next_id
        user = User(id=next_id, name=data.name, email=data.email)
        users_db[next_id] = user
        next_id += 1
        return user

    @patch("/{user_id:int}")
    async def update_user(self, user_id: int, data: UpdateUser) -> User:
        """Update a user."""
        if user_id not in users_db:
            from litestar.exceptions import NotFoundException

            raise NotFoundException(f"User {user_id} not found")

        user = users_db[user_id]
        if data.name is not None:
            user.name = data.name
        if data.email is not None:
            user.email = data.email
        return user

    @delete("/{user_id:int}")
    async def delete_user(self, user_id: int) -> None:
        """Delete a user."""
        if user_id not in users_db:
            from litestar.exceptions import NotFoundException

            raise NotFoundException(f"User {user_id} not found")
        del users_db[user_id]


@get("/items/{item_id:int}")
async def get_item(item_id: int, q: str | None = None) -> dict:
    """Get an item with optional query parameter."""
    return {"item_id": item_id, "query": q}


app = Litestar(
    route_handlers=[root, health, UsersController, get_item],
    debug=True,
)
