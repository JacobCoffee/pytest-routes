# Contributing to pytest-routes

Welcome to pytest-routes! We appreciate your interest in contributing to this property-based smoke testing plugin for ASGI applications. Whether you're fixing a bug, adding a feature, improving documentation, or reporting an issue, your contribution is valuable.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Development Setup](#development-setup)
- [Development Workflow](#development-workflow)
- [Code Standards](#code-standards)
- [Testing Requirements](#testing-requirements)
- [Git Workflow](#git-workflow)
- [Pull Request Process](#pull-request-process)
- [Architecture Overview](#architecture-overview)
- [Adding New Features](#adding-new-features)
- [Documentation Contributions](#documentation-contributions)

---

## Code of Conduct

This project follows the [Litestar Code of Conduct](https://github.com/litestar-org/litestar/blob/main/CODE_OF_CONDUCT.md). By participating, you agree to uphold a welcoming, inclusive, and respectful environment for all contributors.

---

## Development Setup

### Prerequisites

- **Python 3.10+** (supports 3.10, 3.11, 3.12, 3.13)
- **uv** (recommended) or pip for package management
- **Git** for version control

### Installing uv

If you don't have uv installed:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Or use the Makefile target:

```bash
make install-uv
```

### Setting Up the Development Environment

1. **Clone the repository:**

   ```bash
   git clone https://github.com/JacobCoffee/pytest-routes.git
   cd pytest-routes
   ```

2. **Install development dependencies:**

   ```bash
   make dev
   ```

   This installs the package in editable mode with all development dependencies (linting, testing, documentation).

3. **Install pre-commit hooks (optional but recommended):**

   ```bash
   make install-prek
   ```

   This sets up [prek](https://github.com/JacobCoffee/prek) hooks for automated code quality checks on commit.

### Verifying Your Setup

Run the test suite to verify everything is working:

```bash
make test
```

Run all CI checks locally:

```bash
make ci
```

---

## Development Workflow

### Available Make Commands

Use `make help` to see all available commands. Key commands include:

| Command | Description |
|---------|-------------|
| `make dev` | Install with all dev dependencies |
| `make ci` | Run all checks (lint, format, type-check, test) |
| `make test` | Run the test suite |
| `make test-cov` | Run tests with coverage report |
| `make test-fast` | Quick tests without coverage |
| `make lint` | Run linters (ruff, codespell via prek) |
| `make fmt` | Format code with Ruff |
| `make type-check` | Run ty type checker |
| `make docs` | Build documentation |
| `make docs-serve` | Serve docs with live reload (port 8001) |

### Testing Example Applications

The project includes example applications for testing against real frameworks:

```bash
# Test against Litestar app
make test-routes-litestar

# Test against FastAPI app
make test-routes-fastapi

# Test against Starlette app
make test-routes-starlette

# Test all example apps
make test-routes-all
```

### Running Example Applications

To run the example apps locally for manual testing:

```bash
# Litestar on port 8000
make example-litestar

# FastAPI on port 8001
make example-fastapi

# Starlette on port 8002
make example-starlette
```

### Local GitHub Actions Testing

You can run CI workflows locally using [act](https://github.com/nektos/act):

```bash
# Install act (macOS)
brew install act

# Run all CI workflows
make act

# Run specific workflows
make act-ci      # CI workflow only
make act-docs    # Docs workflow only
make act-list    # List available jobs
```

---

## Code Standards

### Python Version and Annotations

- **Target Python 3.10+** - Use features available in 3.10
- **PEP 649 annotations** - Always include the future annotations import:

  ```python
  from __future__ import annotations

  from typing import TYPE_CHECKING

  if TYPE_CHECKING:
      from pytest_routes import RouteInfo
  ```

### Type Hints

- **Full type hints required** - All public APIs must have complete type annotations
- **Strict ty/mypy compatible** - Code must pass the ty type checker (`make type-check`)
- Use `typing.Protocol` for structural typing where appropriate

### Docstrings

Use **Google-style docstrings** for all public classes, methods, and functions:

```python
def extract_routes(self, app: Any) -> list[RouteInfo]:
    """Extract all routes from the application.

    Args:
        app: The ASGI application instance.

    Returns:
        A list of RouteInfo objects representing all discovered routes.

    Raises:
        ValueError: If the application type is not supported.
    """
```

### Code Formatting

- **Ruff** for linting and formatting
- **Line length**: 120 characters
- **Quote style**: Double quotes
- **Indent style**: Spaces (4 spaces)

Run formatting:

```bash
make fmt
```

Check formatting without changes:

```bash
make fmt-check
```

### Import Organization

Imports are organized by Ruff's isort rules:

1. Standard library imports
2. Third-party imports
3. First-party imports (`pytest_routes`, `tests`)

---

## Testing Requirements

### Test Framework

- **pytest 8.0+** for test execution
- **Hypothesis** for property-based testing (core to this project)
- **pytest-asyncio** for async test support
- **pytest-cov** for coverage reporting

### Coverage Target

We aim for **90% test coverage** on all modules. Check coverage with:

```bash
make test-cov
```

### Test Structure

Tests are organized by module:

```
tests/
├── conftest.py              # Shared fixtures
├── test_plugin.py           # Plugin registration tests
├── test_config.py           # Configuration tests
├── discovery/
│   ├── test_litestar.py     # Litestar extractor tests
│   ├── test_starlette.py    # Starlette extractor tests
│   └── test_openapi.py      # OpenAPI extractor tests
├── generation/
│   └── test_strategies.py   # Strategy generation tests
└── execution/
    └── test_runner.py       # Test runner tests
```

### Running Tests

```bash
# Run all tests
make test

# Run fast (no coverage)
make test-fast

# Run specific file
uv run pytest tests/test_plugin.py

# Run by pattern
uv run pytest -k "test_litestar"

# Run with verbose output
uv run pytest -v
```

### Writing Tests

When adding new functionality, write tests that:

1. Cover the happy path
2. Cover edge cases and error conditions
3. Use Hypothesis for property-based testing where applicable
4. Use appropriate markers (`@pytest.mark.unit`, `@pytest.mark.integration`)

Example test:

```python
from __future__ import annotations

import pytest
from hypothesis import given, strategies as st

from pytest_routes.generation.strategies import strategy_for_type


class TestStrategyForType:
    """Tests for type-to-strategy mapping."""

    def test_int_strategy_produces_integers(self) -> None:
        """Integer strategy should produce valid integers."""
        strategy = strategy_for_type(int)
        example = strategy.example()
        assert isinstance(example, int)

    @given(st.integers())
    def test_integers_are_bounded(self, value: int) -> None:
        """Generated integers should be within reasonable bounds."""
        # Property-based test
        strategy = strategy_for_type(int)
        # ... assertions
```

---

## Git Workflow

### Commit Messages

Use **conventional commits**:

- `feat:` - New feature
- `fix:` - Bug fix
- `docs:` - Documentation only
- `chore:` - Maintenance tasks
- `test:` - Test additions or fixes
- `refactor:` - Code refactoring

Examples:

```bash
git commit -m "feat: add query parameter extraction for FastAPI"
git commit -m "fix: handle empty path parameters in Litestar extractor"
git commit -m "docs: add contributing guide"
git commit -m "test: add integration tests for OpenAPI extractor"
```

### Atomic Commits

Each commit should represent **one logical unit of work**. If your change involves multiple logical steps, split them into separate commits.

### Branching

- Create feature branches from `main`
- Use descriptive branch names: `feature/query-params`, `fix/litestar-extraction`

Using git worktrees (recommended for parallel work):

```bash
# Create a worktree for a feature branch
make wt NAME=my-feature

# List worktrees
make wt-ls

# Jump to a worktree
cd $(make wt-j NAME=my-feature)
```

---

## Pull Request Process

### Before Submitting

1. **Run all CI checks locally:**

   ```bash
   make ci
   ```

   This runs linting, formatting, type-checking, and tests.

2. **Test with example apps:**

   ```bash
   make test-routes-all
   ```

3. **Verify GitHub Actions locally (optional):**

   ```bash
   make act-ci
   ```

### Creating a Pull Request

1. Push your branch to GitHub
2. Create a PR against `main`
3. Fill out the PR template with:
   - Summary of changes
   - Related issues
   - Test plan
   - Screenshots/output (if applicable)

### PR Requirements

- All CI checks must pass
- Code review approval required
- Coverage should not decrease significantly
- Documentation updated for new features

### After PR Review

- Address all review comments
- Push fixes as new commits (for easier review)
- Re-request review after addressing feedback
- PRs are squash-merged to keep main history clean

---

## Architecture Overview

pytest-routes follows a modular architecture with clear separation of concerns:

```
src/pytest_routes/
├── plugin.py           # Pytest plugin hooks & fixtures
├── config.py           # Configuration models
├── discovery/          # Route extraction from ASGI apps
│   ├── base.py         # Abstract RouteExtractor protocol
│   ├── litestar.py     # Litestar-specific extraction
│   ├── starlette.py    # Starlette/FastAPI extraction
│   └── openapi.py      # OpenAPI schema-based extraction
├── generation/         # Hypothesis strategy generation
│   ├── strategies.py   # Type-to-strategy mapping
│   ├── headers.py      # Header generation strategies
│   ├── path.py         # Path parameter generation
│   └── body.py         # Request body generation
├── validation/         # Response validation
│   └── response.py     # Status, ContentType, JsonSchema validators
└── execution/          # Test execution
    ├── runner.py       # Test execution engine
    └── client.py       # ASGI test client wrapper
```

For detailed architecture documentation, see [PLAN.md](PLAN.md).

---

## Adding New Features

### Adding a New Route Extractor

To support a new ASGI framework:

1. **Create the extractor module:**

   ```python
   # src/pytest_routes/discovery/my_framework.py
   from __future__ import annotations

   from typing import TYPE_CHECKING, Any

   from pytest_routes.discovery.base import RouteExtractor, RouteInfo

   if TYPE_CHECKING:
       pass


   class MyFrameworkExtractor(RouteExtractor):
       """Extract routes from MyFramework applications."""

       def supports(self, app: Any) -> bool:
           """Check if this extractor supports the given app."""
           return hasattr(app, "__class__") and app.__class__.__name__ == "MyFramework"

       def extract_routes(self, app: Any) -> list[RouteInfo]:
           """Extract all routes from the application."""
           routes = []
           # Framework-specific extraction logic
           for route in app.routes:
               routes.append(
                   RouteInfo(
                       path=route.path,
                       methods=route.methods,
                       name=route.name,
                       handler=route.handler,
                       path_params={},
                       query_params={},
                       body_type=None,
                       tags=[],
                       deprecated=False,
                   )
               )
           return routes
   ```

2. **Register the extractor** in `discovery/__init__.py`

3. **Add tests** in `tests/discovery/test_my_framework.py`

4. **Update documentation**

### Adding a New Type Strategy

To add support for a new type in Hypothesis generation:

1. **Register using the public API:**

   ```python
   from hypothesis import strategies as st
   from pytest_routes.generation.strategies import register_strategy

   # Register a strategy for a custom type
   register_strategy(MyCustomType, st.builds(MyCustomType, name=st.text()))
   ```

2. **Or use the decorator:**

   ```python
   from pytest_routes.generation.strategies import strategy_provider

   @strategy_provider(MyCustomType)
   def my_custom_strategy():
       return st.builds(MyCustomType, name=st.text(min_size=1))
   ```

3. **Add tests** for the new strategy

### Adding a New Validator

To add response validation:

1. **Create a validator class** implementing the validator protocol:

   ```python
   from pytest_routes.validation.response import ResponseValidator

   class MyValidator(ResponseValidator):
       """Custom response validator."""

       def validate(self, response: Response, route: RouteInfo) -> ValidationResult:
           # Validation logic
           if condition_met:
               return ValidationResult(valid=True)
           return ValidationResult(valid=False, error="Validation failed")
   ```

2. **Add tests** in `tests/validation/`

---

## Documentation Contributions

### Documentation Stack

- **Sphinx** for documentation generation
- **MyST Parser** for Markdown support
- **Shibuya theme** for modern styling
- **sphinx-autodoc-typehints** for type hint documentation

### Building Documentation

```bash
# Build docs
make docs

# Serve with live reload
make docs-serve
```

Documentation is served at `http://localhost:8001`.

### Documentation Structure

```
docs/
├── conf.py              # Sphinx configuration
├── index.rst            # Landing page
├── getting-started.rst  # Quick start guide
├── user-guide/          # Detailed usage guides
├── api/                 # API reference (autodoc)
└── contributing.rst     # Link to this file
```

### Writing Documentation

- Use **MyST Markdown** for most content
- Use **reStructuredText** for advanced Sphinx directives
- Include **code examples** that are tested
- Link to relevant **API reference** using cross-references

---

## Questions?

- **Issues**: Open an issue on [GitHub](https://github.com/JacobCoffee/pytest-routes/issues)
- **Discord**: Join the [Litestar Discord](https://discord.gg/litestar-919193495116337154)
- **Discussions**: Use [GitHub Discussions](https://github.com/JacobCoffee/pytest-routes/discussions) for questions

Thank you for contributing to pytest-routes!
