# Stateful Testing

```{rst-class} lead
Stateful testing validates API workflows where operations depend on each other,
testing CRUD sequences and complex interactions automatically.
```

Stateful testing goes beyond testing individual routes in isolation. It generates
sequences of API calls where the output of one operation becomes the input to
subsequent operations - just like real-world API usage.

---

## Quick Start

Enable stateful testing with a single flag:

```bash
pytest --routes --routes-app myapp:app --routes-stateful
```

This automatically:
1. Loads your OpenAPI schema
2. Builds a state machine from operations and links
3. Generates test sequences that create, read, update, and delete resources
4. Validates that your API maintains consistency across operations

---

## How It Works

### State Machine Architecture

pytest-routes builds a [Hypothesis RuleBasedStateMachine](https://hypothesis.readthedocs.io/en/latest/stateful.html)
from your API operations. Each operation becomes a "rule" that can be executed,
and data flows between operations via "bundles".

```
POST /users       -->  Bundle: user_ids
     |
     v
GET /users/{id}   <--  Consumes from user_ids bundle
     |
     v
PUT /users/{id}   <--  Consumes from user_ids bundle
     |
     v
DELETE /users/{id} <-- Consumes from user_ids bundle
```

### OpenAPI Links

The state machine uses [OpenAPI Links](https://swagger.io/docs/specification/links/)
to determine data flow between operations. A link specifies how a response value
maps to a parameter in another operation.

**Example OpenAPI spec with links:**

```yaml
paths:
  /users:
    post:
      operationId: createUser
      responses:
        '201':
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/User'
          links:
            GetUserById:
              operationId: getUser
              parameters:
                userId: '$response.body#/id'
            UpdateUser:
              operationId: updateUser
              parameters:
                userId: '$response.body#/id'

  /users/{userId}:
    get:
      operationId: getUser
      parameters:
        - name: userId
          in: path
          required: true
          schema:
            type: string
```

When pytest-routes sees this spec, it knows:
- After `createUser` returns a user with an `id`
- That `id` can be used to call `getUser` or `updateUser`

### Bundle Exchange

Bundles are the mechanism for passing data between operations:

1. **Producer operations** (typically POST, PUT) add values to bundles
2. **Consumer operations** (typically GET, PUT, DELETE) draw values from bundles
3. Hypothesis ensures operations are called in valid sequences

```python
# Conceptual state machine (generated automatically)
class APIStateMachine(RuleBasedStateMachine):
    user_ids = Bundle("user_ids")

    @rule(target=user_ids, data=user_data_strategy())
    def create_user(self, data):
        response = self.client.post("/users", json=data)
        return response.json()["id"]  # Added to user_ids bundle

    @rule(user_id=user_ids)
    def get_user(self, user_id):
        response = self.client.get(f"/users/{user_id}")
        assert response.status_code == 200

    @rule(user_id=user_ids)
    def delete_user(self, user_id):
        response = self.client.delete(f"/users/{user_id}")
        assert response.status_code in (200, 204)
```

---

## CLI Options

### Core Options

```{list-table} Stateful Testing CLI Options
:header-rows: 1
:widths: 30 15 55

* - Option
  - Default
  - Description
* - `--routes-stateful`
  - `false`
  - Enable stateful testing mode
* - `--routes-stateful-mode`
  - `links`
  - Mode: `links`, `data_dependency`, or `explicit`
* - `--routes-stateful-step-count`
  - `50`
  - Maximum steps (API calls) per test sequence
* - `--routes-stateful-max-examples`
  - `100`
  - Number of test sequences to generate
* - `--routes-stateful-seed`
  - `None`
  - Random seed for reproducibility
```

### Advanced Options

```{list-table} Advanced Stateful Options
:header-rows: 1
:widths: 30 15 55

* - Option
  - Default
  - Description
* - `--routes-stateful-recursion-limit`
  - `5`
  - Maximum depth for nested state transitions
* - `--routes-stateful-timeout-per-step`
  - `30.0`
  - Timeout per step in seconds
* - `--routes-stateful-timeout-total`
  - `600.0`
  - Total timeout for entire test run
* - `--routes-stateful-fail-fast`
  - `false`
  - Stop on first failure
* - `--routes-stateful-verbose`
  - `false`
  - Show detailed execution logs
* - `--routes-stateful-include`
  - `""`
  - Comma-separated operation patterns to include
* - `--routes-stateful-exclude`
  - `""`
  - Comma-separated operation patterns to exclude
* - `--routes-stateful-coverage`
  - `true`
  - Collect state/transition coverage metrics
```

### Example Commands

```bash
# Basic stateful testing
pytest --routes --routes-app myapp:app --routes-stateful

# Quick smoke test (fewer sequences, fewer steps)
pytest --routes --routes-app myapp:app --routes-stateful \
    --routes-stateful-step-count 10 \
    --routes-stateful-max-examples 5

# Thorough testing for CI
pytest --routes --routes-app myapp:app --routes-stateful \
    --routes-stateful-step-count 100 \
    --routes-stateful-max-examples 50 \
    --routes-stateful-seed $GITHUB_RUN_ID

# Test only user-related operations
pytest --routes --routes-app myapp:app --routes-stateful \
    --routes-stateful-include "create*User*,get*User*,update*User*,delete*User*"

# Exclude admin operations
pytest --routes --routes-app myapp:app --routes-stateful \
    --routes-stateful-exclude "*Admin*,*Internal*"

# Verbose mode for debugging
pytest --routes --routes-app myapp:app --routes-stateful \
    --routes-stateful-verbose --routes-stateful-fail-fast
```

---

## Configuration

Configure stateful testing in `pyproject.toml`:

```toml
[tool.pytest-routes.stateful]
enabled = true
mode = "links"
step_count = 50
max_examples = 100
stateful_recursion_limit = 5
timeout_per_step = 30.0
timeout_total = 600.0
fail_fast = false
collect_coverage = true
verbose = false
include_operations = []
exclude_operations = ["*Admin*", "*Internal*"]

[tool.pytest-routes.stateful.link_config]
follow_links = true
max_link_depth = 3
link_timeout = 30.0

[tool.pytest-routes.stateful.hook_config]
enable_hooks = false
hook_timeout = 10.0
```

### Configuration Options

```{list-table} Stateful Config Options
:header-rows: 1
:widths: 25 15 60

* - Option
  - Type
  - Description
* - `enabled`
  - `bool`
  - Enable stateful testing
* - `mode`
  - `str`
  - Testing mode (see below)
* - `step_count`
  - `int`
  - Max API calls per sequence
* - `max_examples`
  - `int`
  - Number of sequences to generate
* - `stateful_recursion_limit`
  - `int`
  - Max state transition depth
* - `timeout_per_step`
  - `float`
  - Seconds per API call
* - `timeout_total`
  - `float`
  - Total seconds for all tests
* - `fail_fast`
  - `bool`
  - Stop on first failure
* - `collect_coverage`
  - `bool`
  - Track coverage metrics
* - `verbose`
  - `bool`
  - Detailed logging
* - `include_operations`
  - `list[str]`
  - Glob patterns to include
* - `exclude_operations`
  - `list[str]`
  - Glob patterns to exclude
```

---

## Testing Modes

### Links Mode (Default)

Uses OpenAPI Links to determine state transitions. This is the most accurate
mode when your OpenAPI spec includes link definitions.

```bash
pytest --routes --routes-app myapp:app --routes-stateful --routes-stateful-mode links
```

```{tip}
Links mode requires OpenAPI links in your spec. If your spec lacks links,
consider using `data_dependency` mode.
```

### Data Dependency Mode

Infers dependencies by analyzing request/response schemas. If a POST returns
an `id` field and a GET requires an `id` parameter, a dependency is inferred.

```bash
pytest --routes --routes-app myapp:app --routes-stateful --routes-stateful-mode data_dependency
```

This mode is useful when:
- Your OpenAPI spec lacks explicit links
- You want broader coverage of potential workflows
- You are testing APIs with standard CRUD patterns

### Explicit Mode

Uses manually configured transition rules. Define exactly which operations
can follow which other operations.

```bash
pytest --routes --routes-app myapp:app --routes-stateful --routes-stateful-mode explicit
```

Configure explicit transitions in `pyproject.toml`:

```toml
[tool.pytest-routes.stateful]
mode = "explicit"
initial_state = { "authenticated" = false }

# Define custom transitions (future feature)
# transitions = [
#     { from = "createUser", to = "getUser", map = { "userId" = "$response.id" } },
# ]
```

---

## CRUD Workflow Example

Consider a typical users API:

```python
# myapp.py
from litestar import Litestar, get, post, put, delete
from pydantic import BaseModel

class CreateUser(BaseModel):
    name: str
    email: str

class User(BaseModel):
    id: str
    name: str
    email: str

users_db: dict[str, User] = {}

@post("/users")
async def create_user(data: CreateUser) -> User:
    user_id = str(len(users_db) + 1)
    user = User(id=user_id, **data.model_dump())
    users_db[user_id] = user
    return user

@get("/users/{user_id:str}")
async def get_user(user_id: str) -> User:
    return users_db[user_id]

@put("/users/{user_id:str}")
async def update_user(user_id: str, data: CreateUser) -> User:
    users_db[user_id] = User(id=user_id, **data.model_dump())
    return users_db[user_id]

@delete("/users/{user_id:str}")
async def delete_user(user_id: str) -> None:
    del users_db[user_id]

app = Litestar([create_user, get_user, update_user, delete_user])
```

**OpenAPI spec with links:**

```yaml
paths:
  /users:
    post:
      operationId: createUser
      responses:
        '201':
          links:
            GetUser:
              operationId: getUser
              parameters:
                user_id: '$response.body#/id'
            UpdateUser:
              operationId: updateUser
              parameters:
                user_id: '$response.body#/id'
            DeleteUser:
              operationId: deleteUser
              parameters:
                user_id: '$response.body#/id'
```

**Running stateful tests:**

```bash
pytest --routes --routes-app myapp:app --routes-stateful -v
```

**Example test sequence generated:**

```text
Step 1: POST /users {"name": "Alice", "email": "alice@example.com"}
        -> 201, {"id": "1", "name": "Alice", "email": "alice@example.com"}

Step 2: GET /users/1
        -> 200, {"id": "1", "name": "Alice", "email": "alice@example.com"}

Step 3: PUT /users/1 {"name": "Alice Updated", "email": "alice@example.com"}
        -> 200, {"id": "1", "name": "Alice Updated", ...}

Step 4: DELETE /users/1
        -> 204

Step 5: GET /users/1  # After deletion - should fail gracefully
        -> 404
```

---

## Coverage Metrics

Stateful testing tracks coverage of:

- **Operation coverage**: Which operations were called
- **Transition coverage**: Which operation sequences were exercised
- **Link coverage**: Which OpenAPI links were followed

```bash
pytest --routes --routes-app myapp:app --routes-stateful --routes-stateful-coverage
```

Coverage is included in reports when `--routes-report` is enabled:

```bash
pytest --routes --routes-app myapp:app --routes-stateful \
    --routes-report stateful-report.html
```

---

## Lifecycle Hooks

For advanced use cases, configure lifecycle hooks to run custom logic:

```python
# conftest.py
import pytest

def setup_hook(context: dict) -> None:
    """Called before state machine starts."""
    context["auth_token"] = get_test_token()

def teardown_hook(context: dict) -> None:
    """Called after state machine completes."""
    cleanup_test_data(context.get("created_ids", []))

def before_call_hook(operation: str, params: dict, context: dict) -> dict | None:
    """Called before each API operation."""
    # Add auth header to all requests
    params.setdefault("headers", {})
    params["headers"]["Authorization"] = f"Bearer {context['auth_token']}"
    return params

def after_call_hook(response, operation: str, context: dict) -> None:
    """Called after each API operation."""
    if response.status_code == 201:
        # Track created resources for cleanup
        context.setdefault("created_ids", []).append(response.json().get("id"))

@pytest.fixture
def stateful_hooks():
    from pytest_routes.stateful import HookConfig
    return HookConfig(
        enable_hooks=True,
        setup_hook=setup_hook,
        teardown_hook=teardown_hook,
        before_call_hook=before_call_hook,
        after_call_hook=after_call_hook,
    )
```

---

## Integration with Schemathesis

When Schemathesis is installed, pytest-routes uses it for enhanced state machine
generation with better OpenAPI link support.

```bash
# Install with Schemathesis support
uv add "pytest-routes[schemathesis]"

# Run with both features
pytest --routes --routes-app myapp:app --routes-stateful --routes-schemathesis
```

Schemathesis provides:
- More sophisticated link following
- Better schema validation during stateful tests
- Additional test case generation strategies

---

## Troubleshooting

### No State Transitions Found

If pytest-routes reports no state transitions:

1. **Check OpenAPI links**: Your spec needs link definitions for `links` mode
2. **Try data_dependency mode**: Falls back to schema-based inference
3. **Verify schema path**: Ensure `--routes-schemathesis-schema-path` is correct

```bash
# Debug: check what schema is being loaded
pytest --routes --routes-app myapp:app --routes-stateful --routes-stateful-verbose
```

### Timeout Errors

For complex APIs, increase timeouts:

```bash
pytest --routes --routes-app myapp:app --routes-stateful \
    --routes-stateful-timeout-per-step 60 \
    --routes-stateful-timeout-total 1200
```

### Reproducibility

When a stateful test fails, note the seed and reproduce:

```bash
# Original failure
pytest --routes --routes-app myapp:app --routes-stateful
# Output: Stateful test failed (seed: 12345)

# Reproduce exact failure
pytest --routes --routes-app myapp:app --routes-stateful \
    --routes-stateful-seed 12345 --routes-stateful-verbose
```

---

## Best Practices

1. **Start with links mode** if your OpenAPI spec has link definitions
2. **Use data_dependency mode** for specs without links
3. **Set reasonable step counts**: 50-100 for development, 200+ for CI
4. **Exclude admin/internal operations** that require special setup
5. **Use seeds in CI** for reproducible failures
6. **Enable coverage tracking** to ensure workflow coverage

```toml
# Recommended pyproject.toml for CI
[tool.pytest-routes.stateful]
enabled = true
mode = "links"
step_count = 100
max_examples = 50
fail_fast = false
collect_coverage = true
exclude_operations = ["*Admin*", "*Internal*", "*Debug*"]
```

---

## See Also

- [CLI Options Reference](cli-options.md) - Complete CLI documentation
- [Schemathesis Integration](schemathesis.md) - Schema-based testing
- [Configuration](configuration.md) - Full configuration reference
