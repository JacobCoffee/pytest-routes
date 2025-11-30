"""Starlette/FastAPI route extraction."""

from __future__ import annotations

import inspect
import re
from typing import Any, get_origin, get_type_hints

from pytest_routes.discovery.base import RouteExtractor, RouteInfo


class StarletteExtractor(RouteExtractor):
    """Extract routes from Starlette and FastAPI applications.

    This extractor provides comprehensive route discovery for Starlette-based
    frameworks including vanilla Starlette and FastAPI applications. It handles
    route mounts, path parameter parsing, and query parameter extraction.

    The extractor supports:
        - Recursive route collection through Mount instances
        - Path parameter extraction with type conversion (int, float, path)
        - Query parameter detection from endpoint signatures
        - FastAPI-specific features (BaseModel bodies, dependency injection)
        - Starlette request/response parameter filtering

    Example:
        >>> from starlette.applications import Starlette
        >>> from starlette.routing import Route
        >>>
        >>> async def get_user(request):
        ...     user_id = request.path_params["user_id"]
        ...     return JSONResponse({"id": user_id})
        >>>
        >>> app = Starlette(routes=[Route("/users/{user_id:int}", get_user, methods=["GET"])])
        >>> extractor = StarletteExtractor()
        >>> routes = extractor.extract_routes(app)
        >>> routes[0].path_params
        {'user_id': <class 'int'>}

    Note:
        - HEAD methods are automatically filtered out
        - Mount instances are recursively traversed with path prefix accumulation
        - FastAPI BaseModel parameters are detected and skipped from query params
    """

    def supports(self, app: Any) -> bool:
        """Check if the application is a Starlette or FastAPI instance.

        Args:
            app: The ASGI application to check.

        Returns:
            True if the app is a Starlette or FastAPI instance, False otherwise.

        Note:
            Checks for both Starlette and FastAPI classes independently,
            returning False if neither framework is installed. This allows
            graceful degradation when frameworks are not available.
        """
        try:
            from starlette.applications import Starlette

            if isinstance(app, Starlette):
                return True
        except ImportError:
            pass

        try:
            from fastapi import FastAPI

            if isinstance(app, FastAPI):
                return True
        except ImportError:
            pass

        return False

    def extract_routes(self, app: Any) -> list[RouteInfo]:
        """Extract all HTTP routes from a Starlette or FastAPI application.

        This method traverses the application's route registry, recursively handling
        Mount instances to collect all routes with their full path prefixes. It extracts
        path parameters, query parameters, and route metadata.

        Args:
            app: A Starlette or FastAPI application instance.

        Returns:
            A list of RouteInfo objects containing route metadata:
            path (full route path including mount prefixes), methods (HTTP methods),
            name (route name), handler (endpoint function), path_params (parameter
            name to type mapping parsed from path), query_params (query parameter
            mapping), body_type (always None for Starlette - use OpenAPI extractor).

        Example:
            >>> from fastapi import FastAPI, Query
            >>> from pydantic import BaseModel
            >>>
            >>> app = FastAPI()
            >>>
            >>> class User(BaseModel):
            ...     name: str
            ...     email: str
            >>>
            >>> @app.get("/users/{user_id}")
            >>> async def get_user(user_id: int, include_posts: bool = Query(False)):
            ...     return {"id": user_id, "include_posts": include_posts}
            >>>
            >>> @app.post("/users")
            >>> async def create_user(user: User):
            ...     return {"name": user.name}
            >>>
            >>> extractor = StarletteExtractor()
            >>> routes = extractor.extract_routes(app)
            >>> len(routes)
            2
            >>> routes[0].path_params
            {'user_id': <class 'int'>}
            >>> routes[0].query_params
            {'include_posts': <class 'bool'>}

        Note:
            - Recursively processes Mount instances to handle sub-applications
            - HEAD methods are automatically filtered out
            - Path prefixes from Mount instances are accumulated
            - Query parameter extraction handles FastAPI Query/Body annotations
        """
        routes: list[RouteInfo] = []
        self._collect_routes(app.routes, "", routes)
        return routes

    def _collect_routes(self, route_list: list[Any], prefix: str, collected: list[RouteInfo]) -> None:
        """Recursively collect routes, handling mounts."""
        from starlette.routing import Mount, Route

        for route in route_list:
            if isinstance(route, Mount):
                self._collect_routes(route.routes or [], prefix + route.path, collected)
            elif isinstance(route, Route):
                for method in route.methods or ["GET"]:
                    if method == "HEAD":
                        continue

                    full_path = prefix + route.path
                    path_params = self._parse_path_params(full_path)
                    collected.append(
                        RouteInfo(
                            path=full_path,
                            methods=[method],
                            name=route.name,
                            handler=route.endpoint,
                            path_params=path_params,
                            query_params=self._extract_query_params(route.endpoint, path_params),
                            body_type=None,
                        )
                    )

    def _parse_path_params(self, path: str) -> dict[str, type]:
        """Parse path parameters from a Starlette path pattern."""
        params: dict[str, type] = {}

        # Match patterns like {param}, {param:int}, {param:path}
        pattern = r"\{([^}:]+)(?::([^}]+))?\}"
        for match in re.finditer(pattern, path):
            param_name = match.group(1)
            param_type = match.group(2)

            if param_type == "int":
                params[param_name] = int
            elif param_type == "float":
                params[param_name] = float
            else:
                params[param_name] = str

        return params

    def _extract_query_params(  # noqa: C901, PLR0912, PLR0915
        self, endpoint: Any, path_params: dict[str, type]
    ) -> dict[str, type]:
        """Extract query parameters from endpoint signature.

        Query parameters are function parameters that:
        - Are not in path_params
        - Are not the Request object (for Starlette)
        - Are not request body parameters (for FastAPI)
        - Have type annotations or default values

        Args:
            endpoint: The endpoint function
            path_params: Already extracted path parameters

        Returns:
            Dictionary mapping query param names to their types
        """
        if not callable(endpoint):
            return {}

        query_params: dict[str, type] = {}

        try:
            sig = inspect.signature(endpoint)
            hints = get_type_hints(endpoint)
        except (ValueError, TypeError, NameError):
            return {}

        path_param_names = set(path_params.keys())

        for param_name, param in sig.parameters.items():
            # Skip path parameters
            if param_name in path_param_names:
                continue

            # Skip request body parameter (commonly named 'data')
            if param_name == "data":
                continue

            # Skip common Starlette/FastAPI framework parameters by name
            if param_name in ("request", "response", "websocket", "background_tasks"):
                continue

            # Skip Request parameter (Starlette)
            param_type = hints.get(param_name, param.annotation)
            if param_type != inspect.Parameter.empty:
                try:
                    type_name = getattr(param_type, "__name__", str(param_type))
                    # Skip Request, WebSocket, and other ASGI types
                    if any(name in str(type_name) for name in ("Request", "WebSocket", "HTTPConnection", "Response")):
                        continue

                    # Skip Pydantic BaseModel subclasses (request bodies in FastAPI)
                    # Check if this type has BaseModel in its MRO
                    if hasattr(param_type, "__mro__"):
                        type_names = [t.__name__ for t in param_type.__mro__]
                        if "BaseModel" in type_names:
                            continue
                except Exception:  # noqa: S110
                    # Ignore errors from getattr or MRO inspection
                    pass

            # For FastAPI, check if the parameter has a Body/Form annotation
            # by checking the default value
            if param.default != inspect.Parameter.empty:
                try:
                    # FastAPI uses special classes for Body(), File(), Form()
                    default_class = type(param.default).__name__
                    if default_class in ("FieldInfo", "Body", "File", "Form"):
                        # This is a body parameter, not a query parameter
                        continue
                except Exception:  # noqa: S110
                    # Ignore errors from type inspection
                    pass

            # If we have a type hint, use it
            if param_type != inspect.Parameter.empty:
                # Handle Optional types (Union[X, None])
                origin = get_origin(param_type)
                if origin is not None:
                    # For Union types, extract the non-None type
                    import types

                    if hasattr(types, "UnionType") and isinstance(param_type, types.UnionType):
                        # Python 3.10+ union syntax (X | None)
                        args = param_type.__args__
                        non_none_types = [t for t in args if t is not type(None)]
                        if non_none_types:
                            param_type = non_none_types[0]
                    elif hasattr(param_type, "__args__"):
                        # typing.Union syntax
                        args = param_type.__args__
                        non_none_types = [t for t in args if t is not type(None)]
                        if non_none_types:
                            param_type = non_none_types[0]

                # Make sure we have a concrete type
                if isinstance(param_type, type):
                    query_params[param_name] = param_type
                else:
                    query_params[param_name] = str
            else:
                # No type hint, default to str
                query_params[param_name] = str

        return query_params
