# Agents Guide

## Project Structure

| Directory | Description | Tech Stack |
|-----------|-------------|------------|
| `/api` | Backend API | Python 3.11+, FastAPI, SQLAlchemy, PostgreSQL |
| `/web` | Frontend App | React 19, TypeScript, TanStack Router/Query, Tailwind CSS |
| `/kubernetes` | K8s manifests | Deployment configs |
| `/docker` | Docker configs | Container setup |
| `/scripts` | Utility scripts | Automation helpers |

## Development Commands

### Backend (`/api`)
```bash
uv run uvicorn api.main:app --reload  # Run dev server
uv run pytest                          # Run tests
uv run ruff check .                    # Lint
uv run ruff format .                   # Format
```

### Frontend (`/web`)
```bash
pnpm dev          # Run dev server (port 3000)
pnpm build        # Build for production
pnpm test         # Run unit tests
pnpm test:e2e     # Run Playwright e2e tests
```

## Best Practices

1. **Always read before editing** - Understand existing code patterns first
2. **Run tests after changes** - Verify nothing is broken
3. **Follow existing conventions** - Match the code style already in place
4. **Use the right package manager** - `uv` for Python, `pnpm` for Node
5. **Check `justfile`** - Common tasks are defined there
6. **Refer to `DEV_SETUP.md`** - For environment setup details
