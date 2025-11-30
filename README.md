# pytest-routes

[![PyPI](https://img.shields.io/pypi/v/pytest-routes)](https://pypi.org/project/pytest-routes/)
[![Python Version](https://img.shields.io/pypi/pyversions/pytest-routes)](https://pypi.org/project/pytest-routes/)
[![License](https://img.shields.io/github/license/JacobCoffee/pytest-routes)](https://github.com/JacobCoffee/pytest-routes/blob/main/LICENSE)

Property-based smoke testing for ASGI application routes.

## Overview

`pytest-routes` automatically discovers routes from your ASGI application and performs randomized smoke testing using [Hypothesis](https://hypothesis.works/). It works with any ASGI framework, with first-class support for [Litestar](https://litestar.dev/).

### Key Features

- **Automatic Route Discovery** - Extracts routes directly from your ASGI app
- **Property-Based Testing** - Uses Hypothesis to generate diverse test inputs
- **Framework Agnostic** - Works with Litestar, FastAPI, Starlette, and any ASGI app
- **Configurable** - Filter routes, set examples per route, customize validation
- **Zero Config** - Works out of the box with sensible defaults

## Installation

```bash
# With pip
pip install pytest-routes

# With uv
uv add pytest-routes

# With framework extras
uv add "pytest-routes[litestar]"
uv add "pytest-routes[fastapi]"
```

## Quick Start

```bash
# Run smoke tests on your ASGI app
pytest --routes --routes-app myapp:app

# With options
pytest --routes --routes-app myapp:app --routes-max-examples 50
```

Or define your app as a fixture:

```python
# conftest.py
import pytest
from myapp import create_app

@pytest.fixture(scope="session")
def app():
    return create_app()
```

```bash
pytest --routes
```

## Configuration

### CLI Options

| Option | Description | Default |
|--------|-------------|---------|
| `--routes` | Enable route smoke testing | `False` |
| `--routes-app` | Import path to ASGI app | - |
| `--routes-max-examples` | Max Hypothesis examples per route | `100` |
| `--routes-exclude` | Comma-separated patterns to exclude | `/health,/metrics,...` |
| `--routes-include` | Comma-separated patterns to include | - |
| `--routes-methods` | HTTP methods to test | `GET,POST,PUT,PATCH,DELETE` |
| `--routes-seed` | Random seed for reproducibility | - |

### pyproject.toml

```toml
[tool.pytest-routes]
app = "myapp:app"
max_examples = 100
exclude = ["/health", "/metrics", "/docs"]
methods = ["GET", "POST"]
```

## Supported Frameworks

| Framework | Status | Notes |
|-----------|--------|-------|
| Litestar | First-class | Full type extraction |
| FastAPI | Supported | Via Starlette |
| Starlette | Supported | Base ASGI support |

## How It Works

1. **Discovery** - Extracts routes from your ASGI app using framework-specific extractors
2. **Generation** - Creates Hypothesis strategies based on route parameter types
3. **Execution** - Runs property-based tests against each route
4. **Validation** - Checks responses meet smoke test criteria (no 5xx, etc.)

## Documentation

Full documentation available at [jacobcoffee.github.io/pytest-routes](https://jacobcoffee.github.io/pytest-routes)

## License

MIT License - see [LICENSE](LICENSE)
