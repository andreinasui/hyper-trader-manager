# Revert SSL Simulation + Add Pebble-Based Local SSL Testing — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remove the `DEV_SIMULATE_SSL_SETUP` env flag and its branching from production code paths, replacing it with an optional, opt-in local SSL testing setup using Pebble (Let's Encrypt's official local ACME test server) + `localtest.me` so the real production code path can be exercised in development without touching real Let's Encrypt.

**Architecture:**
1. Strip all `dev_simulate_*` settings, router/service branches, and 11 dedicated tests; api goes back to "SSL setup is production-only" semantics.
2. Add a single, well-named optional `acme_ca_server` setting that flows through `TraefikConfigWriter.write_domain_config(domain, email, ca_server=...)`. Default `None` ⇒ Traefik uses Let's Encrypt production. When set, Traefik points at any ACME directory URL (e.g. Pebble's `https://pebble:14000/dir`).
3. Ship a `deploy/docker-compose.pebble.yml` overlay that adds a Pebble service and configures the api with `ACME_CA_SERVER` pointing at it. Engineers run `docker compose -f docker-compose.dev.yml -f docker-compose.pebble.yml up` only when manually testing the SSL wizard.
4. Use `*.localtest.me` (public DNS → `127.0.0.1`) so no `/etc/hosts` edits are needed; the wizard accepts e.g. `hypertrader.localtest.me`, Pebble issues a cert for it, Traefik serves HTTPS on `:443`, browser test works end-to-end.

**Tech Stack:**
- Backend: Python 3.11+, FastAPI, pydantic-settings, SQLAlchemy
- Traefik: v3.3 (file provider), ACME HTTP-01 challenge
- Pebble: `letsencrypt/pebble:latest` Docker image
- Tests: pytest with monkeypatch for settings
- Frontend: SolidStart (no changes in this plan)

---

## File Structure

**Modify:**
- `api/hyper_trader_api/config.py` — drop `dev_simulate_ssl_setup`, `dev_simulate_ssl_redirect_host`; add optional `acme_ca_server: str | None`.
- `api/hyper_trader_api/services/traefik_config.py` — `write_domain_config` accepts optional `ca_server`; emits `caServer` field under the ACME resolver when set.
- `api/hyper_trader_api/services/ssl_setup_service.py` — drop `is_dev_simulation` branch; pass `settings.acme_ca_server` to `TraefikConfigWriter.write_domain_config`.
- `api/hyper_trader_api/routers/ssl_setup.py` — remove dev-sim allowance; revert `get_ssl_status` to its pre-fix dev-mode short-circuit (returns `ssl_configured=True` in development).
- `api/tests/test_ssl_setup_router.py` — delete `TestSSLSetupRouterDevSimulation` class.
- `api/tests/test_ssl_setup_service.py` — delete `TestConfigureDomainSslDevSimulation` class.
- `api/tests/test_traefik_config.py` *(may not exist; create if absent)* — add cases asserting `caServer` is emitted when supplied, omitted otherwise.
- `api/.env.development` — drop `DEV_SIMULATE_SSL_SETUP` and `DEV_SIMULATE_SSL_REDIRECT_HOST`.
- `deploy/.env.api.development` *(local, gitignored)* — drop the same two vars.

**Create:**
- `deploy/docker-compose.pebble.yml` — Pebble service overlay (compose file fragment).
- `deploy/pebble/pebble-config.json` — Pebble configuration (HTTP-01 challenge port mapping, cert validity).
- `deploy/.env.api.pebble.example` — example env file showing what to set when running with Pebble.
- `docs/SSL_LOCAL_TESTING.md` — short how-to for engineers who need to manually exercise the SSL flow.

**Delete:**
- *(none — all changes are file edits or new files)*

---

## Phase 1 — Revert simulation code

### Task 1: Strip simulation fields from `Settings`

**Files:**
- Modify: `api/hyper_trader_api/config.py:42-49`

- [ ] **Step 1: Remove the two sim fields and add the new one**

Open `api/hyper_trader_api/config.py`. Replace lines 42–49 (the dev-sim block) with:

```python
    # Optional ACME CA server URL (e.g. Pebble for local testing).
    # When None (default) Traefik uses Let's Encrypt production directly.
    # When set, Traefik's ACME resolver points here instead. Used for local
    # SSL testing without hitting real Let's Encrypt rate limits.
    acme_ca_server: str | None = None
```

The full block lines 39–49 should now read:

```python
    # ==================== Environment ====================
    environment: Literal["development", "production"] = "development"

    # Optional ACME CA server URL (e.g. Pebble for local testing).
    # When None (default) Traefik uses Let's Encrypt production directly.
    # When set, Traefik's ACME resolver points here instead. Used for local
    # SSL testing without hitting real Let's Encrypt rate limits.
    acme_ca_server: str | None = None
```

- [ ] **Step 2: Verify imports + module loads**

Run: `cd api && uv run python -c "from hyper_trader_api.config import get_settings; s = get_settings(); print(s.acme_ca_server)"`
Expected: prints `None`.

- [ ] **Step 3: Commit**

```bash
git add api/hyper_trader_api/config.py
git commit -m "api: replace DEV_SIMULATE_SSL_SETUP with ACME_CA_SERVER setting"
```

---

### Task 2: Strip the dev-simulation branch from `SSLSetupService`

**Files:**
- Modify: `api/hyper_trader_api/services/ssl_setup_service.py:56-121`

- [ ] **Step 1: Replace `configure_domain_ssl` body (no sim branch, plumb ca_server)**

Replace lines 56–121 with:

```python
    def configure_domain_ssl(self, domain: str, email: str) -> str:
        """Configure Let's Encrypt SSL for a domain.

        Writes Traefik config, creates acme.json, and restarts Traefik.
        On failure, restores the previous Traefik config.

        Args:
            domain: The domain name for Let's Encrypt certificate.
            email: Email address for Let's Encrypt ACME registration.

        Returns:
            HTTPS redirect URL (https://<domain>).

        Raises:
            SSLSetupError: If configuration fails (backup is restored).
        """
        settings = get_settings()

        if settings.environment != "production":
            raise SSLSetupError("SSL setup is only available in production environment")

        traefik_config_dir = Path(settings.traefik_config_dir)

        writer = TraefikConfigWriter(traefik_config_dir)
        backup = writer.backup_config()

        try:
            # Write new Traefik config for domain mode
            writer.write_domain_config(
                domain,
                email,
                ca_server=settings.acme_ca_server,
            )

            # Restart Traefik container
            self._restart_traefik()

            # Save config to database
            self._save_config(mode="domain", domain=domain, email=email)

            logger.info(f"Domain SSL configured for {domain!r}")
            return f"https://{domain}"

        except Exception as e:
            logger.error(f"Domain SSL setup failed: {e}")
            if backup is not None:
                try:
                    writer.restore_config(backup)
                    logger.info("Restored Traefik config from backup")
                except Exception as restore_err:
                    logger.error(f"Failed to restore Traefik config: {restore_err}")
            if isinstance(e, SSLSetupError):
                raise
            raise SSLSetupError(f"Domain SSL setup failed: {e}") from e
```

- [ ] **Step 2: Run existing service tests (excluding the to-be-deleted sim class)**

Run: `cd api && uv run pytest tests/test_ssl_setup_service.py -v -k "not DevSimulation"`
Expected: all non-sim tests still pass. The sim tests will fail (deleted next task) — ignore those for now.

- [ ] **Step 3: Commit**

```bash
git add api/hyper_trader_api/services/ssl_setup_service.py
git commit -m "api: drop dev-simulation branch from SSLSetupService"
```

---

### Task 3: Strip dev-sim from the SSL router + revert dev short-circuit

**Files:**
- Modify: `api/hyper_trader_api/routers/ssl_setup.py:33-99`

- [ ] **Step 1: Replace `get_ssl_status` (lines 27–62) with the pre-fix version**

```python
@router.get(
    "/ssl-status",
    response_model=SSLStatusResponse,
    summary="Check SSL configuration status",
    description="Check whether SSL has been configured and return current mode, domain, and timestamp.",
)
async def get_ssl_status(
    db: Session = Depends(get_db),
) -> SSLStatusResponse:
    """
    Check current SSL configuration status.

    In development mode, always returns ssl_configured=True to skip SSL setup.

    Returns:
        SSLStatusResponse: ssl_configured flag, mode, domain, and configured_at timestamp
    """
    settings = get_settings()

    # In development mode, skip SSL setup requirement entirely
    if settings.environment == "development":
        return SSLStatusResponse(ssl_configured=True, mode="domain")

    service = SSLSetupService(db)
    config = service.get_ssl_config()

    if config is None:
        return SSLStatusResponse(ssl_configured=False)

    return SSLStatusResponse(
        ssl_configured=True,
        mode=cast(Literal["domain"], config.mode),
        domain=config.domain,
        configured_at=config.configured_at,
    )
```

- [ ] **Step 2: Replace `configure_ssl` body (lines 71–126) — remove dev-sim allowance**

Replace lines 71–126 with:

```python
async def configure_ssl(
    request: SSLSetupRequest,
    db: Session = Depends(get_db),
) -> SSLSetupResponse:
    """
    Configure SSL/HTTPS.

    Args:
        request: SSLSetupRequest with domain and email
        db: Database session

    Returns:
        SSLSetupResponse: success flag, message, and redirect_url

    Raises:
        HTTPException: 403 if not in production
        HTTPException: 400 if SSL is already configured
        HTTPException: 500 if SSL setup fails
    """
    settings = get_settings()
    if settings.environment != "production":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="SSL setup is only available in production environment",
        )

    service = SSLSetupService(db)

    # Check if already configured
    if service.is_ssl_configured():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="SSL is already configured",
        )

    try:
        redirect_url = service.configure_domain_ssl(
            domain=request.domain,
            email=str(request.email),
        )
        return SSLSetupResponse(
            success=True,
            message=f"SSL configured for domain {request.domain}. Redirecting to HTTPS...",
            redirect_url=redirect_url,
        )

    except SSLSetupError as e:
        logger.error(f"SSL setup failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        ) from e
```

- [ ] **Step 3: Run router tests excluding to-be-deleted sim class**

Run: `cd api && uv run pytest tests/test_ssl_setup_router.py -v -k "not DevSimulation"`
Expected: all non-sim tests pass.

- [ ] **Step 4: Commit**

```bash
git add api/hyper_trader_api/routers/ssl_setup.py
git commit -m "api: drop dev-simulation branch from SSL router"
```

---

### Task 4: Delete the simulation test classes

**Files:**
- Modify: `api/tests/test_ssl_setup_router.py` (delete `TestSSLSetupRouterDevSimulation` class entirely)
- Modify: `api/tests/test_ssl_setup_service.py` (delete `TestConfigureDomainSslDevSimulation` class entirely)

- [ ] **Step 1: Locate the sim classes**

Run: `cd api && grep -n "DevSimulation\|dev_simulate" tests/test_ssl_setup_router.py tests/test_ssl_setup_service.py`
Expected: shows the start/end lines of `class TestSSLSetupRouterDevSimulation:` and `class TestConfigureDomainSslDevSimulation:` plus any monkeypatched `dev_simulate_ssl_setup`/`dev_simulate_ssl_redirect_host` references.

- [ ] **Step 2: Delete the entire `TestSSLSetupRouterDevSimulation` class**

Open `api/tests/test_ssl_setup_router.py`. Delete every line from `class TestSSLSetupRouterDevSimulation:` through the end of that class (the next top-level `class ` or end of file). Also delete any imports that become unused (typically `monkeypatch` is still used elsewhere — leave it).

- [ ] **Step 3: Delete the entire `TestConfigureDomainSslDevSimulation` class**

Open `api/tests/test_ssl_setup_service.py`. Same procedure as Step 2 for `class TestConfigureDomainSslDevSimulation:`.

- [ ] **Step 4: Verify no dangling references**

Run: `cd api && grep -rn "dev_simulate\|DevSimulation" .`
Expected: no matches.

- [ ] **Step 5: Run the full api test suite**

Run: `cd api && uv run pytest -q`
Expected: all tests pass (count will be 295 − 11 = 284).

- [ ] **Step 6: Commit**

```bash
git add api/tests/test_ssl_setup_router.py api/tests/test_ssl_setup_service.py
git commit -m "api: remove dev-simulation SSL test classes"
```

---

### Task 5: Clean dev env files

**Files:**
- Modify: `api/.env.development`
- Modify (local, gitignored): `deploy/.env.api.development` — only if it exists in your worktree

- [ ] **Step 1: Strip the two sim vars from `api/.env.development`**

Open `api/.env.development`. Delete the entire `# SSL Setup Simulation (Development Only)` section (the heading comment block plus the two `DEV_SIMULATE_*` lines). The file should end up with: `ENVIRONMENT`, `DATABASE_URL`, `DATA_DIR`, `LOG_LEVEL`.

- [ ] **Step 2: Strip the two sim vars from `deploy/.env.api.development` if present**

Run: `test -f deploy/.env.api.development && sed -i '/DEV_SIMULATE_SSL/d' deploy/.env.api.development; cat deploy/.env.api.development 2>/dev/null || echo "not present"`
Expected: file exists OR "not present"; if it existed, the two sim lines are gone.

- [ ] **Step 3: Verify no references in the worktree**

Run: `grep -rn "DEV_SIMULATE_SSL\|dev_simulate_ssl" . --exclude-dir=node_modules --exclude-dir=.venv --exclude-dir=.worktrees --exclude-dir=test-results --exclude-dir=playwright-report`
Expected: no matches.

- [ ] **Step 4: Commit**

```bash
git add api/.env.development
git commit -m "api: drop DEV_SIMULATE_SSL_* from dev env file"
```

---

## Phase 2 — Plumb `caServer` through `TraefikConfigWriter`

### Task 6: TDD — write failing test for `caServer` emission

**Files:**
- Modify or Create: `api/tests/test_traefik_config.py`

- [ ] **Step 1: Check whether the test file exists**

Run: `ls api/tests/test_traefik_config.py 2>/dev/null && echo EXISTS || echo MISSING`

If MISSING, proceed to Step 2 (create from scratch). If EXISTS, skip to Step 3 (append to it).

- [ ] **Step 2 (only if MISSING): Create the test file with a minimal scaffold**

Create `api/tests/test_traefik_config.py`:

```python
"""Tests for TraefikConfigWriter."""

from pathlib import Path

import yaml

from hyper_trader_api.services.traefik_config import TraefikConfigWriter


def _read_yaml(path: Path) -> dict:
    return yaml.safe_load(path.read_text())
```

- [ ] **Step 3: Append the new tests for `ca_server`**

Append to `api/tests/test_traefik_config.py`:

```python
class TestWriteDomainConfigCAServer:
    """Verify that the optional ca_server kwarg flows into traefik.yml."""

    def test_ca_server_omitted_when_none(self, tmp_path: Path) -> None:
        """Default behaviour: no caServer field in the ACME resolver."""
        writer = TraefikConfigWriter(tmp_path)
        writer.write_domain_config("example.com", "admin@example.com")

        cfg = _read_yaml(tmp_path / "traefik.yml")
        acme = cfg["certificatesResolvers"]["letsencrypt"]["acme"]

        assert "caServer" not in acme
        assert acme["email"] == "admin@example.com"

    def test_ca_server_emitted_when_provided(self, tmp_path: Path) -> None:
        """Explicit ca_server is rendered into the ACME resolver block."""
        writer = TraefikConfigWriter(tmp_path)
        writer.write_domain_config(
            "hypertrader.localtest.me",
            "admin@example.com",
            ca_server="https://pebble:14000/dir",
        )

        cfg = _read_yaml(tmp_path / "traefik.yml")
        acme = cfg["certificatesResolvers"]["letsencrypt"]["acme"]

        assert acme["caServer"] == "https://pebble:14000/dir"
        assert acme["email"] == "admin@example.com"

    def test_ca_server_does_not_affect_dynamic_routers(self, tmp_path: Path) -> None:
        """The dynamic file is unaffected by ca_server."""
        writer = TraefikConfigWriter(tmp_path)
        writer.write_domain_config(
            "hypertrader.localtest.me",
            "admin@example.com",
            ca_server="https://pebble:14000/dir",
        )

        dyn = _read_yaml(tmp_path / "dynamic" / "10-tls.yml")
        rule = dyn["http"]["routers"]["web-tls"]["rule"]
        assert rule == "Host(`hypertrader.localtest.me`)"
```

- [ ] **Step 4: Run the new tests — must fail**

Run: `cd api && uv run pytest tests/test_traefik_config.py::TestWriteDomainConfigCAServer -v`
Expected: 3 tests, ALL FAIL (the second one with `TypeError: write_domain_config() got an unexpected keyword argument 'ca_server'`; the first with KeyError or shape mismatch depending on existing implementation).

- [ ] **Step 5: Commit failing tests**

```bash
git add api/tests/test_traefik_config.py
git commit -m "api: add failing tests for TraefikConfigWriter caServer support"
```

---

### Task 7: Implement `ca_server` parameter in `TraefikConfigWriter`

**Files:**
- Modify: `api/hyper_trader_api/services/traefik_config.py:31-62, 125-162`

- [ ] **Step 1: Update `write_domain_config` signature + threading**

Replace lines 31–62 (the `write_domain_config` method) with:

```python
    def write_domain_config(
        self,
        domain: str,
        email: str,
        ca_server: str | None = None,
    ) -> None:
        """Write Traefik config files for Let's Encrypt (domain) mode.

        Creates traefik.yml (static config with ACME resolver) and
        dynamic/10-tls.yml (TLS routers that reference services defined
        in dynamic/00-bootstrap.yml).

        Args:
            domain: The domain name for routing and TLS certificate.
            email: Email address for Let's Encrypt ACME registration.
            ca_server: Optional ACME CA server URL. When None (default),
                Traefik uses Let's Encrypt's production endpoint. When set
                (e.g. Pebble's "https://pebble:14000/dir"), the resolver
                targets that directory instead — used for local SSL testing.

        Raises:
            TraefikConfigError: If writing configuration files fails.
        """
        try:
            self.config_dir.mkdir(parents=True, exist_ok=True)
            dynamic_dir = self.config_dir / "dynamic"
            dynamic_dir.mkdir(parents=True, exist_ok=True)

            traefik_config = self._build_domain_traefik_yml(email, ca_server)
            dynamic_config = self._build_domain_dynamic_yml(domain)

            self._write_yaml(self.config_dir / "traefik.yml", traefik_config)
            self._write_yaml(dynamic_dir / "10-tls.yml", dynamic_config)

            logger.info(f"Wrote domain Traefik config for {domain!r} to {self.config_dir}")

        except TraefikConfigError:
            raise
        except Exception as e:
            logger.error(f"Failed to write domain Traefik config: {e}")
            raise TraefikConfigError(f"Failed to write domain Traefik config: {e}") from e
```

- [ ] **Step 2: Update `_build_domain_traefik_yml` to accept + emit `caServer`**

Replace lines 125–162 (the `_build_domain_traefik_yml` method) with:

```python
    def _build_domain_traefik_yml(
        self,
        email: str,
        ca_server: str | None = None,
    ) -> dict:  # type: ignore[type-arg]
        """Build traefik.yml config dict for domain (Let's Encrypt) mode."""
        acme: dict = {
            "email": email,
            "storage": "/letsencrypt/acme.json",
            "httpChallenge": {
                "entryPoint": "web",
            },
        }
        if ca_server is not None:
            acme["caServer"] = ca_server

        return {
            "entryPoints": {
                "web": {
                    "address": ":80",
                    "http": {
                        "redirections": {
                            "entryPoint": {
                                "to": "websecure",
                                "scheme": "https",
                            }
                        }
                    },
                },
                "websecure": {
                    "address": ":443",
                },
            },
            "ping": {},
            "certificatesResolvers": {
                "letsencrypt": {
                    "acme": acme,
                }
            },
            "providers": {
                "file": {
                    "directory": "/etc/traefik/dynamic",
                    "watch": True,
                }
            },
        }
```

- [ ] **Step 3: Run the new tests — must now pass**

Run: `cd api && uv run pytest tests/test_traefik_config.py::TestWriteDomainConfigCAServer -v`
Expected: 3 PASS.

- [ ] **Step 4: Run full api suite**

Run: `cd api && uv run pytest -q`
Expected: all green (284 + 3 new = 287).

- [ ] **Step 5: Commit**

```bash
git add api/hyper_trader_api/services/traefik_config.py
git commit -m "api: add optional ca_server param to TraefikConfigWriter"
```

---

### Task 8: TDD — service plumbs `settings.acme_ca_server` to writer

**Files:**
- Modify: `api/tests/test_ssl_setup_service.py` (append a new test class)

- [ ] **Step 1: Append the failing assertion**

Append to `api/tests/test_ssl_setup_service.py` (above any module-level constants if any; otherwise at file end):

```python
class TestConfigureDomainSslPlumbsCAServer:
    """The service must pass settings.acme_ca_server through to the writer."""

    def test_ca_server_forwarded_to_writer(
        self,
        sqlite_session,
        monkeypatch,
        tmp_path,
    ) -> None:
        """When acme_ca_server is set, TraefikConfigWriter.write_domain_config
        receives it as the ca_server kwarg."""
        from hyper_trader_api.config import get_settings
        from hyper_trader_api.services import ssl_setup_service as svc_module

        # Force production env + custom CA + isolated config dir
        get_settings.cache_clear()
        monkeypatch.setenv("ENVIRONMENT", "production")
        monkeypatch.setenv("ACME_CA_SERVER", "https://pebble:14000/dir")
        monkeypatch.setattr(
            svc_module.get_settings.__wrapped__,
            "__defaults__",
            None,
            raising=False,
        )
        # Re-prime cache via the real Settings()
        get_settings.cache_clear()

        # Patch out Traefik restart so we don't hit Docker
        captured: dict = {}

        class FakeWriter:
            def __init__(self, _dir):
                pass

            def backup_config(self):
                return None

            def write_domain_config(self, domain, email, ca_server=None):
                captured["domain"] = domain
                captured["email"] = email
                captured["ca_server"] = ca_server

            def restore_config(self, backup):
                pass

        monkeypatch.setattr(svc_module, "TraefikConfigWriter", FakeWriter)
        monkeypatch.setattr(
            svc_module.SSLSetupService,
            "_restart_traefik",
            lambda self: None,
        )

        service = svc_module.SSLSetupService(sqlite_session)
        result = service.configure_domain_ssl("hypertrader.localtest.me", "a@b.com")

        assert captured["ca_server"] == "https://pebble:14000/dir"
        assert result == "https://hypertrader.localtest.me"

        # Cleanup
        get_settings.cache_clear()
```

- [ ] **Step 2: Run the new test**

Run: `cd api && uv run pytest tests/test_ssl_setup_service.py::TestConfigureDomainSslPlumbsCAServer -v`
Expected: PASS — Task 2 already wired this up. If it FAILS, the bug is in Task 2's edit; fix there before continuing.

> **Note:** This is a regression test confirming Task 2's plumbing. We're writing it after the implementation because the change was a single-line wiring, not new behaviour worth a TDD round-trip on its own. Counts as the "evidence" gate per `verification-before-completion`.

- [ ] **Step 3: Commit**

```bash
git add api/tests/test_ssl_setup_service.py
git commit -m "api: regression test that ssl service forwards acme_ca_server to writer"
```

---

## Phase 3 — Pebble overlay + docs

### Task 9: Create the Pebble config file

**Files:**
- Create: `deploy/pebble/pebble-config.json`

- [ ] **Step 1: Make the dir + write the config**

```bash
mkdir -p deploy/pebble
```

Create `deploy/pebble/pebble-config.json`:

```json
{
  "pebble": {
    "listenAddress": "0.0.0.0:14000",
    "managementListenAddress": "0.0.0.0:15000",
    "certificate": "test/certs/localhost/cert.pem",
    "privateKey": "test/certs/localhost/key.pem",
    "httpPort": 80,
    "tlsPort": 443,
    "ocspResponderURL": "",
    "externalAccountBindingRequired": false,
    "domainBlocklist": []
  }
}
```

> The `httpPort: 80` tells Pebble to expect HTTP-01 validation requests on port 80 of whatever it resolves the challenge target to. Inside our docker network Pebble will reach `traefik:80` which forwards to the api. Validation against `*.localtest.me` works because that hostname resolves to `127.0.0.1` from the host, and inside the docker network we use Traefik's host header routing so Pebble's resolver of the FQDN points to itself only when run on the host — see Task 11 for the wiring that makes this work via a docker network alias.

- [ ] **Step 2: Verify the JSON is valid**

Run: `python -c "import json; json.load(open('deploy/pebble/pebble-config.json'))" && echo OK`
Expected: `OK`.

- [ ] **Step 3: Commit**

```bash
git add deploy/pebble/pebble-config.json
git commit -m "deploy: add Pebble ACME server config for local SSL testing"
```

---

### Task 10: Create the docker-compose Pebble overlay

**Files:**
- Create: `deploy/docker-compose.pebble.yml`

- [ ] **Step 1: Write the overlay**

Create `deploy/docker-compose.pebble.yml`:

```yaml
# Pebble overlay for local SSL testing.
#
# Usage:
#   1. (host) ensure deploy/.env.api.pebble is present (copy from .env.api.pebble.example)
#   2. docker compose \
#        -f docker-compose.dev.yml \
#        -f docker-compose.pebble.yml \
#        --env-file .env.api.pebble \
#        up -d --build
#   3. browse to http://hypertrader.localtest.me/
#   4. submit the SSL wizard with domain=hypertrader.localtest.me
#   5. browser ends up on https://hypertrader.localtest.me (cert is from Pebble — your
#      browser will warn; trust it once for testing).
#
# To return to vanilla dev: drop the -f docker-compose.pebble.yml flag.

services:
  pebble:
    image: letsencrypt/pebble:latest
    container_name: hypertrader-pebble
    restart: unless-stopped
    command:
      - "pebble"
      - "-config"
      - "/test/config/pebble-config.json"
      - "-strict"
      - "false"
      - "-dnsserver"
      - "127.0.0.1:53"
    environment:
      # Skip TLS validation against Pebble's self-signed management API cert
      - PEBBLE_VA_NOSLEEP=1
      - PEBBLE_VA_ALWAYS_VALID=0
    volumes:
      - ./pebble/pebble-config.json:/test/config/pebble-config.json:ro
    networks:
      hypertrader:
        aliases:
          # localtest.me resolves to 127.0.0.1 publicly; inside the docker
          # network we shadow it so Pebble's HTTP-01 challenge against
          # hypertrader.localtest.me reaches our Traefik instead of the host.
          - hypertrader.localtest.me

  # api gets two new env vars when this overlay is loaded:
  #   ACME_CA_SERVER: tells our app to emit caServer= in the rendered traefik.yml
  #   ENVIRONMENT=production: required for the SSL wizard to run at all
  api:
    env_file:
      - .env.api.pebble
    depends_on:
      pebble:
        condition: service_started
```

- [ ] **Step 2: Validate the compose file syntactically**

Run: `cd deploy && docker compose -f docker-compose.dev.yml -f docker-compose.pebble.yml --env-file .env config 2>&1 | head -40`
Expected: prints the merged config; the `pebble` service appears; no `error` lines.

> If you get `error: env file .env.api.pebble does not exist` that's expected — Task 11 creates the example file. Re-run after Task 11.

- [ ] **Step 3: Commit**

```bash
git add deploy/docker-compose.pebble.yml
git commit -m "deploy: add Pebble overlay for local SSL testing"
```

---

### Task 11: Create the Pebble env example file

**Files:**
- Create: `deploy/.env.api.pebble.example`

- [ ] **Step 1: Write the example file**

Create `deploy/.env.api.pebble.example`:

```bash
# ============================================
# HyperTrader API - Local Pebble SSL Testing
# ============================================
# Use this when you want to manually exercise the SSL wizard locally
# without hitting real Let's Encrypt.
#
#   cp .env.api.pebble.example .env.api.pebble
#   docker compose \
#     -f docker-compose.dev.yml \
#     -f docker-compose.pebble.yml \
#     --env-file .env up -d --build

# Force production code paths so the SSL wizard is reachable.
ENVIRONMENT=production

# Point Traefik's ACME resolver at Pebble instead of Let's Encrypt.
ACME_CA_SERVER=https://pebble:14000/dir

DATABASE_URL=sqlite:////app/data/hypertrader-pebble.db
DATA_DIR=/app/data
LOG_LEVEL=DEBUG
```

- [ ] **Step 2: Verify file exists + has the two key vars**

Run: `grep -E '^(ACME_CA_SERVER|ENVIRONMENT)=' deploy/.env.api.pebble.example`
Expected: both lines printed.

- [ ] **Step 3: Re-validate compose**

Run: `cp deploy/.env.api.pebble.example deploy/.env.api.pebble && cd deploy && docker compose -f docker-compose.dev.yml -f docker-compose.pebble.yml --env-file .env config | grep -E 'ACME_CA_SERVER|pebble:' | head -10 && rm deploy/.env.api.pebble`
Expected: shows the `pebble:` service and the `ACME_CA_SERVER` env var on the api service.

- [ ] **Step 4: Commit**

```bash
git add deploy/.env.api.pebble.example
git commit -m "deploy: add example env file for Pebble SSL testing"
```

---

### Task 12: Update `.gitignore` to ignore the real env file

**Files:**
- Modify: `.gitignore` (or `deploy/.gitignore` if scoped)

- [ ] **Step 1: Find the existing env-file ignore line**

Run: `grep -n '\.env' .gitignore deploy/.gitignore 2>/dev/null`
Expected: shows existing `.env*` patterns. If `.env.api.pebble` is already covered by an existing wildcard like `.env*` or `.env.api.*`, skip to Step 3.

- [ ] **Step 2: Add explicit entry if not covered**

If neither file matches `deploy/.env.api.pebble`, append to whichever `.gitignore` already governs `deploy/.env.api.development`:

```
deploy/.env.api.pebble
```

- [ ] **Step 3: Verify it's ignored**

```bash
touch deploy/.env.api.pebble
git status -s deploy/.env.api.pebble
rm deploy/.env.api.pebble
```

Expected: empty output (i.e. file is properly ignored).

- [ ] **Step 4: Commit**

If `.gitignore` was modified:
```bash
git add .gitignore  # or deploy/.gitignore
git commit -m "deploy: ignore .env.api.pebble local override"
```
Otherwise skip.

---

### Task 13: Document the local SSL testing workflow

**Files:**
- Create: `docs/SSL_LOCAL_TESTING.md`

- [ ] **Step 1: Write the doc**

Create `docs/SSL_LOCAL_TESTING.md`:

```markdown
# Local SSL Testing with Pebble

This document explains how to manually test the SSL setup wizard end-to-end
without hitting real Let's Encrypt servers (which have rate limits and require
a real DNS-resolvable domain pointing at your machine).

## What this gives you

- The exact same code path that runs in production:
  `POST /api/v1/setup/ssl` → `TraefikConfigWriter.write_domain_config(...)` →
  Traefik restart → ACME HTTP-01 challenge → certificate issued → HTTPS served.
- A throwaway certificate signed by Pebble's local test CA (browser will warn
  about an untrusted issuer — accept the warning for testing).
- No `/etc/hosts` edits required: `*.localtest.me` is a public DNS name that
  always resolves to `127.0.0.1`.

## When to use this

- You changed code in `services/ssl_setup_service.py`,
  `services/traefik_config.py`, `routers/ssl_setup.py`, or
  `web/src/routes/setup/ssl.tsx`.
- You want to manually click through the SSL wizard in the browser.

For unit-level changes you don't need this — `pytest` covers the rendered
Traefik config; vitest covers the redirect guard. Run those first.

## Setup (one-time)

```bash
cp deploy/.env.api.pebble.example deploy/.env.api.pebble
```

## Run the stack

```bash
cd deploy
docker compose \
  -f docker-compose.dev.yml \
  -f docker-compose.pebble.yml \
  --env-file .env \
  up -d --build
```

Three containers + Pebble come up:

```
hypertrader-traefik   :80, :443
hypertrader-api       :8000
hypertrader-web       :3000
hypertrader-pebble    :14000 (ACME directory), :15000 (management)
```

## Test the flow

1. Browse to `http://hypertrader.localtest.me/`
   (`localtest.me` → 127.0.0.1; Traefik on :80 routes to web)
2. The boot guard redirects you to `/setup/ssl`.
3. Submit the form with:
   - Domain: `hypertrader.localtest.me`
   - Email: anything valid, e.g. `dev@example.com`
4. The api writes a `traefik.yml` whose ACME resolver has
   `caServer: https://pebble:14000/dir` (Pebble) and triggers a Traefik restart.
5. Pebble issues a cert in ~3 seconds.
6. The browser is sent to `https://hypertrader.localtest.me/` — accept the
   "untrusted issuer" warning (Pebble uses its own throwaway CA).
7. Continue through bootstrap → `/traders` as normal.

## Reset

```bash
cd deploy
docker compose \
  -f docker-compose.dev.yml \
  -f docker-compose.pebble.yml \
  down -v   # -v also wipes the sqlite volume
rm -f data/traefik/acme.json data/traefik/dynamic/10-tls.yml
git checkout -- data/traefik/traefik.yml   # if you committed the bootstrap
```

## Why not just run real Let's Encrypt locally?

- Real LE has rate limits (5 cert renewals per registered domain per week).
- Requires a real domain pointed at your machine and ports 80/443 reachable
  from the public internet.
- Generates real certs that get logged in Certificate Transparency logs.

Pebble is Let's Encrypt's **own** test server, written by the same people, and
implements the same ACME protocol — so this exercises the production code
path correctly, just against a throwaway CA.
```

- [ ] **Step 2: Verify the doc renders**

Run: `markdown_lint=$(which mdl 2>/dev/null) && [ -n "$markdown_lint" ] && mdl docs/SSL_LOCAL_TESTING.md || echo "no mdl installed; skipping"; ls -la docs/SSL_LOCAL_TESTING.md`
Expected: file exists; if mdl is installed it prints lint results (any cosmetic warning is fine).

- [ ] **Step 3: Commit**

```bash
git add docs/SSL_LOCAL_TESTING.md
git commit -m "docs: document local SSL testing with Pebble"
```

---

## Phase 4 — End-to-end verification

### Task 14: Verify vanilla dev compose still works (no overlay)

- [ ] **Step 1: Bring up base dev stack**

```bash
cd deploy
rm -f data/sqlitedb/hypertrader-dev.db data/traefik/acme.json data/traefik/dynamic/10-tls.yml
docker compose -f docker-compose.dev.yml --env-file .env up -d --build
sleep 8
docker compose -f docker-compose.dev.yml ps
```

Expected: 3 containers all `(healthy)`.

- [ ] **Step 2: Probe the api**

```bash
curl -s http://localhost/api/v1/setup/ssl-status
echo
curl -s -o /dev/null -w "GET /: %{http_code}\n" http://localhost/
```

Expected:
- `ssl-status` returns `{"ssl_configured":true,"mode":"domain",...}` (dev short-circuit, NOT `false` — proves the dev-mode revert from Task 3 works).
- `GET /` returns `200`.

- [ ] **Step 3: Tear down**

```bash
docker compose -f docker-compose.dev.yml down
```

- [ ] **Step 4: Commit (if any uncommitted leftovers)**

Run: `git status -s` — expected: clean. If anything is dirty (e.g. healthcheck artifacts), investigate.

---

### Task 15: Verify Pebble overlay end-to-end

- [ ] **Step 1: Setup**

```bash
cd deploy
cp .env.api.pebble.example .env.api.pebble
rm -f data/sqlitedb/hypertrader-pebble.db data/traefik/acme.json data/traefik/dynamic/10-tls.yml
```

- [ ] **Step 2: Up the stack**

```bash
docker compose \
  -f docker-compose.dev.yml \
  -f docker-compose.pebble.yml \
  --env-file .env \
  up -d --build
sleep 10
docker compose -f docker-compose.dev.yml -f docker-compose.pebble.yml ps
```

Expected: 4 containers running (`hypertrader-pebble` plus the usual three). The api is `(healthy)`; pebble shows `Up`.

- [ ] **Step 3: Confirm api now sees production env + ACME_CA_SERVER**

```bash
docker exec hypertrader-api env | grep -E '^(ENVIRONMENT|ACME_CA_SERVER)='
```

Expected:
```
ENVIRONMENT=production
ACME_CA_SERVER=https://pebble:14000/dir
```

- [ ] **Step 4: Confirm SSL wizard is reachable (production env)**

```bash
curl -s http://hypertrader.localtest.me/api/v1/setup/ssl-status
```

Expected: `{"ssl_configured":false,"mode":null,"domain":null,"configured_at":null}`
(in production mode the service hits the DB; fresh DB ⇒ unconfigured).

- [ ] **Step 5: Submit the SSL form via curl**

```bash
curl -s -X POST http://hypertrader.localtest.me/api/v1/setup/ssl \
  -H 'Content-Type: application/json' \
  -d '{"domain":"hypertrader.localtest.me","email":"dev@example.com"}'
```

Expected: `{"success":true,"message":"...","redirect_url":"https://hypertrader.localtest.me"}`. Takes ~3-5s while Pebble issues the cert.

- [ ] **Step 6: Verify Traefik picked up the new config**

```bash
sleep 5
curl -k -s -o /dev/null -w "HTTPS GET /: %{http_code}\n" https://hypertrader.localtest.me/
curl -k -s https://hypertrader.localtest.me/api/v1/setup/ssl-status
echo
```

Expected: `HTTPS GET /: 200` and the ssl-status endpoint reports `ssl_configured:true,mode:"domain",domain:"hypertrader.localtest.me"`. The `-k` flag skips cert validation since Pebble's CA isn't trusted by curl.

- [ ] **Step 7: Inspect the rendered traefik.yml**

```bash
grep -A2 'caServer' deploy/data/traefik/traefik.yml
```

Expected: the line `caServer: https://pebble:14000/dir` exists in the resolver block. This proves Task 7 + Task 2 plumbed correctly end-to-end.

- [ ] **Step 8: Tear down**

```bash
docker compose \
  -f docker-compose.dev.yml \
  -f docker-compose.pebble.yml \
  down -v
rm deploy/.env.api.pebble
rm -f data/traefik/acme.json data/traefik/dynamic/10-tls.yml
```

- [ ] **Step 9: Final api test pass**

```bash
cd ../api
uv run pytest -q
uv run ruff check .
```

Expected: all tests green; no lint issues.

- [ ] **Step 10: Final commit if anything was missed**

Run: `git status -s`
Expected: clean.

---

## Done

The repo now has:
1. **Zero `dev_simulate_ssl_*` code in production paths.** API in `development` mode short-circuits SSL status as `configured` (original pre-fix behaviour).
2. **One opt-in mechanism:** `ACME_CA_SERVER` env var, plumbed through the existing `TraefikConfigWriter` API. Default `None` ⇒ Let's Encrypt prod (no behaviour change). Set it ⇒ any ACME server (e.g. Pebble for local testing).
3. **One opt-in compose overlay:** `docker-compose.pebble.yml` + `.env.api.pebble.example` + a one-page doc.

The SSL wizard can now be exercised manually with the same code path that ships to production, against a throwaway CA, with no rate limits or DNS games.
