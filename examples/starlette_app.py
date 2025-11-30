"""Example Starlette application for pytest-routes demonstration."""

from __future__ import annotations

from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.routing import Route

# In-memory "database"
users_db: dict[int, dict] = {
    1: {"id": 1, "name": "Alice", "email": "alice@example.com"},
    2: {"id": 2, "name": "Bob", "email": "bob@example.com"},
}
next_id = 3


async def root(request: Request) -> JSONResponse:
    """Root endpoint."""
    return JSONResponse({"message": "Welcome to the pytest-routes example API!"})


async def health(request: Request) -> JSONResponse:
    """Health check endpoint."""
    return JSONResponse({"status": "healthy"})


async def list_users(request: Request) -> JSONResponse:
    """List all users."""
    return JSONResponse(list(users_db.values()))


async def get_user(request: Request) -> JSONResponse:
    """Get a user by ID."""
    user_id = int(request.path_params["user_id"])
    if user_id not in users_db:
        return JSONResponse({"detail": f"User {user_id} not found"}, status_code=404)
    return JSONResponse(users_db[user_id])


async def create_user(request: Request) -> JSONResponse:
    """Create a new user."""
    global next_id
    data = await request.json()
    user = {"id": next_id, "name": data["name"], "email": data["email"]}
    users_db[next_id] = user
    next_id += 1
    return JSONResponse(user, status_code=201)


async def update_user(request: Request) -> JSONResponse:
    """Update a user."""
    user_id = int(request.path_params["user_id"])
    if user_id not in users_db:
        return JSONResponse({"detail": f"User {user_id} not found"}, status_code=404)

    data = await request.json()
    user = users_db[user_id]
    if "name" in data and data["name"] is not None:
        user["name"] = data["name"]
    if "email" in data and data["email"] is not None:
        user["email"] = data["email"]
    return JSONResponse(user)


async def delete_user(request: Request) -> Response:
    """Delete a user."""
    user_id = int(request.path_params["user_id"])
    if user_id not in users_db:
        return JSONResponse({"detail": f"User {user_id} not found"}, status_code=404)
    del users_db[user_id]
    return Response(status_code=204)


async def get_item(request: Request) -> JSONResponse:
    """Get an item with optional query parameter."""
    item_id = int(request.path_params["item_id"])
    q = request.query_params.get("q")
    return JSONResponse({"item_id": item_id, "query": q})


routes = [
    Route("/", root, methods=["GET"]),
    Route("/health", health, methods=["GET"]),
    Route("/users", list_users, methods=["GET"]),
    Route("/users", create_user, methods=["POST"]),
    Route("/users/{user_id:int}", get_user, methods=["GET"]),
    Route("/users/{user_id:int}", update_user, methods=["PATCH"]),
    Route("/users/{user_id:int}", delete_user, methods=["DELETE"]),
    Route("/items/{item_id:int}", get_item, methods=["GET"]),
]

app = Starlette(routes=routes, debug=True)
