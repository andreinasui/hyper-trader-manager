# Trader Detail Visual Refresh — Design Spec

**Date:** 2026-04-25  
**Status:** Approved  
**Approach:** Surgical styling updates (Approach A)

## Goal

Apply the enhanced table design language (V1) from the traders list page to the trader detail page (`/traders/[id]`) for visual consistency across the trader management UI.

## Scope

Visual-only changes to match V1 patterns:
- Status-based border tints and background shading
- Typography consistency (font sizes, weights, colors)
- Error styling alignment
- Start attempts badge in header
- Version update indicator polish

No structural changes to layout, tabs, or component hierarchy.

## User Requirements

1. Visual refresh to match V1 design language
2. Uptime metric remains visible only when trader is running (current behavior is correct)
3. Keep action buttons as full-text buttons in header (no compacting to icons)

## Design

### 1. Page Header Section

#### Status & Title
- **Status dot:** Keep existing `<StatusDot status={currentStatus()} />` next to trader name
- **Trader name:** Keep `text-2xl font-semibold text-text-base`
- **Start attempts badge:** Add when `trader().start_attempts > 0`:
  ```tsx
  <Show when={(trader().start_attempts ?? 0) > 0}>
    <span class="text-[10px] font-mono px-1 py-0.5 rounded bg-error/20 text-error leading-none">
      ×{trader().start_attempts}
    </span>
  </Show>
  ```

#### Metadata Strip
Update typography to match V1:
```tsx
<div class="flex items-center gap-4 text-xs text-text-subtle">
  <span class="font-mono">
    {shortWallet(trader().wallet_address)}
  </span>
  <span class="flex items-center gap-1">
    <span>v{trader().image_tag}</span>
    <Show when={needsImageUpdate()}>
      <span class="h-1.5 w-1.5 rounded-full bg-warning flex-shrink-0" 
            title={`Update to ${imageQuery.data?.latest_remote}`} />
    </Show>
  </span>
  <span>Created {relDate(trader().created_at)}</span>
</div>
```

Changes:
- Use `text-xs text-text-subtle` (was mixed sizes)
- Use `shortWallet()` helper from `trader-page-utils.ts`
- Add warning dot for version updates (matching list row pattern)

#### Action Buttons
No changes — keep current layout and styling.

### 2. Overview Tab — Status Panel

Apply status-based visual tinting to the Status panel wrapper:

```tsx
<Panel class={`
  border-l-2 transition-colors
  ${currentStatus() === "running"  ? "border-l-success bg-success/[0.02]"  : ""}
  ${currentStatus() === "failed"   ? "border-l-error  bg-error/[0.03]"     : ""}
  ${currentStatus() === "starting" ? "border-l-warning bg-warning/[0.03]"  : ""}
  ${!["running","failed","starting"].includes(currentStatus()) 
    ? "border-l-border-default" : ""}
`}>
  <PanelHeader title="Status" />
  <PanelBody class="py-0">
    {/* ... existing rows ... */}
  </PanelBody>
</Panel>
```

#### Uptime Row
Current implementation is correct — verify conditional remains:
```tsx
<Show when={trader().status === "running" && statusQuery.data?.runtime_status?.started_at}>
  <PanelRow label="Uptime">
    {formatUptime(statusQuery.data!.runtime_status.started_at!)}
  </PanelRow>
</Show>
```

#### Error Box
Update styling to match V1 pattern:
```tsx
<Show when={statusQuery.data?.runtime_status?.error || trader().last_error}>
  <div class="bg-error/[0.06] rounded p-3 my-3">
    <div class="flex items-start gap-2">
      <AlertCircle class="h-3.5 w-3.5 text-error flex-shrink-0 mt-0.5" stroke-width={1.5} />
      <span class="text-xs text-error font-mono break-all">
        {statusQuery.data?.runtime_status?.error || trader().last_error}
      </span>
    </div>
  </div>
</Show>
```

Changes:
- Icon size: `h-3.5 w-3.5` (was `h-4 w-4`)
- Text size: `text-xs` (was `text-sm`)
- Add `font-mono` to error text
- Use `flex items-start gap-2` layout (simpler than nested divs)

### 3. Trader Info Panel

Add matching border for visual alignment with Status panel:
```tsx
<Panel class="border-l-2 border-l-border-default">
  <PanelHeader title="Trader info" />
  <PanelBody class="space-y-4">
    {/* ... existing form ... */}
  </PanelBody>
</Panel>
```

No background tint (remains neutral).

### 4. Typography Standards

Ensure consistency across all metadata:
- Metadata labels: `text-xs text-text-subtle`
- Monospace values (wallet, version): `font-mono`
- Error messages: `text-xs font-mono text-error`
- Dates: Use existing `relDate()` helper

## Implementation Notes

### Reusable Utilities
Import from `trader-page-utils.ts`:
- `shortWallet(address)` — formats wallet address
- `semverGt(v1, v2)` — used in `needsImageUpdate()`

### Status Color Mapping
Match V1 conventions:
- `running` → `border-l-success`, `bg-success/[0.02]`
- `failed` → `border-l-error`, `bg-error/[0.03]`
- `starting` → `border-l-warning`, `bg-warning/[0.03]`
- Other states → `border-l-border-default`, no background

### Existing Behavior Preserved
- All queries/mutations unchanged
- Tab navigation unchanged
- Form interactions unchanged
- LogViewer and TraderConfigForm components unchanged
- Action button logic unchanged

## Testing Checklist

- [ ] Visual: Status panel shows correct border color for each status
- [ ] Visual: Start attempts badge appears when > 0
- [ ] Visual: Version update dot appears when remote > current
- [ ] Visual: Error box styling matches V1 (small icon, xs mono text)
- [ ] Functional: Uptime shows only when running with started_at
- [ ] Functional: All mutations still work (start/stop/delete/update)
- [ ] Typography: Metadata strip uses xs text throughout
- [ ] Border: Both panels have left border (Status=status-tinted, Info=default)

## Files Changed

- `web/src/routes/traders/[id].tsx` — Apply all visual updates

## Dependencies

- Existing: `trader-page-utils.ts` (already present from list redesign)
- Existing: All UI components (Panel, StatusDot, etc.)
- No new dependencies
