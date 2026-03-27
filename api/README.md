# HyperTrader API

FastAPI backend for the HyperTrader SaaS platform.

## Prerequisites

- Python 3.11+
- [uv](https://github.com/astral-sh/uv) - Fast Python package manager

### Install uv

```bash
# macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Or with pip
pip install uv

# Or with Homebrew
brew install uv
```

## Development Setup

```bash
# Navigate to project root
cd hyper-trader-infra

# Create virtual environment and install all dependencies (including dev)
uv sync --all-extras

# Or install without dev dependencies
uv sync --no-dev
```

## Running the API

```bash
# Using uv run (auto-activates venv)
uv run uvicorn api.main:app --reload --host 0.0.0.0 --port 8000

# Or activate venv manually
source .venv/bin/activate
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
```

## Common Commands

```bash
# Add a new dependency
uv add <package>

# Add a dev dependency
uv add --dev <package>

# Update lockfile after changing pyproject.toml
uv lock

# Update all dependencies to latest compatible versions
uv lock --upgrade

# Run tests
uv run pytest

# Run linter
uv run ruff check api/

# Run formatter
uv run ruff format api/

# Run type checker
uv run mypy api/
```

## Environment Variables

Copy the example env file and configure:

```bash
cp api/.env.example api/.env
```

Required variables:
- `DATABASE_URL` - SQLite connection string (default: `sqlite:///./data/hypertrader.db`)
- `ENCRYPTION_KEY` - Fernet key for encrypting wallet private keys

## API Documentation

When running, visit:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
- OpenAPI JSON: http://localhost:8000/openapi.json

## Docker

Build and run with Docker:

```bash
# Build image
docker build -f docker/Dockerfile.api -t hyper-trader-api .

# Run container
docker run -p 8000:8000 --env-file api/.env hyper-trader-api
```
