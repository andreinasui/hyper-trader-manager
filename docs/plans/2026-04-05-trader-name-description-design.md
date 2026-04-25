# Trader Name & Description Feature Design

## Overview

Add user-friendly `name` and optional `description` fields to traders. Users can assign custom names instead of seeing auto-generated `trader_id` or `runtime_name`. The backend continues to use `trader_id` internally.

## Requirements

- **Name**: Optional, max 50 chars, alphanumeric + spaces/dashes/underscores
- **Description**: Optional, max 255 chars
- **Uniqueness**: Name must be unique per user (when provided)
- **Display**: Show name if set, otherwise fall back to trader_id
- **Editable**: Both fields can be modified after trader creation

## Approach

Add `name` and `description` columns directly to the `Trader` model. Simple, no extra tables needed.

## Database Schema

Add to `Trader` model in `api/hyper_trader_api/models/trader.py`:

```python
name: Mapped[str | None] = mapped_column(String(50), nullable=True)
description: Mapped[str | None] = mapped_column(String(255), nullable=True)
```

Add unique constraint: `UniqueConstraint("user_id", "name", name="uq_trader_user_name")`

Note: SQLite partial unique constraints require special handling - the constraint applies to non-null names only.

## API Changes

### Endpoint Restructuring

Move config updates to a sub-resource for semantic clarity:

| Before | After | Purpose |
|--------|-------|---------|
| `PATCH /api/v1/traders/{id}` | `PATCH /api/v1/traders/{id}/config` | Update config (restarts container) |
| (new) | `PATCH /api/v1/traders/{id}` | Update name/description (no restart) |

### New Schema: TraderInfoUpdate

```python
class TraderInfoUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=50, pattern=r"^[a-zA-Z0-9 _-]+$")
    description: str | None = Field(default=None, max_length=255)
```

### Updated TraderCreate

Add optional fields:
```python
name: str | None = Field(default=None, max_length=50, pattern=r"^[a-zA-Z0-9 _-]+$")
description: str | None = Field(default=None, max_length=255)
```

### Updated TraderResponse

Add fields:
```python
name: str | None = None
description: str | None = None
display_name: str  # Computed: name if set, otherwise id
```

### Error Handling

- Return `409 Conflict` if name already exists for user
- Validation errors return `400 Bad Request`

## Frontend Changes

### Tab Restructuring

Current (2 tabs):
- Overview (Status + Details + LogViewer)
- Configuration

New (3 tabs):
- **Overview**: Trader Info card (editable) + Status card
- **Logs**: LogViewer (moved here)
- **Configuration**: TraderConfigForm (unchanged)

### Overview Tab - Trader Info Card

```
+--------------------------------------+
| Trader Info                          |
| ------------------------------------ |
| Name         [___________________]   |
| Description  [___________________]   |
|              [___________________]   |
|                           [Save]     |
| ------------------------------------ |
| Created      Jan 15, 2024 10:30      |
| Updated      Jan 15, 2024 10:35      |
| Wallet       0x1234...abcd           |
+--------------------------------------+
```

Behavior:
- Name/Description are editable text inputs
- Empty values NOT sent to API (only send filled fields)
- Save button enabled when changes exist
- Validation error shown inline on 409 Conflict

### Create Trader Form

Add optional Name and Description fields at the top of the form.

### Display Name Updates

Replace `runtime_name` with `display_name` in:
- Page header
- Dashboard cards
- Traders table
- Delete confirmation dialog

### API Client

```typescript
// New method for trader info
updateTraderInfo(id: string, data: { name?: string; description?: string }): Promise<Trader>

// Renamed for config (route changes to /config)
updateTraderConfig(id: string, config: TraderConfig): Promise<Trader>
```

## Files to Modify

### Backend

| File | Changes |
|------|---------|
| `models/trader.py` | Add `name`, `description` columns + constraint |
| `schemas/trader.py` | Add `TraderInfoUpdate`, update `TraderCreate`, `TraderResponse` |
| `routers/traders.py` | Move PATCH to `/config`, add PATCH for info |
| `services/trader_service.py` | Add `update_trader_info()` method |
| `alembic/versions/` | New migration for columns |

### Frontend

| File | Changes |
|------|---------|
| `lib/types.ts` | Add `name`, `description`, `display_name` to `Trader` |
| `lib/api.ts` | Add `updateTraderInfo()`, update config method |
| `routes/traders/[id].tsx` | 3 tabs, add Trader Info card with edit form |
| `routes/traders/new.tsx` | Add Name/Description fields |
| `routes/traders/index.tsx` | Show `display_name` in table |
| `routes/dashboard.tsx` | Show `display_name` in cards |

## Migration Strategy

1. Add columns as nullable (backward compatible)
2. Existing traders will have `name=NULL` and display their `id` as fallback
3. No data migration needed

## Testing

- Unit tests for new service method
- API tests for new endpoint and moved endpoint
- Verify uniqueness constraint works
- Test empty field handling (not sent to API)
