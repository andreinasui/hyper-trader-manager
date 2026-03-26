# Self-Hosted V1 Design

## Goal

Turn `hyper-trader-manager` into a simple self-hosted control plane that runs on a single VPS and opens directly in the browser at `http://ip[:port]` or `http://hostname[:port]`.

## Product Shape

- One installation, one operator, one local admin account
- Same product surface: dashboard, trader CRUD, logs, restart, settings
- No SaaS assumptions in v1
- No Kubernetes in v1
- No Privy in v1
- No PostgreSQL in v1
- HTTP only in v1

## Core Decisions

### Runtime

- Use `Docker Compose` for the top-level stack
- Use the Docker Engine API for trader lifecycle management from the backend
- Keep trader containers on an internal Docker network
- Manage per-trader config and secrets from the API

### Public Edge

- Use `Traefik` as the only public-facing service
- Route `/` to the web app
- Route `/api` to the backend API
- Default to a single configurable HTTP port
- Keep `web`, `api`, and trader containers off direct public ports

### Authentication

- Local auth only
- Bootstrap flow creates the first and only required admin account
- Credentials are `username + password`
- Backend issues local auth tokens after login
- Frontend stores and sends the local token for API requests

### Database

- Replace PostgreSQL with `SQLite`
- Store the database file on a mounted volume
- Use SQLAlchemy with SQLite-safe types and startup schema initialization
- Prefer generic `String`/`JSON` columns over PostgreSQL-only `UUID`/`JSONB`

### Secrets

- Store trader private keys encrypted at rest in SQLite
- Keep the encryption key in environment/config, not in source control
- Never expose private keys back to the frontend after creation

## System Architecture

```
Browser
  -> Traefik (:80 or configured HTTP port)
      -> web (Vite static build)
      -> api (FastAPI)
          -> SQLite file
          -> Docker socket / Docker SDK
          -> trader containers
```

## Backend Responsibilities

- first-run bootstrap detection
- create admin user
- login/logout/current-user endpoints
- local token validation
- trader CRUD
- config versioning
- encrypted secret storage
- create/restart/delete trader containers
- fetch trader status and logs from Docker

## Frontend Responsibilities

- detect uninitialized system and show setup screen
- show username/password login screen when initialized
- keep existing authenticated dashboard and trader pages where possible
- remove Privy provider, wallet setup hooks, and wallet-first copy
- call same-origin API through Traefik

## Non-Goals for V1

- TLS termination inside the product
- Kubernetes support
- multi-user permissions
- billing or usage tiers
- email workflows
- advanced observability stack

## Main Risks

- Current backend branch already has broken auth test references and incomplete model/service pieces
- Current web Dockerfile appears mismatched with a standard Vite output
- SQLite migration requires removal of PostgreSQL-specific schema/model types
- Docker runtime control must be isolated behind a clear abstraction so trader logic does not hardcode Docker details everywhere

## Rollout Shape

### Phase 1

- Stabilize the current branch baseline
- Replace dead auth/service references
- Add plan-approved local auth foundations

### Phase 2

- Introduce SQLite and remove PostgreSQL assumptions
- Introduce runtime abstraction and Docker controller

### Phase 3

- Replace Privy auth in API and web
- Replace Kubernetes trader lifecycle with Docker lifecycle

### Phase 4

- Add production packaging: Traefik, Compose, installer, upgrade path
- Rewrite docs for self-hosted VPS deployment

## Success Criteria

- A user can deploy the stack on one VPS with Docker installed
- A user can open `http://ip[:port]` or `http://hostname[:port]`
- The dashboard loads directly
- The first screen allows bootstrap of a local admin username/password
- The user can create, restart, inspect, and delete trader containers from the dashboard
