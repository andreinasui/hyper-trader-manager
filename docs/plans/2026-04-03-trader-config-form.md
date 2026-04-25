# Trader Configuration Form Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add typed trader configuration form matching HyperTrader YAML schema, with validation on both frontend and API.

**Architecture:** Pydantic v2 models validate config on API side, Zod validates on frontend. Config stored as JSON in DB, written as YAML to config files. Reusable form component for create/edit flows.

**Tech Stack:** FastAPI + Pydantic v2 (API), SolidJS + @modular-forms/solid + Zod (Web), PyYAML for config export.

---

## Task 1: Create Pydantic Config Schema

**Files:**
- Create: `api/hyper_trader_api/schemas/trader_config.py`

**Step 1: Create the typed config schema file**

```python
"""
Trader configuration schema for HyperTrader API.

Pydantic v2 models matching the HyperTrader YAML config schema.
"""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class SelfAccount(BaseModel):
    """Self trading account configuration."""

    address: str = Field(
        ...,
        pattern=r"^0x[a-fA-F0-9]{40}$",
        description="Ethereum address (0x...)",
    )
    is_sub: bool = Field(
        default=False,
        description="Whether account is a vault sub-account",
    )


class CopyAccount(BaseModel):
    """Account to copy trades from."""

    address: str = Field(
        ...,
        pattern=r"^0x[a-fA-F0-9]{40}$",
        description="Ethereum address (0x...)",
    )


class ProviderSettings(BaseModel):
    """Exchange and account configuration."""

    exchange: Literal["hyperliquid"] = Field(
        default="hyperliquid",
        description="Exchange identifier",
    )
    network: Literal["mainnet", "testnet"] = Field(
        ...,
        description="Network environment",
    )
    self_account: SelfAccount = Field(
        ...,
        description="Your trading account",
    )
    copy_account: CopyAccount = Field(
        ...,
        description="Account to copy trades from",
    )
    slippage_bps: int | None = Field(
        default=None,
        ge=0,
        le=1000,
        description="Slippage tolerance in basis points (1bp = 0.01%)",
    )
    builder_fee_bps: int | None = Field(
        default=None,
        ge=0,
        le=200,
        description="Builder fee in basis points",
    )


class OpenOnLowPnl(BaseModel):
    """Configuration for opening positions on low PnL."""

    enabled: bool = Field(default=True)
    max_pnl: float = Field(
        default=0.05,
        ge=-1.0,
        le=1.0,
        description="Max PnL threshold (-1.0 to 1.0)",
    )


class RiskParameters(BaseModel):
    """Risk management parameters."""

    allowed_assets: list[str] | None = Field(
        default=None,
        description="Whitelist of assets (null = all allowed)",
    )
    blocked_assets: list[str] = Field(
        default_factory=list,
        description="Blacklist of assets",
    )
    max_leverage: int | None = Field(
        default=None,
        ge=1,
        le=50,
        description="Maximum leverage (null = no limit)",
    )
    self_proportionality_multiplier: float = Field(
        default=1.0,
        ge=0.01,
        le=10.0,
        description="Multiplier for self order sizing",
    )
    open_on_low_pnl: OpenOnLowPnl = Field(
        default_factory=OpenOnLowPnl,
    )


class ManualBucket(BaseModel):
    """Fixed bucket width configuration."""

    width_percent: float = Field(
        ...,
        gt=0.0,
        le=1.0,
        description="Bucket width as percentage (0-1)",
    )


class AutoBucket(BaseModel):
    """Auto-detection bucket configuration."""

    ratio_threshold: float = Field(
        default=1000.0,
        gt=0.0,
        description="Ratio threshold for auto-detection",
    )
    wide_bucket_percent: float = Field(
        default=0.01,
        gt=0.0,
        le=1.0,
        description="Wide bucket percentage",
    )
    narrow_bucket_percent: float = Field(
        default=0.0001,
        gt=0.0,
        le=1.0,
        description="Narrow bucket percentage",
    )


class BucketConfig(BaseModel):
    """Order bucketing configuration."""

    manual: ManualBucket | None = Field(
        default=None,
        description="Fixed bucket width",
    )
    auto: AutoBucket | None = Field(
        default=None,
        description="Auto-detection mode",
    )
    pricing_strategy: Literal["vwap", "aggressive"] = Field(
        default="vwap",
        description="Bucket price calculation strategy",
    )

    model_config = ConfigDict(
        json_schema_extra={
            "description": "Either manual or auto must be set, not both"
        }
    )


class TradingStrategy(BaseModel):
    """Trading strategy configuration."""

    type: Literal["order_based", "position_based"] = Field(
        ...,
        description="Trading strategy type",
    )
    risk_parameters: RiskParameters = Field(
        default_factory=RiskParameters,
    )
    bucket_config: BucketConfig | None = Field(
        default=None,
        description="Order bucketing configuration",
    )


class TraderSettings(BaseModel):
    """Trading strategy and risk parameters."""

    min_self_funds: int = Field(
        ...,
        ge=1,
        description="Minimum USDC in self account to start trading",
    )
    min_copy_funds: int = Field(
        ...,
        ge=1,
        description="Minimum USDC in copy account to start trading",
    )
    trading_strategy: TradingStrategy = Field(
        ...,
        description="Trading strategy configuration",
    )


class TraderConfigSchema(BaseModel):
    """Complete trader configuration schema."""

    provider_settings: ProviderSettings = Field(
        ...,
        description="Exchange and account configuration",
    )
    trader_settings: TraderSettings = Field(
        ...,
        description="Trading strategy and risk parameters",
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "provider_settings": {
                    "exchange": "hyperliquid",
                    "network": "mainnet",
                    "self_account": {
                        "address": "0xe221ef33a07bcf16bde86a5dc6d7c85ebc3a1f9a",
                        "is_sub": False,
                    },
                    "copy_account": {
                        "address": "0x1234567890abcdef1234567890abcdef12345678",
                    },
                },
                "trader_settings": {
                    "min_self_funds": 100,
                    "min_copy_funds": 1000,
                    "trading_strategy": {
                        "type": "order_based",
                        "risk_parameters": {
                            "max_leverage": 10,
                        },
                    },
                },
            }
        }
    )
```

**Step 2: Export from schemas __init__.py**

Modify `api/hyper_trader_api/schemas/__init__.py` to add:
```python
from hyper_trader_api.schemas.trader_config import (
    TraderConfigSchema,
    ProviderSettings,
    TraderSettings,
    # ... other exports
)
```

**Step 3: Run type check to verify**

Run: `cd api && uv run mypy hyper_trader_api/schemas/trader_config.py`
Expected: Success, no errors

**Step 4: Commit**

```bash
git add api/hyper_trader_api/schemas/trader_config.py api/hyper_trader_api/schemas/__init__.py
git commit -m "api: add typed TraderConfigSchema Pydantic models"
```

---

## Task 2: Update Trader Schemas to Use Typed Config

**Files:**
- Modify: `api/hyper_trader_api/schemas/trader.py`

**Step 1: Update imports and TraderCreate**

Change `api/hyper_trader_api/schemas/trader.py`:

```python
# Add import at top
from hyper_trader_api.schemas.trader_config import TraderConfigSchema

# Change TraderCreate.config from dict[str, Any] to:
class TraderCreate(BaseModel):
    """Schema for creating a new trader."""

    wallet_address: str = Field(
        ...,
        pattern=r"^0x[a-fA-F0-9]{40}$",
        description="Ethereum wallet address",
    )
    private_key: str = Field(
        ...,
        pattern=r"^0x[a-fA-F0-9]{64}$",
        description="Private key for the wallet",
    )
    config: TraderConfigSchema = Field(..., description="Trader configuration")
```

**Step 2: Update TraderUpdate**

```python
class TraderUpdate(BaseModel):
    """Schema for updating a trader's configuration."""

    config: TraderConfigSchema | None = Field(
        default=None,
        description="Updated trader configuration",
    )
```

**Step 3: Update TraderResponse**

```python
class TraderResponse(BaseModel):
    """Schema for trader response."""

    # ... existing fields ...
    latest_config: TraderConfigSchema | None = None
```

**Step 4: Run tests to verify API still works**

Run: `cd api && uv run pytest tests/ -v -k trader`
Expected: Tests pass (may need updates if tests use old dict format)

**Step 5: Commit**

```bash
git add api/hyper_trader_api/schemas/trader.py
git commit -m "api: use TraderConfigSchema in trader request/response schemas"
```

---

## Task 3: Update Trader Service for YAML Output

**Files:**
- Modify: `api/hyper_trader_api/services/trader_service.py`

**Step 1: Add YAML import**

```python
import yaml  # Add at top with other imports
```

**Step 2: Change config file extension and write method**

```python
def _get_config_path(self, trader_id: str) -> Path:
    """Get path to trader's config file."""
    return self.config_dir / f"{trader_id}.yaml"  # Changed from .json

def _write_config_file(self, trader: Trader) -> Path:
    """Write trader's latest config to a YAML file."""
    config_path = self._get_config_path(str(trader.id))

    if not trader.latest_config:
        raise TraderServiceError(f"Trader {trader.id} has no config")

    with open(config_path, "w") as f:
        yaml.dump(trader.latest_config.config_json, f, default_flow_style=False, sort_keys=False)

    return config_path
```

**Step 3: Update create_trader to use model_dump**

In `create_trader` method, change:
```python
# Old: config = trader_data.config.copy()
# New:
config = trader_data.config.model_dump()
```

**Step 4: Update update_trader similarly**

In `update_trader` method:
```python
# Old: config = update_data.config.copy()
# New:
config = update_data.config.model_dump()
```

**Step 5: Run tests**

Run: `cd api && uv run pytest tests/ -v`
Expected: Tests pass

**Step 6: Commit**

```bash
git add api/hyper_trader_api/services/trader_service.py
git commit -m "api: write trader config as YAML instead of JSON"
```

---

## Task 4: Add Business Logic Validation

**Files:**
- Modify: `api/hyper_trader_api/services/trader_service.py`

**Step 1: Add validation helper method**

```python
def _validate_config(self, config: dict, wallet_address: str) -> None:
    """Validate config business rules.
    
    Raises:
        ValueError: If validation fails
    """
    # Check copy account is not same as self account
    copy_addr = config.get("provider_settings", {}).get("copy_account", {}).get("address", "").lower()
    if copy_addr == wallet_address.lower():
        raise ValueError("Copy account cannot be the same as self account")
    
    # Check allowed and blocked assets don't overlap
    risk = config.get("trader_settings", {}).get("trading_strategy", {}).get("risk_parameters", {})
    allowed = set(risk.get("allowed_assets") or [])
    blocked = set(risk.get("blocked_assets") or [])
    overlap = allowed & blocked
    if overlap:
        raise ValueError(f"Assets cannot be both allowed and blocked: {overlap}")
    
    # Check bucket config - only manual OR auto, not both
    bucket = config.get("trader_settings", {}).get("trading_strategy", {}).get("bucket_config")
    if bucket:
        has_manual = bucket.get("manual") is not None
        has_auto = bucket.get("auto") is not None
        if has_manual and has_auto:
            raise ValueError("Bucket config must use either manual or auto, not both")
```

**Step 2: Call validation in create_trader**

After `config = trader_data.config.model_dump()`:
```python
self._validate_config(config, trader_data.wallet_address)
```

**Step 3: Call validation in update_trader**

After `config = update_data.config.model_dump()`:
```python
self._validate_config(config, trader.wallet_address)
```

**Step 4: Update router to handle ValueError as 400**

In `api/hyper_trader_api/routers/traders.py`, update `create_trader` and `update_trader` to catch ValueError:
```python
except ValueError as e:
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=str(e),
    ) from e
```

**Step 5: Write test for validation**

Create test in existing test file:
```python
def test_create_trader_copy_same_as_self_fails(client, auth_headers):
    """Test that copy account cannot be same as self account."""
    response = client.post(
        "/api/v1/traders/",
        headers=auth_headers,
        json={
            "wallet_address": "0xe221ef33a07bcf16bde86a5dc6d7c85ebc3a1f9a",
            "private_key": "0x" + "a" * 64,
            "config": {
                "provider_settings": {
                    "network": "testnet",
                    "self_account": {"address": "0xe221ef33a07bcf16bde86a5dc6d7c85ebc3a1f9a"},
                    "copy_account": {"address": "0xe221ef33a07bcf16bde86a5dc6d7c85ebc3a1f9a"},
                },
                "trader_settings": {
                    "min_self_funds": 100,
                    "min_copy_funds": 1000,
                    "trading_strategy": {"type": "order_based"},
                },
            },
        },
    )
    assert response.status_code == 400
    assert "same as self account" in response.json()["detail"]
```

**Step 6: Run tests**

Run: `cd api && uv run pytest tests/ -v`
Expected: All tests pass

**Step 7: Commit**

```bash
git add api/hyper_trader_api/services/trader_service.py api/hyper_trader_api/routers/traders.py
git commit -m "api: add business logic validation for trader config"
```

---

## Task 5: Create Frontend Zod Schema

**Files:**
- Create: `web/src/lib/schemas/trader-config.ts`

**Step 1: Create the Zod schema file**

```typescript
import { z } from "zod";

const ethereumAddressRegex = /^0x[a-fA-F0-9]{40}$/;

export const selfAccountSchema = z.object({
  address: z.string().regex(ethereumAddressRegex, "Invalid Ethereum address"),
  is_sub: z.boolean().default(false),
});

export const copyAccountSchema = z.object({
  address: z.string().regex(ethereumAddressRegex, "Invalid Ethereum address"),
});

export const providerSettingsSchema = z.object({
  exchange: z.literal("hyperliquid").default("hyperliquid"),
  network: z.enum(["mainnet", "testnet"]),
  self_account: selfAccountSchema,
  copy_account: copyAccountSchema,
  slippage_bps: z.number().int().min(0).max(1000).nullable().optional(),
  builder_fee_bps: z.number().int().min(0).max(200).nullable().optional(),
});

export const openOnLowPnlSchema = z.object({
  enabled: z.boolean().default(true),
  max_pnl: z.number().min(-1).max(1).default(0.05),
});

export const riskParametersSchema = z.object({
  allowed_assets: z.array(z.string()).nullable().optional(),
  blocked_assets: z.array(z.string()).default([]),
  max_leverage: z.number().int().min(1).max(50).nullable().optional(),
  self_proportionality_multiplier: z.number().min(0.01).max(10).default(1.0),
  open_on_low_pnl: openOnLowPnlSchema.default({}),
});

export const manualBucketSchema = z.object({
  width_percent: z.number().gt(0).lte(1),
});

export const autoBucketSchema = z.object({
  ratio_threshold: z.number().gt(0).default(1000),
  wide_bucket_percent: z.number().gt(0).lte(1).default(0.01),
  narrow_bucket_percent: z.number().gt(0).lte(1).default(0.0001),
});

export const bucketConfigSchema = z.object({
  manual: manualBucketSchema.nullable().optional(),
  auto: autoBucketSchema.nullable().optional(),
  pricing_strategy: z.enum(["vwap", "aggressive"]).default("vwap"),
}).refine(
  (data) => !(data.manual && data.auto),
  { message: "Cannot use both manual and auto bucket config" }
);

export const tradingStrategySchema = z.object({
  type: z.enum(["order_based", "position_based"]),
  risk_parameters: riskParametersSchema.default({}),
  bucket_config: bucketConfigSchema.nullable().optional(),
});

export const traderSettingsSchema = z.object({
  min_self_funds: z.number().int().min(1),
  min_copy_funds: z.number().int().min(1),
  trading_strategy: tradingStrategySchema,
});

export const traderConfigSchema = z.object({
  provider_settings: providerSettingsSchema,
  trader_settings: traderSettingsSchema,
});

export type TraderConfig = z.infer<typeof traderConfigSchema>;
export type ProviderSettings = z.infer<typeof providerSettingsSchema>;
export type TraderSettings = z.infer<typeof traderSettingsSchema>;
export type TradingStrategy = z.infer<typeof tradingStrategySchema>;
export type RiskParameters = z.infer<typeof riskParametersSchema>;
export type BucketConfig = z.infer<typeof bucketConfigSchema>;

// Form-specific schema that includes wallet credentials
export const createTraderFormSchema = z.object({
  wallet_address: z.string().regex(ethereumAddressRegex, "Invalid Ethereum address"),
  private_key: z.string().regex(/^0x[a-fA-F0-9]{64}$/, "Invalid private key format"),
  config: traderConfigSchema,
}).refine(
  (data) => data.config.provider_settings.copy_account.address.toLowerCase() !== data.wallet_address.toLowerCase(),
  { message: "Copy account cannot be the same as your wallet", path: ["config", "provider_settings", "copy_account", "address"] }
);

export type CreateTraderForm = z.infer<typeof createTraderFormSchema>;
```

**Step 2: Run type check**

Run: `cd web && pnpm typecheck`
Expected: No errors

**Step 3: Commit**

```bash
git add web/src/lib/schemas/trader-config.ts
git commit -m "web: add Zod schema for trader configuration"
```

---

## Task 6: Update Frontend Types

**Files:**
- Modify: `web/src/lib/types.ts`

**Step 1: Add config types**

```typescript
// Add after existing types

export interface TraderConfig {
  provider_settings: {
    exchange: "hyperliquid";
    network: "mainnet" | "testnet";
    self_account: {
      address: string;
      is_sub: boolean;
    };
    copy_account: {
      address: string;
    };
    slippage_bps?: number | null;
    builder_fee_bps?: number | null;
  };
  trader_settings: {
    min_self_funds: number;
    min_copy_funds: number;
    trading_strategy: {
      type: "order_based" | "position_based";
      risk_parameters: {
        allowed_assets?: string[] | null;
        blocked_assets: string[];
        max_leverage?: number | null;
        self_proportionality_multiplier: number;
        open_on_low_pnl: {
          enabled: boolean;
          max_pnl: number;
        };
      };
      bucket_config?: {
        manual?: { width_percent: number } | null;
        auto?: {
          ratio_threshold: number;
          wide_bucket_percent: number;
          narrow_bucket_percent: number;
        } | null;
        pricing_strategy: "vwap" | "aggressive";
      } | null;
    };
  };
}
```

**Step 2: Update Trader interface**

```typescript
export interface Trader {
  id: string;
  user_id: string;
  wallet_address: string;
  runtime_name: string;
  status: "running" | "stopped" | "error" | "pending" | "failed";
  image_tag: string;
  created_at: string;
  updated_at: string;
  latest_config: TraderConfig | null;
}
```

**Step 3: Update CreateTraderRequest**

```typescript
export interface CreateTraderRequest {
  wallet_address: string;
  private_key: string;
  config: TraderConfig;
}
```

**Step 4: Run type check**

Run: `cd web && pnpm typecheck`
Expected: May show errors in existing code using old Trader type - fix them

**Step 5: Commit**

```bash
git add web/src/lib/types.ts
git commit -m "web: update types with TraderConfig interface"
```

---

## Task 7: Create TagInput Component

**Files:**
- Create: `web/src/components/ui/tag-input.tsx`

**Step 1: Create the tag input component**

```typescript
import { type Component, For, createSignal, Show } from "solid-js";
import { X } from "lucide-solid";
import { cn } from "~/lib/utils";
import { Badge } from "./badge";
import { Input } from "./input";

export interface TagInputProps {
  value: string[];
  onChange: (tags: string[]) => void;
  placeholder?: string;
  disabled?: boolean;
  class?: string;
  id?: string;
}

export const TagInput: Component<TagInputProps> = (props) => {
  const [inputValue, setInputValue] = createSignal("");

  const addTag = (tag: string) => {
    const trimmed = tag.trim().toUpperCase();
    if (trimmed && !props.value.includes(trimmed)) {
      props.onChange([...props.value, trimmed]);
    }
    setInputValue("");
  };

  const removeTag = (index: number) => {
    props.onChange(props.value.filter((_, i) => i !== index));
  };

  const handleKeyDown = (e: KeyboardEvent) => {
    if (e.key === "Enter" || e.key === ",") {
      e.preventDefault();
      addTag(inputValue());
    } else if (e.key === "Backspace" && !inputValue() && props.value.length > 0) {
      removeTag(props.value.length - 1);
    }
  };

  return (
    <div
      class={cn(
        "flex flex-wrap gap-2 p-2 rounded-md border border-input bg-transparent min-h-[42px]",
        props.disabled && "opacity-50 cursor-not-allowed",
        props.class
      )}
    >
      <For each={props.value}>
        {(tag, index) => (
          <Badge variant="secondary" class="gap-1 pr-1">
            {tag}
            <button
              type="button"
              onClick={() => removeTag(index())}
              disabled={props.disabled}
              class="ml-1 rounded-full hover:bg-muted-foreground/20 p-0.5"
            >
              <X class="h-3 w-3" />
            </button>
          </Badge>
        )}
      </For>
      <Input
        id={props.id}
        type="text"
        value={inputValue()}
        onInput={(e) => setInputValue(e.currentTarget.value)}
        onKeyDown={handleKeyDown}
        onBlur={() => inputValue() && addTag(inputValue())}
        placeholder={props.value.length === 0 ? props.placeholder : ""}
        disabled={props.disabled}
        class="flex-1 min-w-[120px] border-0 shadow-none focus-visible:ring-0 p-0 h-auto"
      />
    </div>
  );
};
```

**Step 2: Export from ui index (if exists) or just use direct import**

**Step 3: Run type check**

Run: `cd web && pnpm typecheck`
Expected: No errors

**Step 4: Commit**

```bash
git add web/src/components/ui/tag-input.tsx
git commit -m "web: add TagInput component for asset lists"
```

---

## Task 8: Create Collapsible Component

**Files:**
- Create: `web/src/components/ui/collapsible.tsx`

**Step 1: Create the collapsible component**

```typescript
import { type ParentComponent, type JSX, createSignal, Show, splitProps } from "solid-js";
import { ChevronDown, ChevronRight } from "lucide-solid";
import { cn } from "~/lib/utils";

export interface CollapsibleProps {
  title: string;
  defaultOpen?: boolean;
  class?: string;
  children: JSX.Element;
}

export const Collapsible: ParentComponent<CollapsibleProps> = (props) => {
  const [local, others] = splitProps(props, ["title", "defaultOpen", "class", "children"]);
  const [isOpen, setIsOpen] = createSignal(local.defaultOpen ?? false);

  return (
    <div class={cn("border rounded-lg", local.class)} {...others}>
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen())}
        class="flex items-center justify-between w-full p-4 text-left font-medium hover:bg-muted/50 transition-colors"
      >
        <span>{local.title}</span>
        <Show when={isOpen()} fallback={<ChevronRight class="h-4 w-4" />}>
          <ChevronDown class="h-4 w-4" />
        </Show>
      </button>
      <Show when={isOpen()}>
        <div class="p-4 pt-0 border-t">
          {local.children}
        </div>
      </Show>
    </div>
  );
};
```

**Step 2: Run type check**

Run: `cd web && pnpm typecheck`
Expected: No errors

**Step 3: Commit**

```bash
git add web/src/components/ui/collapsible.tsx
git commit -m "web: add Collapsible component for advanced settings"
```

---

## Task 9: Create Select Component

**Files:**
- Create: `web/src/components/ui/select.tsx`

**Step 1: Create basic select component**

```typescript
import { type JSX, splitProps, For } from "solid-js";
import { cn } from "~/lib/utils";

export interface SelectOption {
  value: string;
  label: string;
}

export interface SelectProps extends Omit<JSX.SelectHTMLAttributes<HTMLSelectElement>, "onChange"> {
  options: SelectOption[];
  onChange?: (value: string) => void;
  placeholder?: string;
}

export function Select(props: SelectProps) {
  const [local, others] = splitProps(props, ["class", "options", "onChange", "placeholder"]);

  return (
    <select
      class={cn(
        "flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50",
        local.class
      )}
      onChange={(e) => local.onChange?.(e.currentTarget.value)}
      {...others}
    >
      {local.placeholder && (
        <option value="" disabled>
          {local.placeholder}
        </option>
      )}
      <For each={local.options}>
        {(option) => (
          <option value={option.value}>{option.label}</option>
        )}
      </For>
    </select>
  );
}
```

**Step 2: Run type check**

Run: `cd web && pnpm typecheck`
Expected: No errors

**Step 3: Commit**

```bash
git add web/src/components/ui/select.tsx
git commit -m "web: add Select component for dropdowns"
```

---

## Task 10: Create Checkbox Component

**Files:**
- Create: `web/src/components/ui/checkbox.tsx`

**Step 1: Create checkbox component**

```typescript
import { type JSX, splitProps } from "solid-js";
import { cn } from "~/lib/utils";

export interface CheckboxProps extends Omit<JSX.InputHTMLAttributes<HTMLInputElement>, "type" | "onChange"> {
  onChange?: (checked: boolean) => void;
}

export function Checkbox(props: CheckboxProps) {
  const [local, others] = splitProps(props, ["class", "onChange"]);

  return (
    <input
      type="checkbox"
      class={cn(
        "h-4 w-4 rounded border border-input bg-transparent text-primary shadow-sm transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50",
        local.class
      )}
      onChange={(e) => local.onChange?.(e.currentTarget.checked)}
      {...others}
    />
  );
}
```

**Step 2: Run type check**

Run: `cd web && pnpm typecheck`
Expected: No errors

**Step 3: Commit**

```bash
git add web/src/components/ui/checkbox.tsx
git commit -m "web: add Checkbox component"
```

---

## Task 11: Create TraderConfigForm Component

**Files:**
- Create: `web/src/components/traders/TraderConfigForm.tsx`

**Step 1: Create the form component**

```typescript
import { type Component, createSignal, Show, createEffect } from "solid-js";
import { createForm, zodForm, Field, Form } from "@modular-forms/solid";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "~/components/ui/card";
import { Button } from "~/components/ui/button";
import { Input } from "~/components/ui/input";
import { Label } from "~/components/ui/label";
import { Alert, AlertDescription } from "~/components/ui/alert";
import { Select } from "~/components/ui/select";
import { Checkbox } from "~/components/ui/checkbox";
import { TagInput } from "~/components/ui/tag-input";
import { Collapsible } from "~/components/ui/collapsible";
import { createTraderFormSchema, type CreateTraderForm } from "~/lib/schemas/trader-config";

export interface TraderConfigFormProps {
  initialValues?: Partial<CreateTraderForm>;
  onSubmit: (data: CreateTraderForm) => Promise<void>;
  isSubmitting?: boolean;
  submitLabel?: string;
  isEditing?: boolean;
}

export const TraderConfigForm: Component<TraderConfigFormProps> = (props) => {
  const [error, setError] = createSignal<string | null>(null);
  const [bucketMode, setBucketMode] = createSignal<"none" | "manual" | "auto">("none");

  const [form, { Form: FormComponent, Field }] = createForm<CreateTraderForm>({
    validate: zodForm(createTraderFormSchema),
    initialValues: props.initialValues ?? {
      wallet_address: "",
      private_key: "",
      config: {
        provider_settings: {
          exchange: "hyperliquid",
          network: "mainnet",
          self_account: { address: "", is_sub: false },
          copy_account: { address: "" },
        },
        trader_settings: {
          min_self_funds: 100,
          min_copy_funds: 1000,
          trading_strategy: {
            type: "order_based",
            risk_parameters: {
              blocked_assets: [],
              self_proportionality_multiplier: 1.0,
              open_on_low_pnl: { enabled: true, max_pnl: 0.05 },
            },
          },
        },
      },
    },
  });

  const handleSubmit = async (values: CreateTraderForm) => {
    setError(null);
    try {
      // Auto-fill self_account.address from wallet_address
      values.config.provider_settings.self_account.address = values.wallet_address;
      await props.onSubmit(values);
    } catch (e) {
      setError(e instanceof Error ? e.message : "An error occurred");
    }
  };

  return (
    <FormComponent onSubmit={handleSubmit} class="space-y-6">
      <Show when={error()}>
        <Alert variant="destructive">
          <AlertDescription>{error()}</AlertDescription>
        </Alert>
      </Show>

      {/* Basic Settings Card */}
      <Card>
        <CardHeader>
          <CardTitle>Account Settings</CardTitle>
          <CardDescription>Configure your wallet and copy target</CardDescription>
        </CardHeader>
        <CardContent class="space-y-4">
          <Show when={!props.isEditing}>
            <Field name="wallet_address">
              {(field, props) => (
                <div class="space-y-2">
                  <Label for="wallet_address">Wallet Address</Label>
                  <Input
                    {...props}
                    id="wallet_address"
                    type="text"
                    value={field.value ?? ""}
                    placeholder="0x..."
                    class="font-mono"
                  />
                  <Show when={field.error}>
                    <p class="text-sm text-destructive">{field.error}</p>
                  </Show>
                </div>
              )}
            </Field>

            <Field name="private_key">
              {(field, props) => (
                <div class="space-y-2">
                  <Label for="private_key">Private Key</Label>
                  <Input
                    {...props}
                    id="private_key"
                    type="password"
                    value={field.value ?? ""}
                    placeholder="0x..."
                    class="font-mono"
                  />
                  <p class="text-xs text-muted-foreground">
                    Stored securely as a Docker secret
                  </p>
                  <Show when={field.error}>
                    <p class="text-sm text-destructive">{field.error}</p>
                  </Show>
                </div>
              )}
            </Field>
          </Show>

          <Field name="config.provider_settings.copy_account.address">
            {(field, props) => (
              <div class="space-y-2">
                <Label for="copy_account">Copy Account Address</Label>
                <Input
                  {...props}
                  id="copy_account"
                  type="text"
                  value={field.value ?? ""}
                  placeholder="0x..."
                  class="font-mono"
                />
                <p class="text-xs text-muted-foreground">
                  The address you want to copy trades from
                </p>
                <Show when={field.error}>
                  <p class="text-sm text-destructive">{field.error}</p>
                </Show>
              </div>
            )}
          </Field>

          <div class="grid grid-cols-2 gap-4">
            <Field name="config.provider_settings.network">
              {(field, props) => (
                <div class="space-y-2">
                  <Label for="network">Network</Label>
                  <Select
                    {...props}
                    id="network"
                    value={field.value ?? "mainnet"}
                    options={[
                      { value: "mainnet", label: "Mainnet" },
                      { value: "testnet", label: "Testnet" },
                    ]}
                  />
                </div>
              )}
            </Field>

            <Field name="config.provider_settings.self_account.is_sub">
              {(field, props) => (
                <div class="space-y-2">
                  <Label>Account Type</Label>
                  <div class="flex items-center gap-2 h-9">
                    <Checkbox
                      {...props}
                      id="is_sub"
                      checked={field.value ?? false}
                    />
                    <Label for="is_sub" class="font-normal">Is Subaccount</Label>
                  </div>
                </div>
              )}
            </Field>
          </div>
        </CardContent>
      </Card>

      {/* Trading Settings Card */}
      <Card>
        <CardHeader>
          <CardTitle>Trading Settings</CardTitle>
          <CardDescription>Configure trading strategy and thresholds</CardDescription>
        </CardHeader>
        <CardContent class="space-y-4">
          <div class="grid grid-cols-2 gap-4">
            <Field name="config.trader_settings.min_self_funds">
              {(field, props) => (
                <div class="space-y-2">
                  <Label for="min_self_funds">Min Self Funds (USDC)</Label>
                  <Input
                    {...props}
                    id="min_self_funds"
                    type="number"
                    value={field.value ?? 100}
                    min={1}
                  />
                  <Show when={field.error}>
                    <p class="text-sm text-destructive">{field.error}</p>
                  </Show>
                </div>
              )}
            </Field>

            <Field name="config.trader_settings.min_copy_funds">
              {(field, props) => (
                <div class="space-y-2">
                  <Label for="min_copy_funds">Min Copy Funds (USDC)</Label>
                  <Input
                    {...props}
                    id="min_copy_funds"
                    type="number"
                    value={field.value ?? 1000}
                    min={1}
                  />
                  <Show when={field.error}>
                    <p class="text-sm text-destructive">{field.error}</p>
                  </Show>
                </div>
              )}
            </Field>
          </div>

          <Field name="config.trader_settings.trading_strategy.type">
            {(field, props) => (
              <div class="space-y-2">
                <Label for="strategy_type">Strategy Type</Label>
                <Select
                  {...props}
                  id="strategy_type"
                  value={field.value ?? "order_based"}
                  options={[
                    { value: "order_based", label: "Order Based" },
                    { value: "position_based", label: "Position Based" },
                  ]}
                />
              </div>
            )}
          </Field>
        </CardContent>
      </Card>

      {/* Advanced Settings */}
      <Collapsible title="Advanced Settings" defaultOpen={false}>
        <div class="space-y-6">
          {/* Risk Parameters */}
          <div class="space-y-4">
            <h4 class="font-medium">Risk Parameters</h4>

            <Field name="config.trader_settings.trading_strategy.risk_parameters.allowed_assets">
              {(field, props) => (
                <div class="space-y-2">
                  <Label>Allowed Assets</Label>
                  <TagInput
                    value={field.value ?? []}
                    onChange={(tags) => field.value = tags}
                    placeholder="Type asset and press Enter (empty = all)"
                  />
                  <p class="text-xs text-muted-foreground">
                    Leave empty to allow all assets
                  </p>
                </div>
              )}
            </Field>

            <Field name="config.trader_settings.trading_strategy.risk_parameters.blocked_assets">
              {(field, props) => (
                <div class="space-y-2">
                  <Label>Blocked Assets</Label>
                  <TagInput
                    value={field.value ?? []}
                    onChange={(tags) => field.value = tags}
                    placeholder="Type asset and press Enter"
                  />
                </div>
              )}
            </Field>

            <div class="grid grid-cols-2 gap-4">
              <Field name="config.trader_settings.trading_strategy.risk_parameters.max_leverage">
                {(field, props) => (
                  <div class="space-y-2">
                    <Label for="max_leverage">Max Leverage</Label>
                    <Input
                      {...props}
                      id="max_leverage"
                      type="number"
                      value={field.value ?? ""}
                      min={1}
                      max={50}
                      placeholder="No limit"
                    />
                  </div>
                )}
              </Field>

              <Field name="config.trader_settings.trading_strategy.risk_parameters.self_proportionality_multiplier">
                {(field, props) => (
                  <div class="space-y-2">
                    <Label for="multiplier">Size Multiplier</Label>
                    <Input
                      {...props}
                      id="multiplier"
                      type="number"
                      value={field.value ?? 1.0}
                      min={0.01}
                      max={10}
                      step={0.1}
                    />
                  </div>
                )}
              </Field>
            </div>

            <div class="grid grid-cols-2 gap-4">
              <Field name="config.trader_settings.trading_strategy.risk_parameters.open_on_low_pnl.enabled">
                {(field, props) => (
                  <div class="flex items-center gap-2">
                    <Checkbox
                      {...props}
                      checked={field.value ?? true}
                    />
                    <Label class="font-normal">Open on Low PnL</Label>
                  </div>
                )}
              </Field>

              <Field name="config.trader_settings.trading_strategy.risk_parameters.open_on_low_pnl.max_pnl">
                {(field, props) => (
                  <div class="space-y-2">
                    <Label for="max_pnl">Max PnL Threshold</Label>
                    <Input
                      {...props}
                      id="max_pnl"
                      type="number"
                      value={field.value ?? 0.05}
                      min={-1}
                      max={1}
                      step={0.01}
                    />
                  </div>
                )}
              </Field>
            </div>
          </div>

          {/* Slippage & Fees */}
          <div class="space-y-4">
            <h4 class="font-medium">Slippage & Fees</h4>
            <div class="grid grid-cols-2 gap-4">
              <Field name="config.provider_settings.slippage_bps">
                {(field, props) => (
                  <div class="space-y-2">
                    <Label for="slippage">Slippage (bps)</Label>
                    <Input
                      {...props}
                      id="slippage"
                      type="number"
                      value={field.value ?? ""}
                      min={0}
                      max={1000}
                      placeholder="Default"
                    />
                    <p class="text-xs text-muted-foreground">1 bp = 0.01%</p>
                  </div>
                )}
              </Field>

              <Field name="config.provider_settings.builder_fee_bps">
                {(field, props) => (
                  <div class="space-y-2">
                    <Label for="builder_fee">Builder Fee (bps)</Label>
                    <Input
                      {...props}
                      id="builder_fee"
                      type="number"
                      value={field.value ?? ""}
                      min={0}
                      max={200}
                      placeholder="Default"
                    />
                  </div>
                )}
              </Field>
            </div>
          </div>

          {/* Bucket Configuration */}
          <div class="space-y-4">
            <h4 class="font-medium">Bucket Configuration</h4>
            
            <div class="flex gap-4">
              <label class="flex items-center gap-2">
                <input
                  type="radio"
                  name="bucket_mode"
                  value="none"
                  checked={bucketMode() === "none"}
                  onChange={() => setBucketMode("none")}
                />
                None
              </label>
              <label class="flex items-center gap-2">
                <input
                  type="radio"
                  name="bucket_mode"
                  value="manual"
                  checked={bucketMode() === "manual"}
                  onChange={() => setBucketMode("manual")}
                />
                Manual
              </label>
              <label class="flex items-center gap-2">
                <input
                  type="radio"
                  name="bucket_mode"
                  value="auto"
                  checked={bucketMode() === "auto"}
                  onChange={() => setBucketMode("auto")}
                />
                Auto
              </label>
            </div>

            <Show when={bucketMode() === "manual"}>
              <Field name="config.trader_settings.trading_strategy.bucket_config.manual.width_percent">
                {(field, props) => (
                  <div class="space-y-2">
                    <Label for="width_percent">Width Percent</Label>
                    <Input
                      {...props}
                      id="width_percent"
                      type="number"
                      value={field.value ?? 0.01}
                      min={0.0001}
                      max={1}
                      step={0.001}
                    />
                  </div>
                )}
              </Field>
            </Show>

            <Show when={bucketMode() === "auto"}>
              <div class="grid grid-cols-3 gap-4">
                <Field name="config.trader_settings.trading_strategy.bucket_config.auto.ratio_threshold">
                  {(field, props) => (
                    <div class="space-y-2">
                      <Label for="ratio_threshold">Ratio Threshold</Label>
                      <Input
                        {...props}
                        id="ratio_threshold"
                        type="number"
                        value={field.value ?? 1000}
                        min={0.1}
                      />
                    </div>
                  )}
                </Field>

                <Field name="config.trader_settings.trading_strategy.bucket_config.auto.wide_bucket_percent">
                  {(field, props) => (
                    <div class="space-y-2">
                      <Label for="wide_bucket">Wide Bucket %</Label>
                      <Input
                        {...props}
                        id="wide_bucket"
                        type="number"
                        value={field.value ?? 0.01}
                        min={0.0001}
                        max={1}
                        step={0.001}
                      />
                    </div>
                  )}
                </Field>

                <Field name="config.trader_settings.trading_strategy.bucket_config.auto.narrow_bucket_percent">
                  {(field, props) => (
                    <div class="space-y-2">
                      <Label for="narrow_bucket">Narrow Bucket %</Label>
                      <Input
                        {...props}
                        id="narrow_bucket"
                        type="number"
                        value={field.value ?? 0.0001}
                        min={0.00001}
                        max={1}
                        step={0.0001}
                      />
                    </div>
                  )}
                </Field>
              </div>
            </Show>

            <Show when={bucketMode() !== "none"}>
              <Field name="config.trader_settings.trading_strategy.bucket_config.pricing_strategy">
                {(field, props) => (
                  <div class="space-y-2">
                    <Label for="pricing_strategy">Pricing Strategy</Label>
                    <Select
                      {...props}
                      id="pricing_strategy"
                      value={field.value ?? "vwap"}
                      options={[
                        { value: "vwap", label: "VWAP" },
                        { value: "aggressive", label: "Aggressive" },
                      ]}
                    />
                  </div>
                )}
              </Field>
            </Show>
          </div>
        </div>
      </Collapsible>

      {/* Submit Button */}
      <div class="flex justify-end gap-4">
        <Button type="submit" disabled={props.isSubmitting}>
          {props.isSubmitting ? "Saving..." : (props.submitLabel ?? "Create Trader")}
        </Button>
      </div>
    </FormComponent>
  );
};
```

**Step 2: Run type check**

Run: `cd web && pnpm typecheck`
Expected: May have type errors with @modular-forms - adjust as needed

**Step 3: Commit**

```bash
git add web/src/components/traders/TraderConfigForm.tsx
git commit -m "web: add TraderConfigForm component with full config fields"
```

---

## Task 12: Update New Trader Page

**Files:**
- Modify: `web/src/routes/traders/new.tsx`

**Step 1: Replace with new form component**

```typescript
import { type Component } from "solid-js";
import { useNavigate } from "@solidjs/router";
import { createMutation, useQueryClient } from "@tanstack/solid-query";
import { ProtectedRoute } from "~/components/auth/ProtectedRoute";
import { AppShell } from "~/components/layout/AppShell";
import { TraderConfigForm } from "~/components/traders/TraderConfigForm";
import { api } from "~/lib/api";
import { traderKeys } from "~/lib/query-keys";
import type { CreateTraderForm } from "~/lib/schemas/trader-config";

const NewTraderPage: Component = () => {
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const createTraderMutation = createMutation(() => ({
    mutationFn: (data: CreateTraderForm) =>
      api.createTrader({
        wallet_address: data.wallet_address,
        private_key: data.private_key,
        config: data.config,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: traderKeys.all });
      navigate("/traders");
    },
  }));

  const handleSubmit = async (data: CreateTraderForm) => {
    await createTraderMutation.mutateAsync(data);
  };

  return (
    <ProtectedRoute>
      <AppShell>
        <div class="max-w-3xl mx-auto">
          <h1 class="text-2xl font-bold mb-6">Create New Trader</h1>
          <TraderConfigForm
            onSubmit={handleSubmit}
            isSubmitting={createTraderMutation.isPending}
            submitLabel="Create Trader"
          />
        </div>
      </AppShell>
    </ProtectedRoute>
  );
};

export default NewTraderPage;
```

**Step 2: Run dev server and test**

Run: `cd web && pnpm dev`
Expected: Page loads, form renders with all fields

**Step 3: Commit**

```bash
git add web/src/routes/traders/new.tsx
git commit -m "web: integrate TraderConfigForm in new trader page"
```

---

## Task 13: Update Trader Detail Page with Config Tab

**Files:**
- Modify: `web/src/routes/traders/[id].tsx`

**Step 1: Add imports and config editing state**

Add imports:
```typescript
import { Tabs, TabsContent, TabsList, TabsTrigger } from "~/components/ui/tabs";
import { TraderConfigForm } from "~/components/traders/TraderConfigForm";
```

**Step 2: Add update mutation**

```typescript
const updateMutation = createMutation(() => ({
  mutationFn: (config: TraderConfig) =>
    api.updateTrader(params.id, { config }),
  onSuccess: () => {
    queryClient.invalidateQueries({ queryKey: traderKeys.detail(params.id) });
  },
}));
```

**Step 3: Add tabs with config editing**

Wrap the content in tabs:
```typescript
<Tabs defaultValue="overview">
  <TabsList>
    <TabsTrigger value="overview">Overview</TabsTrigger>
    <TabsTrigger value="config">Configuration</TabsTrigger>
    <TabsTrigger value="logs">Logs</TabsTrigger>
  </TabsList>
  
  <TabsContent value="overview">
    {/* Existing overview cards */}
  </TabsContent>
  
  <TabsContent value="config">
    <Show when={trader().latest_config}>
      <TraderConfigForm
        initialValues={{
          wallet_address: trader().wallet_address,
          private_key: "",
          config: trader().latest_config!,
        }}
        onSubmit={async (data) => {
          await updateMutation.mutateAsync(data.config);
        }}
        isSubmitting={updateMutation.isPending}
        submitLabel="Save Configuration"
        isEditing={true}
      />
    </Show>
  </TabsContent>
  
  <TabsContent value="logs">
    <LogViewer traderId={params.id} />
  </TabsContent>
</Tabs>
```

**Step 4: Run and test**

Run: `cd web && pnpm dev`
Expected: Trader detail shows tabs, config tab shows form with current values

**Step 5: Commit**

```bash
git add web/src/routes/traders/[id].tsx
git commit -m "web: add config editing tab to trader detail page"
```

---

## Task 14: Update API Client

**Files:**
- Modify: `web/src/lib/api.ts`

**Step 1: Add updateTrader method**

```typescript
async updateTrader(id: string, data: { config: TraderConfig }): Promise<Trader> {
  return fetchJson(`/v1/traders/${id}`, {
    method: "PATCH",
    body: JSON.stringify(data),
  });
},
```

**Step 2: Update createTrader to use typed request**

Already correct if types are updated.

**Step 3: Run type check**

Run: `cd web && pnpm typecheck`
Expected: No errors

**Step 4: Commit**

```bash
git add web/src/lib/api.ts
git commit -m "web: add updateTrader API method"
```

---

## Task 15: End-to-End Testing

**Files:**
- Existing test infrastructure

**Step 1: Run API tests**

Run: `cd api && uv run pytest tests/ -v`
Expected: All tests pass

**Step 2: Run frontend type check**

Run: `cd web && pnpm typecheck`
Expected: No errors

**Step 3: Run frontend build**

Run: `cd web && pnpm build`
Expected: Build succeeds

**Step 4: Manual testing**

1. Start API: `cd api && just dev`
2. Start Web: `cd web && pnpm dev`
3. Create a new trader with full config
4. Verify YAML file created in `data/trader_configs/`
5. Edit trader config and verify changes saved

**Step 5: Final commit**

```bash
git add -A
git commit -m "feat: complete trader configuration form implementation"
```

---

## Summary

| Task | Description | Files |
|------|-------------|-------|
| 1 | Pydantic config schema | `api/.../schemas/trader_config.py` |
| 2 | Update trader schemas | `api/.../schemas/trader.py` |
| 3 | YAML output in service | `api/.../services/trader_service.py` |
| 4 | Business validation | `api/.../services/trader_service.py` |
| 5 | Zod schema | `web/src/lib/schemas/trader-config.ts` |
| 6 | Frontend types | `web/src/lib/types.ts` |
| 7 | TagInput component | `web/src/components/ui/tag-input.tsx` |
| 8 | Collapsible component | `web/src/components/ui/collapsible.tsx` |
| 9 | Select component | `web/src/components/ui/select.tsx` |
| 10 | Checkbox component | `web/src/components/ui/checkbox.tsx` |
| 11 | TraderConfigForm | `web/src/components/traders/TraderConfigForm.tsx` |
| 12 | New trader page | `web/src/routes/traders/new.tsx` |
| 13 | Trader detail page | `web/src/routes/traders/[id].tsx` |
| 14 | API client | `web/src/lib/api.ts` |
| 15 | E2E testing | - |
