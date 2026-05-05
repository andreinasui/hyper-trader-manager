# HyperTrader Manager - Development Commands
# Install just: https://github.com/casey/just#installation

set shell := ["bash", "-cu"]

# Default recipe - show help
default:
    @just --list

# ─────────────────────────────────────────────────────────────
# Development Shortcuts (delegate to subdirectories)
# ─────────────────────────────────────────────────────────────

# Run backend API (delegates to api/justfile)
api:
    cd api && just dev

# Run frontend web (delegates to web/justfile)
web:
    cd web && just dev

# Install all dependencies
install:
    cd api && just install-dev
    cd web && just install

# Create a new release (usage: just release 1.2.3 or just release 1.2.3 --dry-run)
release version *args:
    ./scripts/release.sh {{version}} {{args}}

# Simulate update UI states for manual testing (dev compose only)
update-test *args:
    ./scripts/dev-update-test.sh {{args}}

# ─────────────────────────────────────────────────────────────
# Docker Build Commands
# ─────────────────────────────────────────────────────────────

# Build API Docker image
build-api:
    docker build -f docker/Dockerfile.api -t hyper-trader-api .

# Build Web Docker image
build-web:
    docker build -f web/Dockerfile -t hyper-trader-web .

# Build all images
build-all: build-api build-web

# ─────────────────────────────────────────────────────────────
# Verification Commands
# ─────────────────────────────────────────────────────────────

# Check development prerequisites
check-prereqs:
    @echo "Checking prerequisites..."
    @command -v docker >/dev/null 2>&1 || { echo "✗ Docker not found"; exit 1; }
    @echo "✓ Docker"
    @command -v just >/dev/null 2>&1 || { echo "✗ just not found"; exit 1; }
    @echo "✓ just"
    @command -v uv >/dev/null 2>&1 || { echo "✗ uv not found"; exit 1; }
    @echo "✓ uv"
    @command -v nodenv >/dev/null 2>&1 || { echo "✗ nodenv not found"; exit 1; }
    @echo "✓ nodenv"
    @command -v pnpm >/dev/null 2>&1 || { echo "✗ pnpm not found (install: npm install -g pnpm)"; exit 1; }
    @echo "✓ pnpm"
    @echo ""
    @echo "All prerequisites installed!"

# ─────────────────────────────────────────────────────────────
# Info Commands
# ─────────────────────────────────────────────────────────────

# Show development URLs
urls:
    @echo "Development URLs:"
    @echo "  Frontend:    http://localhost:3000"
    @echo "  Backend API: http://localhost:8000"
    @echo "  Swagger:     http://localhost:8000/docs"
    @echo "  ReDoc:       http://localhost:8000/redoc"
    @echo "  SQLite DB:   api/data/hypertrader.db"

# Show quick start guide
quickstart:
    @echo "Quick Start (2 terminals):"
    @echo ""
    @echo "1. Start backend (creates SQLite DB automatically):"
    @echo "   just api"
    @echo "   # Or: cd api && just dev"
    @echo ""
    @echo "2. In a new terminal, start frontend:"
    @echo "   just web"
    @echo "   # Or: cd web && just dev"
    @echo ""
    @echo "3. Open http://localhost:3000"
    @echo ""
    @echo "Database: SQLite file at api/data/hypertrader.db"
    @echo "Reset DB: rm api/data/hypertrader.db && just api"
