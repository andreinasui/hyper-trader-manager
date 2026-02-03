# Backend API - Agent Guide

## Technology Stack

- **Language**: Python 3.11+
- **Framework**: FastAPI
- **Database**: PostgreSQL with SQLAlchemy ORM
- **Validation**: Pydantic v2
- **Authentication**: JWT with python-jose, bcrypt
- **Package Manager**: `uv` (NOT pip)
- **Testing**: pytest with pytest-asyncio

## Project Structure

```
api/
├── routers/          # API route handlers
├── services/         # Business logic layer
├── models/           # SQLAlchemy database models
├── schemas/          # Pydantic request/response models
├── middleware/       # Custom middleware
├── utils/            # Utility functions
├── workers/          # Background tasks
├── tests/            # Test files
├── main.py           # FastAPI app entry point
├── database.py       # Database connection
└── config.py         # Configuration management
```

## Development Commands

All commands use `just` - run `just` to see available commands.

### Common Commands
```bash
just dev              # Run API server with hot reload (port 8000)
just test             # Run all tests
just test-cov         # Run tests with coverage report
just lint             # Check code with ruff
just lint-fix         # Auto-fix linting issues
just format           # Format code with ruff
just typecheck        # Run mypy type checking
just check            # Run all quality checks + tests
just clean            # Clean cache files
```

### Setup
```bash
just install-dev      # Install all dependencies including dev tools
just install          # Install production dependencies only
just lock             # Update lockfile
just upgrade          # Upgrade all dependencies
```

## Coding Guidelines

### Style Guide
- **Line length**: 100 characters
- **Linter**: Ruff (replaces flake8, isort, pyupgrade)
- **Formatter**: Ruff format (Black-compatible)
- **Type checker**: mypy with strict mode
- **Import order**: stdlib → third-party → first-party (`api`)

### Code Quality Rules
Configure in `pyproject.toml`:
- Enable: pycodestyle (E/W), Pyflakes (F), isort (I), bugbear (B), comprehensions (C4), pyupgrade (UP)
- Ignore: E501 (line length - handled by formatter), B008 (function calls in defaults)
- Type checking: strict mode, warn on `Any` returns

### Best Practices
1. **Always use type hints** - mypy strict mode is enabled
2. **Use Pydantic models** for validation - schemas in `schemas/`
3. **Async by default** - FastAPI endpoints should be async when possible
4. **Dependency injection** - Use FastAPI's `Depends()` for database sessions, auth, etc.
5. **Environment variables** - Use `.env.development` for local dev (loaded by justfile)
6. **Database queries** - Use SQLAlchemy in `services/`, not in routers

## Testing

### Test Location
- **Test directory**: `tests/`
- **Test file naming**: `test_*.py` (e.g., `test_auth.py`, `test_traders.py`)
- **Test discovery**: pytest finds all `test_*.py` files automatically

### Writing Tests
```python
# tests/test_example.py
import pytest
from fastapi.testclient import TestClient

def test_something(client: TestClient):
    """Test description"""
    response = client.get("/endpoint")
    assert response.status_code == 200
```

### Test Configuration
- **Config**: `pyproject.toml` under `[tool.pytest.ini_options]`
- **Async mode**: Auto-enabled for async tests
- **Fixtures**: Use `tests/conftest.py` for shared fixtures
- **Coverage**: Run `just test-cov` to generate HTML report in `htmlcov/`

### Running Tests
```bash
just test                    # Run all tests
just test tests/test_auth.py # Run specific test file
just test -v                 # Verbose output
just test -k "test_name"     # Run tests matching pattern
just test-cov                # Run with coverage
```

## API Documentation
- **Swagger UI**: http://localhost:8000/docs (when server running)
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI JSON**: http://localhost:8000/openapi.json

## Environment Setup
- **Local config**: Use `.env.development` (auto-loaded by justfile)
- **Example file**: `.env.example` shows required variables
- **Generate secrets**: Run `just gen-keys` for encryption/JWT keys
