# Docker Swarm Secrets for Trader Private Keys

## Overview

Migrate from SQLite-stored encrypted private keys to Docker Swarm native secrets. This removes the `trader_secrets` table and `encryption_key` configuration, replacing them with Docker's built-in secret management.

## Motivation

- Docker Swarm secrets provide secure storage without custom encryption
- Secrets are never exposed in `docker inspect` or logs
- Simplifies the codebase by removing encryption infrastructure
- Industry-standard approach for container secret management

## Architecture

### Before (Standalone Docker)

```
┌─────────────┐    ┌──────────────┐    ┌─────────────────┐
│ API Request │───▶│ SQLite DB    │───▶│ Container       │
│ (private_key)    │ (encrypted)  │    │ (env: PRIVATE_KEY)
└─────────────┘    └──────────────┘    └─────────────────┘
```

### After (Docker Swarm)

```
┌─────────────┐    ┌──────────────┐    ┌─────────────────┐
│ API Request │───▶│ Docker Secret│───▶│ Service         │
│ (private_key)    │ (native)     │    │ (/run/secrets/private_key)
└─────────────┘    └──────────────┘    └─────────────────┘
```

## Design Details

### Secret Naming Convention

```
ht_{trader_id}_private_key
```

Example: `ht_550e8400-e29b-41d4-a716-446655440000_private_key`

### Secret Lifecycle

| Event           | Action                                           |
|-----------------|--------------------------------------------------|
| Trader created  | `client.secrets.create(name, data=key.encode())` |
| Trader started  | Secret attached to service via `SecretReference` |
| Trader stopped  | Service removed, secret retained                 |
| Trader deleted  | Service removed, secret removed                  |

### Swarm Initialization

The API must ensure Docker Swarm is initialized before creating traders. On startup or first trader creation:

```python
try:
    client.swarm.attrs  # Check if in swarm mode
except docker.errors.APIError:
    client.swarm.init()  # Initialize single-node swarm
```

### Service vs Container Changes

| Aspect          | Before (Container)                        | After (Service)                             |
|-----------------|-------------------------------------------|---------------------------------------------|
| Creation        | `client.containers.run()`                 | `client.services.create()`                  |
| Restart policy  | `restart_policy={"Name": "unless-stopped"}` | `RestartPolicy(condition="any")`            |
| Secrets         | Environment variable                      | `SecretReference` → `/run/secrets/`         |
| Stop/Remove     | `container.stop(); container.remove()`    | `service.remove()`                          |

### Container Access

Private key available at `/run/secrets/private_key` inside the container.

## Scope

### In Scope

1. Remove `trader_secrets` table and `TraderSecret` model
2. Remove `encryption_key` from config and related encryption functions
3. Switch from standalone Docker containers to Swarm services
4. Use Docker Swarm secrets for private keys
5. Initialize Swarm if not already initialized

### Out of Scope

- Changes to hyper-trader container image (reading from `/run/secrets/` vs env var)

## Components Affected

### Removals

| Component                       | Location                                |
|---------------------------------|-----------------------------------------|
| `TraderSecret` model            | `models/trader.py:163-212`              |
| `TraderSecret` relationship     | `models/trader.py:94-99`                |
| `TraderSecret` exports          | `models/__init__.py`                    |
| `encryption_key` setting        | `config.py:62`                          |
| `encryption_key` validator      | `config.py:84-91`                       |
| `encrypt_secret` function       | `utils/crypto.py:49-74`                 |
| `decrypt_secret` function       | `utils/crypto.py:77-102`                |
| `trader_secrets` table          | `schema.sql:55-63`                      |
| `TraderSecret` bootstrap import | `db/bootstrap.py:31`                    |
| Related tests                   | `tests/test_models.py`, `tests/test_traders.py`, `tests/test_config.py` |

### Modifications

| Component         | Change                                              |
|-------------------|-----------------------------------------------------|
| `DockerRuntime`   | Replace `containers.run()` → `services.create()`    |
| `RuntimeProtocol` | Update interface, remove `secret_env` parameter     |
| `TraderService`   | Create Docker secret instead of DB record           |
| `RuntimeFactory`  | May need updates for Swarm initialization           |

## Code Examples

### Creating a Trader with Secret

```python
# 1. Create Docker secret
secret = self.client.secrets.create(
    name=f"ht_{trader.id}_private_key",
    data=private_key.encode(),
    labels={"trader_id": trader.id}
)

# 2. Create Swarm service with secret attached
from docker.types import SecretReference, RestartPolicy, ServiceMode

self.client.services.create(
    image=f"hyper-trader:{trader.image_tag}",
    name=trader.runtime_name,
    networks=[self.NETWORK_NAME],
    secrets=[SecretReference(
        secret_id=secret.id,
        secret_name=secret.name,
        filename="private_key",
    )],
    mounts=[...],
    restart_policy=RestartPolicy(condition="any"),
    mode=ServiceMode("replicated", replicas=1),
)
```

### Deleting a Trader

```python
# 1. Remove service
service = self.client.services.get(runtime_name)
service.remove()

# 2. Remove secret
secret = self.client.secrets.get(f"ht_{trader_id}_private_key")
secret.remove()
```

## Testing Considerations

- Tests need Docker Swarm mode (can use `docker swarm init` in test setup)
- Mock `client.secrets` and `client.services` in unit tests
- Integration tests should verify secret is accessible at `/run/secrets/private_key`
