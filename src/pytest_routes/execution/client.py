"""ASGI test client wrapper."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from httpx import ASGITransport, AsyncClient

if TYPE_CHECKING:
    from httpx import Response


class RouteTestClient:
    """Async test client for ASGI applications."""

    def __init__(self, app: Any, base_url: str = "http://test") -> None:
        """Initialize test client.

        Args:
            app: The ASGI application.
            base_url: Base URL for requests.
        """
        self.app = app
        self.base_url = base_url
        self.transport = ASGITransport(app=app)

    async def request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json: Any = None,
        headers: dict[str, str] | None = None,
        timeout: float = 30.0,
    ) -> Response:
        """Make an HTTP request to the ASGI app.

        Args:
            method: HTTP method.
            path: Request path.
            params: Query parameters.
            json: JSON body.
            headers: Request headers.
            timeout: Request timeout in seconds.

        Returns:
            The HTTP response.
        """
        async with AsyncClient(transport=self.transport, base_url=self.base_url, timeout=timeout) as client:
            return await client.request(
                method=method,
                url=path,
                params=params,
                json=json,
                headers=headers or {},
            )

    async def get(self, path: str, **kwargs: Any) -> Response:
        """Make a GET request."""
        return await self.request("GET", path, **kwargs)

    async def post(self, path: str, **kwargs: Any) -> Response:
        """Make a POST request."""
        return await self.request("POST", path, **kwargs)

    async def put(self, path: str, **kwargs: Any) -> Response:
        """Make a PUT request."""
        return await self.request("PUT", path, **kwargs)

    async def patch(self, path: str, **kwargs: Any) -> Response:
        """Make a PATCH request."""
        return await self.request("PATCH", path, **kwargs)

    async def delete(self, path: str, **kwargs: Any) -> Response:
        """Make a DELETE request."""
        return await self.request("DELETE", path, **kwargs)
