# Trader Name & Description Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add user-friendly `name` and `description` fields to traders, allowing users to identify traders by custom names instead of auto-generated IDs.

**Architecture:** Add columns to Trader model, create new PATCH endpoint for info updates, move config updates to `/config` sub-resource, update frontend with 3-tab layout and editable info card.

**Tech Stack:** Python/FastAPI/SQLAlchemy (backend), SolidJS/TypeScript/TanStack Query (frontend)

**Working Directory:** `/home/andrei/Projects/hyper-trader-project/hyper-trader-manager/.worktrees/trader-config`

---

## Task 1: Add Database Columns

**Files:**
- Modify: `api/hyper_trader_api/models/trader.py:44-96`

**Step 1: Add name and description columns**

In `api/hyper_trader_api/models/trader.py`, add after `image_tag` column (around line 87):

```python
    name: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )
    description: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
```

**Step 2: Add unique constraint for name per user**

Update `__table_args__` (add after class attributes, before relationships):

```python
    __table_args__ = (
        UniqueConstraint("user_id", "name", name="uq_trader_user_name"),
    )
```

Note: Import `UniqueConstraint` is already present from line 12.

**Step 3: Verify syntax**

Run: `cd api && uv run python -c "from hyper_trader_api.models.trader import Trader; print('OK')"`
Expected: `OK`

**Step 4: Commit**

```bash
git add api/hyper_trader_api/models/trader.py
git commit -m "api: add name and description columns to Trader model"
```

---

## Task 2: Create Database Migration

**Files:**
- Create: `api/hyper_trader_api/alembic/versions/xxxx_add_trader_name_description.py`

**Step 1: Generate migration**

Run:
```bash
cd api && uv run alembic revision --autogenerate -m "add trader name and description"
```

**Step 2: Verify migration file**

Check the generated migration has:
- `op.add_column('traders', sa.Column('name', sa.String(50), nullable=True))`
- `op.add_column('traders', sa.Column('description', sa.String(255), nullable=True))`
- `op.create_unique_constraint('uq_trader_user_name', 'traders', ['user_id', 'name'])`

**Step 3: Run migration**

Run: `cd api && uv run alembic upgrade head`
Expected: Migration applies successfully

**Step 4: Commit**

```bash
git add api/hyper_trader_api/alembic/versions/
git commit -m "api: add migration for trader name and description"
```

---

## Task 3: Add TraderInfoUpdate Schema

**Files:**
- Modify: `api/hyper_trader_api/schemas/trader.py`

**Step 1: Add TraderInfoUpdate schema**

Add after `TraderUpdate` class (around line 108):

```python
class TraderInfoUpdate(BaseModel):
    """Schema for updating trader display info (name/description)."""

    name: str | None = Field(
        default=None,
        max_length=50,
        pattern=r"^[a-zA-Z0-9 _-]+$",
        description="User-friendly name for the trader",
    )
    description: str | None = Field(
        default=None,
        max_length=255,
        description="Optional description or notes",
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "Main Trading Bot",
                "description": "Copy trading setup for testnet",
            }
        }
    )
```

**Step 2: Update TraderCreate schema**

Add after `config` field in `TraderCreate` class (around line 42):

```python
    name: str | None = Field(
        default=None,
        max_length=50,
        pattern=r"^[a-zA-Z0-9 _-]+$",
        description="User-friendly name for the trader",
    )
    description: str | None = Field(
        default=None,
        max_length=255,
        description="Optional description or notes",
    )
```

**Step 3: Update TraderResponse schema**

Add after `stopped_at` field in `TraderResponse` class (around line 124):

```python
    name: str | None = None
    description: str | None = None

    @computed_field
    @property
    def display_name(self) -> str:
        """Return name if set, otherwise trader id."""
        return self.name if self.name else self.id
```

Add import at top of file:
```python
from pydantic import BaseModel, ConfigDict, Field, computed_field
```

**Step 4: Export new schema**

Update the `__all__` if present, or verify imports work.

**Step 5: Verify syntax**

Run: `cd api && uv run python -c "from hyper_trader_api.schemas.trader import TraderInfoUpdate, TraderResponse; print('OK')"`
Expected: `OK`

**Step 6: Commit**

```bash
git add api/hyper_trader_api/schemas/trader.py
git commit -m "api: add TraderInfoUpdate schema and update TraderCreate/Response"
```

---

## Task 4: Add Service Method for Info Update

**Files:**
- Modify: `api/hyper_trader_api/services/trader_service.py`

**Step 1: Add update_trader_info method**

Add new method to `TraderService` class:

```python
    def update_trader_info(
        self,
        trader_id: uuid.UUID,
        user_id: str,
        update_data: "TraderInfoUpdate",
    ) -> Trader:
        """
        Update trader display info (name/description).

        Does NOT restart the container - this is metadata only.

        Args:
            trader_id: UUID of the trader to update
            user_id: ID of the requesting user
            update_data: New name and/or description

        Returns:
            Updated Trader instance

        Raises:
            TraderNotFoundError: If trader doesn't exist
            TraderOwnershipError: If user doesn't own the trader
            ValueError: If name already exists for this user
        """
        trader = self.get_trader(trader_id, user_id)

        # Check name uniqueness if name is being set
        if update_data.name is not None:
            existing = (
                self.db.query(Trader)
                .filter(
                    Trader.user_id == user_id,
                    Trader.name == update_data.name,
                    Trader.id != str(trader_id),
                )
                .first()
            )
            if existing:
                raise ValueError(f"A trader with name '{update_data.name}' already exists")

        # Update fields if provided
        if update_data.name is not None:
            trader.name = update_data.name if update_data.name else None
        if update_data.description is not None:
            trader.description = update_data.description if update_data.description else None

        self.db.commit()
        self.db.refresh(trader)
        return trader
```

Add import at top if not present:
```python
from hyper_trader_api.schemas.trader import TraderInfoUpdate
```

**Step 2: Update create_trader to handle name/description**

In the `create_trader` method, when creating the Trader instance, add:

```python
        trader = Trader(
            user_id=user.id,
            wallet_address=trader_data.wallet_address,
            runtime_name=runtime_name,
            status=TraderStatus.CONFIGURED.value,
            name=trader_data.name,  # ADD THIS
            description=trader_data.description,  # ADD THIS
        )
```

Also add name uniqueness check at the start of `create_trader`:

```python
        # Check name uniqueness if provided
        if trader_data.name:
            existing = (
                self.db.query(Trader)
                .filter(Trader.user_id == user.id, Trader.name == trader_data.name)
                .first()
            )
            if existing:
                raise ValueError(f"A trader with name '{trader_data.name}' already exists")
```

**Step 3: Verify syntax**

Run: `cd api && uv run python -c "from hyper_trader_api.services.trader_service import TraderService; print('OK')"`
Expected: `OK`

**Step 4: Commit**

```bash
git add api/hyper_trader_api/services/trader_service.py
git commit -m "api: add update_trader_info service method"
```

---

## Task 5: Update API Router

**Files:**
- Modify: `api/hyper_trader_api/routers/traders.py`

**Step 1: Import new schema**

Update imports to include `TraderInfoUpdate`:

```python
from hyper_trader_api.schemas.trader import (
    DeleteResponse,
    RestartResponse,
    RuntimeStatus,
    StartResponse,
    StopResponse,
    TraderCreate,
    TraderInfoUpdate,  # ADD THIS
    TraderListResponse,
    TraderLogsResponse,
    TraderResponse,
    TraderStatusResponse,
    TraderUpdate,
)
```

**Step 2: Update _trader_to_response helper**

Add name and description to the response:

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
        name=trader.name,  # ADD THIS
        description=trader.description,  # ADD THIS
    )
```

**Step 3: Add new PATCH endpoint for trader info**

Add before the existing PATCH endpoint (around line 158):

```python
@router.patch(
    "/{trader_id}",
    response_model=TraderResponse,
    summary="Update trader info",
    description="Update a trader's display name and description. Does not restart the container.",
)
async def update_trader_info(
    trader_id: uuid.UUID,
    update_data: TraderInfoUpdate,
    user: User = Depends(get_current_user),
    service: TraderService = Depends(get_trader_service),
) -> TraderResponse:
    """
    Update a trader's display info (name/description).

    - **name**: Optional display name (unique per user)
    - **description**: Optional description/notes

    This does NOT restart the container.
    """
    try:
        trader = service.update_trader_info(trader_id, user.id, update_data)
        logger.info(f"Trader info updated: {trader.runtime_name}")
        return _trader_to_response(trader)

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
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
```

**Step 4: Move existing PATCH to /config**

Change the existing `update_trader` endpoint route from `"/{trader_id}"` to `"/{trader_id}/config"`:

```python
@router.patch(
    "/{trader_id}/config",  # CHANGED FROM "/{trader_id}"
    response_model=TraderResponse,
    summary="Update trader configuration",
    description="Update a trader's configuration. The container will be restarted to apply changes.",
)
async def update_trader_config(  # RENAMED FROM update_trader
    # ... rest stays the same
```

**Step 5: Run linting**

Run: `cd api && uv run ruff check hyper_trader_api/routers/traders.py --fix`
Expected: No errors or auto-fixed

**Step 6: Commit**

```bash
git add api/hyper_trader_api/routers/traders.py
git commit -m "api: add PATCH /traders/{id} for info, move config to /config"
```

---

## Task 6: Run Backend Tests

**Files:**
- Check: `api/tests/`

**Step 1: Run existing tests**

Run: `cd api && uv run pytest -v`
Expected: All tests pass (may need to update some if they test the PATCH endpoint)

**Step 2: Fix any failing tests**

If tests fail due to endpoint change, update them to use `/config` for config updates.

**Step 3: Commit fixes if any**

```bash
git add api/tests/
git commit -m "api: update tests for new endpoint structure"
```

---

## Task 7: Update Frontend Types

**Files:**
- Modify: `web/src/lib/types.ts`

**Step 1: Update Trader interface**

Add new fields to `Trader` interface (around line 50-63):

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
  name: string | null;           // ADD THIS
  description: string | null;    // ADD THIS
  display_name: string;          // ADD THIS
}
```

**Step 2: Add UpdateTraderInfoRequest interface**

Add after `UpdateTraderRequest` (around line 79):

```typescript
export interface UpdateTraderInfoRequest {
  name?: string;
  description?: string;
}
```

**Step 3: Update CreateTraderRequest**

Add optional fields:

```typescript
export interface CreateTraderRequest {
  wallet_address: string;
  private_key: string;
  config: TraderConfig;
  name?: string;        // ADD THIS
  description?: string; // ADD THIS
}
```

**Step 4: Verify types compile**

Run: `cd web && pnpm typecheck`
Expected: May have errors in files using Trader type (will fix in next tasks)

**Step 5: Commit**

```bash
git add web/src/lib/types.ts
git commit -m "web: add name, description, display_name to Trader type"
```

---

## Task 8: Update API Client

**Files:**
- Modify: `web/src/lib/api.ts`

**Step 1: Add updateTraderInfo method**

Add new method:

```typescript
  async updateTraderInfo(
    traderId: string,
    data: UpdateTraderInfoRequest
  ): Promise<Trader> {
    // Only send fields that have values
    const payload: UpdateTraderInfoRequest = {};
    if (data.name !== undefined && data.name !== "") {
      payload.name = data.name;
    }
    if (data.description !== undefined && data.description !== "") {
      payload.description = data.description;
    }
    const response = await this.fetch<Trader>(`/v1/traders/${traderId}`, {
      method: "PATCH",
      body: JSON.stringify(payload),
    });
    return response;
  },
```

**Step 2: Update updateTrader to use /config**

Change the existing `updateTrader` method URL:

```typescript
  async updateTrader(
    traderId: string,
    data: UpdateTraderRequest
  ): Promise<Trader> {
    const response = await this.fetch<Trader>(`/v1/traders/${traderId}/config`, {  // CHANGED
      method: "PATCH",
      body: JSON.stringify(data),
    });
    return response;
  },
```

**Step 3: Add import for new type**

Update imports:

```typescript
import type {
  // ... existing imports
  UpdateTraderInfoRequest,
} from "./types";
```

**Step 4: Verify types compile**

Run: `cd web && pnpm typecheck`
Expected: Pass or show remaining type errors

**Step 5: Commit**

```bash
git add web/src/lib/api.ts
git commit -m "web: add updateTraderInfo API method, move config to /config"
```

---

## Task 9: Update Trader Detail Page - Tab Structure

**Files:**
- Modify: `web/src/routes/traders/[id].tsx`

**Step 1: Add Logs tab and restructure**

Update the Tabs section to have 3 tabs. Replace the current tab structure (around lines 223-318):

```tsx
<Tabs defaultValue="overview" class="space-y-6">
  <TabsList>
    <TabsTrigger value="overview">Overview</TabsTrigger>
    <TabsTrigger value="logs">Logs</TabsTrigger>
    <TabsTrigger value="configuration">Configuration</TabsTrigger>
  </TabsList>

  <TabsContent value="overview" class="space-y-6">
    <div class="grid gap-6 md:grid-cols-2">
      {/* Trader Info Card - will add in next task */}
      <Card>
        <CardHeader>
          <CardTitle>Trader Info</CardTitle>
        </CardHeader>
        <CardContent class="space-y-4">
          <div class="flex items-center justify-between">
            <span class="text-muted-foreground">Created</span>
            <span>{new Date(trader().created_at).toLocaleString()}</span>
          </div>
          <div class="flex items-center justify-between">
            <span class="text-muted-foreground">Last Updated</span>
            <span>{new Date(trader().updated_at).toLocaleString()}</span>
          </div>
          <div class="flex items-center justify-between">
            <span class="text-muted-foreground">Wallet</span>
            <span class="font-mono text-xs">{trader().wallet_address}</span>
          </div>
        </CardContent>
      </Card>

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
    </div>
  </TabsContent>

  <TabsContent value="logs">
    <LogViewer traderId={params.id} />
  </TabsContent>

  <TabsContent value="configuration">
    <Show
      when={trader().latest_config}
      fallback={
        <Card>
          <CardContent class="p-8 text-center text-muted-foreground">
            No configuration available for this trader.
          </CardContent>
        </Card>
      }
    >
      {(config) => (
        <TraderConfigForm
          initialValues={{
            wallet_address: trader().wallet_address,
            private_key: "",
            config: config() as TraderConfig,
          }}
          onSubmit={async (data: CreateTraderForm) => {
            await updateMutation.mutateAsync(data.config);
          }}
          isEditing={true}
          isSubmitting={updateMutation.isPending}
          submitLabel="Save Configuration"
        />
      )}
    </Show>
  </TabsContent>
</Tabs>
```

**Step 2: Update header to use display_name**

Change line 148 from:
```tsx
<h1 class="text-2xl font-bold">{trader().runtime_name}</h1>
```
to:
```tsx
<h1 class="text-2xl font-bold">{trader().display_name}</h1>
```

Also update delete dialog (around line 208) from `runtime_name` to `display_name`.

**Step 3: Verify no TypeScript errors**

Run: `cd web && pnpm typecheck`

**Step 4: Commit**

```bash
git add web/src/routes/traders/[id].tsx
git commit -m "web: restructure trader detail to 3 tabs, use display_name"
```

---

## Task 10: Add Editable Info Card

**Files:**
- Modify: `web/src/routes/traders/[id].tsx`

**Step 1: Add state and mutation for info editing**

Add after existing state declarations (around line 80):

```tsx
const [editName, setEditName] = createSignal<string>("");
const [editDescription, setEditDescription] = createSignal<string>("");
const [infoChanged, setInfoChanged] = createSignal(false);
const [infoError, setInfoError] = createSignal<string | null>(null);

// Initialize edit values when trader data loads
createEffect(() => {
  const t = traderQuery.data;
  if (t) {
    setEditName(t.name || "");
    setEditDescription(t.description || "");
    setInfoChanged(false);
  }
});

const updateInfoMutation = createMutation(() => ({
  mutationFn: (data: { name?: string; description?: string }) =>
    api.updateTraderInfo(params.id, data),
  onSuccess: () => {
    queryClient.invalidateQueries({ queryKey: traderKeys.detail(params.id) });
    setInfoError(null);
    setInfoChanged(false);
  },
  onError: (error: Error) => {
    setInfoError(error.message || "Failed to update trader info");
  },
}));

const handleInfoSave = () => {
  const data: { name?: string; description?: string } = {};
  const currentName = editName().trim();
  const currentDesc = editDescription().trim();
  
  if (currentName) data.name = currentName;
  if (currentDesc) data.description = currentDesc;
  
  updateInfoMutation.mutate(data);
};

const handleNameChange = (value: string) => {
  setEditName(value);
  setInfoChanged(true);
  setInfoError(null);
};

const handleDescriptionChange = (value: string) => {
  setEditDescription(value);
  setInfoChanged(true);
  setInfoError(null);
};
```

Add import at top:
```tsx
import { createEffect } from "solid-js";
```

**Step 2: Add TextField import**

Add import for TextField (or use basic input):
```tsx
import { TextField, TextFieldInput, TextFieldLabel } from "~/components/ui/text-field";
import { Textarea } from "~/components/ui/textarea";
```

If Textarea doesn't exist, use a basic textarea element.

**Step 3: Update Trader Info Card with editable fields**

Replace the Trader Info Card content:

```tsx
<Card>
  <CardHeader>
    <CardTitle>Trader Info</CardTitle>
  </CardHeader>
  <CardContent class="space-y-4">
    <div class="space-y-2">
      <label class="text-sm font-medium">Name</label>
      <input
        type="text"
        value={editName()}
        onInput={(e) => handleNameChange(e.currentTarget.value)}
        placeholder="Enter a name for this trader"
        class="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm transition-colors placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
        maxLength={50}
      />
    </div>
    <div class="space-y-2">
      <label class="text-sm font-medium">Description</label>
      <textarea
        value={editDescription()}
        onInput={(e) => handleDescriptionChange(e.currentTarget.value)}
        placeholder="Optional notes about this trader"
        class="flex min-h-[60px] w-full rounded-md border border-input bg-transparent px-3 py-2 text-sm shadow-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
        maxLength={255}
        rows={2}
      />
    </div>
    <Show when={infoError()}>
      <p class="text-sm text-destructive">{infoError()}</p>
    </Show>
    <Show when={infoChanged()}>
      <Button
        onClick={handleInfoSave}
        disabled={updateInfoMutation.isPending}
        size="sm"
      >
        {updateInfoMutation.isPending ? "Saving..." : "Save"}
      </Button>
    </Show>
    <div class="pt-4 border-t space-y-2">
      <div class="flex items-center justify-between">
        <span class="text-muted-foreground text-sm">Created</span>
        <span class="text-sm">{new Date(trader().created_at).toLocaleString()}</span>
      </div>
      <div class="flex items-center justify-between">
        <span class="text-muted-foreground text-sm">Last Updated</span>
        <span class="text-sm">{new Date(trader().updated_at).toLocaleString()}</span>
      </div>
      <div class="flex items-center justify-between">
        <span class="text-muted-foreground text-sm">Wallet</span>
        <span class="font-mono text-xs truncate max-w-[200px]">{trader().wallet_address}</span>
      </div>
    </div>
  </CardContent>
</Card>
```

**Step 4: Verify compilation**

Run: `cd web && pnpm typecheck`

**Step 5: Commit**

```bash
git add web/src/routes/traders/[id].tsx
git commit -m "web: add editable name/description in Overview tab"
```

---

## Task 11: Update Create Trader Form

**Files:**
- Modify: `web/src/routes/traders/new.tsx`

**Step 1: Check current form structure**

Read the file to understand current form fields.

**Step 2: Add name and description fields**

Add at the top of the form (before wallet address):

```tsx
<div class="space-y-2">
  <label class="text-sm font-medium">Name (optional)</label>
  <input
    type="text"
    value={name()}
    onInput={(e) => setName(e.currentTarget.value)}
    placeholder="e.g., Main Trading Bot"
    class="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm transition-colors placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
    maxLength={50}
  />
</div>
<div class="space-y-2">
  <label class="text-sm font-medium">Description (optional)</label>
  <textarea
    value={description()}
    onInput={(e) => setDescription(e.currentTarget.value)}
    placeholder="Optional notes about this trader"
    class="flex min-h-[60px] w-full rounded-md border border-input bg-transparent px-3 py-2 text-sm shadow-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
    maxLength={255}
    rows={2}
  />
</div>
```

**Step 3: Add state signals**

```tsx
const [name, setName] = createSignal("");
const [description, setDescription] = createSignal("");
```

**Step 4: Update form submission**

Include name and description in the API call (only if filled):

```tsx
const payload: CreateTraderRequest = {
  wallet_address: walletAddress(),
  private_key: privateKey(),
  config: config,
};
if (name().trim()) {
  payload.name = name().trim();
}
if (description().trim()) {
  payload.description = description().trim();
}
await api.createTrader(payload);
```

**Step 5: Verify compilation**

Run: `cd web && pnpm typecheck`

**Step 6: Commit**

```bash
git add web/src/routes/traders/new.tsx
git commit -m "web: add optional name/description to create trader form"
```

---

## Task 12: Update Traders List and Dashboard

**Files:**
- Modify: `web/src/routes/traders/index.tsx`
- Modify: `web/src/routes/dashboard.tsx`

**Step 1: Update traders list table**

In `traders/index.tsx`, change the Name column to show `display_name`:

```tsx
<TableCell>
  <A
    href={`/traders/${trader.id}`}
    class="font-medium hover:underline"
  >
    {trader.display_name}
  </A>
</TableCell>
```

**Step 2: Update dashboard cards**

In `dashboard.tsx`, find where `runtime_name` is displayed and change to `display_name`.

**Step 3: Verify compilation**

Run: `cd web && pnpm typecheck`

**Step 4: Commit**

```bash
git add web/src/routes/traders/index.tsx web/src/routes/dashboard.tsx
git commit -m "web: use display_name in traders list and dashboard"
```

---

## Task 13: Run Full Test Suite

**Step 1: Run backend tests**

Run: `cd api && uv run pytest -v`
Expected: All tests pass

**Step 2: Run frontend typecheck**

Run: `cd web && pnpm typecheck`
Expected: No errors

**Step 3: Run frontend build**

Run: `cd web && pnpm build`
Expected: Build succeeds

**Step 4: Manual testing (if dev server available)**

- Create a new trader with name and description
- Edit name/description on existing trader
- Verify display_name shows correctly
- Verify uniqueness constraint works (try duplicate name)

---

## Task 14: Final Commit and Summary

**Step 1: Check git status**

Run: `git status`
Verify all changes are committed.

**Step 2: Push branch**

Run: `git push origin trader-config`

**Step 3: Summary**

Feature complete:
- Database: `name` and `description` columns with uniqueness constraint
- API: New `PATCH /traders/{id}` for info, config moved to `/config`
- Frontend: 3-tab layout, editable info card, create form with name/description
- Display: All views use `display_name` (name or id fallback)
