# Trader Lifecycle Management Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Implement two-phase trader creation where config is saved separately from container deployment, with START/STOP/DELETE lifecycle actions.

**Architecture:** Modify existing trader CRUD to save config + Docker secret on create (no container), add START endpoint with 3-retry logic for container creation, add STOP endpoint to remove service but keep secret/DB, keep DELETE as full cleanup.

**Tech Stack:** Python 3.11+, FastAPI, SQLAlchemy, Docker SDK, SolidJS, TanStack Query

---

## Task 1: Add New Fields to Trader Model

**Files:**
- Modify: `api/hyper_trader_api/models/trader.py:64-68`

**Step 1: Add new fields to Trader model**

Add `start_attempts`, `last_error`, and `stopped_at` fields after the existing `status` field:

```python
    status: Mapped[str] = mapped_column(
        String(50),
        default="configured",
        index=True,
    )
    start_attempts: Mapped[int] = mapped_column(
        Integer,
        default=0,
    )
    last_error: Mapped[str | None] = mapped_column(
        String(1000),
        nullable=True,
    )
    stopped_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
```

Note: Change the default status from `"pending"` to `"configured"`.

**Step 2: Commit**

```bash
git add api/hyper_trader_api/models/trader.py
git commit -m "api: add lifecycle fields to Trader model"
```

---

## Task 2: Update Trader Schemas

**Files:**
- Modify: `api/hyper_trader_api/schemas/trader.py`

**Step 1: Add TraderStatus enum at top of file (after imports)**

```python
from enum import Enum


class TraderStatus(str, Enum):
    """Valid trader lifecycle states."""
    CONFIGURED = "configured"
    STARTING = "starting"
    RUNNING = "running"
    STOPPED = "stopped"
    FAILED = "failed"
```

**Step 2: Add StartResponse and StopResponse schemas after DeleteResponse**

```python
class StartResponse(BaseModel):
    """Schema for start response."""

    message: str
    trader_id: uuid.UUID
    runtime_name: str
    status: str
    start_attempts: int

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "message": "Trader started successfully",
                "trader_id": "550e8400-e29b-41d4-a716-446655440000",
                "runtime_name": "trader-e221ef33",
                "status": "running",
                "start_attempts": 1,
            }
        }
    )


class StopResponse(BaseModel):
    """Schema for stop response."""

    message: str
    trader_id: uuid.UUID
    runtime_name: str
    status: str

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "message": "Trader stopped successfully",
                "trader_id": "550e8400-e29b-41d4-a716-446655440000",
                "runtime_name": "trader-e221ef33",
                "status": "stopped",
            }
        }
    )
```

**Step 3: Update TraderResponse to include new fields**

Add after `updated_at`:

```python
    start_attempts: int = 0
    last_error: str | None = None
    stopped_at: datetime | None = None
```

**Step 4: Commit**

```bash
git add api/hyper_trader_api/schemas/trader.py
git commit -m "api: add lifecycle schemas and status enum"
```

---

## Task 3: Update Docker Runtime with Separate Methods

**Files:**
- Modify: `api/hyper_trader_api/runtime/docker_runtime.py`

**Step 1: Add create_secret method after _get_secret_name**

```python
    def create_secret(self, trader_id: str, private_key: str) -> str:
        """
        Create Docker secret for trader private key.

        Args:
            trader_id: Trader ID for secret naming
            private_key: Plain text private key

        Returns:
            Secret name

        Raises:
            APIError: If secret creation fails
        """
        secret_name = self._get_secret_name(trader_id)
        
        # Check if secret already exists
        try:
            self.client.secrets.get(secret_name)
            return secret_name  # Already exists
        except NotFound:
            pass
        
        self.client.secrets.create(
            name=secret_name,
            data=private_key.encode(),
            labels={"trader_id": trader_id, "managed_by": "hyper-trader-manager"},
        )
        return secret_name
```

**Step 2: Add create_service method after create_secret**

```python
    def create_service(
        self,
        trader: Any,
        config_path: Path,
    ) -> None:
        """
        Create Docker Swarm service for trader (secret must exist).

        Args:
            trader: Trader model with runtime_name, image_tag, wallet_address, id
            config_path: Path to config file to mount

        Raises:
            APIError: If service creation fails
            NotFound: If secret doesn't exist
        """
        self._ensure_network()

        if not config_path.exists():
            raise OSError(f"Config file not found: {config_path}")

        # Get existing secret
        secret_name = self._get_secret_name(trader.id)
        secret = self.client.secrets.get(secret_name)

        image = f"{self.IMAGE_PREFIX}:{trader.image_tag}"

        mounts = [
            Mount(
                target="/app/config.json",
                source=str(config_path.absolute()),
                type="bind",
                read_only=True,
            ),
        ]

        secret_refs = [
            SecretReference(
                secret_id=secret.id,
                secret_name=secret_name,
                filename="private_key",
            ),
        ]

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
```

**Step 3: Add remove_service method after create_service**

```python
    def remove_service(self, runtime_name: str) -> None:
        """
        Remove Docker Swarm service only (keep secret).

        Args:
            runtime_name: Service name to remove

        Raises:
            NotFound: If service doesn't exist
        """
        service = self.client.services.get(runtime_name)
        service.remove()
```

**Step 4: Update remove_trader to accept remove_secret parameter**

Replace the existing `remove_trader` method:

```python
    def remove_trader(self, runtime_name: str, trader_id: str, remove_secret: bool = True) -> None:
        """
        Stop service and optionally remove associated Docker secret.

        Args:
            runtime_name: Service name to remove
            trader_id: Trader ID for secret lookup
            remove_secret: Whether to also remove the Docker secret (default: True)

        Raises:
            NotFound: If service doesn't exist
        """
        # Remove service first (may not exist if never started)
        try:
            service = self.client.services.get(runtime_name)
            service.remove()
        except NotFound:
            pass  # Service doesn't exist, that's fine

        # Remove the secret if requested
        if remove_secret:
            secret_name = self._get_secret_name(trader_id)
            try:
                secret = self.client.secrets.get(secret_name)
                secret.remove()
            except NotFound:
                pass  # Secret already removed
```

**Step 5: Add service_exists method for checking if service is running**

```python
    def service_exists(self, runtime_name: str) -> bool:
        """
        Check if a Docker Swarm service exists.

        Args:
            runtime_name: Service name to check

        Returns:
            True if service exists, False otherwise
        """
        try:
            self.client.services.get(runtime_name)
            return True
        except NotFound:
            return False
```

**Step 6: Commit**

```bash
git add api/hyper_trader_api/runtime/docker_runtime.py
git commit -m "api: add separate create_secret, create_service, remove_service methods"
```

---

## Task 4: Update Runtime Protocol

**Files:**
- Modify: `api/hyper_trader_api/runtime/base.py`

**Step 1: Read the current base.py file to understand the protocol**

**Step 2: Add new methods to the TraderRuntime protocol**

Add these method signatures:

```python
    def create_secret(self, trader_id: str, private_key: str) -> str:
        """Create Docker secret for trader private key."""
        ...

    def create_service(self, trader: Any, config_path: Path) -> None:
        """Create Docker Swarm service for trader."""
        ...

    def remove_service(self, runtime_name: str) -> None:
        """Remove Docker Swarm service only (keep secret)."""
        ...

    def service_exists(self, runtime_name: str) -> bool:
        """Check if service exists."""
        ...
```

**Step 3: Commit**

```bash
git add api/hyper_trader_api/runtime/base.py
git commit -m "api: add new methods to TraderRuntime protocol"
```

---

## Task 5: Update Trader Service - Create Method

**Files:**
- Modify: `api/hyper_trader_api/services/trader_service.py:108-187`

**Step 1: Update create_trader method to only save config + create secret**

Replace the entire `create_trader` method:

```python
    def create_trader(self, user: User, trader_data: TraderCreate) -> Trader:
        """
        Create a new trader (config only, no container).

        Creates the trader record, config version, config file, and Docker secret.
        Does NOT start the container - use start_trader() for that.

        Args:
            user: Owner User object
            trader_data: Trader creation data

        Returns:
            Created Trader model with status "configured"

        Raises:
            ValueError: If wallet address already exists or config invalid
            TraderServiceError: If secret creation fails
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
        config = trader_data.config.model_dump()
        if "provider_settings" not in config:
            config["provider_settings"] = {}
        if "self_account" not in config["provider_settings"]:
            config["provider_settings"]["self_account"] = {}
        config["provider_settings"]["self_account"]["address"] = trader_data.wallet_address

        # Validate config business rules
        self._validate_config(config, trader_data.wallet_address)

        runtime_name = self._get_runtime_name(trader_data.wallet_address)

        # Create trader in DB
        trader = Trader(
            user_id=user.id,
            wallet_address=trader_data.wallet_address.lower(),
            runtime_name=runtime_name,
            status="configured",
            start_attempts=0,
            image_tag=self.settings.image_tag,
        )
        self.db.add(trader)
        self.db.flush()

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

        # Create Docker secret (but don't start container)
        try:
            self.runtime.create_secret(trader.id, trader_data.private_key)
            self.db.commit()
            self.db.refresh(trader)
            logger.info(f"Trader configured: {runtime_name} for user {user.username}")
            return trader
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to create secret for {runtime_name}: {e}")
            raise TraderServiceError(f"Secret creation failed: {e}") from e
```

**Step 2: Commit**

```bash
git add api/hyper_trader_api/services/trader_service.py
git commit -m "api: update create_trader to save config only"
```

---

## Task 6: Add start_trader Method to Service

**Files:**
- Modify: `api/hyper_trader_api/services/trader_service.py`

**Step 1: Add start_trader method after create_trader**

```python
    def start_trader(self, trader_id: uuid.UUID, user_id: str, max_attempts: int = 3) -> Trader:
        """
        Start a trader by creating its Docker Swarm service.

        Attempts to create the service up to max_attempts times with 2s delay between.

        Args:
            trader_id: Trader's UUID
            user_id: Owner's user ID
            max_attempts: Maximum retry attempts (default: 3)

        Returns:
            Updated Trader model

        Raises:
            TraderNotFoundError: If trader doesn't exist
            TraderOwnershipError: If user doesn't own trader
            ValueError: If trader is not in a startable state
            TraderServiceError: If all start attempts fail
        """
        import time

        trader = self.get_trader(trader_id, user_id)

        # Validate trader is in a startable state
        startable_states = ("configured", "stopped", "failed")
        if trader.status not in startable_states:
            raise ValueError(
                f"Trader cannot be started from status '{trader.status}'. "
                f"Must be one of: {startable_states}"
            )

        # Check if service already exists (shouldn't happen, but be safe)
        if self.runtime.service_exists(trader.runtime_name):
            logger.warning(f"Service {trader.runtime_name} already exists, removing first")
            self.runtime.remove_service(trader.runtime_name)

        # Update status to starting
        trader.status = "starting"
        trader.start_attempts = 0
        trader.last_error = None
        self.db.commit()

        config_path = self._get_config_path(str(trader.id))
        last_error = None

        for attempt in range(1, max_attempts + 1):
            trader.start_attempts = attempt
            self.db.commit()

            try:
                self.runtime.create_service(trader, config_path)
                trader.status = "running"
                trader.last_error = None
                self.db.commit()
                self.db.refresh(trader)
                logger.info(f"Trader started: {trader.runtime_name} (attempt {attempt})")
                return trader

            except Exception as e:
                last_error = str(e)
                logger.warning(
                    f"Failed to start trader {trader.runtime_name} "
                    f"(attempt {attempt}/{max_attempts}): {e}"
                )
                if attempt < max_attempts:
                    time.sleep(2)

        # All attempts failed
        trader.status = "failed"
        trader.last_error = last_error
        self.db.commit()
        self.db.refresh(trader)
        logger.error(f"Trader failed to start after {max_attempts} attempts: {trader.runtime_name}")
        raise TraderServiceError(f"Failed to start trader after {max_attempts} attempts: {last_error}")
```

**Step 2: Commit**

```bash
git add api/hyper_trader_api/services/trader_service.py
git commit -m "api: add start_trader method with retry logic"
```

---

## Task 7: Add stop_trader Method to Service

**Files:**
- Modify: `api/hyper_trader_api/services/trader_service.py`

**Step 1: Add stop_trader method after start_trader**

```python
    def stop_trader(self, trader_id: uuid.UUID, user_id: str) -> Trader:
        """
        Stop a trader by removing its Docker Swarm service.

        Keeps the Docker secret and DB record for later restart.

        Args:
            trader_id: Trader's UUID
            user_id: Owner's user ID

        Returns:
            Updated Trader model

        Raises:
            TraderNotFoundError: If trader doesn't exist
            TraderOwnershipError: If user doesn't own trader
            ValueError: If trader is not in a stoppable state
            TraderServiceError: If stop fails
        """
        from datetime import datetime, timezone

        trader = self.get_trader(trader_id, user_id)

        # Validate trader is in a stoppable state
        stoppable_states = ("running", "starting", "failed")
        if trader.status not in stoppable_states:
            raise ValueError(
                f"Trader cannot be stopped from status '{trader.status}'. "
                f"Must be one of: {stoppable_states}"
            )

        try:
            # Remove service only (keep secret)
            if self.runtime.service_exists(trader.runtime_name):
                self.runtime.remove_service(trader.runtime_name)

            trader.status = "stopped"
            trader.stopped_at = datetime.now(timezone.utc)
            self.db.commit()
            self.db.refresh(trader)
            logger.info(f"Trader stopped: {trader.runtime_name}")
            return trader

        except Exception as e:
            logger.error(f"Failed to stop trader {trader.runtime_name}: {e}")
            raise TraderServiceError(f"Failed to stop trader: {e}") from e
```

**Step 2: Commit**

```bash
git add api/hyper_trader_api/services/trader_service.py
git commit -m "api: add stop_trader method"
```

---

## Task 8: Update delete_trader Method

**Files:**
- Modify: `api/hyper_trader_api/services/trader_service.py:293-324`

**Step 1: Update delete_trader to use remove_secret parameter**

Replace the `delete_trader` method:

```python
    def delete_trader(self, trader_id: uuid.UUID, user_id: str) -> None:
        """
        Delete a trader completely.

        Removes Docker service, secret, config file, and all DB records.

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
            self.runtime.remove_trader(trader.runtime_name, trader.id, remove_secret=True)
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

**Step 2: Commit**

```bash
git add api/hyper_trader_api/services/trader_service.py
git commit -m "api: update delete_trader to explicitly remove secret"
```

---

## Task 9: Add Start and Stop API Endpoints

**Files:**
- Modify: `api/hyper_trader_api/routers/traders.py`

**Step 1: Add StartResponse and StopResponse to imports**

Update the import from schemas:

```python
from hyper_trader_api.schemas.trader import (
    DeleteResponse,
    RestartResponse,
    RuntimeStatus,
    StartResponse,
    StopResponse,
    TraderCreate,
    TraderListResponse,
    TraderLogsResponse,
    TraderResponse,
    TraderStatusResponse,
    TraderUpdate,
)
```

**Step 2: Update _trader_to_response to include new fields**

```python
def _trader_to_response(trader: Trader) -> TraderResponse:
    """Convert Trader model to TraderResponse schema."""
    latest_config = None
    if trader.latest_config:
        latest_config = trader.latest_config.config_json

    return TraderResponse(
        id=trader.id,
        user_id=trader.user_id,
        wallet_address=trader.wallet_address,
        runtime_name=trader.runtime_name,
        status=trader.status,
        image_tag=trader.image_tag,
        created_at=trader.created_at,
        updated_at=trader.updated_at,
        latest_config=latest_config,
        start_attempts=trader.start_attempts,
        last_error=trader.last_error,
        stopped_at=trader.stopped_at,
    )
```

**Step 3: Add start endpoint after restart endpoint**

```python
@router.post(
    "/{trader_id}/start",
    response_model=StartResponse,
    summary="Start trader",
    description="Start a trader by creating its Docker Swarm service. Retries up to 3 times.",
)
async def start_trader(
    trader_id: uuid.UUID,
    user: User = Depends(get_current_user),
    service: TraderService = Depends(get_trader_service),
) -> StartResponse:
    """
    Start a trader's Docker container.

    The trader must be in 'configured', 'stopped', or 'failed' state.
    Will retry up to 3 times with 2s delay between attempts.
    """
    try:
        trader = service.start_trader(trader_id, user.id)
        logger.info(f"Trader started: {trader.runtime_name}")

        return StartResponse(
            message="Trader started successfully",
            trader_id=trader_id,
            runtime_name=trader.runtime_name,
            status=trader.status,
            start_attempts=trader.start_attempts,
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e
    except TraderNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Trader not found: {trader_id}",
        ) from e
    except TraderOwnershipError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this trader",
        ) from e
    except TraderServiceError as e:
        logger.error(f"Failed to start trader: {e}")
        # Return the trader info even on failure so UI can show error
        trader = service.get_trader(trader_id, user.id)
        return StartResponse(
            message=f"Failed to start trader: {str(e)}",
            trader_id=trader_id,
            runtime_name=trader.runtime_name,
            status=trader.status,
            start_attempts=trader.start_attempts,
        )
```

**Step 4: Add stop endpoint after start endpoint**

```python
@router.post(
    "/{trader_id}/stop",
    response_model=StopResponse,
    summary="Stop trader",
    description="Stop a trader by removing its Docker Swarm service. Keeps config for later restart.",
)
async def stop_trader(
    trader_id: uuid.UUID,
    user: User = Depends(get_current_user),
    service: TraderService = Depends(get_trader_service),
) -> StopResponse:
    """
    Stop a trader's Docker container.

    The trader must be in 'running', 'starting', or 'failed' state.
    The Docker secret and database record are kept for later restart.
    """
    try:
        trader = service.stop_trader(trader_id, user.id)
        logger.info(f"Trader stopped: {trader.runtime_name}")

        return StopResponse(
            message="Trader stopped successfully",
            trader_id=trader_id,
            runtime_name=trader.runtime_name,
            status=trader.status,
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e
    except TraderNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Trader not found: {trader_id}",
        ) from e
    except TraderOwnershipError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this trader",
        ) from e
    except TraderServiceError as e:
        logger.error(f"Failed to stop trader: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to stop trader: {str(e)}",
        ) from e
```

**Step 5: Commit**

```bash
git add api/hyper_trader_api/routers/traders.py
git commit -m "api: add /start and /stop endpoints"
```

---

## Task 10: Update Frontend Types

**Files:**
- Modify: `web/src/lib/types.ts`

**Step 1: Update Trader interface status type and add new fields**

```typescript
export interface Trader {
  id: string;
  user_id: string;
  wallet_address: string;
  runtime_name: string;
  status: "configured" | "starting" | "running" | "stopped" | "failed";
  image_tag: string;
  created_at: string;
  updated_at: string;
  latest_config: TraderConfig | null;
  start_attempts: number;
  last_error: string | null;
  stopped_at: string | null;
}
```

**Step 2: Add StartResponse and StopResponse types**

```typescript
export interface StartResponse {
  message: string;
  trader_id: string;
  runtime_name: string;
  status: string;
  start_attempts: number;
}

export interface StopResponse {
  message: string;
  trader_id: string;
  runtime_name: string;
  status: string;
}
```

**Step 3: Commit**

```bash
git add web/src/lib/types.ts
git commit -m "web: update Trader type with lifecycle fields"
```

---

## Task 11: Update Frontend API Client

**Files:**
- Modify: `web/src/lib/api.ts`

**Step 1: Add StartResponse and StopResponse to imports**

```typescript
import type {
  User,
  Trader,
  TraderStatusResponse,
  CreateTraderRequest,
  UpdateTraderRequest,
  SystemStats,
  LoginResponse,
  SetupStatusResponse,
  SSLStatusResponse,
  StartResponse,
  StopResponse,
} from "./types";
```

**Step 2: Add startTrader and stopTrader methods after restartTrader**

```typescript
  async startTrader(id: string): Promise<StartResponse> {
    return fetchJson(`/v1/traders/${id}/start`, { method: "POST" });
  },

  async stopTrader(id: string): Promise<StopResponse> {
    return fetchJson(`/v1/traders/${id}/stop`, { method: "POST" });
  },
```

**Step 3: Commit**

```bash
git add web/src/lib/api.ts
git commit -m "web: add startTrader and stopTrader API methods"
```

---

## Task 12: Update Traders List Page with Action Buttons

**Files:**
- Modify: `web/src/routes/traders/index.tsx`

**Step 1: Add new imports**

```typescript
import { type Component, Show, For, Suspense, createSignal } from "solid-js";
import { createQuery, createMutation, useQueryClient } from "@tanstack/solid-query";
import { A } from "@solidjs/router";
import { Plus, Play, Square, Trash2, Loader2, AlertCircle } from "lucide-solid";
```

**Step 2: Replace StatusBadge component with updated version**

```typescript
function StatusBadge(props: { status: Trader["status"] }) {
  const variant = () => {
    switch (props.status) {
      case "running":
        return "success";
      case "configured":
        return "secondary";
      case "stopped":
        return "outline";
      case "starting":
        return "default";
      case "failed":
        return "destructive";
      default:
        return "outline";
    }
  };

  const label = () => {
    if (props.status === "starting") {
      return (
        <span class="flex items-center gap-1">
          <Loader2 class="h-3 w-3 animate-spin" />
          starting
        </span>
      );
    }
    return props.status;
  };

  return <Badge variant={variant()}>{label()}</Badge>;
}
```

**Step 3: Add TraderActions component before TradersPage**

```typescript
function TraderActions(props: { trader: Trader }) {
  const queryClient = useQueryClient();
  const [deleteOpen, setDeleteOpen] = createSignal(false);

  const startMutation = createMutation(() => ({
    mutationFn: () => api.startTrader(props.trader.id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: traderKeys.lists() });
    },
  }));

  const stopMutation = createMutation(() => ({
    mutationFn: () => api.stopTrader(props.trader.id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: traderKeys.lists() });
    },
  }));

  const deleteMutation = createMutation(() => ({
    mutationFn: () => api.deleteTrader(props.trader.id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: traderKeys.lists() });
    },
  }));

  const canStart = () =>
    ["configured", "stopped", "failed"].includes(props.trader.status);
  const canStop = () =>
    ["running", "starting"].includes(props.trader.status);
  const isLoading = () =>
    startMutation.isPending || stopMutation.isPending || deleteMutation.isPending;

  return (
    <div class="flex items-center gap-1">
      <Show when={canStart()}>
        <Button
          variant="ghost"
          size="sm"
          onClick={() => startMutation.mutate()}
          disabled={isLoading()}
          title={props.trader.status === "failed" ? "Retry" : "Start"}
        >
          <Show when={startMutation.isPending} fallback={<Play class="h-4 w-4" />}>
            <Loader2 class="h-4 w-4 animate-spin" />
          </Show>
        </Button>
      </Show>

      <Show when={canStop()}>
        <Button
          variant="ghost"
          size="sm"
          onClick={() => stopMutation.mutate()}
          disabled={isLoading()}
          title="Stop"
        >
          <Show when={stopMutation.isPending} fallback={<Square class="h-4 w-4" />}>
            <Loader2 class="h-4 w-4 animate-spin" />
          </Show>
        </Button>
      </Show>

      <AlertDialog open={deleteOpen()} onOpenChange={setDeleteOpen}>
        <AlertDialogTrigger
          as={Button}
          variant="ghost"
          size="sm"
          disabled={isLoading()}
          title="Delete"
        >
          <Trash2 class="h-4 w-4 text-destructive" />
        </AlertDialogTrigger>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete Trader</AlertDialogTitle>
            <AlertDialogDescription>
              This will permanently delete the trader and all its configuration.
              This action cannot be undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction onClick={() => deleteMutation.mutate()}>
              {deleteMutation.isPending ? "Deleting..." : "Delete"}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
```

**Step 4: Add imports for AlertDialog components**

```typescript
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "~/components/ui/alert-dialog";
```

**Step 5: Update the table to include Actions column and error display**

Replace the Table section in TradersPage:

```typescript
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Name</TableHead>
                    <TableHead>Wallet</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead>Created</TableHead>
                    <TableHead class="text-right">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  <For each={tradersQuery.data}>
                    {(trader) => (
                      <>
                        <TableRow>
                          <TableCell>
                            <A
                              href={`/traders/${trader.id}`}
                              class="font-medium hover:underline"
                            >
                              {trader.runtime_name}
                            </A>
                          </TableCell>
                          <TableCell class="font-mono text-xs truncate max-w-[200px]">
                            {trader.wallet_address}
                          </TableCell>
                          <TableCell>
                            <StatusBadge status={trader.status} />
                          </TableCell>
                          <TableCell>
                            {new Date(trader.created_at).toLocaleDateString()}
                          </TableCell>
                          <TableCell class="text-right">
                            <TraderActions trader={trader} />
                          </TableCell>
                        </TableRow>
                        <Show when={trader.status === "failed" && trader.last_error}>
                          <TableRow>
                            <TableCell colSpan={5} class="py-1">
                              <div class="flex items-center gap-2 text-sm text-destructive">
                                <AlertCircle class="h-4 w-4" />
                                {trader.last_error}
                              </div>
                            </TableCell>
                          </TableRow>
                        </Show>
                      </>
                    )}
                  </For>
                </TableBody>
              </Table>
```

**Step 6: Add polling for starting traders**

Update the tradersQuery to refetch more frequently when there are starting traders:

```typescript
  const tradersQuery = createQuery(() => ({
    queryKey: traderKeys.lists(),
    queryFn: () => api.listTraders(),
    refetchInterval: (query) => {
      const data = query.state.data;
      if (data?.some((t) => t.status === "starting")) {
        return 2000; // Poll every 2s when starting
      }
      return false; // No auto-refresh otherwise
    },
  }));
```

**Step 7: Commit**

```bash
git add web/src/routes/traders/index.tsx
git commit -m "web: add START/STOP/DELETE actions to traders list"
```

---

## Task 13: Update Trader Detail Page

**Files:**
- Modify: `web/src/routes/traders/[id].tsx`

**Step 1: Add new imports**

Update imports to include Play, Square, and Loader2:

```typescript
import { Trash2, RefreshCw, Play, Square, Loader2, AlertCircle } from "lucide-solid";
```

**Step 2: Update StatusBadge component**

Replace the StatusBadge with the same updated version from Task 12.

**Step 3: Add startMutation and stopMutation**

Add after deleteMutation:

```typescript
  const startMutation = createMutation(() => ({
    mutationFn: () => api.startTrader(params.id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: traderKeys.detail(params.id) });
      queryClient.invalidateQueries({ queryKey: traderKeys.status(params.id) });
    },
  }));

  const stopMutation = createMutation(() => ({
    mutationFn: () => api.stopTrader(params.id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: traderKeys.detail(params.id) });
      queryClient.invalidateQueries({ queryKey: traderKeys.status(params.id) });
    },
  }));
```

**Step 4: Update the action buttons section**

Replace the action buttons div:

```typescript
                    <div class="flex items-center gap-2">
                      <Show when={["configured", "stopped", "failed"].includes(trader().status)}>
                        <Button
                          variant="outline"
                          onClick={() => startMutation.mutate()}
                          disabled={startMutation.isPending}
                        >
                          <Show
                            when={startMutation.isPending}
                            fallback={<Play class="h-4 w-4 mr-2" />}
                          >
                            <Loader2 class="h-4 w-4 mr-2 animate-spin" />
                          </Show>
                          {trader().status === "failed" ? "Retry" : "Start"}
                        </Button>
                      </Show>

                      <Show when={["running", "starting"].includes(trader().status)}>
                        <Button
                          variant="outline"
                          onClick={() => stopMutation.mutate()}
                          disabled={stopMutation.isPending}
                        >
                          <Show
                            when={stopMutation.isPending}
                            fallback={<Square class="h-4 w-4 mr-2" />}
                          >
                            <Loader2 class="h-4 w-4 mr-2 animate-spin" />
                          </Show>
                          Stop
                        </Button>
                      </Show>

                      <Show when={trader().status === "running"}>
                        <Button
                          variant="outline"
                          onClick={() => restartMutation.mutate()}
                          disabled={restartMutation.isPending}
                        >
                          <RefreshCw
                            class={`h-4 w-4 mr-2 ${restartMutation.isPending ? "animate-spin" : ""}`}
                          />
                          Restart
                        </Button>
                      </Show>

                      <AlertDialog open={deleteOpen()} onOpenChange={setDeleteOpen}>
                        <AlertDialogTrigger as={Button} variant="destructive">
                          <Trash2 class="h-4 w-4 mr-2" />
                          Delete
                        </AlertDialogTrigger>
                        <AlertDialogContent>
                          <AlertDialogHeader>
                            <AlertDialogTitle>Delete Trader</AlertDialogTitle>
                            <AlertDialogDescription>
                              This will permanently delete "{trader().runtime_name}" and all its configuration.
                              This action cannot be undone.
                            </AlertDialogDescription>
                          </AlertDialogHeader>
                          <AlertDialogFooter>
                            <AlertDialogCancel>Cancel</AlertDialogCancel>
                            <AlertDialogAction onClick={() => deleteMutation.mutate()}>
                              {deleteMutation.isPending ? "Deleting..." : "Delete"}
                            </AlertDialogAction>
                          </AlertDialogFooter>
                        </AlertDialogContent>
                      </AlertDialog>
                    </div>
```

**Step 5: Add error display in the Status card**

Update the Status card to show last_error and start_attempts:

```typescript
                      <Card>
                        <CardHeader>
                          <CardTitle>Status</CardTitle>
                        </CardHeader>
                        <CardContent class="space-y-4">
                          <div class="flex items-center justify-between">
                            <span class="text-muted-foreground">Current Status</span>
                            <StatusBadge status={trader().status} />
                          </div>
                          <Show when={trader().start_attempts > 0}>
                            <div class="flex items-center justify-between">
                              <span class="text-muted-foreground">Start Attempts</span>
                              <span>{trader().start_attempts}</span>
                            </div>
                          </Show>
                          <Show when={trader().stopped_at}>
                            <div class="flex items-center justify-between">
                              <span class="text-muted-foreground">Stopped At</span>
                              <span>{new Date(trader().stopped_at!).toLocaleString()}</span>
                            </div>
                          </Show>
                          <Show when={statusQuery.data?.uptime_seconds}>
                            <div class="flex items-center justify-between">
                              <span class="text-muted-foreground">Uptime</span>
                              <span>{Math.floor(statusQuery.data!.uptime_seconds! / 60)} minutes</span>
                            </div>
                          </Show>
                          <Show when={trader().last_error}>
                            <div class="pt-2 border-t">
                              <div class="flex items-center gap-2 text-destructive text-sm">
                                <AlertCircle class="h-4 w-4" />
                                <span class="font-medium">Error:</span>
                              </div>
                              <p class="text-destructive text-sm mt-1">{trader().last_error}</p>
                            </div>
                          </Show>
                        </CardContent>
                      </Card>
```

**Step 6: Update polling to be faster when starting**

Update the statusQuery:

```typescript
  const statusQuery = createQuery(() => ({
    queryKey: traderKeys.status(params.id),
    queryFn: () => api.getTraderStatus(params.id),
    refetchInterval: () => {
      const status = traderQuery.data?.status;
      if (status === "starting") return 2000;
      if (status === "running") return 10000;
      return false;
    },
    enabled: () => traderQuery.data?.status === "running" || traderQuery.data?.status === "starting",
  }));
```

**Step 7: Commit**

```bash
git add web/src/routes/traders/[id].tsx
git commit -m "web: add START/STOP actions to trader detail page"
```

---

## Task 14: Database Migration

**Files:**
- Create: `api/hyper_trader_api/migrations/add_lifecycle_fields.py` (or use alembic if configured)

**Step 1: Check if alembic is used**

Look for alembic.ini or migrations folder in the api directory.

**Step 2: If no migration system, create a manual migration script**

```python
"""
Add lifecycle fields to traders table.

Run with: uv run python -m hyper_trader_api.migrations.add_lifecycle_fields
"""

import sqlite3
from pathlib import Path


def migrate():
    db_path = Path("./data/hyper_trader.db")
    if not db_path.exists():
        print("Database not found, skipping migration")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Check if columns already exist
    cursor.execute("PRAGMA table_info(traders)")
    columns = {row[1] for row in cursor.fetchall()}

    if "start_attempts" not in columns:
        cursor.execute("ALTER TABLE traders ADD COLUMN start_attempts INTEGER DEFAULT 0")
        print("Added start_attempts column")

    if "last_error" not in columns:
        cursor.execute("ALTER TABLE traders ADD COLUMN last_error VARCHAR(1000)")
        print("Added last_error column")

    if "stopped_at" not in columns:
        cursor.execute("ALTER TABLE traders ADD COLUMN stopped_at DATETIME")
        print("Added stopped_at column")

    # Update existing 'pending' status to 'configured'
    cursor.execute("UPDATE traders SET status = 'configured' WHERE status = 'pending'")
    rows_updated = cursor.rowcount
    if rows_updated > 0:
        print(f"Updated {rows_updated} traders from 'pending' to 'configured' status")

    conn.commit()
    conn.close()
    print("Migration complete")


if __name__ == "__main__":
    migrate()
```

**Step 3: Commit**

```bash
git add api/hyper_trader_api/migrations/
git commit -m "api: add database migration for lifecycle fields"
```

---

## Task 15: Run Tests and Verify

**Step 1: Run API linting and type checking**

```bash
cd api && uv run ruff check . && uv run ruff format --check .
```

Fix any issues found.

**Step 2: Run API tests**

```bash
cd api && uv run pytest
```

Fix any failing tests.

**Step 3: Run frontend type checking**

```bash
cd web && pnpm typecheck
```

Fix any type errors.

**Step 4: Run frontend build**

```bash
cd web && pnpm build
```

**Step 5: Commit any fixes**

```bash
git add -A
git commit -m "fix: address linting and type errors"
```

---

## Task 16: Final Commit and Summary

**Step 1: Verify all changes are committed**

```bash
git status
```

**Step 2: Review the commit history**

```bash
git log --oneline -15
```

**Step 3: Create a summary commit if needed**

If there are any uncommitted changes, commit them with an appropriate message.

---

## Summary of Changes

### API Changes
- `models/trader.py`: Added `start_attempts`, `last_error`, `stopped_at` fields; changed default status to `configured`
- `schemas/trader.py`: Added `TraderStatus` enum, `StartResponse`, `StopResponse`; updated `TraderResponse`
- `runtime/docker_runtime.py`: Added `create_secret()`, `create_service()`, `remove_service()`, `service_exists()`
- `runtime/base.py`: Updated protocol with new methods
- `services/trader_service.py`: Updated `create_trader()`, added `start_trader()`, `stop_trader()`
- `routers/traders.py`: Added `POST /{id}/start`, `POST /{id}/stop` endpoints

### Web Changes
- `lib/types.ts`: Updated `Trader` interface with new fields and status values
- `lib/api.ts`: Added `startTrader()`, `stopTrader()` methods
- `routes/traders/index.tsx`: Added action buttons (START/STOP/DELETE), error display, smart polling
- `routes/traders/[id].tsx`: Added action buttons, error display, smart polling
