# Web Trader Form Refactor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Unify trader creation and trader settings editing behind one form path so a config-field change is implemented once.

**Architecture:** Keep `@modular-forms/solid`. Move defaults, legacy config normalization, validation merge, and API payload shaping into one model file. Rework `TraderConfigForm` into a mode-driven `TraderForm`, then make create/detail routes thin callers.

**Tech Stack:** SolidJS, TypeScript, `@modular-forms/solid`, Zod, TanStack Solid Query, Vitest, Testing Library.

## Global Constraints

- Keep `@modular-forms/solid`; changing form library is out of scope.
- No dynamic schema-driven field renderer.
- No backend API contract changes. Edit submit may call the existing metadata endpoint and config endpoint from one UI submit action.
- No broad e2e rewrite in this refactor.
- Use `pnpm` for frontend commands.
- Do not create git commits unless the user explicitly asks during execution. Commit commands below are markers for commit boundaries only.

---

## File Structure

- Create `web/src/components/traders/trader-form-model.ts`: all non-UI form defaults, normalization, validation, deep merge, and payload helpers.
- Create `web/src/components/traders/trader-form-model.test.ts`: model behavior tests.
- Modify `web/src/components/traders/TraderConfigForm.tsx`: keep filename for small diff, export `TraderForm`, and keep `export const TraderConfigForm = TraderForm` as a temporary alias for tests/imports touched later in the plan.
- Modify `web/src/components/traders/TraderConfigForm.test.tsx`: rename expectations to the unified form behavior.
- Modify `web/src/routes/traders/new.tsx`: use `TraderForm mode="create"` and `toCreateTraderRequest`.
- Modify `web/src/routes/traders/[id].tsx`: use `TraderForm mode="edit"`, remove metadata edit state, call both existing update endpoints from one mutation.
- Modify `web/src/components/traders/overviews/TraderOverview.tsx`: remove editable name/description props and UI.

---

### Task 1: Add Trader Form Model

**Files:**
- Create: `web/src/components/traders/trader-form-model.ts`
- Create: `web/src/components/traders/trader-form-model.test.ts`
- Modify: `web/src/lib/schemas/trader-config.ts`

**Interfaces:**
- Consumes: `CreateTraderForm`, `TraderConfig`, `Trader`, `CreateTraderRequest`, `UpdateTraderRequest`, `UpdateTraderInfoRequest`.
- Produces:
  - `export type TraderFormMode = "create" | "edit"`
  - `export type TraderFormValues = CreateTraderForm`
  - `export const defaultTraderFormValues: TraderFormValues`
  - `export function normalizeTraderConfig(config: TraderConfig): TraderConfig`
  - `export function deepMergeFormValues<T>(base: Partial<T>, next: Partial<T>): T`
  - `export function buildInitialTraderForm(mode: TraderFormMode, trader?: Trader): TraderFormValues`
  - `export function validateTraderForm(mode: TraderFormMode, initialValues: TraderFormValues, values: PartialValues<TraderFormValues>): Record<string, string>`
  - `export function prepareTraderFormValues(values: TraderFormValues): TraderFormValues`
  - `export function toCreateTraderRequest(values: TraderFormValues): CreateTraderRequest`
  - `export function toUpdateTraderRequests(values: TraderFormValues): { info: UpdateTraderInfoRequest; config: UpdateTraderRequest }`

- [ ] **Step 1: Add failing model tests**

Create `web/src/components/traders/trader-form-model.test.ts`:

```ts
import { describe, expect, it } from "vitest";
import type { Trader } from "~/lib/types";
import type { TraderConfig } from "~/lib/schemas/trader-config";
import {
  buildInitialTraderForm,
  defaultTraderFormValues,
  normalizeTraderConfig,
  prepareTraderFormValues,
  toCreateTraderRequest,
  toUpdateTraderRequests,
  validateTraderForm,
} from "./trader-form-model";

const wallet = "0x1111111111111111111111111111111111111111";
const copy = "0x2222222222222222222222222222222222222222";
const privateKey = "0x1111111111111111111111111111111111111111111111111111111111111111";

const config: TraderConfig = {
  provider_settings: {
    exchange: "hyperliquid",
    network: "testnet",
    self_account: { address: wallet, is_sub: true },
    copy_account: { address: copy },
    slippage_bps: 42,
    risk_parameters: {
      allowed_assets: ["BTC"],
      blocked_assets: ["ETH"],
      max_leverage: 10,
    },
  },
  trader_settings: {
    trading_strategy: {
      type: "order_based",
      risk_parameters: {
        self_proportionality_multiplier: 2,
        open_on_low_pnl: { enabled: true, max_pnl: 0.07 },
      },
      bucket_config: {
        type: "manual",
        width_percent: 0.03,
        pricing_strategy: "aggressive",
      },
    },
  },
};

const trader: Trader = {
  id: "trader-1",
  user_id: "user-1",
  wallet_address: wallet,
  runtime_name: "runtime",
  status: "configured",
  image_tag: "1.0.0",
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-02T00:00:00Z",
  latest_config: config,
  start_attempts: 0,
  last_error: null,
  stopped_at: null,
  name: "Alpha",
  description: "Copies BTC",
  display_name: "Alpha",
};

describe("trader-form-model", () => {
  it("builds create defaults once", () => {
    expect(defaultTraderFormValues.config.provider_settings.network).toBe("mainnet");
    expect(defaultTraderFormValues.config.provider_settings.slippage_bps).toBe(200);
    expect(defaultTraderFormValues.config.trader_settings.trading_strategy.bucket_config.type).toBe("auto");
  });

  it("builds edit values from a trader", () => {
    const values = buildInitialTraderForm("edit", trader);

    expect(values.name).toBe("Alpha");
    expect(values.description).toBe("Copies BTC");
    expect(values.wallet_address).toBe(wallet);
    expect(values.private_key).toBe("");
    expect(values.config.provider_settings.network).toBe("testnet");
    expect(values.config.provider_settings.risk_parameters.allowed_assets).toEqual(["BTC"]);
  });

  it("normalizes legacy config with missing bucket_config", () => {
    const legacy = structuredClone(config) as TraderConfig;
    delete (legacy.trader_settings.trading_strategy as Partial<typeof legacy.trader_settings.trading_strategy>).bucket_config;

    expect(normalizeTraderConfig(legacy).trader_settings.trading_strategy.bucket_config).toEqual({
      type: "auto",
      pricing_strategy: "vwap",
      ratio_threshold: 1000,
      wide_bucket_percent: 0.01,
      narrow_bucket_percent: 0.0001,
    });
  });

  it("derives self account from wallet before create submit", () => {
    const request = toCreateTraderRequest({
      ...defaultTraderFormValues,
      wallet_address: wallet,
      private_key: privateKey,
      name: "  Alpha  ",
      description: "  Copies BTC  ",
      config: {
        ...defaultTraderFormValues.config,
        provider_settings: {
          ...defaultTraderFormValues.config.provider_settings,
          copy_account: { address: copy },
        },
      },
    });

    expect(request.name).toBe("Alpha");
    expect(request.description).toBe("Copies BTC");
    expect(request.config.provider_settings.self_account.address).toBe(wallet);
  });

  it("returns separate existing update payloads", () => {
    const { info, config: updateConfig } = toUpdateTraderRequests(buildInitialTraderForm("edit", trader));

    expect(info).toEqual({ name: "Alpha", description: "Copies BTC" });
    expect(updateConfig.config.provider_settings.self_account.address).toBe(wallet);
  });

  it("validates partial values merged with initial values", () => {
    const initial = buildInitialTraderForm("edit", trader);
    const errors = validateTraderForm("edit", initial, {
      config: {
        provider_settings: {
          copy_account: { address: "not-an-address" },
        },
      },
    });

    expect(errors["config.provider_settings.copy_account.address"]).toBe("Invalid Ethereum address");
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pnpm test -- src/components/traders/trader-form-model.test.ts`

Expected: FAIL because `./trader-form-model` does not exist.

- [ ] **Step 3: Align schema type with current form shape**

In `web/src/lib/schemas/trader-config.ts`, keep existing schemas and make `EditTraderForm` use the same optional metadata shape as create/edit UI. Replace lines 130-135 with:

```ts
export const editTraderFormSchema = z.object({
  wallet_address: z.string().optional(),
  private_key: z.string().optional(),
  name: z.string().max(50).optional(),
  description: z.string().max(255).optional(),
  config: traderConfigFormSchema,
});
```

- [ ] **Step 4: Implement model file**

Create `web/src/components/traders/trader-form-model.ts`:

```ts
import type { PartialValues } from "@modular-forms/solid";
import {
  createTraderFormSchema,
  editTraderFormSchema,
  type CreateTraderForm,
  type TraderConfig,
} from "~/lib/schemas/trader-config";
import type { CreateTraderRequest, Trader, UpdateTraderInfoRequest, UpdateTraderRequest } from "~/lib/types";

export type TraderFormMode = "create" | "edit";
export type TraderFormValues = CreateTraderForm;

export const TRADER_FORM_DEFAULTS = {
  multiplier: 1.0,
  maxPnl: 0.05,
  maxLeverage: 50,
  maxLeverageMin: 1,
  maxLeverageMax: 50,
  slippageBps: 200,
  ratioThreshold: 1000,
  wideBucketPct: 0.01,
  narrowBucketPct: 0.0001,
  widthPercent: 0.01,
} as const;

export const defaultTraderFormValues: TraderFormValues = {
  wallet_address: "",
  private_key: "",
  name: "",
  description: "",
  config: {
    provider_settings: {
      exchange: "hyperliquid",
      network: "mainnet",
      self_account: { address: "", is_sub: false },
      copy_account: { address: "" },
      slippage_bps: TRADER_FORM_DEFAULTS.slippageBps,
      risk_parameters: {
        allowed_assets: "*",
        blocked_assets: [],
        max_leverage: TRADER_FORM_DEFAULTS.maxLeverage,
      },
    },
    trader_settings: {
      trading_strategy: {
        type: "order_based",
        risk_parameters: {
          self_proportionality_multiplier: TRADER_FORM_DEFAULTS.multiplier,
          open_on_low_pnl: { enabled: true, max_pnl: TRADER_FORM_DEFAULTS.maxPnl },
        },
        bucket_config: {
          type: "auto",
          pricing_strategy: "vwap",
          ratio_threshold: TRADER_FORM_DEFAULTS.ratioThreshold,
          wide_bucket_percent: TRADER_FORM_DEFAULTS.wideBucketPct,
          narrow_bucket_percent: TRADER_FORM_DEFAULTS.narrowBucketPct,
        },
      },
    },
  },
};

export function deepMergeFormValues<T>(base: Partial<T>, next: Partial<T>): T {
  if (
    base &&
    next &&
    typeof base === "object" &&
    typeof next === "object" &&
    !Array.isArray(base) &&
    !Array.isArray(next)
  ) {
    const out: Record<string, unknown> = { ...(base as Record<string, unknown>) };
    for (const [key, value] of Object.entries(next as Record<string, unknown>)) {
      out[key] = key in out ? deepMergeFormValues(out[key] as never, value as never) : value;
    }
    return out as T;
  }
  return (next === undefined ? base : next) as T;
}

export function normalizeTraderConfig(config: TraderConfig): TraderConfig {
  return deepMergeFormValues(defaultTraderFormValues.config, config);
}

export function buildInitialTraderForm(mode: TraderFormMode, trader?: Trader): TraderFormValues {
  if (mode === "create") return structuredClone(defaultTraderFormValues);

  return deepMergeFormValues(defaultTraderFormValues, {
    wallet_address: trader?.wallet_address ?? "",
    private_key: "",
    name: trader?.name ?? "",
    description: trader?.description ?? "",
    config: trader?.latest_config ? normalizeTraderConfig(trader.latest_config as TraderConfig) : defaultTraderFormValues.config,
  });
}

export function prepareTraderFormValues(values: TraderFormValues): TraderFormValues {
  const prepared = structuredClone(values);
  prepared.config.provider_settings.self_account.address = prepared.wallet_address ?? "";
  return prepared;
}

export function validateTraderForm(
  mode: TraderFormMode,
  initialValues: TraderFormValues,
  values: PartialValues<TraderFormValues>
): Record<string, string> {
  const merged = deepMergeFormValues(initialValues, values as Partial<TraderFormValues>);
  const result = (mode === "edit" ? editTraderFormSchema : createTraderFormSchema).safeParse(merged);
  if (result.success) return {};

  const errors: Record<string, string> = {};
  for (const error of result.error.errors) {
    errors[error.path.join(".")] = error.message;
  }
  return errors;
}

function trimmed(value: string | undefined): string | undefined {
  const next = value?.trim();
  return next ? next : undefined;
}

export function toCreateTraderRequest(values: TraderFormValues): CreateTraderRequest {
  const prepared = prepareTraderFormValues(values);
  return {
    wallet_address: prepared.wallet_address,
    private_key: prepared.private_key,
    config: prepared.config,
    ...(trimmed(prepared.name) ? { name: trimmed(prepared.name) } : {}),
    ...(trimmed(prepared.description) ? { description: trimmed(prepared.description) } : {}),
  };
}

export function toUpdateTraderRequests(values: TraderFormValues): {
  info: UpdateTraderInfoRequest;
  config: UpdateTraderRequest;
} {
  const prepared = prepareTraderFormValues(values);
  return {
    info: {
      ...(trimmed(prepared.name) ? { name: trimmed(prepared.name) } : {}),
      ...(trimmed(prepared.description) ? { description: trimmed(prepared.description) } : {}),
    },
    config: { config: prepared.config },
  };
}
```

- [ ] **Step 5: Run model test**

Run: `pnpm test -- src/components/traders/trader-form-model.test.ts`

Expected: PASS.

- [ ] **Step 6: Run typecheck**

Run: `pnpm exec tsc --noEmit`

Expected: PASS. If `structuredClone` or `TraderConfig` shape exposes an existing type mismatch, prefer a narrow cast in the model over widening public API types.

- [ ] **Step 7: Commit boundary**

If commits are explicitly requested, run:

```bash
git add web/src/lib/schemas/trader-config.ts web/src/components/traders/trader-form-model.ts web/src/components/traders/trader-form-model.test.ts
git commit -m "web refactor trader form model"
```

---

### Task 2: Rework Trader Form UI Around Model

**Files:**
- Modify: `web/src/components/traders/TraderConfigForm.tsx`
- Modify: `web/src/components/traders/TraderConfigForm.test.tsx`

**Interfaces:**
- Consumes Task 1 model exports.
- Produces:
  - `export interface TraderFormProps { mode: TraderFormMode; initialValues?: TraderFormValues; onSubmit: (data: TraderFormValues) => Promise<void>; isSubmitting?: boolean; submitLabel?: string }`
  - `export const TraderForm: Component<TraderFormProps>`
  - `export const TraderConfigForm = TraderForm`

- [ ] **Step 1: Update component tests first**

Replace `web/src/components/traders/TraderConfigForm.test.tsx` imports and first test with:

```ts
import { fireEvent, render, screen, waitFor } from "@solidjs/testing-library";
import { describe, expect, it, vi } from "vitest";
import { TraderForm } from "./TraderConfigForm";
import { buildInitialTraderForm } from "./trader-form-model";
import type { Trader } from "~/lib/types";
```

Replace the strategy-select test with:

```ts
it("shows order based strategy as static text", async () => {
  render(() => <TraderForm mode="create" onSubmit={vi.fn()} />);

  fireEvent.click(screen.getByRole("button", { name: /advanced settings/i }));

  expect(screen.getByText("Order Based")).toBeInTheDocument();
  expect(screen.queryByLabelText("Strategy Type")).not.toBeInTheDocument();
});
```

Add this test after the static strategy test:

```ts
it("shows credentials only in create mode", () => {
  const onSubmit = vi.fn();
  const { unmount } = render(() => <TraderForm mode="create" onSubmit={onSubmit} />);

  expect(screen.getByLabelText("Wallet Address")).toBeInTheDocument();
  expect(screen.getByLabelText("Private Key")).toBeInTheDocument();

  unmount();

  render(() => <TraderForm mode="edit" onSubmit={onSubmit} initialValues={buildInitialTraderForm("edit", trader)} />);

  expect(screen.getByLabelText("Name")).toBeInTheDocument();
  expect(screen.queryByLabelText("Private Key")).not.toBeInTheDocument();
});
```

In the existing edit config test, use `initialValues={buildInitialTraderForm("edit", trader)}` and `mode="edit"`.

In remaining renders, replace `<TraderConfigForm onSubmit={...} />` with `<TraderForm mode="create" onSubmit={...} />`.

- [ ] **Step 2: Run form tests to verify failure**

Run: `pnpm test -- src/components/traders/TraderConfigForm.test.tsx`

Expected: FAIL because `TraderForm` and new model-based props are not wired.

- [ ] **Step 3: Update imports and props**

In `web/src/components/traders/TraderConfigForm.tsx`, replace schema/default imports with model imports:

```ts
import { type Component, createSignal, Show } from "solid-js";
import { createForm, setValue } from "@modular-forms/solid";
import {
  Eye,
  EyeOff,
  ChevronRight,
  Wallet,
  SlidersHorizontal,
  RotateCcw,
  Info,
} from "lucide-solid";
import { Button } from "~/components/ui/button";
import { Input } from "~/components/ui/input";
import { Label } from "~/components/ui/label";
import { Alert, AlertDescription } from "~/components/ui/alert";
import { Select } from "~/components/ui/select";
import { Switch } from "~/components/ui/switch";
import { TagInput } from "~/components/ui/tag-input";
import { Panel, PanelHeader, PanelBody } from "~/components/ui/panel";
import { SectionLabel } from "~/components/ui/section-label";
import { ToggleGroup } from "~/components/ui/toggle-group";
import { Textarea } from "~/components/ui/textarea";
import { FormGrid } from "~/components/ui/form-grid";
import { cn } from "~/lib/utils";
import {
  buildInitialTraderForm,
  deepMergeFormValues,
  prepareTraderFormValues,
  TRADER_FORM_DEFAULTS,
  validateTraderForm,
  type TraderFormMode,
  type TraderFormValues,
} from "./trader-form-model";
```

Replace props interface and component declaration with:

```ts
export interface TraderFormProps {
  mode: TraderFormMode;
  initialValues?: TraderFormValues;
  onSubmit: (data: TraderFormValues) => Promise<void>;
  isSubmitting?: boolean;
  submitLabel?: string;
}

const ASSET_SELECTOR_HELP = '"*" loads all markets. Examples: BTC = default:BTC, default:* loads default market, xyz:* loads xyz market. Block wins over allow.';

const bpsToPercent = (bps: number) => parseFloat((bps / 100).toFixed(4));
const percentToBps = (percent: number) => Math.round(percent * 100);

export const TraderForm: Component<TraderFormProps> = (props) => {
```

Remove the old local `DEFAULTS`, local `deepMerge`, schema selection, and `isEditing` const. Inside component, add:

```ts
  const initialValues = props.initialValues ?? buildInitialTraderForm(props.mode);
  const isEditing = () => props.mode === "edit";
```

- [ ] **Step 4: Wire model validation and submit**

Replace `createForm` and `handleSubmit` with:

```ts
  const [form, { Form: FormComponent, Field: FormField }] =
    createForm<TraderFormValues>({
      validate: (values) => validateTraderForm(props.mode, initialValues, values),
      initialValues,
    });

  const handleSubmit = async (values: TraderFormValues) => {
    setError(null);
    try {
      const merged = deepMergeFormValues(initialValues, values);
      await props.onSubmit(prepareTraderFormValues(merged));
    } catch (e) {
      setError(e instanceof Error ? e.message : "An error occurred");
    }
  };
```

- [ ] **Step 5: Update create/edit visibility**

Replace all `props.isEditing` checks with `isEditing()`.

Change wallet/private key block to remain inside `<Show when={!isEditing()}>`.

Keep name and description fields inside Account Settings for both modes by removing the `Show when={!props.isEditing}` wrapper around lines 190-238. The resulting metadata block is:

```tsx
          <FormGrid>
            <FormField name="name">
              {(field, fieldProps) => (
                <div class="space-y-1.5">
                  <Label for="name" class="text-xs text-text-muted">
                    Name <span class="text-text-faint">(optional)</span>
                  </Label>
                  <Input
                    {...fieldProps}
                    id="name"
                    type="text"
                    value={field.value ?? ""}
                    placeholder="e.g., Main Trading Bot"
                    maxLength={50}
                  />
                  <Show when={field.error}>
                    <p class="text-xs text-error">{field.error}</p>
                  </Show>
                </div>
              )}
            </FormField>

            <FormField name="description">
              {(field, fieldProps) => (
                <div class="space-y-1.5">
                  <Label for="description" class="text-xs text-text-muted">
                    Description <span class="text-text-faint">(optional)</span>
                  </Label>
                  <Textarea
                    {...fieldProps}
                    id="description"
                    value={field.value ?? ""}
                    onInput={(e) => fieldProps.onInput(e)}
                    onBlur={fieldProps.onBlur}
                    placeholder="Optional notes about this trader"
                    class="min-h-[36px] h-9"
                    maxLength={255}
                    rows={1}
                  />
                  <Show when={field.error}>
                    <p class="text-xs text-error">{field.error}</p>
                  </Show>
                </div>
              )}
            </FormField>
          </FormGrid>
```

- [ ] **Step 6: Replace defaults references**

Replace all `DEFAULTS.` references with `TRADER_FORM_DEFAULTS.`.

Examples:

```ts
const [maxLeverageEnabled, setMaxLeverageEnabled] = createSignal(
  (props.initialValues?.config?.provider_settings?.risk_parameters?.max_leverage ?? null) !== null
);
```

becomes:

```ts
const [maxLeverageEnabled, setMaxLeverageEnabled] = createSignal(
  (initialValues.config.provider_settings.risk_parameters.max_leverage ?? null) !== null
);
```

`DEFAULTS.slippageBps` becomes `TRADER_FORM_DEFAULTS.slippageBps`.

- [ ] **Step 7: Remove one-option select**

Replace the Strategy Type `FormField` block with static text:

```tsx
            <div class="space-y-1.5">
              <Label class="text-xs text-text-muted">Strategy Type</Label>
              <div class="h-9 rounded-md border border-border-default bg-surface-raised px-3 py-2 text-sm text-text-secondary">
                Order Based
              </div>
              <p class="text-xs text-text-muted">Position based exists in config but is not available in manager yet.</p>
            </div>
```

The default `type: "order_based"` remains in the model.

- [ ] **Step 8: Export compatibility alias**

At end of `TraderConfigForm.tsx`, add:

```ts
export const TraderConfigForm = TraderForm;
```

- [ ] **Step 9: Run form tests**

Run: `pnpm test -- src/components/traders/TraderConfigForm.test.tsx`

Expected: PASS.

- [ ] **Step 10: Run model + form tests together**

Run: `pnpm test -- src/components/traders/trader-form-model.test.ts src/components/traders/TraderConfigForm.test.tsx`

Expected: PASS.

- [ ] **Step 11: Commit boundary**

If commits are explicitly requested, run:

```bash
git add web/src/components/traders/TraderConfigForm.tsx web/src/components/traders/TraderConfigForm.test.tsx
git commit -m "web unify trader form UI"
```

---

### Task 3: Thin Create Route

**Files:**
- Modify: `web/src/routes/traders/new.tsx`

**Interfaces:**
- Consumes `TraderForm`, `TraderFormValues`, `toCreateTraderRequest`.
- Produces create route with no local payload shaping.

- [ ] **Step 1: Update imports**

In `web/src/routes/traders/new.tsx`, replace form/type imports with:

```ts
import { TraderForm } from "~/components/traders/TraderConfigForm";
import { toCreateTraderRequest, type TraderFormValues } from "~/components/traders/trader-form-model";
```

Remove:

```ts
import type { CreateTraderForm } from "~/lib/schemas/trader-config";
import type { CreateTraderRequest } from "~/lib/types";
```

- [ ] **Step 2: Simplify mutation**

Replace mutation and handler with:

```ts
  const createTraderMutation = createMutation(() => ({
    mutationFn: (data: TraderFormValues) => api.createTrader(toCreateTraderRequest(data)),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: traderKeys.all });
      navigate("/traders");
    },
  }));

  const handleSubmit = async (data: TraderFormValues) => {
    await createTraderMutation.mutateAsync(data);
  };
```

- [ ] **Step 3: Render `TraderForm`**

Replace the form usage with:

```tsx
          <TraderForm
            mode="create"
            onSubmit={handleSubmit}
            isSubmitting={createTraderMutation.isPending}
            submitLabel="Create Trader"
          />
```

- [ ] **Step 4: Run typecheck**

Run: `pnpm exec tsc --noEmit`

Expected: PASS.

- [ ] **Step 5: Run relevant tests**

Run: `pnpm test -- src/components/traders/trader-form-model.test.ts src/components/traders/TraderConfigForm.test.tsx`

Expected: PASS.

- [ ] **Step 6: Commit boundary**

If commits are explicitly requested, run:

```bash
git add web/src/routes/traders/new.tsx
git commit -m "web simplify trader create route"
```

---

### Task 4: Move Edit Metadata Into Unified Form

**Files:**
- Modify: `web/src/routes/traders/[id].tsx`
- Modify: `web/src/components/traders/overviews/TraderOverview.tsx`

**Interfaces:**
- Consumes `TraderForm`, `buildInitialTraderForm`, `toUpdateTraderRequests`, `TraderFormValues`.
- Produces detail route where Configuration tab submits metadata + config from one form.

- [ ] **Step 1: Update detail route imports**

In `web/src/routes/traders/[id].tsx`, replace form/schema imports:

```ts
import { TraderForm } from "~/components/traders/TraderConfigForm";
import {
  buildInitialTraderForm,
  normalizeTraderConfig,
  toUpdateTraderRequests,
  type TraderFormValues,
} from "~/components/traders/trader-form-model";
```

Remove:

```ts
import type { CreateTraderForm, TraderConfig } from "~/lib/schemas/trader-config";
```

Remove local `normalizeConfig` function at top of file.

- [ ] **Step 2: Remove metadata edit signals and mutation**

Delete these signals:

```ts
  const [editName, setEditName] = createSignal<string>("");
  const [editDescription, setEditDescription] = createSignal<string>("");
  const [infoChanged, setInfoChanged] = createSignal(false);
  const [infoError, setInfoError] = createSignal<string | null>(null);
```

Delete the `createEffect` that initializes edit values from trader data.

Delete `updateInfoMutation`, `handleInfoSave`, `handleNameChange`, and `handleDescriptionChange`.

- [ ] **Step 3: Replace config update mutation**

Replace `updateMutation` with:

```ts
  const updateMutation = createMutation(() => ({
    mutationFn: async (values: TraderFormValues) => {
      const requests = toUpdateTraderRequests(values);
      if (requests.info.name !== undefined || requests.info.description !== undefined) {
        await api.updateTraderInfo(params.id, requests.info);
      }
      return api.updateTrader(params.id, requests.config);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: traderKeys.detail(params.id) });
      queryClient.invalidateQueries({ queryKey: traderKeys.all });
      setShowSavedToast(true);
    },
  }));
```

- [ ] **Step 4: Simplify `TraderOverview` usage**

Replace the `TraderOverview` props block with:

```tsx
                        <TraderOverview
                          trader={trader()}
                          currentStatus={currentStatus}
                          statusQuery={statusQuery}
                          needsImageUpdate={needsImageUpdate}
                          imageQuery={imageQuery}
                          formatUptime={formatUptime}
                        />
```

- [ ] **Step 5: Use unified form in Configuration tab**

Replace the edit form block with:

```tsx
                                <TraderForm
                                  mode="edit"
                                  initialValues={buildInitialTraderForm("edit", {
                                    ...trader(),
                                    latest_config: normalizeTraderConfig(config()),
                                  })}
                                  onSubmit={async (data) => {
                                    await updateMutation.mutateAsync(data);
                                  }}
                                  isSubmitting={updateMutation.isPending}
                                  submitLabel="Save Trader"
                                />
```

- [ ] **Step 6: Update `TraderOverview` props**

In `web/src/components/traders/overviews/TraderOverview.tsx`, replace `OverviewDesignProps` with:

```ts
export interface OverviewDesignProps {
  trader: Trader;
  currentStatus: () => Trader["status"] | RuntimeStatus["state"];
  statusQuery: UseQueryResult<TraderStatusResponse, Error>;
  needsImageUpdate: () => boolean;
  imageQuery: { data?: { latest_remote?: string | null } };
  formatUptime: (startedAt: string) => string;
}
```

Remove imports no longer used:

```ts
import { Input } from "~/components/ui/input";
import { Textarea } from "~/components/ui/textarea";
import { Button } from "~/components/ui/button";
```

Delete the `Trader Info Panel` block from `<Panel>` through `</Panel>` that renders editable name/description.

- [ ] **Step 7: Run typecheck**

Run: `pnpm exec tsc --noEmit`

Expected: PASS.

- [ ] **Step 8: Run relevant tests**

Run: `pnpm test -- src/components/traders/trader-form-model.test.ts src/components/traders/TraderConfigForm.test.tsx`

Expected: PASS.

- [ ] **Step 9: Commit boundary**

If commits are explicitly requested, run:

```bash
git add web/src/routes/traders/[id].tsx web/src/components/traders/overviews/TraderOverview.tsx
git commit -m "web unify trader edit form"
```

---

### Task 5: Cleanup and Full Verification

**Files:**
- Modify only files that fail tests/typecheck from prior tasks.

**Interfaces:**
- Consumes all prior tasks.
- Produces passing frontend typecheck and unit tests for touched form code.

- [ ] **Step 1: Search stale names**

Run: `grep -R "isEditing\|CreateTraderForm\|normalizeConfig\|editName\|updateInfoMutation" web/src --include='*.ts' --include='*.tsx'`

Expected: no stale `isEditing` prop usage, no route-local `normalizeConfig`, no detail metadata edit state. `CreateTraderForm` may remain only in schema/model internals.

- [ ] **Step 2: Remove compatibility alias if no callers need old name**

If grep shows no `TraderConfigForm` imports outside `TraderConfigForm.tsx`, rename file later in a separate mechanical cleanup. For this refactor, keep filename and alias to avoid churn.

- [ ] **Step 3: Run full unit tests**

Run: `pnpm test`

Expected: PASS.

- [ ] **Step 4: Run typecheck**

Run: `pnpm exec tsc --noEmit`

Expected: PASS.

- [ ] **Step 5: Run production build**

Run: `pnpm build`

Expected: PASS.

- [ ] **Step 6: Commit boundary**

If commits are explicitly requested, run:

```bash
git add web/src docs/superpowers/specs/2026-06-30-web-trader-form-refactor-design.md docs/superpowers/plans/2026-06-30-web-trader-form-refactor.md
git commit -m "web refactor trader form flow"
```

---

## Self-Review

- Spec coverage: Task 1 covers model/defaults/normalization/payload helpers; Task 2 covers unified UI and ponytail strategy select cut; Task 3 covers create route; Task 4 covers edit route and metadata consolidation; Task 5 covers verification.
- Placeholder scan: no deferred implementation placeholders remain in task steps.
- Type consistency: plan consistently uses `TraderFormValues`, `TraderFormMode`, `toCreateTraderRequest`, and `toUpdateTraderRequests`.
