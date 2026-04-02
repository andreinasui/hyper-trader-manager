# Docker Swarm Secrets Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace SQLite-stored encrypted private keys with Docker Swarm native secrets, switching from standalone containers to Swarm services.

**Architecture:** Remove `TraderSecret` model and `encryption_key` config. Use Docker SDK `client.secrets.create()` to store private keys, and `client.services.create()` with `SecretReference` to attach secrets to trader services. Initialize Swarm mode if not already active.

**Tech Stack:** Python 3.11+, FastAPI, SQLAlchemy, Docker SDK for Python (`docker` package), Docker Swarm

---

## Task 1: Remove TraderSecret Model

**Files:**
- Modify: `hyper_trader_api/models/trader.py:94-99` (remove relationship)
- Modify: `hyper_trader_api/models/trader.py:163-212` (remove class)
- Modify: `hyper_trader_api/models/__init__.py:14,22` (remove exports)

**Step 1: Remove TraderSecret relationship from Trader class**

In `hyper_trader_api/models/trader.py`, delete lines 94-99:

```python
    secret: Mapped[Optional["TraderSecret"]] = relationship(
        "TraderSecret",
        back_populates="trader",
        uselist=False,
        cascade="all, delete-orphan",
    )
```

**Step 2: Remove TraderSecret class**

In `hyper_trader_api/models/trader.py`, delete lines 163-212 (entire `TraderSecret` class).

**Step 3: Remove TraderSecret from models/__init__.py**

Update `hyper_trader_api/models/__init__.py` to:

```python
"""
SQLAlchemy models for HyperTrader API.

This package exports all database models for easy importing:

    from hyper_trader_api.models import User, Trader, TraderConfig, SSLConfig
"""

from hyper_trader_api.models.session_token import SessionToken
from hyper_trader_api.models.ssl_config import SSLConfig
from hyper_trader_api.models.trader import (
    Trader,
    TraderConfig,
)
from hyper_trader_api.models.user import User

__all__ = [
    "User",
    "Trader",
    "TraderConfig",
    "SessionToken",
    "SSLConfig",
]
```

**Step 4: Remove TraderSecret import from bootstrap.py**

In `hyper_trader_api/db/bootstrap.py`, remove line 31:

```python
from hyper_trader_api.models.trader import TraderSecret  # noqa: F401
```

**Step 5: Run tests to verify model removal doesn't break unrelated tests**

Run: `just test tests/test_models.py -v -k "not TraderSecret"`

Expected: Tests pass (TraderSecret tests will fail, that's expected)

**Step 6: Commit**

```bash
git add hyper_trader_api/models/trader.py hyper_trader_api/models/__init__.py hyper_trader_api/db/bootstrap.py
git commit -m "refactor: remove TraderSecret model and database table"
```

---

## Task 2: Remove Encryption Key and Crypto Functions

**Files:**
- Modify: `hyper_trader_api/config.py:62,84-91` (remove encryption_key)
- Modify: `hyper_trader_api/utils/crypto.py:49-102` (remove encrypt/decrypt)

**Step 1: Remove encryption_key from Settings**

In `hyper_trader_api/config.py`, remove line 62:

```python
    encryption_key: str = "dev-encryption-key-change-in-production"
```

And remove the validator at lines 84-91:

```python
    @field_validator("encryption_key")
    @classmethod
    def validate_secrets(cls, v: str, info: ValidationInfo) -> str:
        """Require real secrets in production, allow defaults in development."""
        env = os.getenv("ENVIRONMENT", "development")
        if env == "production" and v.startswith("dev-"):
            raise ValueError(f"{info.field_name} must be set to a secure value in production")
        return v
```

Also remove unused import `ValidationInfo` from line 16 if no longer needed.

**Step 2: Remove encrypt_secret and decrypt_secret from crypto.py**

In `hyper_trader_api/utils/crypto.py`, remove the Fernet import and functions. Final file:

```python
"""
Cryptography utilities for password hashing.

Uses bcrypt for password hashing.
"""

import bcrypt


def hash_password(password: str) -> str:
    """
    Hash a password using bcrypt.

    Args:
        password: Plain text password to hash

    Returns:
        Bcrypt password hash string
    """
    password_bytes = password.encode("utf-8")
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password_bytes, salt)
    return hashed.decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    """
    Verify a password against a hash.

    Args:
        password: Plain text password to verify
        password_hash: Bcrypt hash to verify against

    Returns:
        True if password matches hash, False otherwise
    """
    try:
        password_bytes = password.encode("utf-8")
        hash_bytes = password_hash.encode("utf-8")
        return bcrypt.checkpw(password_bytes, hash_bytes)
    except Exception:
        # Invalid hash format or other verification errors
        return False
```

**Step 3: Run lint to check for unused imports**

Run: `just lint`

Expected: No errors related to removed code

**Step 4: Commit**

```bash
git add hyper_trader_api/config.py hyper_trader_api/utils/crypto.py
git commit -m "refactor: remove encryption_key setting and Fernet crypto functions"
```

---

## Task 3: Update Runtime Protocol for Swarm Services

**Files:**
- Modify: `hyper_trader_api/runtime/base.py`

**Step 1: Update TraderRuntime protocol**

Replace the entire `hyper_trader_api/runtime/base.py` with:

```python
"""
Base protocol for trader runtime abstraction.

Defines the interface that all runtime implementations must follow
for managing trader services lifecycle using Docker Swarm.
"""

from pathlib import Path
from typing import Any, Protocol


class TraderRuntime(Protocol):
    """
    Protocol for trader service runtime operations.

    Defines the interface for creating and managing trader services
    using Docker Swarm with native secret management.
    """

    def create_trader(
        self,
        trader: Any,  # Trader model instance
        config_path: Path,
        private_key: str,
    ) -> None:
        """
        Create Docker secret and start a new trader service.

        Creates a Docker secret for the private key, then creates a Swarm
        service with the secret attached.

        Args:
            trader: Trader model instance with runtime_name, image_tag, wallet_address
            config_path: Path to config JSON file to mount into service
            private_key: Plain text private key to store as Docker secret

        Raises:
            APIError: If service with same name already exists
            OSError: If config file doesn't exist or isn't readable
        """
        ...

    def restart_trader(self, runtime_name: str) -> None:
        """
        Force update a trader service to trigger restart.

        Args:
            runtime_name: Service name to restart

        Raises:
            NotFound: If service doesn't exist
        """
        ...

    def remove_trader(self, runtime_name: str, trader_id: str) -> None:
        """
        Stop service and remove associated Docker secret.

        Args:
            runtime_name: Service name to remove
            trader_id: Trader ID used in secret naming

        Raises:
            NotFound: If service doesn't exist
        """
        ...

    def get_status(self, runtime_name: str) -> dict[str, Any]:
        """
        Get current status of a trader service.

        Args:
            runtime_name: Service name to check

        Returns:
            Status dictionary with keys:
            - state: Service state (running, complete, not_found, etc.)
            - running: Boolean indicating if service has running tasks
            - replicas: Current/desired replica count

            For missing services, returns: {"state": "not_found", "running": False}
        """
        ...

    def get_logs(self, runtime_name: str, tail_lines: int) -> str:
        """
        Get recent logs from a trader service.

        Args:
            runtime_name: Service name
            tail_lines: Number of recent log lines to retrieve

        Returns:
            Log output as string. Empty string if service doesn't exist.
        """
        ...
```

**Step 2: Commit**

```bash
git add hyper_trader_api/runtime/base.py
git commit -m "refactor: update runtime protocol for Swarm services with secret management"
```

---

## Task 4: Implement Swarm-Based Docker Runtime

**Files:**
- Modify: `hyper_trader_api/runtime/docker_runtime.py`

**Step 1: Rewrite DockerRuntime for Swarm**

Replace entire `hyper_trader_api/runtime/docker_runtime.py` with:

```python
"""
Docker Swarm runtime implementation for trader lifecycle management.

Manages trader services using Docker Swarm with native secret management.
"""

from pathlib import Path
from typing import Any

import docker
from docker.errors import APIError, NotFound
from docker.types import (
    EndpointSpec,
    Mount,
    RestartPolicy,
    SecretReference,
    ServiceMode,
)


class DockerRuntime:
    """
    Docker Swarm-based implementation of trader runtime.

    Manages trader services with Docker secrets for private keys,
    proper network isolation, and config mounting.
    """

    NETWORK_NAME = "hyper-trader-internal"
    IMAGE_PREFIX = "hyper-trader"
    SECRET_PREFIX = "ht"

    def __init__(self, client: docker.DockerClient | None = None):
        """
        Initialize Docker runtime.

        Args:
            client: Docker client instance. If None, creates from environment.
        """
        self.client = client or docker.from_env()
        self._ensure_swarm()

    def _ensure_swarm(self) -> None:
        """
        Ensure Docker is in Swarm mode, initialize if needed.

        Single-node swarm is sufficient for secret management.
        """
        try:
            self.client.swarm.attrs
        except APIError:
            # Not in swarm mode, initialize
            self.client.swarm.init()

    def _ensure_network(self) -> None:
        """
        Ensure the internal overlay network exists for swarm services.

        Creates an overlay network for trader services to communicate
        securely without exposing ports to the host.
        """
        try:
            self.client.networks.get(self.NETWORK_NAME)
        except NotFound:
            self.client.networks.create(
                self.NETWORK_NAME,
                driver="overlay",
                attachable=True,
            )

    def _get_secret_name(self, trader_id: str) -> str:
        """Generate secret name from trader ID."""
        return f"{self.SECRET_PREFIX}_{trader_id}_private_key"

    def create_trader(
        self,
        trader: Any,
        config_path: Path,
        private_key: str,
    ) -> None:
        """
        Create Docker secret and start a new trader service.

        Args:
            trader: Trader model with runtime_name, image_tag, wallet_address, id
            config_path: Path to JSON config file to mount
            private_key: Plain text private key to store as Docker secret

        Raises:
            APIError: If service with same name already exists
            OSError: If config file doesn't exist
        """
        # Ensure network exists
        self._ensure_network()

        # Verify config file exists
        if not config_path.exists():
            raise OSError(f"Config file not found: {config_path}")

        # Create Docker secret for private key
        secret_name = self._get_secret_name(trader.id)
        secret = self.client.secrets.create(
            name=secret_name,
            data=private_key.encode(),
            labels={"trader_id": trader.id, "managed_by": "hyper-trader-manager"},
        )

        # Build image name
        image = f"{self.IMAGE_PREFIX}:{trader.image_tag}"

        # Configure mounts
        mounts = [
            Mount(
                target="/app/config.json",
                source=str(config_path.absolute()),
                type="bind",
                read_only=True,
            ),
        ]

        # Create secret reference for the service
        secret_refs = [
            SecretReference(
                secret_id=secret.id,
                secret_name=secret_name,
                filename="private_key",
            ),
        ]

        # Create and start service
        self.client.services.create(
            image=image,
            name=trader.runtime_name,
            mode=ServiceMode("replicated", replicas=1),
            networks=[self.NETWORK_NAME],
            mounts=mounts,
            secrets=secret_refs,
            restart_policy=RestartPolicy(condition="any", max_attempts=0),
            endpoint_spec=EndpointSpec(mode="vip"),
            env=[f"WALLET_ADDRESS={trader.wallet_address}"],
        )

    def restart_trader(self, runtime_name: str) -> None:
        """
        Force update a trader service to trigger restart.

        Args:
            runtime_name: Service name

        Raises:
            NotFound: If service doesn't exist
        """
        service = self.client.services.get(runtime_name)
        service.force_update()

    def remove_trader(self, runtime_name: str, trader_id: str) -> None:
        """
        Stop service and remove associated Docker secret.

        Args:
            runtime_name: Service name to remove
            trader_id: Trader ID for secret lookup

        Raises:
            NotFound: If service doesn't exist
        """
        # Remove service first
        service = self.client.services.get(runtime_name)
        service.remove()

        # Remove the secret
        secret_name = self._get_secret_name(trader_id)
        try:
            secret = self.client.secrets.get(secret_name)
            secret.remove()
        except NotFound:
            # Secret already removed, that's fine
            pass

    def get_status(self, runtime_name: str) -> dict[str, Any]:
        """
        Get current status of a trader service.

        Args:
            runtime_name: Service name to check

        Returns:
            Status dict with state, running flag, and replica info
        """
        try:
            service = self.client.services.get(runtime_name)
            attrs = service.attrs

            # Get task info
            tasks = service.tasks()
            running_tasks = [t for t in tasks if t.get("Status", {}).get("State") == "running"]

            # Get replicas info
            spec = attrs.get("Spec", {})
            mode = spec.get("Mode", {})
            replicated = mode.get("Replicated", {})
            desired_replicas = replicated.get("Replicas", 1)

            status: dict[str, Any] = {
                "state": "running" if running_tasks else "pending",
                "running": len(running_tasks) > 0,
                "replicas": f"{len(running_tasks)}/{desired_replicas}",
            }

            # Add creation time if available
            if "CreatedAt" in attrs:
                status["started_at"] = attrs["CreatedAt"]

            return status

        except NotFound:
            return {
                "state": "not_found",
                "running": False,
            }

    def get_logs(self, runtime_name: str, tail_lines: int) -> str:
        """
        Get recent logs from a trader service.

        Args:
            runtime_name: Service name
            tail_lines: Number of recent lines to retrieve

        Returns:
            Log output as string, empty if service not found
        """
        try:
            service = self.client.services.get(runtime_name)
            # Service logs returns a generator
            logs_gen = service.logs(stdout=True, stderr=True, tail=tail_lines)
            # Collect and decode logs
            logs_bytes = b"".join(logs_gen)
            return logs_bytes.decode("utf-8")
        except NotFound:
            return ""
```

**Step 2: Commit**

```bash
git add hyper_trader_api/runtime/docker_runtime.py
git commit -m "feat: implement Docker Swarm runtime with native secret management"
```

---

## Task 5: Update TraderService to Use Docker Secrets

**Files:**
- Modify: `hyper_trader_api/services/trader_service.py`

**Step 1: Update imports**

Remove encryption imports and TraderSecret. Change line 16 from:

```python
from hyper_trader_api.models import Trader, TraderConfig, TraderSecret, User
```

To:

```python
from hyper_trader_api.models import Trader, TraderConfig, User
```

Remove line 19:

```python
from hyper_trader_api.utils.crypto import decrypt_secret, encrypt_secret
```

**Step 2: Update create_trader method**

Replace the `create_trader` method (lines 86-184) with:

```python
    def create_trader(self, user: User, trader_data: TraderCreate) -> Trader:
        """
        Create a new trader.

        Args:
            user: Owner User object
            trader_data: Trader creation data

        Returns:
            Created Trader model

        Raises:
            ValueError: If wallet address already exists
            TraderServiceError: If container deployment fails
        """
        # Check if wallet already exists
        existing = (
            self.db.query(Trader)
            .filter(Trader.wallet_address == trader_data.wallet_address.lower())
            .first()
        )
        if existing:
            raise ValueError(f"Trader already exists for wallet: {trader_data.wallet_address}")

        # Ensure config has self_account.address matching wallet_address
        config = trader_data.config.copy()
        if "self_account" not in config:
            config["self_account"] = {}
        config["self_account"]["address"] = trader_data.wallet_address

        runtime_name = self._get_runtime_name(trader_data.wallet_address)

        # Create trader in DB first
        trader = Trader(
            user_id=user.id,
            wallet_address=trader_data.wallet_address.lower(),
            runtime_name=runtime_name,
            status="pending",
            image_tag=self.settings.image_tag,
        )
        self.db.add(trader)
        self.db.flush()  # Get the ID without committing

        # Create config version 1
        trader_config = TraderConfig(
            trader_id=trader.id,
            config_json=config,
            version=1,
        )
        self.db.add(trader_config)
        self.db.flush()

        # Write config file
        try:
            config_path = self._write_config_file(trader)
        except Exception as e:
            self.db.rollback()
            raise TraderServiceError(f"Failed to write config file: {e}") from e

        # Deploy to Docker runtime with private key as Docker secret
        try:
            self.runtime.create_trader(trader, config_path, trader_data.private_key)

            # Update status to running
            trader.status = "running"
            self.db.commit()
            self.db.refresh(trader)

            logger.info(f"Trader created: {runtime_name} for user {user.username}")
            return trader

        except Exception as e:
            # Mark as failed but keep in DB for troubleshooting
            trader.status = "failed"
            self.db.commit()
            logger.error(f"Failed to deploy trader {runtime_name}: {e}")
            raise TraderServiceError(f"Container deployment failed: {e}") from e
```

**Step 3: Update delete_trader method**

Replace the `delete_trader` method (lines 287-318) with:

```python
    def delete_trader(self, trader_id: uuid.UUID, user_id: str) -> None:
        """
        Delete a trader.

        Args:
            trader_id: Trader's UUID
            user_id: Owner's user ID

        Raises:
            TraderNotFoundError: If trader doesn't exist
            TraderOwnershipError: If user doesn't own trader
            TraderServiceError: If deletion fails
        """
        trader = self.get_trader(trader_id, user_id)

        # Remove from Docker runtime (service + secret)
        try:
            self.runtime.remove_trader(trader.runtime_name, trader.id)
        except Exception as e:
            logger.error(f"Failed to remove trader {trader.runtime_name} from runtime: {e}")
            raise TraderServiceError(f"Service deletion failed: {e}") from e

        # Delete config file
        config_path = self._get_config_path(str(trader.id))
        if config_path.exists():
            config_path.unlink()

        # Delete from DB (cascade will delete configs)
        self.db.delete(trader)
        self.db.commit()

        logger.info(f"Trader deleted: {trader.runtime_name}")
```

**Step 4: Run linter to verify changes**

Run: `just lint`

Expected: No errors

**Step 5: Commit**

```bash
git add hyper_trader_api/services/trader_service.py
git commit -m "refactor: update TraderService to use Docker secrets instead of DB encryption"
```

---

## Task 6: Update Schema Documentation

**Files:**
- Modify: `schema.sql`

**Step 1: Remove trader_secrets table from schema.sql**

Remove lines 55-63:

```sql
-- Trader secrets
-- Stores encrypted private keys (one per trader)
CREATE TABLE trader_secrets (
    id VARCHAR(36) PRIMARY KEY,
    trader_id VARCHAR(36) UNIQUE REFERENCES traders(id) ON DELETE CASCADE,
    private_key_encrypted TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

Also update the header comment (lines 12-13) to remove mention of trader_secrets:

From:
```sql
--   trader_secrets   - Encrypted private keys for traders
```

To: (delete this line)

**Step 2: Commit**

```bash
git add schema.sql
git commit -m "docs: remove trader_secrets table from schema reference"
```

---

## Task 7: Update Tests

**Files:**
- Modify: `tests/test_models.py`
- Modify: `tests/test_traders.py`
- Modify: `tests/test_config.py`

**Step 1: Remove TraderSecret tests from test_models.py**

Remove import of TraderSecret (line 27):
```python
from hyper_trader_api.models.trader import TraderSecret
```

Remove entire `TestTraderSecretModel` class (lines 273-329).

Update `test_bootstrap_creates_all_tables` to remove `"trader_secrets"` from expected tables (line 77).

**Step 2: Update test_traders.py**

Remove `trader.secret` mock setup in `mock_trader` fixture (lines 71-72):
```python
    trader.secret = MagicMock()
    trader.secret.private_key_encrypted = "encrypted_private_key"
```

Update `test_create_trader_stores_version_1` test - remove TraderSecret references:
- Remove from import (line 289)
- Remove secret object tracking (lines 325-326, 365-367)
- Remove mock_encrypt and mock_decrypt patches and their setup

**Step 3: Update test_config.py**

Remove `test_encryption_key_required` test (lines 26-37) since encryption_key no longer exists.

**Step 4: Run all tests**

Run: `just test`

Expected: All tests pass

**Step 5: Commit**

```bash
git add tests/test_models.py tests/test_traders.py tests/test_config.py
git commit -m "test: update tests to remove TraderSecret and encryption_key references"
```

---

## Task 8: Add Swarm Runtime Tests

**Files:**
- Create: `tests/test_docker_runtime.py`

**Step 1: Create runtime tests**

Create `tests/test_docker_runtime.py`:

```python
"""
Tests for Docker Swarm runtime implementation.

Tests the DockerRuntime class with mocked Docker client.
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from docker.errors import APIError, NotFound


class TestDockerRuntimeSwarmInit:
    """Tests for Swarm initialization."""

    @patch("hyper_trader_api.runtime.docker_runtime.docker")
    def test_initializes_swarm_if_not_active(self, mock_docker):
        """Runtime should initialize swarm if not already active."""
        mock_client = MagicMock()
        # Simulate not in swarm mode
        mock_client.swarm.attrs.__getitem__.side_effect = APIError("not in swarm")
        mock_docker.from_env.return_value = mock_client

        from hyper_trader_api.runtime.docker_runtime import DockerRuntime

        DockerRuntime(mock_client)

        mock_client.swarm.init.assert_called_once()

    @patch("hyper_trader_api.runtime.docker_runtime.docker")
    def test_skips_swarm_init_if_already_active(self, mock_docker):
        """Runtime should not reinitialize if already in swarm mode."""
        mock_client = MagicMock()
        # Simulate already in swarm mode
        mock_client.swarm.attrs = {"ID": "swarm-id"}
        mock_docker.from_env.return_value = mock_client

        from hyper_trader_api.runtime.docker_runtime import DockerRuntime

        DockerRuntime(mock_client)

        mock_client.swarm.init.assert_not_called()


class TestDockerRuntimeCreateTrader:
    """Tests for creating trader services."""

    @patch("hyper_trader_api.runtime.docker_runtime.docker")
    def test_create_trader_creates_secret(self, mock_docker, tmp_path):
        """create_trader should create a Docker secret for private key."""
        mock_client = MagicMock()
        mock_client.swarm.attrs = {"ID": "swarm-id"}
        mock_secret = MagicMock()
        mock_secret.id = "secret-123"
        mock_client.secrets.create.return_value = mock_secret
        mock_docker.from_env.return_value = mock_client

        from hyper_trader_api.runtime.docker_runtime import DockerRuntime

        runtime = DockerRuntime(mock_client)

        # Create config file
        config_path = tmp_path / "config.json"
        config_path.write_text("{}")

        # Mock trader
        trader = MagicMock()
        trader.id = "trader-123"
        trader.runtime_name = "trader-abc"
        trader.image_tag = "latest"
        trader.wallet_address = "0x1234"

        runtime.create_trader(trader, config_path, "0xprivatekey")

        # Verify secret was created
        mock_client.secrets.create.assert_called_once()
        call_kwargs = mock_client.secrets.create.call_args.kwargs
        assert call_kwargs["name"] == "ht_trader-123_private_key"
        assert call_kwargs["data"] == b"0xprivatekey"
        assert call_kwargs["labels"]["trader_id"] == "trader-123"

    @patch("hyper_trader_api.runtime.docker_runtime.docker")
    def test_create_trader_creates_service_with_secret(self, mock_docker, tmp_path):
        """create_trader should create a service with secret attached."""
        mock_client = MagicMock()
        mock_client.swarm.attrs = {"ID": "swarm-id"}
        mock_secret = MagicMock()
        mock_secret.id = "secret-123"
        mock_client.secrets.create.return_value = mock_secret
        mock_docker.from_env.return_value = mock_client

        from hyper_trader_api.runtime.docker_runtime import DockerRuntime

        runtime = DockerRuntime(mock_client)

        config_path = tmp_path / "config.json"
        config_path.write_text("{}")

        trader = MagicMock()
        trader.id = "trader-123"
        trader.runtime_name = "trader-abc"
        trader.image_tag = "v1.0"
        trader.wallet_address = "0x1234"

        runtime.create_trader(trader, config_path, "0xprivatekey")

        # Verify service was created
        mock_client.services.create.assert_called_once()
        call_kwargs = mock_client.services.create.call_args.kwargs
        assert call_kwargs["name"] == "trader-abc"
        assert call_kwargs["image"] == "hyper-trader:v1.0"
        assert len(call_kwargs["secrets"]) == 1


class TestDockerRuntimeRemoveTrader:
    """Tests for removing trader services."""

    @patch("hyper_trader_api.runtime.docker_runtime.docker")
    def test_remove_trader_removes_service_and_secret(self, mock_docker):
        """remove_trader should remove both service and secret."""
        mock_client = MagicMock()
        mock_client.swarm.attrs = {"ID": "swarm-id"}
        mock_service = MagicMock()
        mock_client.services.get.return_value = mock_service
        mock_secret = MagicMock()
        mock_client.secrets.get.return_value = mock_secret
        mock_docker.from_env.return_value = mock_client

        from hyper_trader_api.runtime.docker_runtime import DockerRuntime

        runtime = DockerRuntime(mock_client)
        runtime.remove_trader("trader-abc", "trader-123")

        mock_service.remove.assert_called_once()
        mock_secret.remove.assert_called_once()

    @patch("hyper_trader_api.runtime.docker_runtime.docker")
    def test_remove_trader_handles_missing_secret(self, mock_docker):
        """remove_trader should not fail if secret already removed."""
        mock_client = MagicMock()
        mock_client.swarm.attrs = {"ID": "swarm-id"}
        mock_service = MagicMock()
        mock_client.services.get.return_value = mock_service
        mock_client.secrets.get.side_effect = NotFound("not found")
        mock_docker.from_env.return_value = mock_client

        from hyper_trader_api.runtime.docker_runtime import DockerRuntime

        runtime = DockerRuntime(mock_client)

        # Should not raise
        runtime.remove_trader("trader-abc", "trader-123")

        mock_service.remove.assert_called_once()
```

**Step 2: Run new tests**

Run: `just test tests/test_docker_runtime.py -v`

Expected: All tests pass

**Step 3: Commit**

```bash
git add tests/test_docker_runtime.py
git commit -m "test: add Docker Swarm runtime tests"
```

---

## Task 9: Final Verification

**Step 1: Run all quality checks**

Run: `just check`

Expected: All linting, formatting, type checking, and tests pass

**Step 2: Verify no references to removed code remain**

Run: `grep -r "TraderSecret" hyper_trader_api/`

Expected: No results

Run: `grep -r "encryption_key" hyper_trader_api/`

Expected: No results

Run: `grep -r "encrypt_secret\|decrypt_secret" hyper_trader_api/`

Expected: No results

**Step 3: Final commit for any cleanup**

If any issues found, fix and commit:

```bash
git add -A
git commit -m "chore: final cleanup for Docker Swarm secrets migration"
```

---

## Summary of Changes

| File | Action |
|------|--------|
| `models/trader.py` | Remove `TraderSecret` class and relationship |
| `models/__init__.py` | Remove `TraderSecret` export |
| `db/bootstrap.py` | Remove `TraderSecret` import |
| `config.py` | Remove `encryption_key` setting and validator |
| `utils/crypto.py` | Remove `encrypt_secret`/`decrypt_secret` functions |
| `runtime/base.py` | Update protocol for Swarm services |
| `runtime/docker_runtime.py` | Rewrite for Swarm with secret management |
| `services/trader_service.py` | Use Docker secrets instead of DB encryption |
| `schema.sql` | Remove `trader_secrets` table reference |
| `tests/test_models.py` | Remove `TraderSecret` tests |
| `tests/test_traders.py` | Remove encryption mocks |
| `tests/test_config.py` | Remove `encryption_key` test |
| `tests/test_docker_runtime.py` | Add new Swarm runtime tests |
