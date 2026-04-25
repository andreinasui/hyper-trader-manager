# Trader Form Unification — Design Spec

**Date:** 2026-04-25  
**Status:** Approved

---

## Problem

Two bugs exist in the trader configuration form:

1. **Silent discard of name/description in edit mode.** `TraderConfigForm` renders name and description fields in both create and edit mode. In edit mode, the `onSubmit` handler in `[id].tsx` only saves `data.config`; any name/description edits in the Configuration tab are silently discarded. The Overview tab has its own working name/description editor — so users have two editors but only one works.

2. **Code duplication in `validateForm`.** The validation helper contains an if/else with two identical code branches — the only difference is which Zod schema is used.

3. **Max leverage cap inconsistency.** The intended maximum leverage is 40, but all three layers (frontend DEFAULTS, frontend Zod schema, backend Pydantic schema) currently cap it at 50. This needs to be corrected to 40 everywhere.

---

## Decision

**Option A — minimal targeted fixes.** The form is already unified (one `TraderConfigForm` component, used by both create and edit routes). No architectural change is needed. Three focused edits:

1. Hide name/description in edit mode.
2. Deduplicate `validateForm`.
3. Lower the max leverage cap from 50 → 40 across all layers.

---

## Changes

### 1. `web/src/components/traders/TraderConfigForm.tsx`

**Hide name/description in edit mode.**

Wrap the name/description `<FormField>` grid in `<Show when={!props.isEditing}>`. This matches the existing pattern already used for `wallet_address` and `private_key` (line 205). In edit mode these fields are owned by the Overview tab's Trader Info card; showing them in Configuration would mislead users into making edits that are silently discarded.

**Deduplicate `validateForm`.**

Replace the if/else double-branch with a single computed schema variable:

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

**Lower max leverage DEFAULTS.**

Change `DEFAULTS.maxLeverageMax` from `50` to `40`.

### 2. `web/src/lib/schemas/trader-config.ts`

Change `riskParametersSchema`:
```ts
// before
max_leverage: z.number().int().min(1).max(50).nullable().optional(),
// after
max_leverage: z.number().int().min(1).max(40).nullable().optional(),
```

### 3. `api/hyper_trader_api/schemas/trader_config.py`

Change `RiskParameters.max_leverage` field:
```python
# before
max_leverage: int | None = Field(default=None, ge=1, le=50, ...)
# after
max_leverage: int | None = Field(default=None, ge=1, le=40, ...)
```

### 4. `api/tests/test_trader_config_schema.py`

Update `test_max_leverage_bounds` assertions to use `40` as the valid upper bound and `41` as the first invalid value:
```python
# before
params = RiskParameters(max_leverage=50)   # valid upper
RiskParameters(max_leverage=51)             # invalid
# after
params = RiskParameters(max_leverage=40)   # valid upper
RiskParameters(max_leverage=41)             # invalid
```

---

## What does NOT change

- `[id].tsx` — unchanged; Overview Trader Info card keeps its working name/description editor.
- `new.tsx` — unchanged; create flow is unaffected.
- The two Zod schemas (`createTraderFormSchema` / `editTraderFormSchema`) — kept as-is; they serve different purposes (create includes wallet/key validation + cross-field refinement; edit does not).
- All other form fields, validation logic, and UI layout.

---

## Acceptance criteria

- [ ] Name and Description fields are NOT visible in the Configuration tab when editing an existing trader.
- [ ] Name and Description fields ARE visible when creating a new trader.
- [ ] Entering max leverage > 40 on either create or edit form shows a validation error and blocks submission.
- [ ] Entering max leverage ≤ 40 (≥ 1) on either create or edit form saves successfully.
- [ ] Backend rejects `max_leverage: 41` with a validation error.
- [ ] `validateForm` has one code path, not two.
- [ ] `pnpm exec tsc --noEmit` passes with zero errors.
- [ ] `uv run pytest` passes with zero failures.
