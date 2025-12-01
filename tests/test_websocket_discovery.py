"""Tests for WebSocket route discovery."""

from __future__ import annotations

import pytest

from pytest_routes.discovery.base import RouteInfo, WebSocketMessageType, WebSocketMetadata


class TestRouteInfoWebSocketExtensions:
    """Tests for WebSocket extensions to RouteInfo."""

    def test_http_route_is_not_websocket(self) -> None:
        """Test that HTTP routes are not marked as WebSocket."""
        route = RouteInfo(path="/api/users", methods=["GET", "POST"], is_websocket=False)

        assert route.is_websocket is False
        assert route.is_http is True
        assert route.websocket_metadata is None

    def test_websocket_route_is_websocket(self) -> None:
        """Test that WebSocket routes are correctly marked."""
        route = RouteInfo(path="/ws/chat", methods=[], is_websocket=True)

        assert route.is_websocket is True
        assert route.is_http is False

    def test_is_http_property_for_http_route(self) -> None:
        """Test is_http property returns True for HTTP routes."""
        route = RouteInfo(path="/api/test", methods=["GET"], is_websocket=False)

        assert route.is_http is True

    def test_is_http_property_for_websocket_route(self) -> None:
        """Test is_http property returns False for WebSocket routes."""
        route = RouteInfo(path="/ws/test", methods=[], is_websocket=True)

        assert route.is_http is False

    def test_get_websocket_metadata_creates_default(self) -> None:
        """Test that get_websocket_metadata creates default metadata."""
        route = RouteInfo(path="/ws/test", methods=[], is_websocket=True)

        metadata = route.get_websocket_metadata()

        assert isinstance(metadata, WebSocketMetadata)
        assert metadata.auto_accept is True
        assert metadata.subprotocols == []
        assert WebSocketMessageType.TEXT in metadata.accepted_message_types
        assert WebSocketMessageType.JSON in metadata.accepted_message_types

    def test_get_websocket_metadata_raises_for_http(self) -> None:
        """Test that get_websocket_metadata raises for HTTP routes."""
        route = RouteInfo(path="/api/test", methods=["GET"], is_websocket=False)

        with pytest.raises(ValueError, match="not a WebSocket route"):
            route.get_websocket_metadata()

    def test_get_websocket_metadata_returns_existing(self) -> None:
        """Test that get_websocket_metadata returns existing metadata."""
        metadata = WebSocketMetadata(subprotocols=["graphql-ws"], auto_accept=False)
        route = RouteInfo(path="/ws/test", methods=[], is_websocket=True, websocket_metadata=metadata)

        retrieved = route.get_websocket_metadata()

        assert retrieved is metadata
        assert retrieved.subprotocols == ["graphql-ws"]
        assert retrieved.auto_accept is False

    def test_websocket_route_repr(self) -> None:
        """Test string representation of WebSocket route."""
        route = RouteInfo(path="/ws/chat", methods=[], is_websocket=True)

        repr_str = repr(route)

        assert "WS" in repr_str
        assert "/ws/chat" in repr_str

    def test_http_route_repr(self) -> None:
        """Test string representation of HTTP route."""
        route = RouteInfo(path="/api/users", methods=["GET", "POST"], is_websocket=False)

        repr_str = repr(route)

        assert "GET,POST" in repr_str
        assert "/api/users" in repr_str


class TestWebSocketMetadata:
    """Tests for WebSocketMetadata dataclass."""

    def test_default_values(self) -> None:
        """Test default WebSocketMetadata values."""
        metadata = WebSocketMetadata()

        assert metadata.subprotocols == []
        assert WebSocketMessageType.TEXT in metadata.accepted_message_types
        assert WebSocketMessageType.JSON in metadata.accepted_message_types
        assert WebSocketMessageType.TEXT in metadata.sends_message_types
        assert WebSocketMessageType.JSON in metadata.sends_message_types
        assert metadata.auto_accept is True
        assert metadata.ping_interval is None
        assert metadata.max_message_size is None
        assert metadata.close_codes == [1000, 1001]

    def test_custom_values(self) -> None:
        """Test WebSocketMetadata with custom values."""
        metadata = WebSocketMetadata(
            subprotocols=["graphql-ws", "graphql-transport-ws"],
            accepted_message_types=[WebSocketMessageType.JSON],
            sends_message_types=[WebSocketMessageType.JSON],
            auto_accept=False,
            ping_interval=30.0,
            max_message_size=1048576,
            close_codes=[1000, 1001, 1011],
        )

        assert metadata.subprotocols == ["graphql-ws", "graphql-transport-ws"]
        assert metadata.accepted_message_types == [WebSocketMessageType.JSON]
        assert metadata.sends_message_types == [WebSocketMessageType.JSON]
        assert metadata.auto_accept is False
        assert metadata.ping_interval == 30.0
        assert metadata.max_message_size == 1048576
        assert metadata.close_codes == [1000, 1001, 1011]

    def test_message_types_enum(self) -> None:
        """Test that message types use WebSocketMessageType enum."""
        metadata = WebSocketMetadata(
            accepted_message_types=[WebSocketMessageType.TEXT, WebSocketMessageType.BINARY],
        )

        assert all(isinstance(mt, WebSocketMessageType) for mt in metadata.accepted_message_types)


class TestWebSocketMessageType:
    """Tests for WebSocketMessageType enum."""

    def test_enum_values(self) -> None:
        """Test WebSocketMessageType enum values."""
        assert WebSocketMessageType.TEXT.value == "text"
        assert WebSocketMessageType.BINARY.value == "binary"
        assert WebSocketMessageType.JSON.value == "json"

    def test_enum_members(self) -> None:
        """Test all expected enum members exist."""
        types = {mt.name for mt in WebSocketMessageType}
        assert types == {"TEXT", "BINARY", "JSON"}


class TestLitestarWebSocketDiscovery:
    """Tests for Litestar WebSocket route discovery."""

    @pytest.fixture
    def litestar_ws_app(self):
        """Create a Litestar app with WebSocket routes."""
        try:
            from litestar import Litestar, websocket
            from litestar.connection import WebSocket

            @websocket("/ws/echo")
            async def echo_handler(socket: WebSocket) -> None:
                await socket.accept()
                data = await socket.receive_text()
                await socket.send_text(data)
                await socket.close()

            @websocket("/ws/chat/{room_id:str}")
            async def chat_handler(socket: WebSocket, room_id: str) -> None:
                await socket.accept()
                await socket.send_json({"room": room_id, "status": "connected"})
                await socket.close()

            return Litestar(route_handlers=[echo_handler, chat_handler])
        except ImportError:
            pytest.skip("Litestar not installed")

    def test_litestar_discovers_websocket_routes(self, litestar_ws_app) -> None:
        """Test that Litestar extractor discovers WebSocket routes."""
        from pytest_routes.discovery.litestar import LitestarExtractor

        extractor = LitestarExtractor()
        routes = extractor.extract_routes(litestar_ws_app)

        ws_routes = [r for r in routes if r.is_websocket]

        assert len(ws_routes) >= 2

        paths = {r.path for r in ws_routes}
        assert "/ws/echo" in paths
        assert "/ws/chat/{room_id:str}" in paths

    def test_litestar_websocket_metadata(self, litestar_ws_app) -> None:
        """Test that Litestar WebSocket routes have correct metadata."""
        from pytest_routes.discovery.litestar import LitestarExtractor

        extractor = LitestarExtractor()
        routes = extractor.extract_routes(litestar_ws_app)

        ws_routes = [r for r in routes if r.is_websocket]
        assert len(ws_routes) > 0

        for route in ws_routes:
            metadata = route.get_websocket_metadata()
            assert metadata.auto_accept is True

    def test_litestar_websocket_path_params(self, litestar_ws_app) -> None:
        """Test that Litestar WebSocket routes extract path parameters."""
        from pytest_routes.discovery.litestar import LitestarExtractor

        extractor = LitestarExtractor()
        routes = extractor.extract_routes(litestar_ws_app)

        chat_route = next((r for r in routes if "/chat/" in r.path), None)
        assert chat_route is not None
        assert chat_route.is_websocket is True


class TestStarletteWebSocketDiscovery:
    """Tests for Starlette/FastAPI WebSocket route discovery."""

    @pytest.fixture
    def starlette_ws_app(self):
        """Create a Starlette app with WebSocket routes."""
        try:
            from starlette.applications import Starlette
            from starlette.routing import WebSocketRoute

            async def echo_endpoint(websocket):
                await websocket.accept()
                data = await websocket.receive_text()
                await websocket.send_text(data)
                await websocket.close()

            async def chat_endpoint(websocket):
                await websocket.accept()
                room_id = websocket.path_params["room_id"]
                await websocket.send_json({"room": room_id})
                await websocket.close()

            routes = [
                WebSocketRoute("/ws/echo", echo_endpoint),
                WebSocketRoute("/ws/chat/{room_id}", chat_endpoint),
            ]

            return Starlette(routes=routes)
        except ImportError:
            pytest.skip("Starlette not installed")

    def test_starlette_discovers_websocket_routes(self, starlette_ws_app) -> None:
        """Test that Starlette extractor discovers WebSocket routes."""
        from pytest_routes.discovery.starlette import StarletteExtractor

        extractor = StarletteExtractor()
        routes = extractor.extract_routes(starlette_ws_app)

        ws_routes = [r for r in routes if r.is_websocket]

        assert len(ws_routes) >= 2

        paths = {r.path for r in ws_routes}
        assert "/ws/echo" in paths
        assert "/ws/chat/{room_id}" in paths

    def test_starlette_websocket_metadata(self, starlette_ws_app) -> None:
        """Test that Starlette WebSocket routes have correct metadata."""
        from pytest_routes.discovery.starlette import StarletteExtractor

        extractor = StarletteExtractor()
        routes = extractor.extract_routes(starlette_ws_app)

        ws_routes = [r for r in routes if r.is_websocket]
        assert len(ws_routes) > 0

        for route in ws_routes:
            metadata = route.get_websocket_metadata()
            assert metadata.auto_accept is False

    def test_starlette_websocket_path_params(self, starlette_ws_app) -> None:
        """Test that Starlette WebSocket routes extract path parameters."""
        from pytest_routes.discovery.starlette import StarletteExtractor

        extractor = StarletteExtractor()
        routes = extractor.extract_routes(starlette_ws_app)

        chat_route = next((r for r in routes if "/chat/" in r.path), None)
        assert chat_route is not None
        assert chat_route.is_websocket is True


class TestFastAPIWebSocketDiscovery:
    """Tests for FastAPI WebSocket route discovery."""

    @pytest.fixture
    def fastapi_ws_app(self):
        """Create a FastAPI app with WebSocket routes."""
        try:
            from fastapi import FastAPI, WebSocket

            app = FastAPI()

            @app.websocket("/ws/echo")
            async def echo_endpoint(websocket: WebSocket):
                await websocket.accept()
                data = await websocket.receive_text()
                await websocket.send_text(data)
                await websocket.close()

            @app.websocket("/ws/notifications/{user_id}")
            async def notifications_endpoint(websocket: WebSocket, user_id: int):
                await websocket.accept()
                await websocket.send_json({"user_id": user_id, "notifications": []})
                await websocket.close()

            return app
        except ImportError:
            pytest.skip("FastAPI not installed")

    def test_fastapi_discovers_websocket_routes(self, fastapi_ws_app) -> None:
        """Test that FastAPI WebSocket routes are discovered."""
        from pytest_routes.discovery.starlette import StarletteExtractor

        extractor = StarletteExtractor()
        routes = extractor.extract_routes(fastapi_ws_app)

        ws_routes = [r for r in routes if r.is_websocket]

        assert len(ws_routes) >= 2

        paths = {r.path for r in ws_routes}
        assert "/ws/echo" in paths
        assert "/ws/notifications/{user_id}" in paths

    def test_fastapi_websocket_metadata(self, fastapi_ws_app) -> None:
        """Test that FastAPI WebSocket routes have correct metadata."""
        from pytest_routes.discovery.starlette import StarletteExtractor

        extractor = StarletteExtractor()
        routes = extractor.extract_routes(fastapi_ws_app)

        ws_routes = [r for r in routes if r.is_websocket]
        assert len(ws_routes) > 0

        for route in ws_routes:
            metadata = route.get_websocket_metadata()
            assert metadata.auto_accept is False


class TestMixedRouteDiscovery:
    """Tests for discovering both HTTP and WebSocket routes."""

    @pytest.fixture
    def litestar_mixed_app(self):
        """Create a Litestar app with both HTTP and WebSocket routes."""
        try:
            from litestar import Litestar, get, websocket
            from litestar.connection import WebSocket

            @get("/api/health")
            async def health() -> dict:
                return {"status": "ok"}

            @get("/api/users/{user_id:int}")
            async def get_user(user_id: int) -> dict:
                return {"id": user_id}

            @websocket("/ws/events")
            async def events_handler(socket: WebSocket) -> None:
                await socket.accept()
                await socket.send_json({"type": "connected"})
                await socket.close()

            return Litestar(route_handlers=[health, get_user, events_handler])
        except ImportError:
            pytest.skip("Litestar not installed")

    def test_discovers_both_http_and_websocket(self, litestar_mixed_app) -> None:
        """Test that both HTTP and WebSocket routes are discovered."""
        from pytest_routes.discovery.litestar import LitestarExtractor

        extractor = LitestarExtractor()
        routes = extractor.extract_routes(litestar_mixed_app)

        http_routes = [r for r in routes if r.is_http]
        ws_routes = [r for r in routes if r.is_websocket]

        assert len(http_routes) >= 2
        assert len(ws_routes) >= 1

        http_paths = {r.path for r in http_routes}
        assert "/api/health" in http_paths
        assert "/api/users/{user_id:int}" in http_paths

        ws_paths = {r.path for r in ws_routes}
        assert "/ws/events" in ws_paths

    def test_http_and_websocket_routes_distinct(self, litestar_mixed_app) -> None:
        """Test that HTTP and WebSocket routes are properly distinguished."""
        from pytest_routes.discovery.litestar import LitestarExtractor

        extractor = LitestarExtractor()
        routes = extractor.extract_routes(litestar_mixed_app)

        for route in routes:
            if route.is_http:
                assert route.is_websocket is False
                assert len(route.methods) > 0
            elif route.is_websocket:
                assert route.is_http is False


class TestWebSocketRouteMetadataExtraction:
    """Tests for extracting WebSocket-specific metadata."""

    def test_graphql_websocket_metadata(self) -> None:
        """Test metadata for GraphQL WebSocket endpoint."""
        metadata = WebSocketMetadata(
            subprotocols=["graphql-ws", "graphql-transport-ws"],
            accepted_message_types=[WebSocketMessageType.JSON],
            sends_message_types=[WebSocketMessageType.JSON],
        )

        route = RouteInfo(
            path="/graphql",
            methods=[],
            is_websocket=True,
            websocket_metadata=metadata,
        )

        retrieved = route.get_websocket_metadata()

        assert "graphql-ws" in retrieved.subprotocols
        assert WebSocketMessageType.JSON in retrieved.accepted_message_types

    def test_binary_websocket_metadata(self) -> None:
        """Test metadata for binary WebSocket endpoint."""
        metadata = WebSocketMetadata(
            accepted_message_types=[WebSocketMessageType.BINARY],
            sends_message_types=[WebSocketMessageType.BINARY],
            max_message_size=10485760,
        )

        route = RouteInfo(
            path="/ws/stream",
            methods=[],
            is_websocket=True,
            websocket_metadata=metadata,
        )

        retrieved = route.get_websocket_metadata()

        assert WebSocketMessageType.BINARY in retrieved.accepted_message_types
        assert retrieved.max_message_size == 10485760

    def test_ping_interval_metadata(self) -> None:
        """Test metadata with ping interval configuration."""
        metadata = WebSocketMetadata(ping_interval=30.0, close_codes=[1000, 1001, 1006])

        route = RouteInfo(
            path="/ws/realtime",
            methods=[],
            is_websocket=True,
            websocket_metadata=metadata,
        )

        retrieved = route.get_websocket_metadata()

        assert retrieved.ping_interval == 30.0
        assert 1006 in retrieved.close_codes
