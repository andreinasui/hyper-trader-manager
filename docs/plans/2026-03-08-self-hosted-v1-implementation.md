# Self-Hosted V1 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Turn `hyper-trader-manager` into a single-VPS self-hosted product using `SQLite`, `Traefik`, `HTTP-only` access, and local `username/password` admin auth.

**Architecture:** Keep the existing React frontend and FastAPI backend, but replace Privy/Kubernetes/PostgreSQL assumptions with local auth, SQLite persistence, and a Docker-based trader runtime. Serve the UI and API through Traefik on one HTTP entrypoint so the dashboard opens directly at `http://host[:port]`.

**Tech Stack:** React 19 + Vite, FastAPI, SQLAlchemy, SQLite, Traefik, Docker Compose, Docker SDK for Python, JWT or signed bearer tokens, encrypted secrets at rest.

---

### Task 1: Stabilize the current baseline before feature work

**Files:**
- Modify: `api/tests/test_auth.py`
- Modify: `api/tests/test_auth_service.py`
- Modify: `api/tests/test_jwt_service.py`
- Modify: `api/tests/conftest.py`
- Test: `api/tests/test_auth.py`
- Test: `api/tests/test_auth_service.py`
- Test: `api/tests/test_jwt_service.py`

**Step 1: Write a short baseline note in the PR/commit context**

Document that the current branch already fails collection because `hyper_trader_api.services.auth_service` and `hyper_trader_api.services.jwt_service` do not exist, while `api/tests/test_auth.py` targets a completely different auth system than `api/hyper_trader_api/routers/auth.py`.

**Step 2: Replace or quarantine obsolete auth tests**

Refactor tests so they match the codebase you are about to build instead of the dead email/refresh-token design. Keep only tests that still map to the desired local auth target.

```python
def test_placeholder_baseline_note():
    assert True
```

**Step 3: Run backend tests to confirm collection is clean**

Run: `cd api && just test`

Expected: no collection errors; failing tests should now reflect real implementation gaps, not missing modules.

**Step 4: Commit baseline cleanup**

```bash
git add api/tests/test_auth.py api/tests/test_auth_service.py api/tests/test_jwt_service.py api/tests/conftest.py
git commit -m "test: align auth baseline with planned self-hosted rewrite"
```

---

### Task 2: Replace PostgreSQL-first config with SQLite-safe configuration

**Files:**
- Modify: `api/pyproject.toml`
- Modify: `api/hyper_trader_api/config.py`
- Modify: `api/hyper_trader_api/database.py`
- Create: `api/.env.selfhosted.example`
- Test: `api/tests/test_config.py`

**Step 1: Write failing config/database tests**

Create tests for:
- default SQLite database URL
- HTTP base URL / public port parsing
- SQLite engine initialization without PostgreSQL-only pooling assumptions

```python
def test_default_selfhosted_database_url(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    settings = Settings()
    assert settings.database_url.startswith("sqlite")
```

**Step 2: Run the targeted tests and verify failure**

Run: `cd api && uv run pytest tests/test_config.py -v`

Expected: FAIL because the current settings still assume Privy + PostgreSQL.

**Step 3: Implement the new settings surface**

In `api/hyper_trader_api/config.py`, replace Privy/K8s/Postgres-first settings with self-hosted settings:

```python
class Settings(BaseSettings):
    environment: Literal["development", "production"] = "development"
    database_url: str = "sqlite:///./data/hypertrader.db"
    jwt_secret_key: str
    encryption_key: str
    public_base_url: str = "http://localhost:80"
    public_port: int = 80
    docker_socket: str = "unix:///var/run/docker.sock"
    runtime_mode: Literal["docker"] = "docker"
```

In `api/hyper_trader_api/database.py`, branch engine creation for SQLite:

```python
engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False} if settings.database_url.startswith("sqlite") else {},
)
```

In `api/pyproject.toml`, remove `psycopg2-binary` and add `docker` and a password hashing library such as `pwdlib` or `passlib[bcrypt]`.

**Step 4: Run the targeted tests and then full backend tests**

Run:
- `cd api && uv run pytest tests/test_config.py -v`
- `cd api && just test`

Expected: config tests pass; remaining failures are now auth/runtime implementation gaps.

**Step 5: Commit**

```bash
git add api/pyproject.toml api/hyper_trader_api/config.py api/hyper_trader_api/database.py api/.env.selfhosted.example api/tests/test_config.py
git commit -m "chore: prepare api settings for sqlite self-hosted mode"
```

---

### Task 3: Convert the data model to self-hosted SQLite-safe entities

**Files:**
- Modify: `api/hyper_trader_api/models/user.py`
- Modify: `api/hyper_trader_api/models/trader.py`
- Modify: `api/hyper_trader_api/models/__init__.py`
- Create: `api/hyper_trader_api/models/session_token.py`
- Create: `api/hyper_trader_api/db/bootstrap.py`
- Modify: `api/schema.sql`
- Test: `api/tests/test_models.py`

**Step 1: Write failing model/bootstrap tests**

Cover:
- bootstrap creates tables in SQLite
- `users.username` is unique
- `trader_configs` use generic JSON, not PostgreSQL `JSONB`
- token/session rows can be created and revoked

```python
def test_user_username_is_unique(sqlite_session):
    sqlite_session.add(User(username="admin", password_hash="x", is_admin=True))
    sqlite_session.commit()
    sqlite_session.add(User(username="admin", password_hash="y", is_admin=False))
    with pytest.raises(Exception):
        sqlite_session.commit()
```

**Step 2: Run tests to confirm failure**

Run: `cd api && uv run pytest tests/test_models.py -v`

**Step 3: Replace SaaS/K8s/Postgres-specific columns**

Update `api/hyper_trader_api/models/user.py` to a local-admin model:

```python
class User(Base):
    __tablename__ = "users"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    username: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
```

Update `api/hyper_trader_api/models/trader.py` to:
- use `String(36)` IDs instead of PostgreSQL UUID columns
- use `JSON` instead of `JSONB`
- rename `k8s_name` to `runtime_name`
- add `TraderSecret` explicitly
- remove deployment/usage tables unless they are needed in v1

Add `api/hyper_trader_api/models/session_token.py` if refresh/session revocation is kept in v1.

Add `api/hyper_trader_api/db/bootstrap.py` to run `Base.metadata.create_all()` on startup for v1.

**Step 4: Run tests**

Run:
- `cd api && uv run pytest tests/test_models.py -v`
- `cd api && just test`

**Step 5: Commit**

```bash
git add api/hyper_trader_api/models/user.py api/hyper_trader_api/models/trader.py api/hyper_trader_api/models/__init__.py api/hyper_trader_api/models/session_token.py api/hyper_trader_api/db/bootstrap.py api/schema.sql api/tests/test_models.py
git commit -m "refactor: convert data model to sqlite self-hosted schema"
```

---

### Task 4: Implement local username/password bootstrap and auth services

**Files:**
- Create: `api/hyper_trader_api/services/local_auth_service.py`
- Create: `api/hyper_trader_api/services/token_service.py`
- Create: `api/hyper_trader_api/utils/crypto.py`
- Create: `api/tests/test_local_auth_service.py`
- Create: `api/tests/test_token_service.py`

**Step 1: Write failing service tests**

Cover:
- bootstrap admin can be created only once
- username/password authentication succeeds and fails correctly
- token creation and verification work

```python
def test_bootstrap_admin_only_once(mock_db):
    service = LocalAuthService(mock_db)
    service.bootstrap_admin("admin", "secret123")
    with pytest.raises(ValueError, match="already initialized"):
        service.bootstrap_admin("admin2", "secret123")
```

**Step 2: Run tests to confirm failure**

Run:
- `cd api && uv run pytest tests/test_local_auth_service.py -v`
- `cd api && uv run pytest tests/test_token_service.py -v`

**Step 3: Write minimal implementation**

`api/hyper_trader_api/utils/crypto.py`

```python
def hash_password(password: str) -> str: ...
def verify_password(password: str, password_hash: str) -> bool: ...
def encrypt_secret(plaintext: str, key: str) -> str: ...
def decrypt_secret(ciphertext: str, key: str) -> str: ...
```

`api/hyper_trader_api/services/local_auth_service.py`

```python
class LocalAuthService:
    def system_initialized(self) -> bool: ...
    def bootstrap_admin(self, username: str, password: str) -> User: ...
    def authenticate(self, username: str, password: str) -> User | None: ...
```

`api/hyper_trader_api/services/token_service.py`

```python
class TokenService:
    def create_access_token(self, user: User) -> str: ...
    def verify_access_token(self, token: str) -> dict | None: ...
```

**Step 4: Run tests**

Run:
- `cd api && uv run pytest tests/test_local_auth_service.py -v`
- `cd api && uv run pytest tests/test_token_service.py -v`

**Step 5: Commit**

```bash
git add api/hyper_trader_api/services/local_auth_service.py api/hyper_trader_api/services/token_service.py api/hyper_trader_api/utils/crypto.py api/tests/test_local_auth_service.py api/tests/test_token_service.py
git commit -m "feat: add local username auth services for self-hosted mode"
```

---

### Task 5: Replace Privy auth router and middleware with local auth endpoints

**Files:**
- Modify: `api/hyper_trader_api/routers/auth.py`
- Modify: `api/hyper_trader_api/middleware/jwt_auth.py`
- Modify: `api/hyper_trader_api/routers/__init__.py`
- Modify: `api/hyper_trader_api/schemas/auth.py`
- Modify: `api/hyper_trader_api/main.py`
- Test: `api/tests/test_auth.py`

**Step 1: Write failing endpoint tests**

Cover these endpoints:
- `GET /api/v1/auth/setup-status`
- `POST /api/v1/auth/bootstrap`
- `POST /api/v1/auth/login`
- `GET /api/v1/auth/me`
- `POST /api/v1/auth/logout` if implemented

```python
def test_setup_status_returns_uninitialized(client):
    response = client.get("/api/v1/auth/setup-status")
    assert response.status_code == 200
    assert response.json()["initialized"] is False
```

**Step 2: Run targeted tests and confirm failure**

Run: `cd api && uv run pytest tests/test_auth.py -v`

**Step 3: Replace the router and middleware**

In `api/hyper_trader_api/schemas/auth.py`, define:

```python
class SetupStatusResponse(BaseModel):
    initialized: bool

class BootstrapRequest(BaseModel):
    username: str
    password: str

class LoginRequest(BaseModel):
    username: str
    password: str
```

In `api/hyper_trader_api/routers/auth.py`, replace Privy `/me` with local auth endpoints.

In `api/hyper_trader_api/middleware/jwt_auth.py`, replace Privy token validation with local bearer-token validation.

In `api/hyper_trader_api/main.py`, update the API description and auth docs to reflect username/password self-hosted auth, not Privy.

**Step 4: Run tests**

Run:
- `cd api && uv run pytest tests/test_auth.py -v`
- `cd api && just test`

**Step 5: Commit**

```bash
git add api/hyper_trader_api/routers/auth.py api/hyper_trader_api/middleware/jwt_auth.py api/hyper_trader_api/routers/__init__.py api/hyper_trader_api/schemas/auth.py api/hyper_trader_api/main.py api/tests/test_auth.py
git commit -m "feat: replace privy auth with local bootstrap and login"
```

---

### Task 6: Introduce a Docker runtime abstraction for trader lifecycle

**Files:**
- Create: `api/hyper_trader_api/runtime/base.py`
- Create: `api/hyper_trader_api/runtime/docker_runtime.py`
- Create: `api/hyper_trader_api/runtime/factory.py`
- Create: `api/tests/test_docker_runtime.py`
- Modify: `api/pyproject.toml`

**Step 1: Write failing runtime tests**

Cover:
- container create arguments
- restart/remove/status/log behavior
- secret/config file mounting behavior

```python
def test_create_trader_container_uses_internal_network(mock_docker_client):
    runtime = DockerRuntime(mock_docker_client)
    runtime.create_trader_container(...)
    mock_docker_client.containers.run.assert_called_once()
```

**Step 2: Run tests and verify failure**

Run: `cd api && uv run pytest tests/test_docker_runtime.py -v`

**Step 3: Write minimal runtime layer**

`api/hyper_trader_api/runtime/base.py`

```python
class TraderRuntime(Protocol):
    def create_trader(self, trader: Trader, config_path: Path, secret_env: dict[str, str]) -> None: ...
    def restart_trader(self, runtime_name: str) -> None: ...
    def remove_trader(self, runtime_name: str) -> None: ...
    def get_status(self, runtime_name: str) -> dict[str, Any]: ...
    def get_logs(self, runtime_name: str, tail_lines: int) -> str: ...
```

`api/hyper_trader_api/runtime/docker_runtime.py`

```python
class DockerRuntime:
    def __init__(self, client: docker.DockerClient | None = None): ...
```

Use the Docker SDK, not shelling out to `docker` commands from request handlers.

**Step 4: Run tests**

Run:
- `cd api && uv run pytest tests/test_docker_runtime.py -v`
- `cd api && just test`

**Step 5: Commit**

```bash
git add api/hyper_trader_api/runtime/base.py api/hyper_trader_api/runtime/docker_runtime.py api/hyper_trader_api/runtime/factory.py api/tests/test_docker_runtime.py api/pyproject.toml
git commit -m "feat: add docker runtime abstraction for trader lifecycle"
```

---

### Task 7: Rework trader service and schemas around Docker runtime instead of Kubernetes

**Files:**
- Modify: `api/hyper_trader_api/services/trader_service.py`
- Modify: `api/hyper_trader_api/schemas/trader.py`
- Modify: `api/hyper_trader_api/routers/traders.py`
- Create: `api/tests/test_traders.py`

**Step 1: Write failing trader API tests for self-hosted behavior**

Cover:
- create trader stores encrypted secret + config version
- list/get return `runtime_name` and Docker-backed status
- restart/delete call runtime layer
- logs come from runtime layer

```python
def test_create_trader_persists_runtime_name(client, auth_headers):
    response = client.post("/api/v1/traders/", json={...}, headers=auth_headers)
    assert response.status_code == 201
    assert response.json()["runtime_name"].startswith("trader-")
```

**Step 2: Run tests and verify failure**

Run: `cd api && uv run pytest tests/test_traders.py -v`

**Step 3: Replace K8s-specific code paths**

In `api/hyper_trader_api/services/trader_service.py`:
- remove `KubernetesTraderController` dependency
- inject runtime from `runtime/factory.py`
- replace `k8s_name` with `runtime_name`
- write config files into a managed data directory
- encrypt trader secret before persistence

In `api/hyper_trader_api/schemas/trader.py`:
- rename `K8sStatus` to `RuntimeStatus`
- rename `k8s_name` to `runtime_name`
- update descriptions/examples to Docker/self-hosted wording

In `api/hyper_trader_api/routers/traders.py`:
- rewrite descriptions from Kubernetes to local runtime
- update logging to use local username or user id, not `privy_user_id`

**Step 4: Run tests**

Run:
- `cd api && uv run pytest tests/test_traders.py -v`
- `cd api && just test`

**Step 5: Commit**

```bash
git add api/hyper_trader_api/services/trader_service.py api/hyper_trader_api/schemas/trader.py api/hyper_trader_api/routers/traders.py api/tests/test_traders.py
git commit -m "refactor: move trader lifecycle from kubernetes to docker runtime"
```

---

### Task 8: Remove Privy from frontend bootstrap and add setup/login flows

**Files:**
- Modify: `web/src/main.tsx`
- Modify: `web/src/hooks/useAuth.ts`
- Delete: `web/src/hooks/useAuthWithWalletSetup.ts`
- Delete: `web/src/hooks/useWalletSetup.ts`
- Modify: `web/src/routes/index.tsx`
- Modify: `web/src/routes/_authenticated.tsx`
- Modify: `web/src/routes/__root.tsx`
- Create: `web/src/routes/setup.tsx`
- Create: `web/src/components/auth/LoginForm.tsx`
- Create: `web/src/components/auth/BootstrapForm.tsx`
- Test: `web/e2e/auth/login.spec.ts`
- Test: `web/e2e/authenticated/dashboard.spec.ts`

**Step 1: Write failing frontend tests for local auth**

Cover:
- first-run setup screen
- username/password login screen
- redirect to dashboard after login
- redirect unauthenticated users back to `/`

```ts
test('login page shows username and password fields', async ({ page }) => {
  await page.goto('/')
  await expect(page.getByLabel('Username')).toBeVisible()
  await expect(page.getByLabel('Password')).toBeVisible()
})
```

**Step 2: Run tests and confirm failure**

Run:
- `cd web && pnpm test`
- `cd web && pnpm test:e2e -- --grep "Authentication Flow"`

**Step 3: Replace frontend auth plumbing**

In `web/src/main.tsx`, remove `PrivyProvider` and provide plain auth context.

In `web/src/hooks/useAuth.ts`, replace wallet login with API-backed login/setup state:

```ts
export interface AuthUser {
  id: string
  username: string
  is_admin: boolean
}
```

In `web/src/routes/index.tsx`, replace the wallet screen with a username/password login screen.

Add `web/src/routes/setup.tsx` for first-run bootstrap.

Update router auth context in `web/src/routes/__root.tsx` and `web/src/routes/_authenticated.tsx` to use the new user shape.

**Step 4: Run tests**

Run:
- `cd web && pnpm test`
- `cd web && pnpm test:e2e`

**Step 5: Commit**

```bash
git add web/src/main.tsx web/src/hooks/useAuth.ts web/src/routes/index.tsx web/src/routes/_authenticated.tsx web/src/routes/__root.tsx web/src/routes/setup.tsx web/src/components/auth/LoginForm.tsx web/src/components/auth/BootstrapForm.tsx web/e2e/auth/login.spec.ts web/e2e/authenticated/dashboard.spec.ts
git rm web/src/hooks/useAuthWithWalletSetup.ts web/src/hooks/useWalletSetup.ts
git commit -m "feat: add local bootstrap and login flow to web app"
```

---

### Task 9: Update API client, frontend types, and same-origin config

**Files:**
- Modify: `web/src/config.ts`
- Modify: `web/src/lib/api/client.ts`
- Modify: `web/src/lib/api.ts`
- Modify: `web/src/lib/types.ts`
- Regenerate: `web/src/lib/api/generated/*`
- Test: `web/src/lib/__tests__/types.test.ts`

**Step 1: Write failing tests for the new user/runtime types**

```ts
it('models local auth user shape', () => {
  const user: User = { id: '1', username: 'admin', is_admin: true, created_at: '2026-03-08T00:00:00Z' }
  expect(user.username).toBe('admin')
})
```

**Step 2: Run tests and verify failure**

Run: `cd web && pnpm test`

**Step 3: Update client config**

Make the frontend default to same-origin API access:

```ts
const envSchema = z.object({
  VITE_API_URL: z.string().default('/api'),
})
```

Update `web/src/lib/api/client.ts` to keep bearer token support but remove Privy token getter naming.

Update `web/src/lib/types.ts` for:
- `User.username`
- `Trader.runtime_name`
- runtime status fields instead of K8s fields

Regenerate the OpenAPI client against the rewritten API.

**Step 4: Run tests**

Run:
- `cd web && pnpm test`
- `cd web && pnpm build`

**Step 5: Commit**

```bash
git add web/src/config.ts web/src/lib/api/client.ts web/src/lib/api.ts web/src/lib/types.ts web/src/lib/__tests__/types.test.ts web/src/lib/api/generated
git commit -m "refactor: align web api client with self-hosted auth and runtime"
```

---

### Task 10: Package the stack for self-hosted deployment with Traefik

**Files:**
- Create: `docker-compose.selfhosted.yml`
- Create: `deploy/traefik/traefik.yml`
- Create: `deploy/traefik/dynamic.yml`
- Modify: `api/docker/Dockerfile.api`
- Modify: `web/Dockerfile`
- Create: `deploy/.env.selfhosted.example`
- Test: `README.md`

**Step 1: Write a smoke-check script or checklist**

Define the expected stack shape:
- `traefik`
- `api`
- `web`
- persistent `data/` volume for SQLite and app files

**Step 2: Verify current Dockerfiles fail the target packaging assumptions**

Run:
- `docker build -f api/docker/Dockerfile.api .`
- `docker build -f web/Dockerfile web`

Expected: at least the web image needs fixing because it currently copies `.output` rather than a Vite `dist/` build.

**Step 3: Implement production packaging**

`docker-compose.selfhosted.yml`

```yaml
services:
  traefik:
    image: traefik:v3.3
    command:
      - --providers.file.filename=/etc/traefik/dynamic.yml
      - --entrypoints.web.address=:${PUBLIC_PORT:-80}
    ports:
      - "${PUBLIC_PORT:-80}:${PUBLIC_PORT:-80}"

  api:
    labels:
      - traefik.enable=true

  web:
    labels:
      - traefik.enable=true
```

Fix `web/Dockerfile` to build Vite static assets and serve them with a tiny HTTP server or nginx-compatible static image.

Fix `api/docker/Dockerfile.api` to remove K8s-only packages, `kubectl`, and PostgreSQL libraries.

**Step 4: Run packaging verification**

Run:
- `docker compose -f docker-compose.selfhosted.yml config`
- `docker build -f api/docker/Dockerfile.api .`
- `docker build -f web/Dockerfile web`

**Step 5: Commit**

```bash
git add docker-compose.selfhosted.yml deploy/traefik/traefik.yml deploy/traefik/dynamic.yml api/docker/Dockerfile.api web/Dockerfile deploy/.env.selfhosted.example README.md
git commit -m "feat: package self-hosted stack behind traefik"
```

---

### Task 11: Add installer, bootstrap scripts, and operational docs

**Files:**
- Create: `scripts/install-selfhosted.sh`
- Create: `scripts/upgrade-selfhosted.sh`
- Create: `scripts/backup-selfhosted.sh`
- Modify: `README.md`
- Create: `docs/SELF_HOSTED_QUICKSTART.md`
- Create: `docs/SELF_HOSTED_OPERATIONS.md`

**Step 1: Write a smoke-test checklist for the installer**

The checklist must prove:
- compose file starts
- dashboard opens at `http://host[:port]`
- setup status is reachable
- admin bootstrap works

**Step 2: Implement the minimal installer**

`scripts/install-selfhosted.sh`

```bash
#!/usr/bin/env bash
set -euo pipefail
cp deploy/.env.selfhosted.example .env.selfhosted
docker compose --env-file .env.selfhosted -f docker-compose.selfhosted.yml up -d --build
```

Add upgrade and backup scripts for v1 basics.

**Step 3: Rewrite docs from K8s/Privy wording to self-hosted wording**

Update `README.md` and add:
- `docs/SELF_HOSTED_QUICKSTART.md`
- `docs/SELF_HOSTED_OPERATIONS.md`

**Step 4: Verify the docs against real commands**

Run the documented commands once in a clean local environment.

**Step 5: Commit**

```bash
git add scripts/install-selfhosted.sh scripts/upgrade-selfhosted.sh scripts/backup-selfhosted.sh README.md docs/SELF_HOSTED_QUICKSTART.md docs/SELF_HOSTED_OPERATIONS.md
git commit -m "docs: add self-hosted install and operations guides"
```

---

### Task 12: Run end-to-end verification for the v1 self-hosted slice

**Files:**
- Test: `api/tests/test_auth.py`
- Test: `api/tests/test_traders.py`
- Test: `web/e2e/auth/login.spec.ts`
- Test: `web/e2e/authenticated/dashboard.spec.ts`
- Test: `docker-compose.selfhosted.yml`

**Step 1: Run backend verification**

Run: `cd api && just check`

Expected: lint, format check, typecheck, and tests all pass.

**Step 2: Run frontend verification**

Run:
- `cd web && pnpm test`
- `cd web && pnpm build`
- `cd web && pnpm test:e2e`

Expected: green unit and e2e coverage for setup/login/dashboard/trader flow.

**Step 3: Run stack verification**

Run:
- `docker compose -f docker-compose.selfhosted.yml up -d --build`
- `curl http://localhost:${PUBLIC_PORT:-80}/api/v1/auth/setup-status`

Expected:

```json
{"initialized":false}
```

**Step 4: Manual browser verification**

Check:
- `/` shows setup when uninitialized
- bootstrap creates admin
- login redirects to dashboard
- create trader works
- logs and restart work

**Step 5: Commit release candidate state**

```bash
git add .
git commit -m "feat: deliver self-hosted v1 control plane"
```

---

## Rollout Plan

### Rollout 0: Internal branch hardening

- Finish Tasks 1-5 first
- Do not ship packaging until local auth + SQLite + tests are stable
- Exit criteria:
  - backend tests green
  - frontend unit tests green
  - no remaining Privy auth path in runtime code

### Rollout 1: Developer-only self-hosted stack

- Finish Tasks 6-10
- Run the full stack locally with one sample trader
- Exit criteria:
  - `docker compose -f docker-compose.selfhosted.yml up -d --build` works on a clean machine
  - dashboard opens at `http://localhost[:port]`
  - bootstrap/login/trader lifecycle works end to end

### Rollout 2: Friendly-user VPS pilot

- Finish Task 11 and Task 12
- Test on one or two real VPS providers
- Exit criteria:
  - install docs need no repo knowledge
  - bootstrap works on raw IP + custom port
  - backup and upgrade scripts succeed once

### Rollout 3: Public v1 release

- publish images and release notes
- rewrite root docs away from K8s/Privy/Postgres language
- clearly mark supported scope:
  - HTTP only
  - single VPS
  - single local admin
  - SQLite
  - Traefik

### Post-v1 candidates

- HTTPS modes
- multi-user local auth
- richer backups/import-export
- optional PostgreSQL mode
- optional external reverse proxy mode
- optional Kubernetes runtime backend later

## Notes for the Implementer

- `api/hyper_trader_api/services/trader_service.py` is currently tightly coupled to Kubernetes and to `privy_user_id`; replace that coupling early.
- `api/hyper_trader_api/models/trader.py` currently uses PostgreSQL-only `UUID` and `JSONB`; convert those before attempting SQLite integration.
- `web/src/main.tsx`, `web/src/hooks/useAuth.ts`, and `web/src/routes/index.tsx` are the main Privy entrypoints.
- `web/Dockerfile` currently copies `.output`, but `web/package.json` uses a Vite build that produces `dist`; fix this before any release packaging work.
- Current backend tests already show branch debt; clean that debt first so new failures mean something.
