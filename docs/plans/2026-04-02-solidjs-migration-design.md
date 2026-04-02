# SolidJS v2 Migration Design

**Date:** 2026-04-02  
**Status:** Approved  
**Scope:** Complete rewrite of web dashboard from React/TanStack to SolidJS v2

## Overview

Migrate the hyper-trader-manager web dashboard from React 19 with TanStack Router/Query to SolidJS 2.0. This is a clean rewrite - no backwards compatibility or incremental migration.

## Tech Stack

| Concern           | Current (React)             | New (SolidJS)                     |
| ----------------- | --------------------------- | --------------------------------- |
| Framework         | React 19                    | SolidJS 2.0                       |
| Routing           | @tanstack/react-router      | @solidjs/router                   |
| Data Fetching     | @tanstack/react-query       | @tanstack/solid-query             |
| Forms             | react-hook-form + zod       | @modular-forms/solid + zod        |
| UI Primitives     | Radix UI                    | Kobalte                           |
| UI Components     | shadcn/ui                   | shadcn-solid                      |
| Icons             | lucide-react                | lucide-solid                      |
| Styling           | Tailwind CSS + CVA          | Tailwind CSS + CVA (unchanged)    |
| API Client        | @hey-api/client-fetch       | @hey-api/client-fetch (unchanged) |
| Build Tool        | Vite + @vitejs/plugin-react | Vite + vite-plugin-solid          |
| Unit Testing      | vitest + @testing-library/react | vitest + @solidjs/testing-library |
| E2E Testing       | Playwright                  | Playwright (unchanged)            |

## UI Library Decision

**Choice:** Kobalte + shadcn-solid

**Rationale:**
- Kobalte is the SolidJS equivalent of Radix UI - unstyled, accessible primitives
- shadcn-solid is a community port of shadcn/ui built on Kobalte
- Direct mapping from current Radix primitives to Kobalte
- Same Tailwind + CVA styling patterns transfer directly
- Actively maintained, used in production

## Project Structure

```
web/
├── src/
│   ├── api/                    # Framework agnostic API modules
│   ├── components/
│   │   ├── ui/                 # shadcn-solid components
│   │   ├── layout/             # AppShell, Sidebar
│   │   ├── auth/               # LoginForm, BootstrapForm
│   │   └── traders/            # TraderCard, StatusBadge, LogViewer
│   ├── lib/
│   │   ├── api/                # Generated OpenAPI client
│   │   ├── api.ts              # Typed API wrapper
│   │   ├── query-keys.ts       # TanStack Query key factories
│   │   ├── types.ts            # TypeScript types
│   │   └── utils.ts            # cn() utility
│   ├── routes/                 # Page components
│   │   ├── login.tsx
│   │   ├── setup.tsx
│   │   ├── setup-ssl.tsx
│   │   ├── dashboard.tsx
│   │   ├── settings.tsx
│   │   ├── traders.tsx
│   │   ├── traders-new.tsx
│   │   └── trader-detail.tsx
│   ├── stores/                 # Solid signals/stores
│   │   └── auth.ts             # Auth store
│   ├── config.ts               # Environment configuration
│   ├── index.tsx               # Entry point
│   └── styles.css              # Tailwind styles
├── e2e/                        # Playwright E2E tests
├── public/                     # Static assets
├── components.json             # shadcn-solid config
└── package.json
```

## SolidJS v2 Patterns

### Signals & Stores (replaces useState/useContext)

```typescript
// stores/auth.ts
import { createSignal, createRoot } from "solid-js";

function createAuthStore() {
  const [user, setUser] = createSignal<User | null>(null);
  const [token, setToken] = createSignal<string | null>(null);
  const [loading, setLoading] = createSignal(true);
  
  const authenticated = () => !!user() && !!token();
  
  async function login(username: string, password: string) { ... }
  async function logout() { ... }
  
  return { user, token, authenticated, loading, login, logout };
}

export const authStore = createRoot(createAuthStore);
```

### Data Fetching (TanStack Solid Query)

```typescript
import { createQuery } from "@tanstack/solid-query";

function TradersList() {
  const traders = createQuery(() => ({
    queryKey: traderKeys.lists(),
    queryFn: () => api.listTraders(),
  }));
  
  return (
    <Suspense fallback={<Skeleton />}>
      <For each={traders.data}>
        {(trader) => <TraderCard trader={trader} />}
      </For>
    </Suspense>
  );
}
```

### Route-Level Data Loading

```typescript
import { createAsync, cache } from "@solidjs/router";

const getTrader = cache(async (id: string) => {
  return api.getTrader(id);
}, "trader");

export const route = {
  load: ({ params }) => getTrader(params.id),
};

export default function TraderDetailPage() {
  const params = useParams();
  const trader = createAsync(() => getTrader(params.id));
  
  return (
    <Suspense fallback={<LoadingScreen />}>
      <TraderDetail trader={trader()} />
    </Suspense>
  );
}
```

## Routing Structure

### Route Configuration

```typescript
// index.tsx
import { Router, Route } from "@solidjs/router";

<Router>
  {/* Public routes */}
  <Route path="/" component={LoginPage} />
  <Route path="/setup" component={SetupPage} />
  <Route path="/setup/ssl" component={SSLSetupPage} />
  
  {/* Protected routes */}
  <Route path="/" component={AuthenticatedLayout}>
    <Route path="/dashboard" component={DashboardPage} />
    <Route path="/settings" component={SettingsPage} />
    <Route path="/traders" component={TradersListPage} />
    <Route path="/traders/new" component={NewTraderPage} />
    <Route path="/traders/:id" component={TraderDetailPage} />
  </Route>
</Router>
```

### Route Mapping

| Current Route  | New Route      | Component File           |
| -------------- | -------------- | ------------------------ |
| `/`            | `/`            | routes/login.tsx         |
| `/setup`       | `/setup`       | routes/setup.tsx         |
| `/setup/ssl`   | `/setup/ssl`   | routes/setup-ssl.tsx     |
| `/dashboard`   | `/dashboard`   | routes/dashboard.tsx     |
| `/settings`    | `/settings`    | routes/settings.tsx      |
| `/traders`     | `/traders`     | routes/traders.tsx       |
| `/traders/new` | `/traders/new` | routes/traders-new.tsx   |
| `/traders/$id` | `/traders/:id` | routes/trader-detail.tsx |

## UI Components

### shadcn-solid Components (15 total)

| Component      | Primitive    | Notes               |
| -------------- | ------------ | ------------------- |
| alert-dialog   | Kobalte      | Confirmation dialogs |
| alert          | CVA          | Informational alerts |
| avatar         | Kobalte      | User avatars         |
| badge          | CVA          | Status badges        |
| button         | Kobalte Slot | Buttons with variants |
| card           | Tailwind     | Card containers      |
| dialog         | Kobalte      | Modal dialogs        |
| dropdown-menu  | Kobalte      | Dropdown menus       |
| input          | Tailwind     | Form inputs          |
| label          | Kobalte      | Form labels          |
| separator      | Kobalte      | Visual separators    |
| skeleton       | Tailwind     | Loading skeletons    |
| table          | Tailwind     | Data tables          |
| tabs           | Kobalte      | Tab navigation       |
| tooltip        | Kobalte      | Tooltips             |

### Custom Components

| Component      | Description                              |
| -------------- | ---------------------------------------- |
| AppShell       | Main app layout with sidebar             |
| Sidebar        | Navigation sidebar (responsive)          |
| LoginForm      | Username/password login form             |
| BootstrapForm  | Initial admin setup form                 |
| TraderCard     | Card showing trader summary              |
| StatusBadge    | Status indicator (running/stopped/error) |
| LogViewer      | Log display with refresh                 |
| LoadingScreen  | Full-page loading spinner                |

## Migration Strategy

### Approach: Delete and Rebuild

1. **Delete entire `web/src/` directory**
2. **Keep framework-agnostic files:**
   - `web/e2e/` - Playwright tests (update selectors)
   - `web/public/` - Static assets
   - OpenAPI spec
3. **Scaffold new SolidJS 2.0 project**

### Build Order

**Phase 1: Foundation**
- Project setup (Vite + SolidJS 2.0 + Tailwind)
- Install dependencies
- Port lib/utils.ts, lib/types.ts, lib/query-keys.ts
- Configure API client
- Set up Tailwind with CSS variables

**Phase 2: UI Components**
- Install/configure shadcn-solid (all 15 components)
- Create cn() utility

**Phase 3: Core Infrastructure**
- Auth store (signals-based)
- Router setup
- QueryClient provider
- SSL check logic

**Phase 4: Pages**
1. Login page
2. Bootstrap/Setup page
3. SSL Setup page
4. Dashboard
5. Settings
6. Traders list
7. New trader
8. Trader detail

**Phase 5: Polish & Testing**
- Update Playwright e2e tests
- Write unit tests
- Manual QA

## Dependencies

### Production

```json
{
  "solid-js": "^2.0.0",
  "@solidjs/router": "^0.15.0",
  "@tanstack/solid-query": "^5.0.0",
  "@kobalte/core": "^0.13.0",
  "@modular-forms/solid": "^0.23.0",
  "zod": "^3.25.0",
  "lucide-solid": "^0.400.0",
  "class-variance-authority": "^0.7.0",
  "clsx": "^2.1.0",
  "tailwind-merge": "^3.0.0",
  "@hey-api/client-fetch": "^0.13.0"
}
```

### Development

```json
{
  "vite": "^6.0.0",
  "vite-plugin-solid": "^2.10.0",
  "typescript": "^5.7.0",
  "@hey-api/openapi-ts": "^0.91.0",
  "tailwindcss": "^4.0.0",
  "@tailwindcss/vite": "^4.0.0",
  "@playwright/test": "^1.58.0",
  "vitest": "^3.0.0",
  "@solidjs/testing-library": "^0.8.0"
}
```

## Testing Strategy

### Unit Tests (Complete Rewrite)

- Framework: vitest + @solidjs/testing-library
- Delete all existing `__tests__/` files
- Rewrite with SolidJS patterns

### E2E Tests (Keep Structure, Update Selectors)

- Framework: Playwright (unchanged)
- Keep test scenarios
- Update selectors as needed for new component structure

## Packages to Remove

- `react`, `react-dom`
- `@tanstack/react-router`, `@tanstack/react-query`
- All `@radix-ui/*` packages
- `react-hook-form`, `@hookform/resolvers`
- `@vitejs/plugin-react`
- `lucide-react`
- `@testing-library/react`, `@testing-library/dom`, `@testing-library/jest-dom`, `@testing-library/user-event`
- All React DevTools packages
