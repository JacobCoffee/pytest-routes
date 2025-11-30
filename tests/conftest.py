"""Shared test fixtures."""

from __future__ import annotations

import pytest


@pytest.fixture
def litestar_app():
    """Create a sample Litestar application for testing."""
    try:
        from litestar import Litestar, get, post

        @get("/")
        async def root() -> dict:
            return {"message": "Hello"}

        @get("/users/{user_id:int}")
        async def get_user(user_id: int) -> dict:
            return {"id": user_id}

        @post("/users")
        async def create_user(data: dict) -> dict:
            return {"created": True, **data}

        @get("/health")
        async def health() -> dict:
            return {"status": "ok"}

        @get("/items/{item_id:int}")
        async def get_item(item_id: int, q: str | None = None) -> dict:
            return {"item_id": item_id, "query": q}

        return Litestar(route_handlers=[root, get_user, create_user, health, get_item])
    except ImportError:
        pytest.skip("Litestar not installed")


@pytest.fixture
def litestar_app_with_errors():
    """Create a Litestar app that includes error routes for testing."""
    try:
        from litestar import Litestar, get

        @get("/")
        async def root() -> dict:
            return {"message": "Hello"}

        @get("/error")
        async def error_route() -> dict:
            raise ValueError("Test error")

        @get("/users/{user_id:int}")
        async def get_user(user_id: int) -> dict:
            return {"id": user_id}

        @get("/health")
        async def health() -> dict:
            return {"status": "ok"}

        return Litestar(route_handlers=[root, error_route, get_user, health])
    except ImportError:
        pytest.skip("Litestar not installed")


@pytest.fixture
def fastapi_app():
    """Create a sample FastAPI application for testing."""
    try:
        from fastapi import FastAPI

        app = FastAPI()

        @app.get("/")
        async def root():
            return {"message": "Hello"}

        @app.get("/users/{user_id}")
        async def get_user(user_id: int):
            return {"id": user_id}

        @app.post("/users")
        async def create_user(data: dict):
            return {"created": True, **data}

        @app.get("/items/{item_id}")
        async def get_item(item_id: int, q: str | None = None):
            return {"item_id": item_id, "query": q}

        return app
    except ImportError:
        pytest.skip("FastAPI not installed")


@pytest.fixture
def starlette_app():
    """Create a sample Starlette application for testing."""
    try:
        from starlette.applications import Starlette
        from starlette.responses import JSONResponse
        from starlette.routing import Route

        async def root(request):
            return JSONResponse({"message": "Hello"})

        async def get_user(request):
            user_id = request.path_params["user_id"]
            return JSONResponse({"id": user_id})

        async def get_item(request):
            item_id = request.path_params["item_id"]
            q = request.query_params.get("q")
            return JSONResponse({"item_id": item_id, "query": q})

        routes = [
            Route("/", root),
            Route("/users/{user_id:int}", get_user),
            Route("/items/{item_id:int}", get_item),
        ]

        return Starlette(routes=routes)
    except ImportError:
        pytest.skip("Starlette not installed")
