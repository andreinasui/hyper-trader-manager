# Web Component Refactor Design

**Date:** 2026-04-25  
**Status:** Approved  
**Approach:** Top-Down Route Refactor (B)

## Problem Statement

The web codebase has Tailwind CSS scattered throughout route files, making code unreadable and hard to maintain. Hardcoded color values (`#111214`, `#222426`, etc.) repeated 100+ times. Repeated layout patterns (breadcrumb bars, panels, KPI cards) duplicated across pages instead of abstracted into components.

## Goals

1. **Restrict Tailwind to components** — Route files use only structural layout utilities (`grid`, `flex`, `gap-*`), no colors/typography/spacing
2. **Parametrized color scheme** — CSS custom properties + Tailwind `@theme` so theme can be swapped later
3. **Extract repeated patterns** — Create semantic layout/UI components for common patterns
4. **Maximize Kobalte UI usage** — Build on existing shadcn-solid primitives
5. **Remove ⌘K button** — Useless feature, remove from all pages

## Color Token System

### CSS Variables (in `styles.css` via `@theme`)

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

### Usage

Before:
```tsx
<div class="bg-[#111214] border border-[#222426] text-zinc-400">
```

After:
```tsx
<div class="bg-surface-raised border border-border-default text-text-muted">
```

## Component Taxonomy

### New Layout Components (`components/layout/`)

| Component     | Purpose                                 |
| ------------- | --------------------------------------- |
| `PageHeader`  | Sticky top bar with breadcrumbs         |
| `PageContent` | Padded container with max-width         |
| `PageTitle`   | Title + subtitle + optional action/back |

### New UI Components (`components/ui/`)

| Component       | Purpose                                    |
| --------------- | ------------------------------------------ |
| `Panel`         | Card-like container                        |
| `PanelHeader`   | Panel header with icon + title + desc      |
| `PanelBody`     | Panel content wrapper                      |
| `PanelRow`      | Key-value row with border                  |
| `KpiCard`       | Metric card with dot + label + value       |
| `KpiStrip`      | Grid container for KpiCards                |
| `EmptyState`    | Icon + title + description + action        |
| `SectionLabel`  | Divider label for form sections            |
| `IconButton`    | Small icon-only button with tooltip        |
| `DataTable`     | Table wrapper with header styling          |
| `DataTableRow`  | Row with hover + left border accent        |
| `Textarea`      | Styled multiline input                     |
| `ToggleGroup`   | Button group for mode selection            |

### Enhanced Existing Components

| Component     | Enhancement                    |
| ------------- | ------------------------------ |
| `Button`      | Add `icon` variant             |
| `Card`        | Update to use color tokens     |
| `Alert`       | Use semantic error/warning     |
| `StatusBadge` | Use color tokens               |

## Component API Design

### PageHeader

```tsx
interface Breadcrumb {
  label: string;
  href?: string;  // undefined = current page
}

interface PageHeaderProps {
  breadcrumbs: Breadcrumb[];
}
```

### PageTitle

```tsx
interface PageTitleProps {
  title: string;
  subtitle?: string;
  action?: JSX.Element;
  backLink?: { label: string; href: string };
}
```

### Panel

```tsx
interface PanelProps {
  children: JSX.Element;
  class?: string;
}

interface PanelHeaderProps {
  icon?: Component<{ class?: string }>;
  title: string;
  description?: string;
}

interface PanelBodyProps {
  children: JSX.Element;
  class?: string;
}

interface PanelRowProps {
  label: string;
  children: JSX.Element;
  border?: boolean;  // default true
}

// Usage:
<Panel>
  <PanelHeader icon={Wallet} title="Account" description="Your info" />
  <PanelBody>
    <PanelRow label="Username">{user().username}</PanelRow>
    <PanelRow label="Role" border={false}><Badge>Admin</Badge></PanelRow>
  </PanelBody>
</Panel>
```

### KpiCard

```tsx
type KpiVariant = "default" | "success" | "warning" | "error";

interface KpiCardProps {
  label: string;
  value: number | string;
  variant?: KpiVariant;
}
```

### EmptyState

```tsx
interface EmptyStateProps {
  icon: Component<{ class?: string }>;
  title: string;
  description: string;
  action?: JSX.Element;
}
```

### IconButton

```tsx
interface IconButtonProps extends ButtonHTMLAttributes {
  icon: Component<{ class?: string }>;
  tooltip: string;
  variant?: "ghost" | "danger";
  loading?: boolean;
}
```

### DataTable

```tsx
interface Column {
  key: string;
  label: string;
  span: number;  // col-span out of 12
}

interface DataTableProps {
  columns: Column[];
  children: JSX.Element;
}
```

## Implementation Strategy

### Order of Operations

1. Color tokens in `styles.css`
2. Update `components/ui/` to use tokens
3. Create new layout/ui components
4. Refactor routes one-by-one

### Route Refactor Order

| Order | Route                    | Complexity |
| ----- | ------------------------ | ---------- |
| 1     | `routes/index.tsx`       | Low        |
| 2     | `routes/setup/index.tsx` | Low        |
| 3     | `routes/setup/ssl.tsx`   | Low        |
| 4     | `routes/settings.tsx`    | Medium     |
| 5     | `routes/traders/new.tsx` | Medium     |
| 6     | `routes/traders/[id].tsx`| High       |
| 7     | `routes/traders/index.tsx`| High      |

### Tailwind Rules After Refactor

**Allowed in routes:**
- `grid`, `flex`, `gap-*`
- `space-y-*`, `space-x-*`
- `max-w-*`, `w-full`
- `hidden`, `sm:block`

**NOT allowed in routes:**
- Any color: `bg-*`, `text-*`, `border-*`
- Specific spacing: `p-6`, `px-5`
- Typography: `text-sm`, `font-medium`
- Shadows, rounds: `shadow-*`, `rounded-*`

## File Structure

### New Files

```
src/components/
├── layout/
│   ├── PageHeader.tsx
│   ├── PageContent.tsx
│   └── PageTitle.tsx
└── ui/
    ├── panel.tsx
    ├── kpi-card.tsx
    ├── empty-state.tsx
    ├── icon-button.tsx
    ├── data-table.tsx
    ├── section-label.tsx
    ├── toggle-group.tsx
    └── textarea.tsx
```

### Modified Files

```
src/
├── styles.css              (add @theme tokens)
├── components/
│   ├── layout/
│   │   ├── AppShell.tsx    (token update)
│   │   └── Sidebar.tsx     (token update)
│   ├── ui/
│   │   ├── button.tsx      (tokens)
│   │   ├── input.tsx       (tokens)
│   │   ├── card.tsx        (tokens)
│   │   ├── alert.tsx       (tokens)
│   │   ├── badge.tsx       (tokens)
│   │   ├── status-badge.tsx(tokens)
│   │   ├── tabs.tsx        (tokens)
│   │   └── index.ts        (exports)
│   └── traders/
│       ├── TraderConfigForm.tsx
│       ├── ImageVersionBanner.tsx
│       └── LogViewer.tsx
└── routes/
    ├── index.tsx
    ├── settings.tsx
    ├── setup/
    │   ├── index.tsx
    │   └── ssl.tsx
    └── traders/
        ├── index.tsx
        ├── new.tsx
        └── [id].tsx
```

## Expected Outcomes

- Route files ~50% shorter
- ~300 net lines reduced (routes shrink more than components grow)
- All colors parametrized for future theming
- Consistent component usage across all pages
- ⌘K button removed from codebase
- Improved readability and maintainability

## Testing Strategy

- Run `pnpm dev` after each route refactor — verify page renders correctly
- Run `pnpm build` — verify no TypeScript errors
- Manual visual inspection of each page
- Run `pnpm test:e2e` at the end to verify no regressions
