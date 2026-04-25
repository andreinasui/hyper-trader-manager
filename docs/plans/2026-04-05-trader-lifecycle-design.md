# Trader Lifecycle Management Design

**Date:** 2026-04-05  
**Status:** Approved

## Overview

Implement a two-phase trader creation flow where configuration is saved separately from container deployment. Users can START, STOP, and DELETE traders with distinct behaviors for each action.

## Requirements

- CREATE: Save config to DB without starting container
- START: Deploy Docker Swarm service with 3 retry attempts
- STOP: Remove container but retain config for later restart
- DELETE: Remove container and all associated data permanently
- UI shows appropriate actions based on trader status

## Lifecycle States

```
                    ┌──────────────┐
                    │  configured  │ ◄─── POST /traders (create config only)
                    └──────┬───────┘
                           │ POST /traders/{id}/start
                           ▼
                    ┌──────────────┐
              ┌────►│   starting   │ (retry loop, max 3 attempts)
              │     └──────┬───────┘
              │            │
              │     ┌──────┴──────┐
              │     ▼             ▼
              │ ┌────────┐   ┌────────┐
              │ │ running│   │ failed │
              │ └───┬────┘   └───┬────┘
              │     │            │
              │     │ POST       │ POST /traders/{id}/start (retry)
              │     │ /stop      │
              │     ▼            │
              │ ┌────────┐       │
              └─┤ stopped│◄──────┘
                └────────┘
                     
        Any state ──► DELETE ──► removed from DB
```

## Data Model Changes

### Trader Status Enum

```python
class TraderStatus(str, Enum):
    CONFIGURED = "configured"  # Config saved, container never created
    STARTING = "starting"      # Container creation in progress
    RUNNING = "running"        # Container running
    STOPPED = "stopped"        # User stopped, config retained
    FAILED = "failed"          # Failed after 3 retry attempts
```

### New Fields on Trader Model

| Field            | Type       | Description                             |
|------------------|------------|-----------------------------------------|
| `start_attempts` | `int`      | Counter for retry attempts (0-3)        |
| `last_error`     | `str?`     | Last error message if failed            |
| `stopped_at`     | `datetime?`| Timestamp when user stopped the trader  |

## API Endpoints

### Modified Endpoints

| Endpoint               | Current Behavior                    | New Behavior                                               |
|------------------------|-------------------------------------|------------------------------------------------------------|
| `POST /traders`        | Creates config + starts container   | Creates config + Docker secret only (status: `configured`) |
| `DELETE /traders/{id}` | Removes service + secret + DB       | Same (removes everything)                                  |

### New Endpoints

| Method | Endpoint              | Description                                            |
|--------|-----------------------|--------------------------------------------------------|
| `POST` | `/traders/{id}/start` | Creates Docker Swarm service with 3 retry attempts     |
| `POST` | `/traders/{id}/stop`  | Removes Docker service only, keeps secret + DB record  |

### Start Endpoint Logic

```
POST /traders/{id}/start
├── Validate trader exists and belongs to user
├── Validate status is "configured" or "stopped" or "failed"
├── Set status = "starting", start_attempts = 0
├── Loop (max 3 attempts):
│   ├── Try create/recreate Swarm service
│   ├── If success: status = "running", return 200
│   └── If fail: increment start_attempts, retry after 2s delay
├── If all retries fail: status = "failed", last_error = message
└── Return response with final status
```

### Stop Endpoint Logic

```
POST /traders/{id}/stop
├── Validate trader exists and belongs to user
├── Validate status is "running" or "starting"
├── Remove Docker service (keep secret)
├── Set status = "stopped", stopped_at = now()
└── Return 200
```

## Docker Runtime Changes

### Method Modifications

| Method            | Change                                          |
|-------------------|-------------------------------------------------|
| `create_trader()` | Split into `create_secret()` + `create_service()` |
| `remove_trader()` | Add parameter `remove_secret: bool = True`      |

### New Methods

```python
def create_secret(self, trader_id: str, private_key: str) -> str:
    """Creates Docker secret, returns secret name."""

def create_service(self, trader: Trader, config_path: Path) -> None:
    """Creates Swarm service using existing secret."""

def remove_service(self, runtime_name: str) -> None:
    """Removes Swarm service only, keeps secret."""
```

## Web UI Design

### Traders List Layout

```
┌─────────────────────────────────────────────────────────────────┐
│ Traders                                            [+ New Trader]│
├─────────────────────────────────────────────────────────────────┤
│ ┌─────────────────────────────────────────────────────────────┐ │
│ │ 0x1234...5678        [configured]    [START]  [DELETE]      │ │
│ └─────────────────────────────────────────────────────────────┘ │
│ ┌─────────────────────────────────────────────────────────────┐ │
│ │ 0xabcd...efgh        [running ●]     [STOP]   [DELETE]      │ │
│ └─────────────────────────────────────────────────────────────┘ │
│ ┌─────────────────────────────────────────────────────────────┐ │
│ │ 0x9876...5432        [stopped]       [START]  [DELETE]      │ │
│ └─────────────────────────────────────────────────────────────┘ │
│ ┌─────────────────────────────────────────────────────────────┐ │
│ │ 0xdead...beef        [failed ✗]      [RETRY]  [DELETE]      │ │
│ │ Error: Connection timeout                                   │ │
│ └─────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

### Button States by Status

| Status       | Primary Action  | Secondary |
|--------------|-----------------|-----------|
| `configured` | START           | DELETE    |
| `starting`   | (spinner)       | -         |
| `running`    | STOP            | DELETE    |
| `stopped`    | START           | DELETE    |
| `failed`     | RETRY (=START)  | DELETE    |

### Status Badges

- `configured` - gray badge
- `starting` - blue badge with spinner
- `running` - green badge with dot
- `stopped` - yellow badge
- `failed` - red badge with X, show error message

### Polling Behavior

- When status is `starting`: poll `/status` every 2 seconds
- When status is `running`: poll every 10 seconds (existing behavior)
- Other statuses: no polling

### Delete Confirmation

Show confirmation dialog: "This will permanently delete the trader and all its configuration. This action cannot be undone."

## Files to Modify

### API

| File                                              | Changes                                                                 |
|---------------------------------------------------|-------------------------------------------------------------------------|
| `api/hyper_trader_api/models/trader.py`           | Add `start_attempts`, `last_error`, `stopped_at` fields; update status enum |
| `api/hyper_trader_api/routers/traders.py`         | Add `/start`, `/stop` endpoints; modify `POST /`                        |
| `api/hyper_trader_api/services/trader_service.py` | Add `start_trader()`, `stop_trader()`; modify `create_trader()`         |
| `api/hyper_trader_api/runtime/docker_runtime.py`  | Split `create_trader()`, add `remove_service()`                         |
| `api/hyper_trader_api/schemas/trader.py`          | Add `StartResponse`, `StopResponse`; update status enum                 |

### Web

| File                               | Changes                                      |
|------------------------------------|----------------------------------------------|
| `web/src/routes/traders/index.tsx` | Add START/STOP/DELETE buttons per status     |
| `web/src/routes/traders/[id].tsx`  | Add action buttons to detail page            |
| `web/src/lib/api.ts`               | Add `startTrader()`, `stopTrader()` functions |
| `web/src/lib/types.ts`             | Update `TraderStatus` type                   |
| `web/src/components/ui/`           | Add confirmation dialog component            |

## Decisions

| Decision                  | Rationale                                                        |
|---------------------------|------------------------------------------------------------------|
| Synchronous start with retry | No background job infrastructure needed; Swarm ops are fast    |
| Keep Docker secret on stop | Allows restart without re-entering private key                  |
| 3 retry attempts          | Balance between resilience and fast failure feedback             |
| 2s delay between retries  | Allows transient issues to resolve                               |
| Polling over WebSockets   | Simpler implementation; no new infrastructure needed             |
