# Trader Form Unification Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remove name/description from the edit-mode Configuration tab, deduplicate `validateForm`, and lower the max leverage cap from 50 to 40 across all layers.

**Architecture:** Three targeted edits across four files — no structural changes. The form component already uses `isEditing` guards for wallet/key fields; we extend that same pattern to name/description. The cap change propagates through frontend DEFAULTS → frontend Zod schema → backend Pydantic schema → backend tests.

**Tech Stack:** SolidJS, `@modular-forms/solid`, Zod (frontend); Python 3.11, Pydantic v2, pytest (backend).

---

## File map

| File | Change |
|------|--------|
| `web/src/components/traders/TraderConfigForm.tsx` | Wrap name/description grid in `<Show when={!props.isEditing}>`, flatten `validateForm`, lower `DEFAULTS.maxLeverageMax` 50→40 |
| `web/src/lib/schemas/trader-config.ts` | Lower `max_leverage` Zod constraint `.max(50)` → `.max(40)` |
| `api/hyper_trader_api/schemas/trader_config.py` | Lower `RiskParameters.max_leverage` field `le=50` → `le=40` |
| `api/tests/test_trader_config_schema.py` | Update `test_max_leverage_bounds` docstring, valid-upper (50→40), invalid-lower (51→41) |

---

## Task 1: Lower max leverage cap in backend schema and tests

**Files:**
- Modify: `api/hyper_trader_api/schemas/trader_config.py`
- Modify: `api/tests/test_trader_config_schema.py`

- [ ] **Step 1: Confirm current tests pass**

```bash
cd api && uv run pytest tests/test_trader_config_schema.py::TestRiskParametersValidation::test_max_leverage_bounds -v
```

Expected output contains: `PASSED`

- [ ] **Step 2: Update the test to expect 40 as the valid upper bound**

In `api/tests/test_trader_config_schema.py`, find `test_max_leverage_bounds` (around line 295) and update:

```python
def test_max_leverage_bounds(self):
    """RiskParameters validates max_leverage is between 1 and 40."""
    # Valid: 1
    params = RiskParameters(max_leverage=1)
    assert params.max_leverage == 1

    # Valid: 40
    params = RiskParameters(max_leverage=40)
    assert params.max_leverage == 40

    # Valid: None (disabled)
    params = RiskParameters(max_leverage=None)
    assert params.max_leverage is None

    # Invalid: 0
    with pytest.raises(ValidationError) as exc_info:
        RiskParameters(max_leverage=0)
    assert "max_leverage" in str(exc_info.value).lower()

    # Invalid: 41
    with pytest.raises(ValidationError) as exc_info:
        RiskParameters(max_leverage=41)
    assert "max_leverage" in str(exc_info.value).lower()
```

- [ ] **Step 3: Run test — expect FAIL (still 50 in schema)**

```bash
cd api && uv run pytest tests/test_trader_config_schema.py::TestRiskParametersValidation::test_max_leverage_bounds -v
```

Expected: `FAILED` — `RiskParameters(max_leverage=41)` does not raise yet.

- [ ] **Step 4: Update backend schema**

In `api/hyper_trader_api/schemas/trader_config.py`, find the `max_leverage` field (around line 92):

```python
max_leverage: int | None = Field(
    default=None,
    ge=1,
    le=40,
    description="Maximum leverage allowed for positions",
)
```

(Change `le=50` to `le=40`.)

- [ ] **Step 5: Run test — expect PASS**

```bash
cd api && uv run pytest tests/test_trader_config_schema.py::TestRiskParametersValidation::test_max_leverage_bounds -v
```

Expected: `PASSED`

- [ ] **Step 6: Run full backend test suite**

```bash
cd api && uv run pytest
```

Expected: all tests pass.

- [ ] **Step 7: Commit**

```bash
cd api && git add hyper_trader_api/schemas/trader_config.py tests/test_trader_config_schema.py
git commit -m "api: lower max_leverage cap from 50 to 40"
```

---

## Task 2: Lower max leverage cap in frontend Zod schema

**Files:**
- Modify: `web/src/lib/schemas/trader-config.ts`

- [ ] **Step 1: Update Zod constraint**

In `web/src/lib/schemas/trader-config.ts`, find `riskParametersSchema` (around line 44) and change `.max(50)` to `.max(40)`:

```ts
export const riskParametersSchema = z.object({
  allowed_assets: z.array(z.string()).nullable().optional(),
  blocked_assets: z.array(z.string()).default([]),
  max_leverage: z.number().int().min(1).max(40).nullable().optional(),
  self_proportionality_multiplier: z.number().min(0.01).max(10).default(1.0),
  open_on_low_pnl: openOnLowPnlSchema.default({}),
});
```

- [ ] **Step 2: Verify TypeScript still compiles**

```bash
cd web && pnpm exec tsc --noEmit
```

Expected: no output (zero errors).

- [ ] **Step 3: Commit**

```bash
cd web && git add src/lib/schemas/trader-config.ts
git commit -m "web: lower max_leverage Zod constraint from 50 to 40"
```

---

## Task 3: Update `TraderConfigForm` — DEFAULTS, `validateForm`, hide name/description in edit mode

**Files:**
- Modify: `web/src/components/traders/TraderConfigForm.tsx`

All three changes are in the same file and are small enough to do in one task.

- [ ] **Step 1: Lower `DEFAULTS.maxLeverageMax`**

In `web/src/components/traders/TraderConfigForm.tsx`, find the `DEFAULTS` object (around line 37) and change `maxLeverageMax` from `50` to `40`:

```ts
const DEFAULTS = {
  multiplier: 1.0,
  maxPnl: 0.05,
  maxLeverage: 10,
  maxLeverageMin: 1,
  maxLeverageMax: 40,          // was 50
  slippageBps: 200,
  ratioThreshold: 1000,
  wideBucketPct: 0.01,
  narrowBucketPct: 0.0001,
  widthPercent: 0.01,
} as const;
```

- [ ] **Step 2: Flatten `validateForm`**

Find the `validateForm` function (around line 63) and replace it with the single-path version. The `schema` variable must be declared **before** the `createForm` call that references `validateForm` (it already is — `isEditing` is set on line 60, before the function).

Replace:

```ts
const validateForm = (values: PartialValues<CreateTraderForm>) => {
  if (isEditing) {
    const result = editTraderFormSchema.safeParse(values);
    if (!result.success) {
      const errors: Record<string, string> = {};
      result.error.errors.forEach((err) => {
        errors[err.path.join(".")] = err.message;
      });
      return errors;
    }
    return {};
  } else {
    const result = createTraderFormSchema.safeParse(values);
    if (!result.success) {
      const errors: Record<string, string> = {};
      result.error.errors.forEach((err) => {
        errors[err.path.join(".")] = err.message;
      });
      return errors;
    }
    return {};
  }
};
```

With:

```ts
const schema = isEditing ? editTraderFormSchema : createTraderFormSchema;
const validateForm = (values: PartialValues<CreateTraderForm>) => {
  const result = schema.safeParse(values);
  if (!result.success) {
    const errors: Record<string, string> = {};
    result.error.errors.forEach((err) => {
      errors[err.path.join(".")] = err.message;
    });
    return errors;
  }
  return {};
};
```

- [ ] **Step 3: Wrap name/description in `<Show when={!props.isEditing}>`**

Find the name/description grid (around line 158). It currently starts with:

```tsx
{/* Name + Description */}
<div class="grid grid-cols-1 gap-4 sm:grid-cols-2">
  <FormField name="name">
  ...
  </FormField>

  <FormField name="description">
  ...
  </FormField>
</div>
```

Wrap it:

```tsx
{/* Name + Description — create mode only; edit mode uses Overview tab */}
<Show when={!props.isEditing}>
  <div class="grid grid-cols-1 gap-4 sm:grid-cols-2">
    <FormField name="name">
    ...
    </FormField>

    <FormField name="description">
    ...
    </FormField>
  </div>
</Show>
```

- [ ] **Step 4: Verify TypeScript compiles**

```bash
cd web && pnpm exec tsc --noEmit
```

Expected: no output.

- [ ] **Step 5: Commit**

```bash
cd web && git add src/components/traders/TraderConfigForm.tsx
git commit -m "web: hide name/description in edit mode, flatten validateForm, lower maxLeverageMax to 40"
```

---

## Task 4: Manual browser verification

- [ ] **Step 1: Start dev server** (if not already running)

```bash
cd web && pnpm dev
```

- [ ] **Step 2: Verify create form still shows name/description**

Navigate to `http://localhost:3000/traders/new`. Confirm the Name and Description fields are visible in the Account Settings panel.

- [ ] **Step 3: Verify edit form hides name/description**

Navigate to any existing trader's detail page → Configuration tab. Confirm Name and Description fields are NOT shown. Copy Account Address should be the first visible field.

- [ ] **Step 4: Verify max leverage cap is now 40 on create form**

On `/traders/new`, expand Advanced Settings, enable "Set max leverage", type `41`. Click "Create Trader". Confirm error: "Number must be less than or equal to 40" appears and form does not submit.

- [ ] **Step 5: Verify max leverage cap is now 40 on edit form**

On the existing trader's Configuration tab, expand Advanced Settings, enable "Set max leverage" (or it may already be on), type `41`. Click "Save Configuration". Confirm the same error appears.

- [ ] **Step 6: Verify valid value 40 saves on edit form**

Type `40` in max leverage. Click "Save Configuration". Confirm "Saved." toast appears.
