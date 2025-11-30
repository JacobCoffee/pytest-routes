"""Example Litestar application for pytest-routes demonstration.

Includes both public and authenticated routes to demonstrate auth features.
Also includes WebSocket routes for v0.4.0 WebSocket testing demonstration.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from litestar import Controller, Litestar, delete, get, patch, post, websocket
from litestar.exceptions import NotAuthorizedException

if TYPE_CHECKING:
    from litestar.connection import ASGIConnection
    from litestar.handlers import BaseRouteHandler
    from litestar.channels import ChannelsPlugin


def require_auth(connection: ASGIConnection[Any, Any, Any], _: BaseRouteHandler) -> None:
    """Guard that requires a valid Authorization header."""
    auth_header = connection.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise NotAuthorizedException("Authentication required")


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


@get("/protected/profile", guards=[require_auth])
async def get_profile() -> dict:
    """Protected endpoint requiring Bearer token auth."""
    return {"message": "Authenticated!", "user": "demo-user"}


@get("/protected/data", guards=[require_auth])
async def get_protected_data() -> dict:
    """Another protected endpoint."""
    return {"data": [1, 2, 3], "protected": True}


# WebSocket routes for v0.4.0 demonstration
@websocket("/ws/echo")
async def ws_echo(socket: "litestar.WebSocket") -> None:
    """Echo WebSocket - sends back whatever it receives."""
    await socket.accept()
    try:
        while True:
            data = await socket.receive_text()
            await socket.send_text(f"Echo: {data}")
    except Exception:
        pass
    finally:
        await socket.close()


@websocket("/ws/chat/{room_id:str}")
async def ws_chat(socket: "litestar.WebSocket", room_id: str) -> None:
    """Chat room WebSocket with path parameter."""
    await socket.accept()
    await socket.send_json({"type": "joined", "room": room_id})
    try:
        while True:
            data = await socket.receive_json()
            response = {
                "type": "message",
                "room": room_id,
                "content": data.get("content", ""),
            }
            await socket.send_json(response)
    except Exception:
        pass
    finally:
        await socket.close()


@websocket("/ws/notifications")
async def ws_notifications(socket: "litestar.WebSocket") -> None:
    """Notifications WebSocket - server-push pattern."""
    await socket.accept()
    await socket.send_json({"type": "connected", "status": "ok"})
    try:
        while True:
            await socket.receive_text()
            await socket.send_json({"type": "notification", "message": "You have updates"})
    except Exception:
        pass
    finally:
        await socket.close()


# Import for WebSocket type hint
import litestar

app = Litestar(
    route_handlers=[
        root,
        health,
        UsersController,
        get_item,
        get_profile,
        get_protected_data,
        ws_echo,
        ws_chat,
        ws_notifications,
    ],
    debug=True,
)
