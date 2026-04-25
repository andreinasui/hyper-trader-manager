# Trader Configuration Form Design

**Date:** 2026-04-03  
**Status:** Approved

## Overview

Implement trader configuration creation and editing through a form-based UI in the web app, with typed schema validation in both frontend and API, storing as JSON in the database and exporting as YAML config files.

## Requirements

- Users can configure traders via form fields matching the HyperTrader config schema
- Real-time validation with inline error messages
- Collapsible advanced settings with sensible defaults
- Same form for create and edit flows
- Config stored as JSON in DB, written as YAML to config files

## Data Model

### Pydantic Schema (`api/hyper_trader_api/schemas/trader_config.py`)

```
TraderConfigSchema
├── provider_settings: ProviderSettings
│   ├── exchange: Literal["hyperliquid"]
│   ├── network: Literal["mainnet", "testnet"]
│   ├── self_account: SelfAccount
│   │   ├── address: str (auto-filled from wallet_address)
│   │   └── is_sub: bool = False
│   ├── copy_account: CopyAccount
│   │   └── address: str (0x Ethereum address)
│   ├── slippage_bps: int | None (0-1000)
│   └── builder_fee_bps: int | None (0-200)
│
└── trader_settings: TraderSettings
    ├── min_self_funds: int (≥1)
    ├── min_copy_funds: int (≥1)
    └── trading_strategy: TradingStrategy
        ├── type: Literal["order_based", "position_based"]
        ├── risk_parameters: RiskParameters
        │   ├── allowed_assets: list[str] | None
        │   ├── blocked_assets: list[str] = []
        │   ├── max_leverage: int | None (1-50)
        │   ├── self_proportionality_multiplier: float = 1.0
        │   └── open_on_low_pnl: OpenOnLowPnl
        │       ├── enabled: bool = True
        │       └── max_pnl: float = 0.05
        └── bucket_config: BucketConfig | None
            ├── manual: ManualBucket | None
            ├── auto: AutoBucket | None
            └── pricing_strategy: Literal["vwap", "aggressive"] = "vwap"
```

### Key Decisions

- `self_account.address` auto-filled from `wallet_address` (not user-editable)
- `allowed_assets: null` means all assets allowed
- `bucket_config.manual` and `bucket_config.auto` are mutually exclusive (radio selection)

## Frontend Design

### Form Structure

```
TraderConfigForm (reusable component)
├── Basic Fields Section (always visible)
│   ├── Name (text)
│   ├── Wallet Address (text, 0x pattern)
│   ├── Private Key (password, create only)
│   ├── Copy Account Address (text, 0x pattern)
│   ├── Network (select: mainnet/testnet)
│   ├── Is Subaccount (toggle)
│   ├── Min Self Funds (number, USDC)
│   ├── Min Copy Funds (number, USDC)
│   └── Strategy Type (select: order_based/position_based)
│
├── Advanced Settings (collapsible, defaults pre-filled)
│   ├── Risk Parameters
│   │   ├── Allowed Assets (tag input)
│   │   ├── Blocked Assets (tag input)
│   │   ├── Max Leverage (number, nullable)
│   │   ├── Proportionality Multiplier (number)
│   │   └── Open on Low PnL (enabled toggle + max_pnl number)
│   │
│   ├── Slippage & Fees
│   │   ├── Slippage BPS (number)
│   │   └── Builder Fee BPS (number)
│   │
│   └── Bucket Configuration
│       ├── Mode (radio: Manual / Auto)
│       ├── [Manual] Width Percent
│       ├── [Auto] Ratio Threshold, Wide/Narrow Bucket Percent
│       └── Pricing Strategy (select)
```

### New UI Components

- `TagInput` - chip-style input for asset arrays
- `Collapsible` - expandable section wrapper

### Libraries

- `@modular-forms/solid` - form state management
- `zod` - schema validation (mirrors Pydantic schema)

## Validation

**Frontend (Zod):**
- Real-time validation on blur/change
- Inline error messages
- Submit disabled while invalid

**API (Pydantic):**
- Returns 422 with detailed field-level errors
- Business logic validation returns 400

**Business Rules:**
- `copy_account.address` ≠ `self_account.address`
- `allowed_assets` and `blocked_assets` cannot overlap

## Files

### Create

| File | Purpose |
|------|---------|
| `api/hyper_trader_api/schemas/trader_config.py` | Pydantic models |
| `web/src/lib/schemas/trader-config.ts` | Zod schema |
| `web/src/components/traders/TraderConfigForm.tsx` | Form component |
| `web/src/components/ui/tag-input.tsx` | Tag input component |
| `web/src/components/ui/collapsible.tsx` | Collapsible sections |

### Modify

| File | Changes |
|------|---------|
| `api/hyper_trader_api/schemas/trader.py` | Use typed config |
| `api/hyper_trader_api/services/trader_service.py` | YAML output |
| `web/src/routes/traders/new.tsx` | Integrate form |
| `web/src/routes/traders/[id].tsx` | Add config tab |
| `web/src/lib/types.ts` | Add config types |
| `web/src/lib/api.ts` | Update types |
