"""Example FastAPI application for pytest-routes demonstration.

Includes WebSocket routes for v0.4.0 WebSocket testing demonstration.
"""

from __future__ import annotations

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel

app = FastAPI(title="pytest-routes Example", version="0.1.0")


class User(BaseModel):
    """User model."""

    id: int
    name: str
    email: str


class CreateUser(BaseModel):
    """Create user request body."""

    name: str
    email: str


class UpdateUser(BaseModel):
    """Update user request body."""

    name: str | None = None
    email: str | None = None


# In-memory "database"
users_db: dict[int, User] = {
    1: User(id=1, name="Alice", email="alice@example.com"),
    2: User(id=2, name="Bob", email="bob@example.com"),
}
next_id = 3


@app.get("/")
async def root() -> dict[str, str]:
    """Root endpoint."""
    return {"message": "Welcome to the pytest-routes example API!"}


@app.get("/health")
async def health() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "healthy"}


@app.get("/users", tags=["users"])
async def list_users() -> list[User]:
    """List all users."""
    return list(users_db.values())


@app.get("/users/{user_id}", tags=["users"])
async def get_user(user_id: int) -> User:
    """Get a user by ID."""
    if user_id not in users_db:
        raise HTTPException(status_code=404, detail=f"User {user_id} not found")
    return users_db[user_id]


@app.post("/users", tags=["users"], status_code=201)
async def create_user(data: CreateUser) -> User:
    """Create a new user."""
    global next_id
    user = User(id=next_id, name=data.name, email=data.email)
    users_db[next_id] = user
    next_id += 1
    return user


@app.patch("/users/{user_id}", tags=["users"])
async def update_user(user_id: int, data: UpdateUser) -> User:
    """Update a user."""
    if user_id not in users_db:
        raise HTTPException(status_code=404, detail=f"User {user_id} not found")

    user = users_db[user_id]
    if data.name is not None:
        user.name = data.name
    if data.email is not None:
        user.email = data.email
    return user


@app.delete("/users/{user_id}", tags=["users"], status_code=204)
async def delete_user(user_id: int) -> None:
    """Delete a user."""
    if user_id not in users_db:
        raise HTTPException(status_code=404, detail=f"User {user_id} not found")
    del users_db[user_id]


@app.get("/items/{item_id}")
async def get_item(item_id: int, q: str | None = None) -> dict:
    """Get an item with optional query parameter."""
    return {"item_id": item_id, "query": q}


# WebSocket routes for v0.4.0 demonstration
@app.websocket("/ws/echo")
async def ws_echo(websocket: WebSocket) -> None:
    """Echo WebSocket - sends back whatever it receives."""
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_text()
            await websocket.send_text(f"Echo: {data}")
    except WebSocketDisconnect:
        pass


@app.websocket("/ws/chat/{room_id}")
async def ws_chat(websocket: WebSocket, room_id: str) -> None:
    """Chat room WebSocket with path parameter."""
    await websocket.accept()
    await websocket.send_json({"type": "joined", "room": room_id})
    try:
        while True:
            data = await websocket.receive_json()
            response = {
                "type": "message",
                "room": room_id,
                "content": data.get("content", ""),
            }
            await websocket.send_json(response)
    except WebSocketDisconnect:
        pass


@app.websocket("/ws/notifications")
async def ws_notifications(websocket: WebSocket) -> None:
    """Notifications WebSocket - server-push pattern."""
    await websocket.accept()
    await websocket.send_json({"type": "connected", "status": "ok"})
    try:
        while True:
            await websocket.receive_text()
            await websocket.send_json({"type": "notification", "message": "You have updates"})
    except WebSocketDisconnect:
        pass
