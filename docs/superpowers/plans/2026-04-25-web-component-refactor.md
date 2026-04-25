# Web Component Refactor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Refactor web codebase to abstract Tailwind into reusable components with parametrized color scheme.

**Architecture:** Define CSS color tokens via Tailwind v4 `@theme`, create semantic layout/UI components, then refactor routes one-by-one to use components instead of inline Tailwind.

**Tech Stack:** SolidJS 1.9+, Tailwind CSS v4, Kobalte UI, TypeScript

**Spec:** `docs/superpowers/specs/2026-04-25-web-component-refactor-design.md`

---

## File Structure

### New Files
```
web/src/components/layout/
├── PageHeader.tsx      # Sticky breadcrumb bar
├── PageContent.tsx     # Padded page container
└── PageTitle.tsx       # Title + subtitle + action

web/src/components/ui/
├── panel.tsx           # Panel, PanelHeader, PanelBody, PanelRow
├── kpi-card.tsx        # KpiCard, KpiStrip
├── empty-state.tsx     # EmptyState
├── icon-button.tsx     # IconButton with tooltip
├── data-table.tsx      # DataTable, DataTableRow
├── section-label.tsx   # SectionLabel divider
├── toggle-group.tsx    # ToggleGroup for mode switching
└── textarea.tsx        # Textarea component
```

### Modified Files
```
web/src/styles.css                          # Add @theme color tokens
web/src/components/ui/index.ts              # Export new components
web/src/components/ui/button.tsx            # Use color tokens
web/src/components/ui/input.tsx             # Use color tokens
web/src/components/ui/card.tsx              # Use color tokens
web/src/components/ui/alert.tsx             # Use color tokens
web/src/components/ui/badge.tsx             # Use color tokens
web/src/components/ui/status-badge.tsx      # Use color tokens
web/src/components/ui/tabs.tsx              # Use color tokens
web/src/components/layout/AppShell.tsx      # Use color tokens
web/src/components/layout/Sidebar.tsx       # Use color tokens
web/src/routes/index.tsx                    # Refactor to components
web/src/routes/setup/index.tsx              # Refactor to components
web/src/routes/setup/ssl.tsx                # Refactor to components
web/src/routes/settings.tsx                 # Refactor to components
web/src/routes/traders/new.tsx              # Refactor to components
web/src/routes/traders/[id].tsx             # Refactor to components
web/src/routes/traders/index.tsx            # Refactor to components
web/src/components/traders/TraderConfigForm.tsx    # Use tokens, extract SectionLabel
web/src/components/traders/ImageVersionBanner.tsx  # Use tokens
web/src/components/traders/LogViewer.tsx           # Use tokens
web/src/app.tsx                             # Use color tokens
```

---

## Task 1: Add Color Tokens to styles.css

**Files:**
- Modify: `web/src/styles.css`

- [ ] **Step 1: Read current styles.css**

Check existing content to understand current structure.

- [ ] **Step 2: Add @theme color tokens**

Add after existing imports in `web/src/styles.css`:

```css
@theme {
  /* ── Surfaces ─────────────────────────────────────── */
  --color-surface-base: #08090a;
  --color-surface-raised: #111214;
  --color-surface-overlay: #1a1b1e;
  --color-surface-subtle: #161719;

  /* ── Borders ──────────────────────────────────────── */
  --color-border-default: #222426;
  --color-border-ring: #5e6ad2;

  /* ── Primary ──────────────────────────────────────── */
  --color-primary: #5e6ad2;
  --color-primary-hover: #6b76d9;
  --color-primary-muted: oklch(from #5e6ad2 l c h / 20%);

  /* ── Text ─────────────────────────────────────────── */
  --color-text-base: var(--color-zinc-50);
  --color-text-secondary: var(--color-zinc-200);
  --color-text-tertiary: var(--color-zinc-300);
  --color-text-muted: var(--color-zinc-400);
  --color-text-subtle: var(--color-zinc-500);
  --color-text-faint: var(--color-zinc-600);

  /* ── Semantic ─────────────────────────────────────── */
  --color-success: var(--color-emerald-400);
  --color-warning: var(--color-amber-400);
  --color-error: var(--color-red-400);
  --color-error-muted: var(--color-red-900);
  --color-error-surface: oklch(from var(--color-red-950) l c h / 20%);
  --color-warning-muted: var(--color-amber-900);
  --color-warning-surface: oklch(from var(--color-amber-950) l c h / 30%);
}
```

- [ ] **Step 3: Run dev server to verify no errors**

Run: `pnpm dev`
Expected: Server starts without CSS errors, page loads.

- [ ] **Step 4: Commit**

```bash
git add web/src/styles.css
git commit -m "web: add color token system via @theme"
```

---

## Task 2: Create Panel Component

**Files:**
- Create: `web/src/components/ui/panel.tsx`
- Modify: `web/src/components/ui/index.ts`

- [ ] **Step 1: Create panel.tsx**

Create `web/src/components/ui/panel.tsx`:

```tsx
import { type JSX, type Component, splitProps } from "solid-js";
import { cn } from "~/lib/utils";

export interface PanelProps extends JSX.HTMLAttributes<HTMLDivElement> {}

export function Panel(props: PanelProps) {
  const [local, others] = splitProps(props, ["class", "children"]);
  return (
    <div
      class={cn(
        "bg-surface-raised border border-border-default rounded-md overflow-hidden",
        local.class
      )}
      {...others}
    >
      {local.children}
    </div>
  );
}

export interface PanelHeaderProps {
  icon?: Component<{ class?: string }>;
  title: string;
  description?: string;
  class?: string;
}

export function PanelHeader(props: PanelHeaderProps) {
  return (
    <div
      class={cn(
        "px-5 py-3.5 border-b border-border-default flex items-center gap-2.5",
        props.class
      )}
    >
      {props.icon && <props.icon class="w-4 h-4 text-text-subtle shrink-0" />}
      <span class="text-sm font-medium text-text-secondary">{props.title}</span>
      {props.description && (
        <span class="ml-auto text-xs text-text-faint hidden sm:block">
          {props.description}
        </span>
      )}
    </div>
  );
}

export interface PanelBodyProps extends JSX.HTMLAttributes<HTMLDivElement> {}

export function PanelBody(props: PanelBodyProps) {
  const [local, others] = splitProps(props, ["class", "children"]);
  return (
    <div class={cn("px-5 py-5", local.class)} {...others}>
      {local.children}
    </div>
  );
}

export interface PanelRowProps {
  label: string;
  children: JSX.Element;
  border?: boolean;
  class?: string;
}

export function PanelRow(props: PanelRowProps) {
  const showBorder = props.border ?? true;
  return (
    <div
      class={cn(
        "flex justify-between items-center py-3",
        showBorder && "border-b border-border-default",
        props.class
      )}
    >
      <span class="text-sm text-text-subtle">{props.label}</span>
      <div class="text-sm text-text-secondary">{props.children}</div>
    </div>
  );
}
```

- [ ] **Step 2: Export from index.ts**

Add to `web/src/components/ui/index.ts`:

```ts
export * from "./panel";
```

- [ ] **Step 3: Run build to verify types**

Run: `pnpm build`
Expected: Build succeeds with no TypeScript errors.

- [ ] **Step 4: Commit**

```bash
git add web/src/components/ui/panel.tsx web/src/components/ui/index.ts
git commit -m "web: add Panel component family"
```

---

## Task 3: Create KpiCard Component

**Files:**
- Create: `web/src/components/ui/kpi-card.tsx`
- Modify: `web/src/components/ui/index.ts`

- [ ] **Step 1: Create kpi-card.tsx**

Create `web/src/components/ui/kpi-card.tsx`:

```tsx
import { type JSX, splitProps } from "solid-js";
import { cn } from "~/lib/utils";

export type KpiVariant = "default" | "success" | "warning" | "error";

export interface KpiCardProps {
  label: string;
  value: number | string;
  variant?: KpiVariant;
  class?: string;
}

const dotColors: Record<KpiVariant, string> = {
  default: "bg-text-subtle",
  success: "bg-success",
  warning: "bg-warning",
  error: "bg-error",
};

export function KpiCard(props: KpiCardProps) {
  const variant = () => props.variant ?? "default";
  return (
    <div
      class={cn(
        "bg-surface-raised border border-border-default rounded-md p-4 hover:bg-surface-overlay transition-all",
        props.class
      )}
    >
      <div class="flex items-center gap-2 mb-2">
        <div class={cn("w-1.5 h-1.5 rounded-full", dotColors[variant()])} />
        <span class="text-xs font-medium text-text-subtle uppercase tracking-wide">
          {props.label}
        </span>
      </div>
      <div class="text-2xl font-semibold tabular-nums text-text-base">
        {props.value}
      </div>
    </div>
  );
}

export interface KpiStripProps extends JSX.HTMLAttributes<HTMLDivElement> {}

export function KpiStrip(props: KpiStripProps) {
  const [local, others] = splitProps(props, ["class", "children"]);
  return (
    <div class={cn("grid grid-cols-3 gap-4", local.class)} {...others}>
      {local.children}
    </div>
  );
}
```

- [ ] **Step 2: Export from index.ts**

Add to `web/src/components/ui/index.ts`:

```ts
export * from "./kpi-card";
```

- [ ] **Step 3: Run build to verify types**

Run: `pnpm build`
Expected: Build succeeds.

- [ ] **Step 4: Commit**

```bash
git add web/src/components/ui/kpi-card.tsx web/src/components/ui/index.ts
git commit -m "web: add KpiCard and KpiStrip components"
```

---

## Task 4: Create EmptyState Component

**Files:**
- Create: `web/src/components/ui/empty-state.tsx`
- Modify: `web/src/components/ui/index.ts`

- [ ] **Step 1: Create empty-state.tsx**

Create `web/src/components/ui/empty-state.tsx`:

```tsx
import { type JSX, type Component } from "solid-js";
import { cn } from "~/lib/utils";

export interface EmptyStateProps {
  icon: Component<{ class?: string }>;
  title: string;
  description: string;
  action?: JSX.Element;
  class?: string;
}

export function EmptyState(props: EmptyStateProps) {
  return (
    <div
      class={cn(
        "bg-surface-raised border border-border-default rounded-md p-12 flex flex-col items-center justify-center text-center",
        props.class
      )}
    >
      <div class="bg-surface-overlay rounded-md p-3 mb-4">
        <props.icon class="w-10 h-10 text-text-subtle" />
      </div>
      <h3 class="text-base font-semibold text-text-secondary mb-1">
        {props.title}
      </h3>
      <p class="text-sm text-text-subtle mb-4">{props.description}</p>
      {props.action}
    </div>
  );
}
```

- [ ] **Step 2: Export from index.ts**

Add to `web/src/components/ui/index.ts`:

```ts
export * from "./empty-state";
```

- [ ] **Step 3: Run build to verify types**

Run: `pnpm build`
Expected: Build succeeds.

- [ ] **Step 4: Commit**

```bash
git add web/src/components/ui/empty-state.tsx web/src/components/ui/index.ts
git commit -m "web: add EmptyState component"
```

---

## Task 5: Create IconButton Component

**Files:**
- Create: `web/src/components/ui/icon-button.tsx`
- Modify: `web/src/components/ui/index.ts`

- [ ] **Step 1: Create icon-button.tsx**

Create `web/src/components/ui/icon-button.tsx`:

```tsx
import { type JSX, type Component, splitProps, Show } from "solid-js";
import { Loader2 } from "lucide-solid";
import { Tooltip, TooltipContent, TooltipTrigger } from "./tooltip";
import { cn } from "~/lib/utils";

export interface IconButtonProps
  extends JSX.ButtonHTMLAttributes<HTMLButtonElement> {
  icon: Component<{ class?: string }>;
  tooltip: string;
  variant?: "ghost" | "danger";
  loading?: boolean;
}

export function IconButton(props: IconButtonProps) {
  const [local, others] = splitProps(props, [
    "icon",
    "tooltip",
    "variant",
    "loading",
    "class",
    "disabled",
  ]);

  const variant = () => local.variant ?? "ghost";

  return (
    <Tooltip>
      <TooltipTrigger
        as="button"
        type="button"
        disabled={local.disabled || local.loading}
        class={cn(
          "p-1.5 rounded transition-colors disabled:opacity-50",
          variant() === "ghost" &&
            "hover:bg-surface-overlay text-text-muted hover:text-text-secondary",
          variant() === "danger" &&
            "hover:bg-surface-overlay text-text-muted hover:text-error",
          local.class
        )}
        {...others}
      >
        <Show
          when={local.loading}
          fallback={<local.icon class="h-4 w-4" />}
        >
          <Loader2 class="h-4 w-4 animate-spin" />
        </Show>
      </TooltipTrigger>
      <TooltipContent>{local.tooltip}</TooltipContent>
    </Tooltip>
  );
}
```

- [ ] **Step 2: Export from index.ts**

Add to `web/src/components/ui/index.ts`:

```ts
export * from "./icon-button";
```

- [ ] **Step 3: Run build to verify types**

Run: `pnpm build`
Expected: Build succeeds.

- [ ] **Step 4: Commit**

```bash
git add web/src/components/ui/icon-button.tsx web/src/components/ui/index.ts
git commit -m "web: add IconButton component with tooltip"
```

---

## Task 6: Create DataTable Component

**Files:**
- Create: `web/src/components/ui/data-table.tsx`
- Modify: `web/src/components/ui/index.ts`

- [ ] **Step 1: Create data-table.tsx**

Create `web/src/components/ui/data-table.tsx`:

```tsx
import { type JSX, splitProps, For } from "solid-js";
import { cn } from "~/lib/utils";

export interface Column {
  key: string;
  label: string;
  span: number;
}

export interface DataTableProps {
  columns: Column[];
  children: JSX.Element;
  class?: string;
}

const colSpanClasses: Record<number, string> = {
  1: "col-span-1",
  2: "col-span-2",
  3: "col-span-3",
  4: "col-span-4",
  5: "col-span-5",
  6: "col-span-6",
  7: "col-span-7",
  8: "col-span-8",
  9: "col-span-9",
  10: "col-span-10",
  11: "col-span-11",
  12: "col-span-12",
};

export function DataTable(props: DataTableProps) {
  return (
    <div
      class={cn(
        "bg-surface-raised border border-border-default rounded-md overflow-hidden",
        props.class
      )}
    >
      {/* Header */}
      <div class="border-b border-border-default px-4 py-3 grid grid-cols-12 gap-4">
        <For each={props.columns}>
          {(col) => (
            <div
              class={cn(
                colSpanClasses[col.span],
                "text-xs font-medium text-text-subtle uppercase tracking-wide"
              )}
            >
              {col.label}
            </div>
          )}
        </For>
      </div>
      {/* Body */}
      {props.children}
    </div>
  );
}

export interface DataTableRowProps extends JSX.HTMLAttributes<HTMLDivElement> {
  selected?: boolean;
}

export function DataTableRow(props: DataTableRowProps) {
  const [local, others] = splitProps(props, ["class", "children", "selected"]);
  return (
    <div
      class={cn(
        "border-b border-border-default last:border-b-0 px-4 py-3 grid grid-cols-12 gap-4 items-center",
        "border-l-2 border-l-transparent transition-all",
        "hover:bg-surface-raised hover:border-l-primary",
        "[&_.row-actions]:opacity-0 [&:hover_.row-actions]:opacity-100",
        local.selected && "bg-surface-raised border-l-primary",
        local.class
      )}
      {...others}
    >
      {local.children}
    </div>
  );
}
```

- [ ] **Step 2: Export from index.ts**

Add to `web/src/components/ui/index.ts`:

```ts
export * from "./data-table";
```

- [ ] **Step 3: Run build to verify types**

Run: `pnpm build`
Expected: Build succeeds.

- [ ] **Step 4: Commit**

```bash
git add web/src/components/ui/data-table.tsx web/src/components/ui/index.ts
git commit -m "web: add DataTable component"
```

---

## Task 7: Create SectionLabel Component

**Files:**
- Create: `web/src/components/ui/section-label.tsx`
- Modify: `web/src/components/ui/index.ts`

- [ ] **Step 1: Create section-label.tsx**

Create `web/src/components/ui/section-label.tsx`:

```tsx
import { cn } from "~/lib/utils";

export interface SectionLabelProps {
  label: string;
  class?: string;
}

export function SectionLabel(props: SectionLabelProps) {
  return (
    <div class={cn("flex items-center gap-3 pt-1 pb-0.5", props.class)}>
      <span class="text-[10px] font-semibold text-text-subtle uppercase tracking-widest shrink-0">
        {props.label}
      </span>
      <div class="flex-1 h-px bg-border-default" />
    </div>
  );
}
```

- [ ] **Step 2: Export from index.ts**

Add to `web/src/components/ui/index.ts`:

```ts
export * from "./section-label";
```

- [ ] **Step 3: Run build to verify types**

Run: `pnpm build`
Expected: Build succeeds.

- [ ] **Step 4: Commit**

```bash
git add web/src/components/ui/section-label.tsx web/src/components/ui/index.ts
git commit -m "web: add SectionLabel component"
```

---

## Task 8: Create Textarea Component

**Files:**
- Create: `web/src/components/ui/textarea.tsx`
- Modify: `web/src/components/ui/index.ts`

- [ ] **Step 1: Create textarea.tsx**

Create `web/src/components/ui/textarea.tsx`:

```tsx
import { type JSX, splitProps } from "solid-js";
import { cn } from "~/lib/utils";

export interface TextareaProps
  extends JSX.TextareaHTMLAttributes<HTMLTextAreaElement> {}

export function Textarea(props: TextareaProps) {
  const [local, others] = splitProps(props, ["class"]);
  return (
    <textarea
      class={cn(
        "flex min-h-[60px] w-full rounded-md border border-border-default bg-transparent px-3 py-2 text-sm text-text-base placeholder:text-text-faint",
        "focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-border-ring",
        "disabled:cursor-not-allowed disabled:opacity-50 resize-none",
        local.class
      )}
      {...others}
    />
  );
}
```

- [ ] **Step 2: Export from index.ts**

Add to `web/src/components/ui/index.ts`:

```ts
export * from "./textarea";
```

- [ ] **Step 3: Run build to verify types**

Run: `pnpm build`
Expected: Build succeeds.

- [ ] **Step 4: Commit**

```bash
git add web/src/components/ui/textarea.tsx web/src/components/ui/index.ts
git commit -m "web: add Textarea component"
```

---

## Task 9: Create ToggleGroup Component

**Files:**
- Create: `web/src/components/ui/toggle-group.tsx`
- Modify: `web/src/components/ui/index.ts`

- [ ] **Step 1: Create toggle-group.tsx**

Create `web/src/components/ui/toggle-group.tsx`:

```tsx
import { type JSX, For, splitProps } from "solid-js";
import { cn } from "~/lib/utils";

export interface ToggleOption {
  value: string;
  label: string;
}

export interface ToggleGroupProps {
  options: ToggleOption[];
  value: string;
  onChange: (value: string) => void;
  class?: string;
}

export function ToggleGroup(props: ToggleGroupProps) {
  return (
    <div
      class={cn(
        "flex h-7 w-fit rounded border border-border-default overflow-hidden text-xs",
        props.class
      )}
    >
      <For each={props.options}>
        {(option, index) => (
          <>
            {index() > 0 && <div class="w-px bg-border-default" />}
            <button
              type="button"
              class={cn(
                "px-4 h-full transition-colors",
                props.value === option.value
                  ? "bg-surface-overlay text-text-base font-medium"
                  : "text-text-subtle hover:text-text-tertiary"
              )}
              onClick={() => props.onChange(option.value)}
            >
              {option.label}
            </button>
          </>
        )}
      </For>
    </div>
  );
}
```

- [ ] **Step 2: Export from index.ts**

Add to `web/src/components/ui/index.ts`:

```ts
export * from "./toggle-group";
```

- [ ] **Step 3: Run build to verify types**

Run: `pnpm build`
Expected: Build succeeds.

- [ ] **Step 4: Commit**

```bash
git add web/src/components/ui/toggle-group.tsx web/src/components/ui/index.ts
git commit -m "web: add ToggleGroup component"
```

---

## Task 10: Create PageHeader Component

**Files:**
- Create: `web/src/components/layout/PageHeader.tsx`

- [ ] **Step 1: Create PageHeader.tsx**

Create `web/src/components/layout/PageHeader.tsx`:

```tsx
import { type Component, For, Show } from "solid-js";
import { A } from "@solidjs/router";
import { cn } from "~/lib/utils";

export interface Breadcrumb {
  label: string;
  href?: string;
}

export interface PageHeaderProps {
  breadcrumbs: Breadcrumb[];
  class?: string;
}

export const PageHeader: Component<PageHeaderProps> = (props) => {
  return (
    <div
      class={cn(
        "sticky top-0 z-20 h-14 border-b border-border-default bg-surface-base flex items-center px-6",
        props.class
      )}
    >
      <div class="flex items-center gap-2 text-sm">
        <For each={props.breadcrumbs}>
          {(crumb, index) => (
            <>
              <Show when={index() > 0}>
                <span class="text-text-faint">/</span>
              </Show>
              <Show
                when={crumb.href}
                fallback={
                  <span class="text-text-tertiary font-medium">
                    {crumb.label}
                  </span>
                }
              >
                <A
                  href={crumb.href!}
                  class="text-text-subtle hover:text-text-tertiary transition-colors"
                >
                  {crumb.label}
                </A>
              </Show>
            </>
          )}
        </For>
      </div>
    </div>
  );
};
```

- [ ] **Step 2: Run build to verify types**

Run: `pnpm build`
Expected: Build succeeds.

- [ ] **Step 3: Commit**

```bash
git add web/src/components/layout/PageHeader.tsx
git commit -m "web: add PageHeader component"
```

---

## Task 11: Create PageContent Component

**Files:**
- Create: `web/src/components/layout/PageContent.tsx`

- [ ] **Step 1: Create PageContent.tsx**

Create `web/src/components/layout/PageContent.tsx`:

```tsx
import { type JSX, splitProps } from "solid-js";
import { cn } from "~/lib/utils";

export interface PageContentProps extends JSX.HTMLAttributes<HTMLDivElement> {
  maxWidth?: "sm" | "md" | "lg" | "xl" | "2xl" | "3xl" | "7xl" | "full";
}

const maxWidthClasses: Record<string, string> = {
  sm: "max-w-sm",
  md: "max-w-md",
  lg: "max-w-lg",
  xl: "max-w-xl",
  "2xl": "max-w-2xl",
  "3xl": "max-w-3xl",
  "7xl": "max-w-7xl",
  full: "max-w-full",
};

export function PageContent(props: PageContentProps) {
  const [local, others] = splitProps(props, ["class", "children", "maxWidth"]);
  const width = () => local.maxWidth ?? "7xl";

  return (
    <div
      class={cn("p-6", maxWidthClasses[width()], local.class)}
      {...others}
    >
      {local.children}
    </div>
  );
}
```

- [ ] **Step 2: Run build to verify types**

Run: `pnpm build`
Expected: Build succeeds.

- [ ] **Step 3: Commit**

```bash
git add web/src/components/layout/PageContent.tsx
git commit -m "web: add PageContent component"
```

---

## Task 12: Create PageTitle Component

**Files:**
- Create: `web/src/components/layout/PageTitle.tsx`

- [ ] **Step 1: Create PageTitle.tsx**

Create `web/src/components/layout/PageTitle.tsx`:

```tsx
import { type JSX, Show } from "solid-js";
import { A } from "@solidjs/router";
import { ChevronLeft } from "lucide-solid";
import { cn } from "~/lib/utils";

export interface PageTitleProps {
  title: string;
  subtitle?: string;
  action?: JSX.Element;
  backLink?: { label: string; href: string };
  class?: string;
}

export function PageTitle(props: PageTitleProps) {
  return (
    <div class={cn("flex items-start justify-between mb-6", props.class)}>
      <div>
        <Show when={props.backLink}>
          <A
            href={props.backLink!.href}
            class="inline-flex items-center gap-1 text-xs text-text-faint hover:text-text-muted transition-colors mb-3 group"
          >
            <ChevronLeft class="w-3.5 h-3.5 transition-transform group-hover:-translate-x-0.5" />
            {props.backLink!.label}
          </A>
        </Show>
        <h1 class="text-2xl font-semibold tracking-tight text-text-base">
          {props.title}
        </h1>
        <Show when={props.subtitle}>
          <p class="text-sm text-text-subtle mt-1">{props.subtitle}</p>
        </Show>
      </div>
      <Show when={props.action}>{props.action}</Show>
    </div>
  );
}
```

- [ ] **Step 2: Run build to verify types**

Run: `pnpm build`
Expected: Build succeeds.

- [ ] **Step 3: Commit**

```bash
git add web/src/components/layout/PageTitle.tsx
git commit -m "web: add PageTitle component"
```

---

## Task 13: Update Existing UI Components to Use Tokens

**Files:**
- Modify: `web/src/components/ui/button.tsx`
- Modify: `web/src/components/ui/input.tsx`
- Modify: `web/src/components/ui/card.tsx`
- Modify: `web/src/components/ui/alert.tsx`
- Modify: `web/src/components/ui/badge.tsx`
- Modify: `web/src/components/ui/status-badge.tsx`

- [ ] **Step 1: Update button.tsx**

Replace variant colors in `web/src/components/ui/button.tsx`:

```tsx
import { type JSX, splitProps } from "solid-js";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "~/lib/utils";

const buttonVariants = cva(
  "inline-flex items-center justify-center whitespace-nowrap rounded-md text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-border-ring disabled:pointer-events-none disabled:opacity-50",
  {
    variants: {
      variant: {
        default: "bg-primary text-white shadow hover:bg-primary-hover",
        destructive: "bg-error text-white shadow-sm hover:bg-error/90",
        outline: "border border-border-default bg-transparent shadow-sm hover:bg-surface-overlay text-text-secondary",
        secondary: "bg-surface-overlay text-text-secondary shadow-sm hover:bg-surface-subtle",
        ghost: "hover:bg-surface-overlay text-text-secondary",
        link: "text-primary underline-offset-4 hover:underline",
      },
      size: {
        default: "h-9 px-4 py-2",
        sm: "h-8 rounded-md px-3 text-xs",
        lg: "h-10 rounded-md px-8",
        icon: "h-9 w-9",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "default",
    },
  }
);

export interface ButtonProps
  extends JSX.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {}

export function Button(props: ButtonProps) {
  const [local, others] = splitProps(props, ["variant", "size", "class"]);
  return (
    <button
      class={cn(buttonVariants({ variant: local.variant, size: local.size }), local.class)}
      {...others}
    />
  );
}

export { buttonVariants };
```

- [ ] **Step 2: Update input.tsx**

Replace in `web/src/components/ui/input.tsx`:

```tsx
import { type JSX, splitProps } from "solid-js";
import { cn } from "~/lib/utils";

export interface InputProps extends JSX.InputHTMLAttributes<HTMLInputElement> {}

export function Input(props: InputProps) {
  const [local, others] = splitProps(props, ["class", "type"]);
  return (
    <input
      type={local.type}
      class={cn(
        "flex h-9 w-full rounded-md border border-border-default bg-transparent px-3 py-1 text-sm text-text-base shadow-sm transition-colors",
        "file:border-0 file:bg-transparent file:text-sm file:font-medium",
        "placeholder:text-text-faint",
        "focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-border-ring",
        "disabled:cursor-not-allowed disabled:opacity-50",
        local.class
      )}
      {...others}
    />
  );
}
```

- [ ] **Step 3: Update card.tsx**

Replace in `web/src/components/ui/card.tsx`:

```tsx
import { type JSX, splitProps } from "solid-js";
import { cn } from "~/lib/utils";

export function Card(props: JSX.HTMLAttributes<HTMLDivElement>) {
  const [local, others] = splitProps(props, ["class"]);
  return (
    <div
      class={cn("rounded-xl border border-border-default bg-surface-raised text-text-secondary shadow", local.class)}
      {...others}
    />
  );
}

export function CardHeader(props: JSX.HTMLAttributes<HTMLDivElement>) {
  const [local, others] = splitProps(props, ["class"]);
  return <div class={cn("flex flex-col space-y-1.5 p-6", local.class)} {...others} />;
}

export function CardTitle(props: JSX.HTMLAttributes<HTMLHeadingElement>) {
  const [local, others] = splitProps(props, ["class"]);
  return <h3 class={cn("font-semibold leading-none tracking-tight text-text-base", local.class)} {...others} />;
}

export function CardDescription(props: JSX.HTMLAttributes<HTMLParagraphElement>) {
  const [local, others] = splitProps(props, ["class"]);
  return <p class={cn("text-sm text-text-subtle", local.class)} {...others} />;
}

export function CardContent(props: JSX.HTMLAttributes<HTMLDivElement>) {
  const [local, others] = splitProps(props, ["class"]);
  return <div class={cn("p-6 pt-0", local.class)} {...others} />;
}

export function CardFooter(props: JSX.HTMLAttributes<HTMLDivElement>) {
  const [local, others] = splitProps(props, ["class"]);
  return <div class={cn("flex items-center p-6 pt-0", local.class)} {...others} />;
}
```

- [ ] **Step 4: Update alert.tsx**

Replace in `web/src/components/ui/alert.tsx`:

```tsx
import { type JSX, splitProps } from "solid-js";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "~/lib/utils";

const alertVariants = cva(
  "relative w-full rounded-lg border px-4 py-3 text-sm [&>svg+div]:translate-y-[-3px] [&>svg]:absolute [&>svg]:left-4 [&>svg]:top-4 [&>svg~*]:pl-7",
  {
    variants: {
      variant: {
        default: "bg-surface-raised border-border-default text-text-secondary",
        destructive: "border-error-muted bg-error-surface text-error [&>svg]:text-error",
      },
    },
    defaultVariants: {
      variant: "default",
    },
  }
);

export interface AlertProps
  extends JSX.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof alertVariants> {}

export function Alert(props: AlertProps) {
  const [local, others] = splitProps(props, ["class", "variant"]);
  return (
    <div
      role="alert"
      class={cn(alertVariants({ variant: local.variant }), local.class)}
      {...others}
    />
  );
}

export function AlertTitle(props: JSX.HTMLAttributes<HTMLHeadingElement>) {
  const [local, others] = splitProps(props, ["class"]);
  return <h5 class={cn("mb-1 font-medium leading-none tracking-tight", local.class)} {...others} />;
}

export function AlertDescription(props: JSX.HTMLAttributes<HTMLParagraphElement>) {
  const [local, others] = splitProps(props, ["class"]);
  return <div class={cn("text-sm [&_p]:leading-relaxed", local.class)} {...others} />;
}
```

- [ ] **Step 5: Update badge.tsx**

Replace in `web/src/components/ui/badge.tsx`:

```tsx
import { type JSX, splitProps } from "solid-js";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "~/lib/utils";

const badgeVariants = cva(
  "inline-flex items-center rounded-md border px-2.5 py-0.5 text-xs font-semibold transition-colors focus:outline-none focus:ring-2 focus:ring-border-ring focus:ring-offset-2",
  {
    variants: {
      variant: {
        default: "border-transparent bg-primary text-white shadow hover:bg-primary-hover",
        secondary: "border-transparent bg-surface-overlay text-text-secondary hover:bg-surface-subtle",
        destructive: "border-transparent bg-error text-white shadow hover:bg-error/80",
        outline: "border-border-default text-text-secondary",
        success: "border-transparent bg-success/20 text-success",
        warning: "border-transparent bg-warning/20 text-warning",
      },
    },
    defaultVariants: {
      variant: "default",
    },
  }
);

export interface BadgeProps
  extends JSX.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof badgeVariants> {}

export function Badge(props: BadgeProps) {
  const [local, others] = splitProps(props, ["class", "variant"]);
  return <div class={cn(badgeVariants({ variant: local.variant }), local.class)} {...others} />;
}
```

- [ ] **Step 6: Update status-badge.tsx**

Replace in `web/src/components/ui/status-badge.tsx`:

```tsx
import { type JSX } from "solid-js";
import type { Trader, RuntimeStatus } from "~/lib/types";

type AnyStatus = Trader["status"] | RuntimeStatus["state"];

export function getStatusColor(status: AnyStatus): string {
  switch (status) {
    case "running":
      return "bg-success";
    case "failed":
    case "error":
    case "not_found":
      return "bg-error";
    case "starting":
    case "pending":
    case "restarting":
      return "bg-warning";
    case "stopped":
    case "configured":
    case "unknown":
    default:
      return "bg-text-subtle";
  }
}

export function getStatusLabel(status: AnyStatus): string {
  const labels: Record<string, string> = {
    configured: "Configured",
    starting: "Starting",
    running: "Running",
    stopped: "Stopped",
    failed: "Failed",
    pending: "Pending",
    restarting: "Restarting",
    error: "Error",
    not_found: "Not found",
    unknown: "Unknown",
  };
  return labels[status] ?? String(status);
}

interface StatusDotProps {
  status: AnyStatus;
  class?: string;
}

export function StatusDot(props: StatusDotProps): JSX.Element {
  const isPulsing = () =>
    props.status === "starting" ||
    props.status === "pending" ||
    props.status === "restarting";

  return (
    <span
      class={`inline-block rounded-full flex-shrink-0 ${getStatusColor(props.status)} ${isPulsing() ? "animate-pulse" : ""} ${props.class ?? ""}`}
      style={{ width: "6px", height: "6px" }}
    />
  );
}

interface StatusIndicatorProps {
  status: AnyStatus;
  class?: string;
}

export function StatusIndicator(props: StatusIndicatorProps): JSX.Element {
  return (
    <span class={`inline-flex items-center gap-2 ${props.class ?? ""}`}>
      <StatusDot status={props.status} />
      <span class="text-sm text-text-muted">{getStatusLabel(props.status)}</span>
    </span>
  );
}
```

- [ ] **Step 7: Run build to verify all updates**

Run: `pnpm build`
Expected: Build succeeds with no TypeScript errors.

- [ ] **Step 8: Commit**

```bash
git add web/src/components/ui/button.tsx web/src/components/ui/input.tsx web/src/components/ui/card.tsx web/src/components/ui/alert.tsx web/src/components/ui/badge.tsx web/src/components/ui/status-badge.tsx
git commit -m "web: update UI components to use color tokens"
```

---

## Task 14: Update Layout Components to Use Tokens

**Files:**
- Modify: `web/src/components/layout/AppShell.tsx`
- Modify: `web/src/components/layout/Sidebar.tsx`

- [ ] **Step 1: Update AppShell.tsx**

Replace in `web/src/components/layout/AppShell.tsx`:

```tsx
import { type Component, type JSX, createSignal } from "solid-js";
import { Sidebar } from "./Sidebar";

interface AppShellProps {
  children: JSX.Element;
}

export const AppShell: Component<AppShellProps> = (props) => {
  const [expanded, setExpanded] = createSignal(true);

  return (
    <div class="min-h-screen bg-surface-base">
      <Sidebar expanded={expanded()} onToggle={() => setExpanded((v) => !v)} />
      <main
        class="transition-all duration-200 min-h-screen flex flex-col"
        style={{ "margin-left": expanded() ? "220px" : "64px" }}
      >
        {props.children}
      </main>
    </div>
  );
};
```

- [ ] **Step 2: Update Sidebar.tsx**

Replace in `web/src/components/layout/Sidebar.tsx`:

```tsx
import { type Component, type JSX, Show, createSignal, For } from "solid-js";
import { A, useLocation, useNavigate } from "@solidjs/router";
import { Bot, Settings, LogOut, ChevronLeft, Menu, X } from "lucide-solid";
import { authStore } from "~/stores/auth";
import { cn } from "~/lib/utils";

interface NavItem {
  href: string;
  label: string;
  icon: Component<{ class?: string }>;
}

const navItems: NavItem[] = [
  { href: "/traders", label: "Traders", icon: Bot },
  { href: "/settings", label: "Settings", icon: Settings },
];

interface SidebarProps {
  expanded: boolean;
  onToggle: () => void;
}

export const Sidebar: Component<SidebarProps> = (props) => {
  const location = useLocation();
  const navigate = useNavigate();
  const [mobileOpen, setMobileOpen] = createSignal(false);

  async function handleLogout() {
    await authStore.logout();
    navigate("/");
  }

  const isActive = (href: string): boolean => {
    return location.pathname === href || location.pathname.startsWith(href + "/");
  };

  const NavContent = (contentProps: { expanded: boolean; mobile?: boolean }): JSX.Element => (
    <div class="flex flex-col h-full bg-surface-raised border-r border-border-default">
      {/* Logo section */}
      <div
        class={cn(
          "flex items-center gap-3 p-4 border-b border-border-default",
          !contentProps.expanded && !contentProps.mobile && "justify-center"
        )}
        style={{ height: "56px" }}
      >
        <div class="w-8 h-8 rounded-md bg-primary flex items-center justify-center flex-shrink-0">
          <span class="text-white font-bold text-sm font-mono">HT</span>
        </div>
        <Show when={contentProps.expanded || contentProps.mobile}>
          <span class="text-text-base font-semibold text-base">HyperTrader</span>
        </Show>
      </div>

      {/* Navigation */}
      <nav class="flex-1 p-3 space-y-1">
        <For each={navItems}>
          {(item) => (
            <A
              href={item.href}
              class={cn(
                "flex items-center gap-3 px-3 py-2 rounded-md text-sm transition-all duration-150",
                isActive(item.href)
                  ? "text-primary bg-surface-overlay"
                  : "text-text-muted hover:text-text-secondary hover:bg-surface-raised",
                !contentProps.expanded && !contentProps.mobile && "justify-center"
              )}
              onClick={() => contentProps.mobile && setMobileOpen(false)}
              title={!contentProps.expanded && !contentProps.mobile ? item.label : undefined}
            >
              <item.icon class="h-4 w-4 flex-shrink-0" />
              <Show when={contentProps.expanded || contentProps.mobile}>
                <span>{item.label}</span>
              </Show>
            </A>
          )}
        </For>
      </nav>

      {/* Collapse toggle (desktop only) */}
      <Show when={!contentProps.mobile}>
        <div class="px-3 pb-3">
          <button
            onClick={props.onToggle}
            class={cn(
              "w-full flex items-center gap-3 px-3 py-2 rounded-md text-sm transition-all duration-150",
              "text-text-muted hover:text-text-secondary hover:bg-surface-raised",
              !contentProps.expanded && "justify-center"
            )}
            title={!contentProps.expanded ? "Expand sidebar" : undefined}
          >
            <ChevronLeft
              class={cn(
                "h-4 w-4 flex-shrink-0 transition-transform duration-150",
                !contentProps.expanded && "rotate-180"
              )}
            />
            <Show when={contentProps.expanded}>
              <span>Collapse</span>
            </Show>
          </button>
        </div>
      </Show>

      {/* User section */}
      <div class="border-t border-border-default p-3">
        <div
          class={cn(
            "flex items-center gap-3 mb-3",
            !contentProps.expanded && !contentProps.mobile && "justify-center"
          )}
        >
          <div class="h-8 w-8 rounded-full bg-primary-muted flex items-center justify-center text-sm font-medium text-primary flex-shrink-0">
            {authStore.user()?.username?.charAt(0).toUpperCase()}
          </div>
          <Show when={contentProps.expanded || contentProps.mobile}>
            <div class="flex-1 min-w-0">
              <p class="text-sm font-medium text-text-base truncate">
                {authStore.user()?.username}
              </p>
              <Show when={authStore.user()?.is_admin}>
                <span class="inline-block px-1.5 py-0.5 text-[10px] font-medium text-primary bg-primary-muted rounded mt-0.5">
                  ADMIN
                </span>
              </Show>
            </div>
          </Show>
        </div>

        {/* Logout button */}
        <button
          onClick={handleLogout}
          class={cn(
            "w-full flex items-center gap-3 px-3 py-2 rounded-md text-sm transition-all duration-150",
            "text-text-muted hover:text-text-secondary hover:bg-surface-raised border border-border-default",
            !contentProps.expanded && !contentProps.mobile && "justify-center px-2"
          )}
          title={!contentProps.expanded && !contentProps.mobile ? "Sign out" : undefined}
        >
          <LogOut class="h-4 w-4 flex-shrink-0" />
          <Show when={contentProps.expanded || contentProps.mobile}>
            <span>Sign Out</span>
          </Show>
        </button>
      </div>

      {/* Version footer */}
      <Show when={contentProps.expanded || contentProps.mobile}>
        <div class="px-3 pb-2">
          <p class="text-xs text-text-faint font-mono">v1.0</p>
        </div>
      </Show>
    </div>
  );

  return (
    <>
      {/* Mobile menu button */}
      <div class="lg:hidden fixed top-4 left-4 z-50">
        <button
          onClick={() => setMobileOpen(!mobileOpen())}
          class="h-10 w-10 rounded-md bg-surface-raised border border-border-default flex items-center justify-center text-text-muted hover:text-text-secondary hover:bg-surface-overlay transition-all duration-150"
        >
          <Show when={mobileOpen()} fallback={<Menu class="h-4 w-4" />}>
            <X class="h-4 w-4" />
          </Show>
        </button>
      </div>

      {/* Mobile overlay */}
      <Show when={mobileOpen()}>
        <div
          class="lg:hidden fixed inset-0 bg-black/50 z-40"
          onClick={() => setMobileOpen(false)}
        />
      </Show>

      {/* Mobile sidebar */}
      <aside
        class={cn(
          "lg:hidden fixed inset-y-0 left-0 z-40 w-64 transform transition-transform duration-200",
          mobileOpen() ? "translate-x-0" : "-translate-x-full"
        )}
      >
        <NavContent expanded={true} mobile={true} />
      </aside>

      {/* Desktop sidebar */}
      <aside
        class="hidden lg:flex lg:flex-col lg:fixed lg:inset-y-0 transition-all duration-200"
        style={{ width: props.expanded ? "220px" : "64px" }}
      >
        <NavContent expanded={props.expanded} />
      </aside>
    </>
  );
};
```

- [ ] **Step 3: Run build to verify**

Run: `pnpm build`
Expected: Build succeeds.

- [ ] **Step 4: Commit**

```bash
git add web/src/components/layout/AppShell.tsx web/src/components/layout/Sidebar.tsx
git commit -m "web: update layout components to use color tokens"
```

---

## Task 15: Refactor routes/index.tsx (Login Page)

**Files:**
- Modify: `web/src/routes/index.tsx`

- [ ] **Step 1: Refactor login page**

Replace `web/src/routes/index.tsx`:

```tsx
import { useNavigate } from "@solidjs/router";
import { LoginForm } from "~/components/auth/LoginForm";
import { authStore } from "~/stores/auth";

export default function LoginPage() {
  const navigate = useNavigate();

  // Redirect to setup if not initialized
  if (!authStore.isInitialized()) {
    navigate("/setup", { replace: true });
    return null;
  }

  // Redirect to traders if already authenticated
  if (authStore.authenticated()) {
    navigate("/traders", { replace: true });
    return null;
  }

  return (
    <div class="min-h-screen bg-surface-base flex items-center justify-center p-4">
      <div class="w-full max-w-md bg-surface-raised border border-border-default rounded-md overflow-hidden">
        {/* Header strip */}
        <div class="px-8 pt-8 pb-6 border-b border-border-default">
          <div class="w-10 h-10 rounded-md bg-primary flex items-center justify-center mb-5">
            <span class="text-white text-sm font-semibold">HT</span>
          </div>
          <h1 class="text-xl font-semibold text-text-base">Welcome back</h1>
          <p class="text-sm text-text-subtle mt-1">Sign in to your account</p>
        </div>

        {/* Form area */}
        <div class="px-8 py-6">
          <LoginForm />
        </div>
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Run dev to verify**

Run: `pnpm dev`
Navigate to: `http://localhost:3000`
Expected: Login page renders correctly with same visual appearance.

- [ ] **Step 3: Commit**

```bash
git add web/src/routes/index.tsx
git commit -m "web: refactor login page to use color tokens"
```

---

## Task 16: Refactor routes/setup/index.tsx

**Files:**
- Modify: `web/src/routes/setup/index.tsx`

- [ ] **Step 1: Refactor setup page**

Replace `web/src/routes/setup/index.tsx`:

```tsx
import { type Component, Show } from "solid-js";
import { Navigate } from "@solidjs/router";
import { BootstrapForm } from "~/components/auth/BootstrapForm";
import { authStore } from "~/stores/auth";

const SetupPage: Component = () => {
  return (
    <Show 
      when={!authStore.isInitialized()} 
      fallback={<Navigate href="/" />}
    >
      <div class="min-h-screen bg-surface-base flex items-center justify-center p-4">
        <div class="w-full max-w-md bg-surface-raised border border-border-default rounded-md overflow-hidden">
          {/* Header strip */}
          <div class="px-8 pt-8 pb-6 border-b border-border-default">
            <div class="w-10 h-10 rounded-md bg-primary flex items-center justify-center mb-5">
              <span class="text-white text-sm font-semibold">HT</span>
            </div>
            <h1 class="text-xl font-semibold text-text-base">Create your account</h1>
            <p class="text-sm text-text-subtle mt-1">Set up the admin account to get started</p>
          </div>

          {/* Form area */}
          <div class="px-8 py-6">
            <BootstrapForm />
          </div>
        </div>
      </div>
    </Show>
  );
};

export default SetupPage;
```

- [ ] **Step 2: Run build to verify**

Run: `pnpm build`
Expected: Build succeeds.

- [ ] **Step 3: Commit**

```bash
git add web/src/routes/setup/index.tsx
git commit -m "web: refactor setup page to use color tokens"
```

---

## Task 17: Refactor routes/setup/ssl.tsx

**Files:**
- Modify: `web/src/routes/setup/ssl.tsx`

- [ ] **Step 1: Refactor SSL setup page**

Replace `web/src/routes/setup/ssl.tsx`:

```tsx
import { type Component, createSignal, Show } from "solid-js";
import { useNavigate } from "@solidjs/router";
import { Lock } from "lucide-solid";
import { Button } from "~/components/ui/button";
import { Input } from "~/components/ui/input";
import { Alert, AlertDescription } from "~/components/ui/alert";
import { api } from "~/lib/api";

const SSLSetupPage: Component = () => {
  const navigate = useNavigate();
  const [mode, setMode] = createSignal<"domain" | "ip">("domain");
  const [domain, setDomain] = createSignal("");
  const [error, setError] = createSignal<string | null>(null);
  const [loading, setLoading] = createSignal(false);

  async function handleSubmit(e: Event) {
    e.preventDefault();
    setError(null);
    setLoading(true);

    try {
      await api.configureSSL(mode(), mode() === "domain" ? domain() : undefined);
      navigate("/");
    } catch (err) {
      setError(err instanceof Error ? err.message : "SSL configuration failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div class="min-h-screen bg-surface-base flex items-center justify-center p-4">
      <div class="w-full max-w-md bg-surface-raised border border-border-default rounded-md overflow-hidden">
        {/* Header strip */}
        <div class="px-8 pt-8 pb-6 border-b border-border-default">
          <div class="w-10 h-10 rounded-md bg-primary flex items-center justify-center mb-5">
            <Lock size={18} stroke-width={1.5} class="text-white" />
          </div>
          <h1 class="text-xl font-semibold text-text-base">SSL Configuration</h1>
          <p class="text-sm text-text-subtle mt-1">Configure SSL for secure connections</p>
        </div>

        {/* Form area */}
        <div class="px-8 py-6">
          <form onSubmit={handleSubmit} class="space-y-6">
            <Show when={error()}>
              <Alert variant="destructive">
                <AlertDescription>{error()}</AlertDescription>
              </Alert>
            </Show>

            <div class="space-y-3">
              <label class="text-sm font-medium text-text-tertiary block">SSL Mode</label>
              <div class="grid grid-cols-2 gap-3">
                <button
                  type="button"
                  onClick={() => setMode("domain")}
                  class={`border rounded-md px-4 py-2.5 text-sm cursor-pointer transition-all ${
                    mode() === "domain"
                      ? "border-primary bg-primary-muted text-text-base"
                      : "border-border-default text-text-muted hover:border-text-faint"
                  }`}
                >
                  Domain (Let's Encrypt)
                </button>
                <button
                  type="button"
                  onClick={() => setMode("ip")}
                  class={`border rounded-md px-4 py-2.5 text-sm cursor-pointer transition-all ${
                    mode() === "ip"
                      ? "border-primary bg-primary-muted text-text-base"
                      : "border-border-default text-text-muted hover:border-text-faint"
                  }`}
                >
                  IP Only (Self-signed)
                </button>
              </div>
            </div>

            <Show when={mode() === "domain"}>
              <div class="space-y-2">
                <label for="domain" class="text-sm font-medium text-text-tertiary block">
                  Domain Name
                </label>
                <Input
                  id="domain"
                  type="text"
                  value={domain()}
                  onInput={(e) => setDomain(e.currentTarget.value)}
                  placeholder="example.com"
                  required
                />
              </div>
            </Show>

            <Button type="submit" class="w-full" disabled={loading()}>
              {loading() ? "Configuring..." : "Configure SSL"}
            </Button>
          </form>
        </div>
      </div>
    </div>
  );
};

export default SSLSetupPage;
```

- [ ] **Step 2: Run build to verify**

Run: `pnpm build`
Expected: Build succeeds.

- [ ] **Step 3: Commit**

```bash
git add web/src/routes/setup/ssl.tsx
git commit -m "web: refactor SSL setup page to use components"
```

---

## Task 18: Refactor routes/settings.tsx

**Files:**
- Modify: `web/src/routes/settings.tsx`

- [ ] **Step 1: Refactor settings page**

Replace `web/src/routes/settings.tsx`:

```tsx
import { type Component, Show } from "solid-js";
import { ProtectedRoute } from "~/components/auth/ProtectedRoute";
import { AppShell } from "~/components/layout/AppShell";
import { PageHeader } from "~/components/layout/PageHeader";
import { PageContent } from "~/components/layout/PageContent";
import { PageTitle } from "~/components/layout/PageTitle";
import { Panel, PanelHeader, PanelBody, PanelRow } from "~/components/ui/panel";
import { Badge } from "~/components/ui/badge";
import { authStore } from "~/stores/auth";

const SettingsPage: Component = () => {
  const user = () => authStore.user();

  return (
    <ProtectedRoute>
      <AppShell>
        <PageHeader breadcrumbs={[{ label: "Settings" }]} />
        <PageContent maxWidth="2xl">
          <PageTitle title="Settings" subtitle="Your account information" />

          <Panel>
            <PanelHeader title="Account" description="Your account details" />
            <PanelBody class="py-0">
              <PanelRow label="Username">
                <span class="font-medium">{user()?.username}</span>
              </PanelRow>
              <PanelRow label="Role">
                <Show
                  when={user()?.is_admin}
                  fallback={<Badge variant="secondary">User</Badge>}
                >
                  <Badge>Admin</Badge>
                </Show>
              </PanelRow>
              <PanelRow label="Account created" border={false}>
                {user()?.created_at
                  ? new Date(user()!.created_at).toLocaleDateString()
                  : "—"}
              </PanelRow>
            </PanelBody>
          </Panel>
        </PageContent>
      </AppShell>
    </ProtectedRoute>
  );
};

export default SettingsPage;
```

- [ ] **Step 2: Run dev to verify**

Run: `pnpm dev`
Navigate to: `http://localhost:3000/settings`
Expected: Settings page renders correctly.

- [ ] **Step 3: Commit**

```bash
git add web/src/routes/settings.tsx
git commit -m "web: refactor settings page to use layout components"
```

---

## Task 19: Refactor routes/traders/new.tsx

**Files:**
- Modify: `web/src/routes/traders/new.tsx`

- [ ] **Step 1: Refactor new trader page**

Replace `web/src/routes/traders/new.tsx`:

```tsx
import { type Component } from "solid-js";
import { useNavigate } from "@solidjs/router";
import { createMutation, useQueryClient } from "@tanstack/solid-query";
import { ProtectedRoute } from "~/components/auth/ProtectedRoute";
import { AppShell } from "~/components/layout/AppShell";
import { PageHeader } from "~/components/layout/PageHeader";
import { PageContent } from "~/components/layout/PageContent";
import { PageTitle } from "~/components/layout/PageTitle";
import { TraderConfigForm } from "~/components/traders/TraderConfigForm";
import { api } from "~/lib/api";
import { traderKeys } from "~/lib/query-keys";
import type { CreateTraderForm } from "~/lib/schemas/trader-config";
import type { CreateTraderRequest } from "~/lib/types";

const NewTraderPage: Component = () => {
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const createTraderMutation = createMutation(() => ({
    mutationFn: (data: CreateTraderForm) => {
      const payload: CreateTraderRequest = {
        wallet_address: data.wallet_address,
        private_key: data.private_key,
        config: data.config,
      };

      // Include name and description if provided
      if (data.name?.trim()) {
        payload.name = data.name.trim();
      }
      if (data.description?.trim()) {
        payload.description = data.description.trim();
      }

      return api.createTrader(payload);
    },
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: traderKeys.all });
      navigate("/traders");
    },
  }));

  const handleSubmit = async (data: CreateTraderForm) => {
    await createTraderMutation.mutateAsync(data);
  };

  return (
    <ProtectedRoute>
      <AppShell>
        <PageHeader
          breadcrumbs={[
            { label: "Traders", href: "/traders" },
            { label: "New trader" },
          ]}
        />
        <PageContent maxWidth="3xl">
          <PageTitle
            backLink={{ label: "Back to traders", href: "/traders" }}
            title="New trader"
            subtitle="Configure and deploy a new trading bot"
          />

          <TraderConfigForm
            onSubmit={handleSubmit}
            isSubmitting={createTraderMutation.isPending}
            submitLabel="Create Trader"
          />
        </PageContent>
      </AppShell>
    </ProtectedRoute>
  );
};

export default NewTraderPage;
```

- [ ] **Step 2: Run dev to verify**

Run: `pnpm dev`
Navigate to: `http://localhost:3000/traders/new`
Expected: New trader page renders correctly.

- [ ] **Step 3: Commit**

```bash
git add web/src/routes/traders/new.tsx
git commit -m "web: refactor new trader page to use layout components"
```

---

## Task 20: Update TraderConfigForm to Use Components

**Files:**
- Modify: `web/src/components/traders/TraderConfigForm.tsx`

- [ ] **Step 1: Update imports and replace inline SectionLabel**

In `web/src/components/traders/TraderConfigForm.tsx`, update imports at top:

```tsx
import { type Component, createSignal, Show } from "solid-js";
import { createForm, setValue, type PartialValues } from "@modular-forms/solid";
import {
  Eye,
  EyeOff,
  ChevronRight,
  Wallet,
  SlidersHorizontal,
  KeyRound,
} from "lucide-solid";
import { Button } from "~/components/ui/button";
import { Input } from "~/components/ui/input";
import { Label } from "~/components/ui/label";
import { Alert, AlertDescription } from "~/components/ui/alert";
import { Select } from "~/components/ui/select";
import { Checkbox } from "~/components/ui/checkbox";
import { TagInput } from "~/components/ui/tag-input";
import { Panel, PanelHeader, PanelBody } from "~/components/ui/panel";
import { SectionLabel } from "~/components/ui/section-label";
import { ToggleGroup } from "~/components/ui/toggle-group";
import { Textarea } from "~/components/ui/textarea";
import { cn } from "~/lib/utils";
import {
  createTraderFormSchema,
  editTraderFormSchema,
  type CreateTraderForm,
} from "~/lib/schemas/trader-config";
```

- [ ] **Step 2: Remove local SectionLabel function**

Delete the local `SectionLabel` function (lines ~35-43) that was defined inline.

- [ ] **Step 3: Update Account Settings panel to use Panel component**

Replace the Account Settings section (starting around line 143) with:

```tsx
      {/* ── Account Settings panel ──────────────────────────────────────── */}
      <Panel>
        <PanelHeader
          icon={Wallet}
          title="Account Settings"
          description="Wallet, copy target & funds"
        />
        <PanelBody class="space-y-4">
          {/* Name + Description */}
          <div class="grid grid-cols-1 gap-4 sm:grid-cols-2">
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
          </div>

          {/* Rest of form fields continue here... */}
```

- [ ] **Step 4: Update Advanced Settings panel**

Replace the Advanced Settings collapsible (starting around line 389) with:

```tsx
      {/* ── Advanced Settings panel (collapsible) ───────────────────────── */}
      <Panel>
        <button
          type="button"
          onClick={() => setAdvancedOpen(!advancedOpen())}
          class="w-full px-5 py-3.5 flex items-center gap-2.5 text-left hover:bg-surface-overlay transition-colors"
        >
          <SlidersHorizontal class="w-4 h-4 text-text-subtle shrink-0" />
          <span class="text-sm font-medium text-text-tertiary">Advanced Settings</span>
          <span class="ml-auto text-xs text-text-faint hidden sm:block">
            Strategy, risk, slippage &amp; buckets
          </span>
          <ChevronRight
            class={cn(
              "w-4 h-4 text-text-faint transition-transform duration-200 ml-2",
              advancedOpen() && "rotate-90"
            )}
          />
        </button>

        <Show when={advancedOpen()}>
          <PanelBody class="border-t border-border-default space-y-5">
            {/* Strategy section */}
            <SectionLabel label="Strategy" />
            {/* ... rest of advanced settings ... */}
          </PanelBody>
        </Show>
      </Panel>
```

- [ ] **Step 5: Update ToggleGroup usage for bucket mode**

Replace the bucket mode toggle buttons with:

```tsx
              <ToggleGroup
                options={[
                  { value: "manual", label: "Manual" },
                  { value: "auto", label: "Auto" },
                ]}
                value={bucketMode()}
                onChange={(v) => setBucketMode(v as "manual" | "auto")}
              />
```

- [ ] **Step 6: Update all remaining hardcoded colors to tokens**

Replace throughout the file:
- `text-zinc-*` → `text-text-*` (appropriate level)
- `bg-[#111214]` → `bg-surface-raised`
- `bg-[#08090a]` → `bg-surface-base`
- `border-[#222426]` → `border-border-default`
- `text-destructive` → `text-error`

- [ ] **Step 7: Run build to verify**

Run: `pnpm build`
Expected: Build succeeds.

- [ ] **Step 8: Commit**

```bash
git add web/src/components/traders/TraderConfigForm.tsx
git commit -m "web: refactor TraderConfigForm to use UI components"
```

---

## Task 21: Update app.tsx to Use Tokens

**Files:**
- Modify: `web/src/app.tsx`

- [ ] **Step 1: Update app.tsx**

Replace `web/src/app.tsx`:

```tsx
import { type ParentProps, Suspense, onMount, createSignal, Show, ErrorBoundary } from "solid-js";
import { Router } from "@solidjs/router";
import { FileRoutes } from "@solidjs/start/router";
import { QueryClient, QueryClientProvider } from "@tanstack/solid-query";
import { MetaProvider } from "@solidjs/meta";
import { authStore } from "~/stores/auth";
import "./styles.css";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 1000 * 60,
      retry: 1,
    },
  },
});

function LoadingScreen() {
  return (
    <div class="min-h-screen flex items-center justify-center bg-surface-base">
      <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
    </div>
  );
}

function AuthGuard(props: ParentProps) {
  const [initialized, setInitialized] = createSignal(false);

  onMount(async () => {
    await authStore.checkSetup();
    await authStore.checkAuth();
    setInitialized(true);
  });

  return (
    <Show when={initialized()} fallback={<LoadingScreen />}>
      {props.children}
    </Show>
  );
}

function ErrorFallback(props: { error: Error }) {
  return (
    <div class="min-h-screen flex items-center justify-center bg-surface-base p-4">
      <div class="max-w-md text-center">
        <h1 class="text-2xl font-bold text-error mb-4">Something went wrong</h1>
        <pre class="text-sm text-text-subtle bg-surface-raised p-4 rounded overflow-auto">
          {props.error.message}
        </pre>
      </div>
    </div>
  );
}

export default function App() {
  return (
    <ErrorBoundary fallback={(err) => <ErrorFallback error={err} />}>
      <MetaProvider>
        <QueryClientProvider client={queryClient}>
          <AuthGuard>
            <Router root={(props) => <Suspense fallback={<LoadingScreen />}>{props.children}</Suspense>}>
              <FileRoutes />
            </Router>
          </AuthGuard>
        </QueryClientProvider>
      </MetaProvider>
    </ErrorBoundary>
  );
}
```

- [ ] **Step 2: Run build to verify**

Run: `pnpm build`
Expected: Build succeeds.

- [ ] **Step 3: Commit**

```bash
git add web/src/app.tsx
git commit -m "web: update app.tsx to use color tokens"
```

---

## Task 22: Refactor routes/traders/[id].tsx (Trader Detail)

**Files:**
- Modify: `web/src/routes/traders/[id].tsx`

- [ ] **Step 1: Update imports**

Replace imports at top of `web/src/routes/traders/[id].tsx`:

```tsx
import { type Component, Show, Suspense, createSignal, createEffect } from "solid-js";
import { useParams, useNavigate, A } from "@solidjs/router";
import { createQuery, createMutation, useQueryClient } from "@tanstack/solid-query";
import { Trash2, RefreshCw, Play, Square, Loader2, AlertCircle } from "lucide-solid";
import { ProtectedRoute } from "~/components/auth/ProtectedRoute";
import { AppShell } from "~/components/layout/AppShell";
import { PageHeader } from "~/components/layout/PageHeader";
import { PageContent } from "~/components/layout/PageContent";
import { Button } from "~/components/ui/button";
import { Input } from "~/components/ui/input";
import { Textarea } from "~/components/ui/textarea";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "~/components/ui/tabs";
import { Toast } from "~/components/ui/toast";
import { Panel, PanelHeader, PanelBody, PanelRow } from "~/components/ui/panel";
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
import { StatusDot, StatusIndicator } from "~/components/ui/status-badge";
import { LogViewer } from "~/components/traders/LogViewer";
import { TraderConfigForm } from "~/components/traders/TraderConfigForm";
import { api } from "~/lib/api";
import { traderKeys, imageKeys } from "~/lib/query-keys";
import type { Trader, RuntimeStatus } from "~/lib/types";
import type { CreateTraderForm, TraderConfig } from "~/lib/schemas/trader-config";
```

- [ ] **Step 2: Update LoadingSkeleton**

Replace `LoadingSkeleton` function:

```tsx
function LoadingSkeleton() {
  return (
    <div class="p-6 space-y-6">
      <div class="flex items-start justify-between">
        <div class="space-y-2">
          <div class="h-8 w-48 bg-surface-raised rounded-md animate-pulse" />
          <div class="h-4 w-64 bg-surface-raised rounded-md animate-pulse" />
          <div class="h-3 w-96 bg-surface-raised rounded-md animate-pulse mt-3" />
        </div>
        <div class="flex gap-2">
          <div class="h-9 w-20 bg-surface-raised rounded-md animate-pulse" />
          <div class="h-9 w-20 bg-surface-raised rounded-md animate-pulse" />
        </div>
      </div>
      <div class="border-b border-border-default pb-0">
        <div class="h-10 w-64 bg-surface-raised rounded-md animate-pulse" />
      </div>
      <div class="grid gap-6 md:grid-cols-2">
        <div class="bg-surface-raised border border-border-default rounded-md p-5 h-64" />
        <div class="bg-surface-raised border border-border-default rounded-md p-5 h-64" />
      </div>
    </div>
  );
}
```

- [ ] **Step 3: Update page header section**

Replace the breadcrumb header with:

```tsx
                  <PageHeader
                    breadcrumbs={[
                      { label: "Traders", href: "/traders" },
                      { label: trader().display_name },
                    ]}
                  />
```

- [ ] **Step 4: Update main content header**

Replace the page header section (title, status, actions) with:

```tsx
                    <div class="flex items-start justify-between mb-6">
                      <div class="space-y-3">
                        <div class="flex items-center gap-2.5">
                          <StatusDot status={currentStatus()} />
                          <h1 class="text-2xl font-semibold text-text-base">{trader().display_name}</h1>
                        </div>
                        <Show when={trader().description}>
                          <p class="text-sm text-text-subtle mt-0.5">{trader().description}</p>
                        </Show>
                        <div class="flex items-center gap-4 text-xs text-text-subtle">
                          <span class="font-mono">
                            {trader().wallet_address.slice(0, 6)}...{trader().wallet_address.slice(-4)}
                          </span>
                          <span>v{trader().image_tag}</span>
                          <span>Created {relDate(trader().created_at)}</span>
                        </div>
                      </div>

                      {/* Action buttons */}
                      <div class="flex items-center gap-2">
                        {/* ... buttons stay similar but use Button component variants ... */}
                      </div>
                    </div>
```

- [ ] **Step 5: Update action buttons to use Button component**

Replace inline button styles with Button component:

```tsx
                        <Show when={["configured", "stopped", "failed"].includes(trader().status)}>
                          <Button
                            onClick={() => startMutation.mutate()}
                            disabled={startMutation.isPending}
                          >
                            <Show
                              when={startMutation.isPending}
                              fallback={<Play class="h-4 w-4 mr-2" stroke-width={1.5} />}
                            >
                              <Loader2 class="h-4 w-4 mr-2 animate-spin" stroke-width={1.5} />
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
                              fallback={<Square class="h-4 w-4 mr-2" stroke-width={1.5} />}
                            >
                              <Loader2 class="h-4 w-4 mr-2 animate-spin" stroke-width={1.5} />
                            </Show>
                            Stop
                          </Button>
                        </Show>
```

- [ ] **Step 6: Update tabs styling**

Replace tabs with token-based styling:

```tsx
                    <Tabs defaultValue="overview" class="space-y-6">
                      <TabsList class="inline-flex gap-1 border-b border-border-default w-full">
                        <TabsTrigger 
                          value="overview"
                          class="px-4 py-2 text-sm font-medium text-text-muted hover:text-text-secondary border-b-2 border-transparent transition-all data-[selected]:text-text-base data-[selected]:border-primary"
                        >
                          Overview
                        </TabsTrigger>
                        <TabsTrigger 
                          value="logs"
                          class="px-4 py-2 text-sm font-medium text-text-muted hover:text-text-secondary border-b-2 border-transparent transition-all data-[selected]:text-text-base data-[selected]:border-primary"
                        >
                          Logs
                        </TabsTrigger>
                        <TabsTrigger 
                          value="configuration"
                          class="px-4 py-2 text-sm font-medium text-text-muted hover:text-text-secondary border-b-2 border-transparent transition-all data-[selected]:text-text-base data-[selected]:border-primary"
                        >
                          Configuration
                        </TabsTrigger>
                      </TabsList>
```

- [ ] **Step 7: Update Overview tab cards to use Panel**

Replace status card with:

```tsx
                      <TabsContent value="overview" class="space-y-0">
                        <div class="grid gap-6 md:grid-cols-2">
                          {/* Status Card */}
                          <Panel>
                            <PanelHeader title="Status" />
                            <PanelBody class="py-0">
                              <PanelRow label="Status">
                                <StatusIndicator status={currentStatus()} />
                              </PanelRow>
                              <Show when={trader().status === "running" && statusQuery.data?.runtime_status?.started_at}>
                                <PanelRow label="Uptime">
                                  {formatUptime(statusQuery.data!.runtime_status.started_at!)}
                                </PanelRow>
                              </Show>
                              <PanelRow label="Image version" border={!statusQuery.data?.runtime_status?.error && !trader().last_error}>
                                <div class="flex items-center gap-2">
                                  <span class="font-mono">{trader().image_tag}</span>
                                  <Show when={needsImageUpdate()}>
                                    <span class="text-xs text-warning">
                                      → {imageQuery.data?.latest_remote} available
                                    </span>
                                  </Show>
                                </div>
                              </PanelRow>
                              <Show when={statusQuery.data?.runtime_status?.error || trader().last_error}>
                                <div class="bg-error-surface rounded p-3 my-3">
                                  <div class="flex items-center gap-2 text-error text-sm mb-1">
                                    <AlertCircle class="h-4 w-4" stroke-width={1.5} />
                                    <span class="font-medium">Error</span>
                                  </div>
                                  <p class="text-sm text-error break-all">
                                    {statusQuery.data?.runtime_status?.error || trader().last_error}
                                  </p>
                                </div>
                              </Show>
                            </PanelBody>
                          </Panel>

                          {/* Trader Info Card */}
                          <Panel>
                            <PanelHeader title="Trader info" />
                            <PanelBody class="space-y-4">
                              <div class="space-y-2">
                                <label class="text-sm font-medium text-text-muted">Name</label>
                                <Input
                                  type="text"
                                  value={editName()}
                                  onInput={(e) => handleNameChange(e.currentTarget.value)}
                                  placeholder="Enter a name for this trader"
                                  maxLength={50}
                                />
                              </div>
                              <div class="space-y-2">
                                <label class="text-sm font-medium text-text-muted">Description</label>
                                <Textarea
                                  value={editDescription()}
                                  onInput={(e) => handleDescriptionChange(e.currentTarget.value)}
                                  placeholder="Optional notes about this trader"
                                  class="min-h-[60px]"
                                  maxLength={255}
                                  rows={2}
                                />
                              </div>
                              <Show when={infoError()}>
                                <p class="text-sm text-error">{infoError()}</p>
                              </Show>
                              <Show when={infoChanged()}>
                                <Button
                                  onClick={handleInfoSave}
                                  disabled={updateInfoMutation.isPending}
                                >
                                  {updateInfoMutation.isPending ? "Saving..." : "Save"}
                                </Button>
                              </Show>
                              <div class="border-t border-border-default pt-4 mt-4 space-y-2">
                                <div class="flex items-center justify-between">
                                  <span class="text-sm text-text-subtle">Created</span>
                                  <span class="text-sm text-text-muted">{relDate(trader().created_at)}</span>
                                </div>
                                <div class="flex items-center justify-between">
                                  <span class="text-sm text-text-subtle">Last updated</span>
                                  <span class="text-sm text-text-muted">{relDate(trader().updated_at)}</span>
                                </div>
                              </div>
                            </PanelBody>
                          </Panel>
                        </div>
                      </TabsContent>
```

- [ ] **Step 8: Update Logs tab**

```tsx
                      <TabsContent value="logs">
                        <Panel>
                          <LogViewer traderId={params.id} />
                        </Panel>
                      </TabsContent>
```

- [ ] **Step 9: Update Configuration tab**

```tsx
                      <TabsContent value="configuration">
                        <Show
                          when={trader().latest_config}
                          fallback={
                            <Panel class="p-8 text-center">
                              <p class="text-sm text-text-subtle">No configuration available for this trader.</p>
                            </Panel>
                          }
                        >
                          {(config) => (
                            <Panel>
                              <PanelBody>
                                <TraderConfigForm
                                  initialValues={{
                                    wallet_address: trader().wallet_address,
                                    private_key: "",
                                    config: normalizeConfig(config() as TraderConfig),
                                  }}
                                  onSubmit={async (data: CreateTraderForm) => {
                                    await updateMutation.mutateAsync(data.config);
                                  }}
                                  isEditing={true}
                                  isSubmitting={updateMutation.isPending}
                                  submitLabel="Save Configuration"
                                />
                              </PanelBody>
                            </Panel>
                          )}
                        </Show>
                      </TabsContent>
```

- [ ] **Step 10: Run build to verify**

Run: `pnpm build`
Expected: Build succeeds.

- [ ] **Step 11: Commit**

```bash
git add web/src/routes/traders/\[id\].tsx
git commit -m "web: refactor trader detail page to use components"
```

---

## Task 23: Refactor routes/traders/index.tsx (Trader List)

**Files:**
- Modify: `web/src/routes/traders/index.tsx`

- [ ] **Step 1: Update imports**

Replace imports at top of `web/src/routes/traders/index.tsx`:

```tsx
import { type Component, Show, For, Suspense, createSignal } from "solid-js";
import { createQuery, createMutation, useQueryClient } from "@tanstack/solid-query";
import { A } from "@solidjs/router";
import { Play, Square, Trash2, Loader2, AlertCircle, RefreshCw, Inbox } from "lucide-solid";
import { ProtectedRoute } from "~/components/auth/ProtectedRoute";
import { AppShell } from "~/components/layout/AppShell";
import { PageHeader } from "~/components/layout/PageHeader";
import { PageContent } from "~/components/layout/PageContent";
import { PageTitle } from "~/components/layout/PageTitle";
import { Button } from "~/components/ui/button";
import { IconButton } from "~/components/ui/icon-button";
import { KpiCard, KpiStrip } from "~/components/ui/kpi-card";
import { EmptyState } from "~/components/ui/empty-state";
import { DataTable, DataTableRow } from "~/components/ui/data-table";
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
import { api } from "~/lib/api";
import { traderKeys, imageKeys } from "~/lib/query-keys";
import type { Trader } from "~/lib/types";
import { ImageVersionBanner } from "~/components/traders/ImageVersionBanner";
import { StatusDot, StatusIndicator } from "~/components/ui/status-badge";
```

- [ ] **Step 2: Update TraderRow component**

Replace `TraderRow` component:

```tsx
function TraderRow(props: { trader: Trader }) {
  const queryClient = useQueryClient();
  const [deleteOpen, setDeleteOpen] = createSignal(false);

  const imageQuery = createQuery(() => ({
    queryKey: imageKeys.versions(),
    queryFn: () => api.getImageVersions(),
  }));

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

  const updateImageMutation = createMutation(() => ({
    mutationFn: (newTag: string) => api.updateTraderImage(props.trader.id, newTag),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: traderKeys.lists() });
      queryClient.invalidateQueries({ queryKey: imageKeys.versions() });
    },
  }));

  const needsUpdate = () => {
    const remote = imageQuery.data?.latest_remote;
    if (!remote) return false;
    const current = props.trader.image_tag;
    if (!current) return false;
    const [rMaj, rMin, rPat] = remote.split(".").map(Number);
    const [cMaj, cMin, cPat] = current.split(".").map(Number);
    if (rMaj !== cMaj) return rMaj > cMaj;
    if (rMin !== cMin) return rMin > cMin;
    return rPat > cPat;
  };

  const canStart = () =>
    ["configured", "stopped", "failed"].includes(props.trader.status);
  const canStop = () =>
    ["running", "starting"].includes(props.trader.status);
  const isLoading = () =>
    startMutation.isPending || stopMutation.isPending || deleteMutation.isPending || updateImageMutation.isPending;

  return (
    <>
      <DataTableRow>
        {/* Name column */}
        <div class="col-span-3 flex items-center gap-2.5">
          <StatusDot status={props.trader.status} />
          <div class="min-w-0">
            <A
              href={`/traders/${props.trader.id}`}
              class="text-sm font-medium text-text-base hover:text-primary transition-colors"
            >
              {props.trader.display_name}
            </A>
            <Show when={props.trader.description}>
              <div class="text-xs text-text-subtle truncate">
                {props.trader.description}
              </div>
            </Show>
          </div>
        </div>

        {/* Wallet column */}
        <div class="col-span-3 font-mono text-sm text-text-subtle">
          {props.trader.wallet_address.slice(0, 6)}…{props.trader.wallet_address.slice(-4)}
        </div>

        {/* Status column */}
        <div class="col-span-2">
          <StatusIndicator status={props.trader.status} />
        </div>

        {/* Version column */}
        <div class="col-span-2 font-mono text-sm text-text-subtle">
          {props.trader.image_tag}
        </div>

        {/* Last activity + actions column */}
        <div class="col-span-2 flex items-center justify-between">
          <span class="text-sm text-text-subtle">{relTime(props.trader.created_at)}</span>
          
          <div class="row-actions flex items-center gap-1">
            <Show when={needsUpdate()}>
              <IconButton
                icon={RefreshCw}
                tooltip={`Update to ${imageQuery.data?.latest_remote}`}
                onClick={() => updateImageMutation.mutate(imageQuery.data!.latest_remote!)}
                disabled={isLoading()}
                loading={updateImageMutation.isPending}
              />
            </Show>

            <Show when={canStart()}>
              <IconButton
                icon={Play}
                tooltip={props.trader.status === "failed" ? "Retry" : "Start"}
                onClick={() => startMutation.mutate()}
                disabled={isLoading()}
                loading={startMutation.isPending}
              />
            </Show>

            <Show when={canStop()}>
              <IconButton
                icon={Square}
                tooltip="Stop"
                onClick={() => stopMutation.mutate()}
                disabled={isLoading()}
                loading={stopMutation.isPending}
              />
            </Show>

            <AlertDialog open={deleteOpen()} onOpenChange={setDeleteOpen}>
              <AlertDialogTrigger
                as={(triggerProps: any) => (
                  <IconButton
                    {...triggerProps}
                    icon={Trash2}
                    tooltip="Delete"
                    variant="danger"
                    disabled={isLoading()}
                  />
                )}
              />
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
        </div>
      </DataTableRow>

      {/* Error row */}
      <Show when={props.trader.status === "failed" && props.trader.last_error}>
        <div class="col-span-12 bg-error-surface px-4 py-2 border-b border-border-default flex items-start gap-2">
          <AlertCircle class="h-4 w-4 text-error flex-shrink-0 mt-0.5" stroke-width={1.5} />
          <span class="text-sm text-error">{props.trader.last_error}</span>
        </div>
      </Show>
    </>
  );
}
```

- [ ] **Step 3: Update LoadingSkeleton**

Replace `LoadingSkeleton`:

```tsx
function LoadingSkeleton() {
  return (
    <div class="bg-surface-raised border border-border-default rounded-md overflow-hidden">
      {/* Column headers */}
      <div class="border-b border-border-default px-4 py-3 grid grid-cols-12 gap-4">
        <div class="col-span-3 text-xs font-medium text-text-subtle uppercase tracking-wide">Name</div>
        <div class="col-span-3 text-xs font-medium text-text-subtle uppercase tracking-wide">Wallet</div>
        <div class="col-span-2 text-xs font-medium text-text-subtle uppercase tracking-wide">Status</div>
        <div class="col-span-2 text-xs font-medium text-text-subtle uppercase tracking-wide">Version</div>
        <div class="col-span-2 text-xs font-medium text-text-subtle uppercase tracking-wide">Last activity</div>
      </div>
      
      {/* Skeleton rows */}
      <For each={[1, 2, 3, 4, 5]}>
        {() => (
          <div class="border-b border-border-default last:border-b-0 px-4 py-3 grid grid-cols-12 gap-4 items-center">
            <div class="col-span-3">
              <div class="h-4 w-32 rounded bg-surface-overlay animate-pulse" />
            </div>
            <div class="col-span-3">
              <div class="h-4 w-24 rounded bg-surface-overlay animate-pulse" />
            </div>
            <div class="col-span-2">
              <div class="h-4 w-16 rounded bg-surface-overlay animate-pulse" />
            </div>
            <div class="col-span-2">
              <div class="h-4 w-20 rounded bg-surface-overlay animate-pulse" />
            </div>
            <div class="col-span-2">
              <div class="h-4 w-16 rounded bg-surface-overlay animate-pulse" />
            </div>
          </div>
        )}
      </For>
    </div>
  );
}
```

- [ ] **Step 4: Update main TradersPage component**

Replace `TradersPage` component:

```tsx
const TradersPage: Component = () => {
  const tradersQuery = createQuery(() => ({
    queryKey: traderKeys.lists(),
    queryFn: () => api.listTraders(),
    refetchInterval: (query) => {
      const data = query.state.data;
      if (Array.isArray(data) && data.some((t) => t.status === "starting")) {
        return 2000;
      }
      return false;
    },
  }));

  const totalCount = () => tradersQuery.data?.length ?? 0;
  const runningCount = () => tradersQuery.data?.filter(t => t.status === "running").length ?? 0;
  const failedCount = () => tradersQuery.data?.filter(t => t.status === "failed").length ?? 0;

  const columns = [
    { key: "name", label: "Name", span: 3 },
    { key: "wallet", label: "Wallet", span: 3 },
    { key: "status", label: "Status", span: 2 },
    { key: "version", label: "Version", span: 2 },
    { key: "activity", label: "Last activity", span: 2 },
  ];

  return (
    <ProtectedRoute>
      <AppShell>
        <PageHeader breadcrumbs={[{ label: "Traders" }]} />
        <PageContent>
          <PageTitle
            title="Traders"
            subtitle="Manage and monitor your trading bots"
            action={
              <Button as={A} href="/traders/new">
                <Play class="h-4 w-4 mr-2" stroke-width={1.5} />
                New trader
              </Button>
            }
          />

          <KpiStrip class="mb-6">
            <KpiCard label="Total" value={totalCount()} />
            <KpiCard label="Running" value={runningCount()} variant="success" />
            <KpiCard label="Failed" value={failedCount()} variant="error" />
          </KpiStrip>

          <Suspense fallback={<LoadingSkeleton />}>
            <Show
              when={tradersQuery.data && tradersQuery.data.length > 0}
              fallback={
                <EmptyState
                  icon={Inbox}
                  title="No traders yet"
                  description="Get started by creating your first trading bot"
                  action={
                    <Button as={A} href="/traders/new">
                      <Play class="h-4 w-4 mr-2" stroke-width={1.5} />
                      New trader
                    </Button>
                  }
                />
              }
            >
              <div class="space-y-4">
                <ImageVersionBanner traders={tradersQuery.data ?? []} />
                <DataTable columns={columns}>
                  <For each={tradersQuery.data}>
                    {(trader) => <TraderRow trader={trader} />}
                  </For>
                </DataTable>
              </div>
            </Show>
          </Suspense>
        </PageContent>
      </AppShell>
    </ProtectedRoute>
  );
};

export default TradersPage;
```

- [ ] **Step 5: Remove inline style block**

Delete the `<style>` block that was used for hover effects (the DataTableRow component handles this now).

- [ ] **Step 6: Run dev to verify**

Run: `pnpm dev`
Navigate to: `http://localhost:3000/traders`
Expected: Traders list page renders correctly with same visual appearance.

- [ ] **Step 7: Commit**

```bash
git add web/src/routes/traders/index.tsx
git commit -m "web: refactor traders list page to use components"
```

---

## Task 24: Update ImageVersionBanner and LogViewer

**Files:**
- Modify: `web/src/components/traders/ImageVersionBanner.tsx`
- Modify: `web/src/components/traders/LogViewer.tsx`

- [ ] **Step 1: Update ImageVersionBanner.tsx**

Replace `web/src/components/traders/ImageVersionBanner.tsx`:

```tsx
import { type Component, Show, createSignal } from "solid-js";
import { createQuery, createMutation, useQueryClient } from "@tanstack/solid-query";
import { RefreshCw } from "lucide-solid";
import { Button } from "~/components/ui/button";
import { api } from "~/lib/api";
import { traderKeys, imageKeys } from "~/lib/query-keys";
import type { Trader } from "~/lib/types";

interface Props {
  traders: Trader[];
}

export const ImageVersionBanner: Component<Props> = (props) => {
  const queryClient = useQueryClient();
  const [updateError, setUpdateError] = createSignal<string | null>(null);

  const imageQuery = createQuery(() => ({
    queryKey: imageKeys.versions(),
    queryFn: () => api.getImageVersions(),
  }));

  const semverGt = (a: string, b: string): boolean => {
    const [aMaj, aMin, aPat] = a.split(".").map(Number);
    const [bMaj, bMin, bPat] = b.split(".").map(Number);
    if (aMaj !== bMaj) return aMaj > bMaj;
    if (aMin !== bMin) return aMin > bMin;
    return aPat > bPat;
  };

  const updateNeeded = () => {
    const data = imageQuery.data;
    if (!data?.latest_remote || !data?.latest_local) return false;
    return semverGt(data.latest_remote, data.latest_local);
  };

  const updateAllMutation = createMutation(() => ({
    mutationFn: async () => {
      const data = imageQuery.data;
      if (!data?.latest_remote) return;
      for (const trader of props.traders) {
        await api.updateTraderImage(trader.id, data.latest_remote);
      }
    },
    onSuccess: () => {
      setUpdateError(null);
      queryClient.invalidateQueries({ queryKey: traderKeys.lists() });
      queryClient.invalidateQueries({ queryKey: imageKeys.versions() });
    },
    onError: (error: Error) => {
      setUpdateError(error.message || "Failed to update some traders");
    },
  }));

  return (
    <Show when={updateNeeded()}>
      <div class="flex items-center justify-between bg-surface-raised border border-warning-muted rounded-md px-4 py-3">
        <div class="flex items-center gap-3">
          <span class="h-1.5 w-1.5 rounded-full bg-warning animate-pulse" />
          <span class="text-sm text-text-tertiary">
            Update available{" "}
            <span class="font-mono text-warning">
              {imageQuery.data?.latest_local} → {imageQuery.data?.latest_remote}
            </span>
          </span>
          <Show when={updateError()}>
            <span class="text-xs text-error">{updateError()}</span>
          </Show>
        </div>
        <Button
          variant="outline"
          size="sm"
          onClick={() => updateAllMutation.mutate()}
          disabled={updateAllMutation.isPending || props.traders.length === 0}
          class="border-warning-muted text-warning hover:bg-warning-surface"
        >
          <RefreshCw class={`h-4 w-4 mr-1.5 ${updateAllMutation.isPending ? "animate-spin" : ""}`} stroke-width={1.5} />
          Update all
        </Button>
      </div>
    </Show>
  );
};
```

- [ ] **Step 2: Update LogViewer.tsx**

Replace `web/src/components/traders/LogViewer.tsx`:

```tsx
import { type Component, For, createSignal, Show } from "solid-js";
import { createQuery } from "@tanstack/solid-query";
import { RefreshCw } from "lucide-solid";
import { Button } from "~/components/ui/button";
import { api } from "~/lib/api";
import { traderKeys } from "~/lib/query-keys";

interface LogViewerProps {
  traderId: string;
}

export const LogViewer: Component<LogViewerProps> = (props) => {
  const [lines] = createSignal(100);

  const logsQuery = createQuery(() => ({
    queryKey: traderKeys.logs(props.traderId),
    queryFn: () => api.getTraderLogs(props.traderId, lines()),
    refetchInterval: 5000,
  }));

  return (
    <div>
      <div class="flex items-center justify-between px-5 py-3.5 border-b border-border-default">
        <h3 class="text-sm font-medium text-text-secondary">Logs</h3>
        <Button
          variant="outline"
          size="sm"
          onClick={() => logsQuery.refetch()}
          disabled={logsQuery.isFetching}
        >
          <RefreshCw class={`h-4 w-4 mr-2 ${logsQuery.isFetching ? "animate-spin" : ""}`} />
          Refresh
        </Button>
      </div>
      <div class="p-4">
        <Show
          when={!logsQuery.isLoading}
          fallback={
            <div class="space-y-2">
              <For each={[1, 2, 3, 4, 5]}>
                {() => <div class="h-4 w-full bg-surface-overlay rounded animate-pulse" />}
              </For>
            </div>
          }
        >
          <div class="bg-surface-base rounded-md p-4 max-h-96 overflow-auto">
            <pre class="text-xs font-mono whitespace-pre-wrap text-text-muted">
              <Show
                when={logsQuery.data?.length}
                fallback={<span class="text-text-subtle">No logs available</span>}
              >
                <For each={logsQuery.data}>
                  {(line) => <div>{line}</div>}
                </For>
              </Show>
            </pre>
          </div>
        </Show>
      </div>
    </div>
  );
};
```

- [ ] **Step 3: Run build to verify**

Run: `pnpm build`
Expected: Build succeeds.

- [ ] **Step 4: Commit**

```bash
git add web/src/components/traders/ImageVersionBanner.tsx web/src/components/traders/LogViewer.tsx
git commit -m "web: update trader components to use color tokens"
```

---

## Task 25: Final Verification

- [ ] **Step 1: Run full build**

Run: `pnpm build`
Expected: Build succeeds with no errors.

- [ ] **Step 2: Run dev server and test all pages**

Run: `pnpm dev`
Test each page manually:
- `http://localhost:3000` (login)
- `http://localhost:3000/setup` (if not initialized)
- `http://localhost:3000/traders` (list)
- `http://localhost:3000/traders/new` (create)
- `http://localhost:3000/traders/[id]` (detail)
- `http://localhost:3000/settings`

Expected: All pages render correctly with consistent styling.

- [ ] **Step 3: Run e2e tests**

Run: `pnpm test:e2e`
Expected: All tests pass.

- [ ] **Step 4: Final commit**

```bash
git add -A
git commit -m "web: complete component refactor with color token system"
```

---

## Summary

This plan creates:
- **1 new CSS file section** with color tokens
- **8 new UI components** (Panel, KpiCard, EmptyState, IconButton, DataTable, SectionLabel, Textarea, ToggleGroup)
- **3 new layout components** (PageHeader, PageContent, PageTitle)
- **Updates 6 existing UI components** to use tokens
- **Refactors 7 route files** to use semantic components
- **Updates 5 other components** (AppShell, Sidebar, TraderConfigForm, ImageVersionBanner, LogViewer)

Total estimated tasks: 25
Estimated time: 3-4 hours
