# WebSocket Testing

```{rst-class} lead
Property-based testing for WebSocket endpoints with automatic message generation
and protocol validation.
```

pytest-routes extends its property-based testing approach to WebSocket endpoints,
automatically discovering WebSocket routes and generating randomized message
sequences to validate your real-time API behavior.

---

## Quick Start

Enable WebSocket testing alongside regular route testing:

```bash
pytest --routes --routes-app myapp:app --routes-websocket
```

This automatically:
1. Discovers WebSocket routes from your application
2. Generates message sequences using Hypothesis
3. Tests connection establishment, message exchange, and graceful shutdown
4. Reports failures with minimal reproducing examples

---

## How It Works

### Route Discovery

pytest-routes detects WebSocket routes from your ASGI application:

**Litestar:**
```python
from litestar import Litestar, websocket

@websocket("/ws/chat")
async def chat_handler(socket) -> None:
    await socket.accept()
    while True:
        data = await socket.receive_text()
        await socket.send_text(f"Echo: {data}")

app = Litestar([chat_handler])
```

**FastAPI/Starlette:**
```python
from fastapi import FastAPI, WebSocket

app = FastAPI()

@app.websocket("/ws/chat")
async def chat_handler(websocket: WebSocket) -> None:
    await websocket.accept()
    while True:
        data = await websocket.receive_text()
        await websocket.send_text(f"Echo: {data}")
```

### Message Generation

For each WebSocket route, pytest-routes generates message sequences:

```python
# Generated message sequence example
[
    ("text", "Hello, World!"),
    ("json", {"action": "subscribe", "channel": "news"}),
    ("text", "Another message"),
    ("bytes", b"\x00\x01\x02"),
]
```

Message types include:
- **Text messages**: Random strings and structured text
- **JSON messages**: Randomly generated JSON objects
- **Binary messages**: Random byte sequences

### Test Execution

Each test:
1. Establishes a WebSocket connection
2. Sends the generated message sequence
3. Validates that the server handles all messages without crashing
4. Verifies graceful connection shutdown

---

## CLI Options

```{list-table} WebSocket CLI Options
:header-rows: 1
:widths: 30 15 55

* - Option
  - Default
  - Description
* - `--routes-websocket`
  - `false`
  - Enable WebSocket route testing
* - `--routes-ws-max-messages`
  - `10`
  - Maximum messages per test sequence
* - `--routes-ws-timeout`
  - `30.0`
  - Connection timeout in seconds
* - `--routes-ws-message-timeout`
  - `10.0`
  - Message receive timeout in seconds
* - `--routes-ws-include`
  - `""`
  - Comma-separated patterns to include
* - `--routes-ws-exclude`
  - `""`
  - Comma-separated patterns to exclude
```

### Example Commands

```bash
# Basic WebSocket testing
pytest --routes --routes-app myapp:app --routes-websocket

# Quick smoke test (fewer messages)
pytest --routes --routes-app myapp:app --routes-websocket \
    --routes-ws-max-messages 3

# Test specific WebSocket routes
pytest --routes --routes-app myapp:app --routes-websocket \
    --routes-ws-include "/ws/chat,/ws/notifications"

# Exclude internal WebSocket routes
pytest --routes --routes-app myapp:app --routes-websocket \
    --routes-ws-exclude "/ws/internal/*,/ws/admin/*"

# Extended timeout for slow handlers
pytest --routes --routes-app myapp:app --routes-websocket \
    --routes-ws-timeout 60.0 --routes-ws-message-timeout 30.0

# Combined with regular route testing
pytest --routes --routes-app myapp:app --routes-websocket \
    --routes-max-examples 50
```

---

## Configuration

Configure WebSocket testing in `pyproject.toml`:

```toml
[tool.pytest-routes.websocket]
enabled = true
max_messages = 10
connection_timeout = 30.0
message_timeout = 10.0
max_message_size = 65536
test_close_codes = [1000, 1001]
validate_subprotocols = true
include = ["/ws/*"]
exclude = ["/ws/internal/*"]
```

### Configuration Options

```{list-table} WebSocket Config Options
:header-rows: 1
:widths: 25 15 60

* - Option
  - Type
  - Description
* - `enabled`
  - `bool`
  - Enable WebSocket testing
* - `max_messages`
  - `int`
  - Maximum messages per test sequence
* - `connection_timeout`
  - `float`
  - Connection establishment timeout (seconds)
* - `message_timeout`
  - `float`
  - Message receive timeout (seconds)
* - `max_message_size`
  - `int`
  - Maximum generated message size (bytes)
* - `test_close_codes`
  - `list[int]`
  - Close codes to test for graceful shutdown
* - `validate_subprotocols`
  - `bool`
  - Validate subprotocol negotiation
* - `include`
  - `list[str]`
  - Glob patterns to include routes
* - `exclude`
  - `list[str]`
  - Glob patterns to exclude routes
```

---

## Message Strategies

pytest-routes provides built-in message strategies for different protocols:

### Text Messages

Random strings with configurable length:

```python
# Generated examples
"Hello"
"A longer message with special chars: @#$%"
""  # Empty string (edge case)
```

### JSON Messages

Randomly generated JSON structures:

```python
# Generated examples
{"key": "value"}
{"nested": {"deep": {"structure": 42}}}
{"array": [1, 2, 3], "boolean": true, "null": null}
```

### Binary Messages

Random byte sequences:

```python
# Generated examples
b"\x00\x01\x02"
b"\xff\xfe\xfd"
b""  # Empty bytes (edge case)
```

### GraphQL Subscriptions

For GraphQL WebSocket endpoints:

```python
# Generated examples
{"type": "connection_init", "payload": {}}
{"type": "subscribe", "id": "1", "payload": {"query": "subscription { ..."}}
```

---

## Custom Message Strategies

Register custom strategies for your application's protocol:

```python
# conftest.py
from hypothesis import strategies as st
from pytest_routes.websocket import register_message_strategy

# Custom chat protocol
chat_message = st.fixed_dictionaries({
    "type": st.sampled_from(["message", "typing", "presence"]),
    "content": st.text(min_size=1, max_size=500),
    "timestamp": st.integers(min_value=0),
})

# Register for specific route pattern
register_message_strategy("/ws/chat", "json", chat_message)

# Custom binary protocol
binary_command = st.binary(min_size=4, max_size=4)  # 4-byte command
register_message_strategy("/ws/binary", "bytes", binary_command)
```

---

## Framework Support

### Litestar

Litestar WebSocket routes are auto-detected with full type information:

```python
from litestar import Litestar, websocket
from litestar.channels import ChannelsPlugin
from litestar.channels.backends.memory import MemoryChannelsBackend

@websocket("/ws/notifications")
async def notifications_handler(socket) -> None:
    await socket.accept()
    # Handle messages...

@websocket("/ws/chat/{room_id:str}")
async def chat_room_handler(socket, room_id: str) -> None:
    await socket.accept()
    # Handle messages for specific room...

app = Litestar(
    route_handlers=[notifications_handler, chat_room_handler],
    plugins=[ChannelsPlugin(backend=MemoryChannelsBackend())],
)
```

```{note}
Litestar WebSocket handlers auto-accept connections, which pytest-routes handles
transparently.
```

### FastAPI

FastAPI WebSocket routes require manual accept:

```python
from fastapi import FastAPI, WebSocket

app = FastAPI()

@app.websocket("/ws/chat")
async def chat_handler(websocket: WebSocket) -> None:
    await websocket.accept()  # Required in FastAPI
    try:
        while True:
            data = await websocket.receive_text()
            await websocket.send_text(f"Echo: {data}")
    except Exception:
        pass

@app.websocket("/ws/binary")
async def binary_handler(websocket: WebSocket) -> None:
    await websocket.accept()
    data = await websocket.receive_bytes()
    await websocket.send_bytes(data)
```

### Starlette

Starlette WebSocket routes work similarly to FastAPI:

```python
from starlette.applications import Starlette
from starlette.routing import WebSocketRoute
from starlette.websockets import WebSocket

async def chat_handler(websocket: WebSocket) -> None:
    await websocket.accept()
    while True:
        data = await websocket.receive_text()
        await websocket.send_text(f"Echo: {data}")

app = Starlette(routes=[
    WebSocketRoute("/ws/chat", chat_handler),
])
```

---

## Chat Server Example

A complete example testing a chat server:

**Application:**

```python
# chat_app.py
from litestar import Litestar, websocket

connected_clients: list = []

@websocket("/ws/chat")
async def chat_handler(socket) -> None:
    await socket.accept()
    connected_clients.append(socket)

    try:
        while True:
            message = await socket.receive_text()
            # Broadcast to all clients
            for client in connected_clients:
                if client is not socket:
                    await client.send_text(message)
    finally:
        connected_clients.remove(socket)

app = Litestar([chat_handler])
```

**Test configuration:**

```toml
# pyproject.toml
[tool.pytest-routes]
app = "chat_app:app"

[tool.pytest-routes.websocket]
enabled = true
max_messages = 20
connection_timeout = 10.0
message_timeout = 5.0
```

**Running tests:**

```bash
pytest --routes --routes-websocket -v
```

**Example output:**

```text
tests/test_routes.py::test_websocket[/ws/chat] PASSED

pytest-routes: WebSocket Test Summary
=====================================
Route: /ws/chat
  Sequences tested: 100
  Messages sent: 1,247
  Connections established: 100
  Failures: 0
=====================================
```

---

## Failure Reporting

When a WebSocket test fails, pytest-routes provides detailed failure information:

```text
============================================================
WEBSOCKET TEST FAILURE: /ws/chat
============================================================

Error Type: message_handler_error
Message: Server closed connection unexpectedly

Failed at message index: 5

Sent (json):
  {"type": "subscribe", "channel": "invalid_\x00_channel"}

Expected:
  Connection to remain open

Actual:
  Connection closed with code 1011

Connection State: closed
Close Code: 1011

Additional Context:
  total_messages_sent: 5
  last_response: None
  elapsed_time_ms: 127.5
============================================================
```

### Reproducing Failures

Use the seed for reproducibility:

```bash
# Original failure
pytest --routes --routes-app myapp:app --routes-websocket
# Output: WebSocket test failed (seed: 54321)

# Reproduce
pytest --routes --routes-app myapp:app --routes-websocket \
    --routes-seed 54321 -v
```

---

## Testing Patterns

### Echo Server Testing

For simple echo servers:

```python
@websocket("/ws/echo")
async def echo(socket) -> None:
    await socket.accept()
    while True:
        msg = await socket.receive_text()
        await socket.send_text(msg)
```

Test validates:
- Connection establishment
- Message round-trip
- Various message contents (including edge cases)
- Graceful shutdown

### Pub/Sub Testing

For publish-subscribe patterns:

```python
@websocket("/ws/subscribe/{channel:str}")
async def subscribe(socket, channel: str) -> None:
    await socket.accept()
    # Subscribe to channel, receive broadcasts
```

Test validates:
- Path parameter handling
- Subscription lifecycle
- Message handling per channel

### Authentication Testing

For authenticated WebSocket endpoints:

```python
@websocket("/ws/private")
async def private_handler(socket) -> None:
    # Check auth token in query params or first message
    token = socket.query_params.get("token")
    if not validate_token(token):
        await socket.close(code=4001)
        return

    await socket.accept()
    # Handle authenticated messages
```

Test with authentication:

```bash
pytest --routes --routes-app myapp:app --routes-websocket \
    --routes-auth "bearer:$WS_AUTH_TOKEN"
```

---

## Best Practices

1. **Set appropriate timeouts**: WebSocket tests can hang if timeouts are too long

   ```bash
   --routes-ws-timeout 10.0 --routes-ws-message-timeout 5.0
   ```

2. **Limit message count for development**: Start small, increase for CI

   ```bash
   # Development: quick feedback
   --routes-ws-max-messages 5

   # CI: thorough testing
   --routes-ws-max-messages 20
   ```

3. **Exclude internal routes**: Focus on public-facing endpoints

   ```bash
   --routes-ws-exclude "/ws/internal/*,/ws/debug/*"
   ```

4. **Combine with HTTP testing**: Test both in one run

   ```bash
   pytest --routes --routes-websocket --routes-app myapp:app
   ```

5. **Use custom strategies**: Match your application's protocol

   ```python
   register_message_strategy("/ws/api", "json", your_api_message_strategy)
   ```

---

## Troubleshooting

### Connection Refused

If connections are refused:

1. Verify the route is a WebSocket route (not HTTP)
2. Check the route pattern matches correctly
3. Ensure the handler calls `accept()` (FastAPI/Starlette)

### Timeout Errors

If tests timeout:

1. Increase `--routes-ws-timeout` for connection phase
2. Increase `--routes-ws-message-timeout` for message handling
3. Check if your handler has infinite loops without proper exception handling

### Unexpected Closures

If connections close unexpectedly:

1. Check handler exception handling
2. Verify message format matches handler expectations
3. Enable verbose mode to see message sequences:

   ```bash
   pytest --routes --routes-app myapp:app --routes-websocket --routes-verbose
   ```

---

## See Also

- [CLI Options Reference](cli-options.md) - Complete CLI documentation
- [Configuration](configuration.md) - Full configuration reference
- [Stateful Testing](stateful.md) - API workflow testing
