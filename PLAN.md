# pytest-routes - Architecture Plan

> Property-based smoke testing for ASGI application routes. First-class Litestar support with generic ASGI framework compatibility.

---

## Current Status

**Version**: 0.1.0 (Released)
**Phase**: Post-Release - Ready for v0.2.0 Development
**Last Updated**: 2025-11-30

### Test Coverage

| Metric | Value |
|--------|-------|
| Unit Tests | 176 |
| Route Smoke Tests | 7 (per example app) |
| Coverage | ~90% |
| Target | 90% |

### Test Files

| File | Tests | Description |
|------|-------|-------------|
| `test_discovery.py` | 9 | Route extraction tests |
| `test_strategies.py` | 25 | Type-to-strategy mapping (enhanced) |
| `test_plugin.py` | 13 | Plugin and pattern matching |
| `test_runner.py` | 11 | Runner and validation |
| `test_client.py` | 10 | ASGI test client |
| `test_integration.py` | 17 | End-to-end tests |
| `test_config.py` | 15 | Configuration and pyproject.toml |
| `test_headers.py` | 21 | Header generation strategies |
| `test_query_params.py` | 11 | Query parameter extraction |
| `test_openapi_body_extraction.py` | 12 | OpenAPI body type extraction |
| `validation/test_response.py` | 26 | Response validation |
| `validation/test_integration.py` | 6 | Validation integration |

### Example Apps

| App | Framework | Routes | Command |
|-----|-----------|--------|---------|
| `examples/litestar_app.py` | Litestar 2.x | 7 | `make test-routes-litestar` |
| `examples/fastapi_app.py` | FastAPI | 7 | `make test-routes-fastapi` |
| `examples/starlette_app.py` | Starlette | 8 | `make test-routes-starlette` |

### Branch Status

Initial development on `main`:
- Phase 1 Core Infrastructure - Complete ✅
- Phase 2 Enhanced Framework Support - Complete ✅
- Phase 3 Documentation & Polish - Complete ✅
- CI/CD Infrastructure - Complete ✅

### Completed

#### Phase 1: Core Infrastructure (Complete) ✅
- [x] Project scaffolding (pyproject.toml, Makefile)
- [x] CI/CD configuration (.pre-commit-config.yaml)
- [x] Core module structure
- [x] RouteInfo dataclass
- [x] RouteExtractor protocol
- [x] LitestarExtractor implementation
- [x] StarletteExtractor implementation (FastAPI compatible)
- [x] OpenAPIExtractor stub
- [x] Type-to-strategy mapping (strategies.py)
- [x] Path parameter generation (path.py)
- [x] Body generation with dataclass/Pydantic support (body.py)
- [x] ASGI test client (client.py)
- [x] Route test runner (runner.py)
- [x] Pytest plugin with CLI options (plugin.py)
- [x] Configuration dataclass (config.py)
- [x] Integration test suite
- [x] CLI options (`--routes`, `--routes-app`, `--routes-exclude`, etc.)
- [x] Route filtering (include/exclude pattern matching)
- [x] Enhanced error reporting with shrunk examples (`RouteTestFailure`)
- [x] **Dynamic test generation** - Routes appear as individual pytest items
- [x] **Example applications** - Litestar, FastAPI, Starlette demos
- [x] **Makefile targets** - `test-routes-*` commands

#### Phase 2: Enhanced Framework Support (Complete) ✅
- [x] Query parameter extraction (Litestar, Starlette, FastAPI)
- [x] Query parameter generation strategies
- [x] Header generation strategies module (`headers.py`)
- [x] OpenAPI extractor full implementation with body type extraction
  - [x] Request body schema parsing (inline and $ref)
  - [x] Dynamic dataclass generation from JSON schema
  - [x] Format type mapping (date-time, uuid, etc.)
  - [x] Nested object support
  - [x] Array and enum handling
- [x] Response schema validation (optional)
  - [x] `StatusCodeValidator` - Validates HTTP status codes
  - [x] `ContentTypeValidator` - Validates Content-Type headers
  - [x] `JsonSchemaValidator` - Validates against JSON schema (requires jsonschema)
  - [x] `OpenAPIResponseValidator` - Validates against OpenAPI spec
  - [x] `CompositeValidator` - Combines multiple validators
- [x] Custom strategy registration API improvements
  - [x] `register_strategy()` with override protection
  - [x] `unregister_strategy()` for cleanup
  - [x] `@strategy_provider` decorator
  - [x] `temporary_strategy()` context manager
  - [x] `register_strategies()` batch registration
  - [x] `get_registered_types()` introspection
- [x] `pyproject.toml` configuration support (`[tool.pytest-routes]`)
  - [x] `load_config_from_pyproject()` function
  - [x] `RouteTestConfig.from_dict()` classmethod
  - [x] `merge_configs()` with CLI > file > defaults precedence
  - [x] Python 3.10 compatibility (tomli fallback)

#### Phase 3: Documentation & Polish (Complete) ✅
- [x] README with usage examples
- [x] Sphinx documentation site (shibuya theme, red accent)
  - [x] `docs/conf.py` - Sphinx configuration
  - [x] `docs/index.md` - Home page with feature grid
  - [x] `docs/getting-started.md` - Installation and quick start
  - [x] `docs/usage/` - Usage guides (CLI, config, frameworks)
  - [x] `docs/api/` - API reference (autodoc)
- [x] API reference docs (auto-generated from docstrings)
- [x] Contributing guide (`CONTRIBUTING.md`)
- [x] Comprehensive docstrings on all public APIs
  - [x] `plugin.py` - pytest hooks and test items
  - [x] `discovery/litestar.py` - Litestar extractor
  - [x] `discovery/starlette.py` - Starlette/FastAPI extractor
  - [x] `discovery/openapi.py` - OpenAPI extractor

#### CI/CD Infrastructure (Complete) ✅

| Workflow | Purpose | Status |
|----------|---------|--------|
| `ci.yml` | Zizmor security, lint, smoke tests, full matrix | Complete ✅ |
| `docs.yml` | Build docs, PR preview, GitHub Pages deploy | Complete ✅ |
| `cd.yml` | Changelog generation (git-cliff) | Complete ✅ |
| `publish.yml` | Build → Sign → Draft Release → PyPI → Publish | Complete ✅ |
| `pages-deploy.yml` | Deploy from gh-pages branch | Complete ✅ |
| `pr-title.yml` | Semantic PR title validation | Complete ✅ |

**Additional Files:**
- `.github/dependabot.yml` - Weekly updates for actions & pip
- `.github/PULL_REQUEST_TEMPLATE.md` - PR checklist

**Security**: All workflows validated with zizmor (1 accepted finding: `pull_request_target`).

**Released**: v0.1.0 on PyPI with Sigstore signatures.

### Next Up

#### v0.2.0 - Authentication & Advanced Features
- [ ] Authentication support (Bearer token, API key)
- [ ] Per-route configuration overrides
- [ ] `@pytest.mark.routes_skip` marker for excluding routes
- [ ] `@pytest.mark.routes_auth` marker for auth requirements
- [ ] Improved error messages with request/response details

#### Future Releases
- **v0.3.0**: HTML report generation, coverage metrics per route
- **v0.4.0**: Stateful testing (CRUD flows), WebSocket routes
- **v1.0.0**: Stable release, fuzz testing mode

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Research Analysis](#research-analysis)
3. [Architecture Overview](#architecture-overview)
4. [Core Domain Model](#core-domain-model)
5. [Route Discovery](#route-discovery)
6. [Data Generation](#data-generation)
7. [Test Execution](#test-execution)
8. [Package Structure](#package-structure)
9. [Implementation Phases](#implementation-phases)
10. [API Reference](#api-reference)
11. [Design Decisions](#design-decisions)

---

## Executive Summary

**pytest-routes** provides property-based smoke testing for ASGI applications using Hypothesis. It automatically discovers routes and generates randomized test inputs to validate that endpoints don't crash.

### Key Differentiators

- **Schema-optional**: Works without OpenAPI schema (extracts routes from app internals)
- **Framework-aware**: First-class Litestar support, generic ASGI compatibility
- **Lightweight**: Focused on smoke testing, not full contract testing
- **Configurable**: Flexible route filtering, status code validation, auth support

### Key Design Principles

1. **Property-Based**: Leverage Hypothesis for intelligent input generation
2. **Framework-Native**: Deep integration with Litestar route handlers
3. **Pytest-First**: Natural pytest workflow with fixtures and markers
4. **Fail-Fast**: Quick detection of 5xx errors and crashes
5. **Type-Safe**: Full typing with Protocol-based interfaces

---

## Research Analysis

### Existing Solutions

#### Schemathesis

| Aspect | Implementation | Relevance |
|--------|---------------|-----------|
| Input Source | OpenAPI/GraphQL schemas | Reference for schema-based extraction |
| Testing | Hypothesis-based property testing | Core pattern to adopt |
| ASGI Support | `from_asgi()` for direct testing | Transport pattern reference |
| Limitation | Requires OpenAPI schema | Our differentiator |

#### Hypothesis

| Pattern | Description | Application |
|---------|-------------|-------------|
| `st.builds()` | Generate instances from types | Request body generation |
| `st.from_type()` | Infer strategies from types | Parameter generation |
| `@given` decorator | Test parameterization | Route test generation |
| `@settings` | Test configuration | Max examples, timeouts |

### Framework Route Patterns

#### Litestar

| Feature | Access Pattern | Usage |
|---------|---------------|-------|
| Routes | `app.routes` → `HTTPRoute` | Route enumeration |
| Handlers | `route.route_handler_map` | Method → handler mapping |
| Path params | `route.path_parameters` | Parameter names/types |
| Type hints | `get_type_hints(handler.fn)` | Body/param types |
| OpenAPI | `app.openapi_schema` | Optional schema extraction |

#### Starlette/FastAPI

| Feature | Access Pattern | Usage |
|---------|---------------|-------|
| Routes | `app.routes` → `Route`, `Mount` | Route enumeration |
| Handler | `route.endpoint` | Endpoint function |
| Methods | `route.methods` | HTTP methods |
| Path pattern | `route.path` | URL pattern with params |
| OpenAPI | `app.openapi()` (FastAPI) | Optional schema |

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                          User Application                            │
├─────────────────────────────────────────────────────────────────────┤
│                           pytest-routes                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────────┐  │
│  │   Plugin     │  │  Discovery   │  │       Generation         │  │
│  │ (pytest11)   │  │ (Extractors) │  │   (Hypothesis strats)    │  │
│  └──────────────┘  └──────────────┘  └──────────────────────────┘  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────────┐  │
│  │  Execution   │  │    Config    │  │       Validation         │  │
│  │  (Runner)    │  │   (Options)  │  │    (Status codes)        │  │
│  └──────────────┘  └──────────────┘  └──────────────────────────┘  │
├─────────────────────────────────────────────────────────────────────┤
│                      ASGI Frameworks                                 │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────────┐  │
│  │   Litestar   │  │   FastAPI    │  │        Starlette         │  │
│  │ (1st class)  │  │  (Starlette) │  │        (generic)         │  │
│  └──────────────┘  └──────────────┘  └──────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Core Domain Model

### RouteInfo

```python
@dataclass
class RouteInfo:
    """Normalized route information from any framework."""

    path: str                           # "/users/{user_id}"
    methods: list[str]                  # ["GET", "POST"]
    name: str | None                    # Optional route name
    handler: Callable[..., Any] | None  # Handler function

    # Parameter info
    path_params: dict[str, type]        # {"user_id": int}
    query_params: dict[str, type]       # {"limit": int}
    body_type: type | None              # Pydantic model or dataclass

    # Metadata
    tags: list[str]                     # OpenAPI tags
    deprecated: bool                    # Skip deprecated routes
```

### RouteExtractor Protocol

```python
class RouteExtractor(Protocol):
    """Protocol for framework-specific route extraction."""

    def supports(self, app: Any) -> bool:
        """Check if extractor supports this app type."""
        ...

    def extract_routes(self, app: Any) -> list[RouteInfo]:
        """Extract all routes from application."""
        ...
```

### RouteTestConfig

```python
@dataclass
class RouteTestConfig:
    """Configuration for route smoke testing."""

    # Test execution
    max_examples: int = 100
    timeout_per_route: float = 30.0

    # Route filtering
    include_patterns: list[str] = field(default_factory=list)
    exclude_patterns: list[str] = field(
        default_factory=lambda: ["/health", "/metrics", "/openapi*"]
    )
    methods: list[str] = field(
        default_factory=lambda: ["GET", "POST", "PUT", "PATCH", "DELETE"]
    )

    # Validation
    allowed_status_codes: list[int] = field(
        default_factory=lambda: list(range(200, 500))
    )
    fail_on_5xx: bool = True

    # Framework hints
    framework: Literal["auto", "litestar", "fastapi", "starlette"] = "auto"
```

---

## Route Discovery

### Litestar Extractor

```python
class LitestarExtractor(RouteExtractor):
    """Extract routes from Litestar applications."""

    def supports(self, app: Any) -> bool:
        return hasattr(app, "__class__") and app.__class__.__name__ == "Litestar"

    def extract_routes(self, app: Any) -> list[RouteInfo]:
        routes = []
        for route in app.routes:
            if hasattr(route, "route_handler_map"):
                for method, handler in route.route_handler_map.items():
                    if method == "HEAD":
                        continue
                    routes.append(self._build_route_info(route, method, handler))
        return routes
```

### Starlette/FastAPI Extractor

```python
class StarletteExtractor(RouteExtractor):
    """Extract routes from Starlette/FastAPI applications."""

    def supports(self, app: Any) -> bool:
        return hasattr(app, "routes") and hasattr(app, "middleware_stack")

    def extract_routes(self, app: Any) -> list[RouteInfo]:
        routes = []
        self._collect_routes(app.routes, "", routes)
        return routes

    def _collect_routes(self, route_list, prefix: str, collected: list) -> None:
        for route in route_list:
            if hasattr(route, "routes"):  # Mount
                self._collect_routes(route.routes, prefix + route.path, collected)
            elif hasattr(route, "endpoint"):  # Route
                # Extract route info...
```

---

## Data Generation

### Type Strategy Registry

```python
TYPE_STRATEGIES: dict[type, SearchStrategy[Any]] = {
    str: st.text(min_size=1, max_size=100),
    int: st.integers(min_value=-1000, max_value=1000),
    float: st.floats(allow_nan=False, allow_infinity=False),
    bool: st.booleans(),
    uuid.UUID: st.uuids(),
    datetime: st.datetimes(),
    date: st.dates(),
}

def strategy_for_type(typ: type) -> SearchStrategy[Any]:
    """Get Hypothesis strategy for a Python type."""
    if typ in TYPE_STRATEGIES:
        return TYPE_STRATEGIES[typ]

    origin = get_origin(typ)
    if origin is Union:  # Optional[X]
        return st.none() | strategy_for_type(non_none_arg)
    if origin is list:   # list[X]
        return st.lists(strategy_for_type(item_type), max_size=10)
    if origin is dict:   # dict[K, V]
        return st.dictionaries(key_strat, val_strat, max_size=10)

    return st.from_type(typ)
```

### Path Parameter Generation

```python
def generate_path_params(
    path_params: dict[str, type],
    path: str,
) -> SearchStrategy[dict[str, Any]]:
    """Generate valid path parameter combinations."""
    strategies = {}
    for name, typ in path_params.items():
        if typ == str:
            strategies[name] = st.text(
                alphabet=st.characters(whitelist_categories=("Ll", "Lu", "Nd")),
                min_size=1, max_size=50
            )
        elif typ == int:
            strategies[name] = st.integers(min_value=1, max_value=10000)
        else:
            strategies[name] = strategy_for_type(typ)
    return st.fixed_dictionaries(strategies)
```

---

## Test Execution

### ASGI Test Client

```python
class RouteTestClient:
    """Async test client for ASGI apps using httpx."""

    def __init__(self, app: Any) -> None:
        self.app = app
        self.transport = ASGITransport(app=app)

    async def request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json: Any = None,
        headers: dict[str, str] | None = None,
    ) -> Response:
        async with AsyncClient(
            transport=self.transport,
            base_url="http://test"
        ) as client:
            return await client.request(
                method=method, url=path,
                params=params, json=json, headers=headers or {}
            )
```

### Route Test Runner

```python
class RouteTestRunner:
    """Executes Hypothesis-based smoke tests against routes."""

    def __init__(self, app: Any, config: RouteTestConfig) -> None:
        self.app = app
        self.config = config
        self.client = RouteTestClient(app)

    def create_test(self, route: RouteInfo) -> Callable[[], None]:
        """Create a Hypothesis test for a route."""

        @settings(max_examples=self.config.max_examples, deadline=None)
        @given(
            path_params=generate_path_params(route.path_params),
            body=generate_body(route.body_type),
        )
        def test_route(path_params, body):
            formatted_path = self._format_path(route.path, path_params)
            response = asyncio.run(
                self.client.request(route.methods[0], formatted_path, json=body)
            )
            self._validate_response(response, route)

        return test_route
```

---

## Package Structure

> **Note**: ✅ = Implemented in Phase 1, 🆕 = New/Updated in Phase 2

```
src/pytest_routes/
├── __init__.py              # Public API exports ✅
├── __metadata__.py          # Version info ✅
├── py.typed                 # PEP 561 marker ✅
├── plugin.py                # Pytest plugin hooks ✅🆕
├── config.py                # RouteTestConfig ✅🆕
│
├── discovery/               # Route extraction ✅🆕
│   ├── __init__.py
│   ├── base.py              # RouteInfo, RouteExtractor protocol
│   ├── litestar.py          # LitestarExtractor + query params 🆕
│   ├── starlette.py         # StarletteExtractor + query params 🆕
│   └── openapi.py           # OpenAPIExtractor (full) 🆕
│
├── generation/              # Hypothesis strategies ✅🆕
│   ├── __init__.py
│   ├── strategies.py        # Type-to-strategy mapping (enhanced) 🆕
│   ├── headers.py           # Header generation strategies 🆕
│   ├── path.py              # Path parameter generation
│   └── body.py              # Request body generation
│
├── execution/               # Test execution ✅🆕
│   ├── __init__.py
│   ├── client.py            # ASGI test client
│   └── runner.py            # RouteTestRunner + validation 🆕
│
├── validation/              # Response validation 🆕
│   ├── __init__.py          # Validation exports
│   └── response.py          # Response validators (Status, ContentType, JsonSchema, OpenAPI, Composite)
│
└── auth/                    # Auth support (Planned)
    ├── __init__.py
    └── providers.py         # Auth token providers
```

---

## Implementation Phases

### Phase 1: Core Infrastructure (v0.1.0) - Complete ✅

**Goal**: Basic route discovery and smoke testing

**Deliverables**:
- [x] Project scaffolding and tooling
- [x] Core protocols (`RouteInfo`, `RouteExtractor`)
- [x] `LitestarExtractor` implementation
- [x] `StarletteExtractor` implementation
- [x] Type-to-strategy mapping
- [x] Path/body generation
- [x] ASGI test client
- [x] Route test runner
- [x] Pytest plugin with CLI options
- [x] CLI options (`--routes`, `--routes-app`, `--routes-exclude`, etc.)
- [x] Route filtering (include/exclude patterns)
- [x] Enhanced error reporting with shrunk examples
- [x] Integration tests (71 tests passing)
- [ ] Basic documentation

### Phase 2: Framework Support (v0.2.0)

**Goal**: Enhanced framework compatibility

**Deliverables**:
- [ ] `OpenAPIExtractor` (full implementation)
- [ ] Query parameter extraction
- [ ] Header generation
- [ ] Pydantic model support
- [ ] Dataclass support
- [ ] Custom strategy registration
- [ ] Framework auto-detection

### Phase 3: Configuration & Auth (v0.3.0)

**Goal**: Production-ready configuration

**Deliverables**:
- [ ] `pyproject.toml` configuration parsing
- [ ] Route filtering (include/exclude patterns)
- [ ] Authentication support (Bearer, API key)
- [ ] Per-route overrides
- [ ] Detailed failure reporting

### Phase 4: Reporting & Polish (v0.4.0)

**Goal**: Enhanced developer experience

**Deliverables**:
- [ ] HTML report generation
- [ ] Coverage metrics per route
- [ ] Shrunk example display
- [ ] Performance metrics
- [ ] Comprehensive documentation

### Phase 5: Advanced Features (v1.0.0)

**Goal**: Stable release

**Deliverables**:
- [ ] Stateful testing (CRUD flows)
- [ ] WebSocket route testing
- [ ] Response schema validation
- [ ] Fuzz testing mode
- [ ] CI/CD integration examples

---

## API Reference

### Public API

```python
from pytest_routes import (
    # Configuration
    RouteTestConfig,

    # Discovery
    RouteInfo,
    RouteExtractor,
    get_extractor,

    # Generation
    strategy_for_type,
    register_strategy,

    # Execution
    RouteTestRunner,
    RouteTestClient,
    RouteTestFailure,  # Detailed error reporting

    # Decorators (planned)
    smoke_test,
)
```

### CLI Options

```bash
# Basic usage
pytest --routes --routes-app myapp:app

# With options
pytest --routes \
    --routes-app myapp:app \
    --routes-max-examples 50 \
    --routes-exclude "/health,/metrics"

# Filter specific routes
pytest --routes -k "GET:/users"
```

### pyproject.toml Configuration

```toml
[tool.pytest-routes]
app = "myapp:app"
max_examples = 100
timeout = 30.0

include = ["/api/*"]
exclude = ["/health", "/metrics", "/openapi*"]
methods = ["GET", "POST", "PUT", "DELETE"]

fail_on_5xx = true
allowed_status_codes = [200, 201, 204, 400, 401, 403, 404, 422]

[tool.pytest-routes.auth]
bearer_token = "${API_TOKEN}"
```

---

## Design Decisions

### 1. Schema-Optional Extraction

**Decision**: Extract routes from app internals, not just OpenAPI

**Rationale**:
- Works without OpenAPI schema requirement
- Catches routes that aren't in schema
- Framework-specific optimizations possible
- OpenAPI available as optional enhancement

### 2. Hypothesis-Based Generation

**Decision**: Use Hypothesis for all input generation

**Rationale**:
- Property-based testing finds edge cases
- Shrinking provides minimal failing examples
- Stateful testing possible for CRUD flows
- Industry-proven approach (Schemathesis)

### 3. HTTPX ASGI Transport

**Decision**: Use httpx with ASGITransport for testing

**Rationale**:
- No server startup required
- Consistent with Litestar/Starlette testing patterns
- Async-native
- Request/response inspection

### 4. Protocol-Based Extractors

**Decision**: Use Protocol for RouteExtractor interface

**Rationale**:
- Structural typing for flexibility
- Users can add custom extractors
- No inheritance required
- Clean separation from frameworks

### 5. Fixture-Based App Loading

**Decision**: Support both CLI `--routes-app` and pytest fixtures

**Rationale**:
- CLI for simple cases
- Fixtures for complex setup (DB, auth)
- Consistent with pytest patterns
- Configuration flexibility

---

## Dependencies

**Required**:
- `pytest >= 7.0`
- `hypothesis >= 6.0`
- `httpx >= 0.24`

**Optional (Framework Support)**:
- `litestar >= 2.0` - First-class support
- `fastapi >= 0.100` - Full support
- `starlette >= 0.27` - Full support

**Development**:
- `uv` - Package management
- `ruff` - Linting and formatting
- `mypy` - Type checking
- `pytest-cov` - Coverage

---

## References

- **Schemathesis** - OpenAPI property testing (inspiration)
- **Hypothesis** - Property-based testing framework
- **HTTPX** - Modern async HTTP client
- **Litestar Testing** - Framework testing patterns
- **pytest Plugin Development** - Entry points and hooks

---

*Document Version: 1.1.0*
*Last Updated: 2025-11-30*
*Author: Claude (Architecture Review)*
*Status: Phase 1 Complete - Ready for Phase 2*
