"""Route discovery from ASGI applications."""

from __future__ import annotations

from typing import Any

from pytest_routes.discovery.base import RouteExtractor, RouteInfo

__all__ = [
    "RouteExtractor",
    "RouteInfo",
    "get_extractor",
]


def get_extractor(app: Any) -> RouteExtractor:
    """Get the appropriate route extractor for an ASGI app.

    Args:
        app: The ASGI application.

    Returns:
        A RouteExtractor instance that can handle this app.

    Raises:
        ValueError: If no suitable extractor is found.
    """
    from pytest_routes.discovery.litestar import LitestarExtractor
    from pytest_routes.discovery.starlette import StarletteExtractor

    extractors: list[type[RouteExtractor]] = [
        LitestarExtractor,
        StarletteExtractor,
    ]

    for extractor_cls in extractors:
        extractor = extractor_cls()
        if extractor.supports(app):
            return extractor

    msg = f"No route extractor found for app type: {type(app).__name__}"
    raise ValueError(msg)
