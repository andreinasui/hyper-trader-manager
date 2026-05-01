# Frontend Web - Agent Guide

## Technology Stack

- **Language**: TypeScript 5.7+
- **Framework**: SolidJS 1.9+
- **Routing**: @solidjs/router v0.15
- **State Management**: TanStack Solid Query v5 (server state), SolidJS signals (client state)
- **Styling**: Tailwind CSS v4
- **UI Components**: Kobalte primitives + shadcn-solid
- **Build Tool**: Vite 7
- **Package Manager**: `pnpm` (NOT npm/yarn)
- **Node Version**: >=22.12.0

## Project Structure

```
web/
├── src/
│   ├── routes/          # Page components
│   │   ├── dashboard.tsx
│   │   ├── login.tsx
│   │   ├── settings.tsx
│   │   ├── setup.tsx
│   │   ├── setup-ssl.tsx
│   │   ├── trader-detail.tsx
│   │   ├── traders.tsx
│   │   └── traders-new.tsx
│   ├── components/      # SolidJS components
│   │   ├── ui/          # shadcn-solid components (Kobalte-based)
│   │   ├── auth/        # Authentication forms
│   │   ├── layout/      # App shell, sidebar
│   │   └── traders/     # Trader-specific components
│   ├── lib/             # Utilities and helpers
│   │   ├── api.ts       # Typed API wrapper
│   │   ├── api/         # API client with token management
│   │   ├── types.ts     # TypeScript interfaces
│   │   ├── query-keys.ts # TanStack Query key factories
│   │   └── utils.ts     # cn() helper and utilities
│   ├── stores/          # SolidJS signal-based stores
│   │   └── auth.ts      # Authentication store
│   ├── test/            # Test setup and utilities
│   ├── index.tsx        # App entry point
│   ├── App.tsx          # Root component with auth guard
│   ├── config.ts        # Zod-validated configuration
│   └── styles.css       # Tailwind v4 styles
├── e2e/                 # Playwright end-to-end tests
├── public/              # Static assets
└── dist/                # Production build output
```

## Development Commands

All commands use `just` - run `just` to see available commands.

### Common Commands
```bash
just dev              # Run dev server (port 3000)
just build            # Build for production
just preview          # Preview production build
just typecheck        # Run TypeScript type checking
just clean            # Clean build artifacts
```

### Setup
```bash
just install          # Install dependencies with pnpm
just install-clean    # Clean install (remove node_modules first)
just update           # Update dependencies
just check-node       # Verify Node.js version
```

### Direct pnpm Commands
```bash
pnpm dev              # Dev server with hot reload
pnpm build            # Production build
pnpm test             # Run unit tests (vitest)
pnpm test:e2e         # Run Playwright e2e tests
pnpm test:e2e:ui      # Run e2e tests with Playwright UI
```

## Coding Guidelines

### Style Guide
- **TypeScript**: Strict mode enabled
- **Linting**: TypeScript compiler checks (no ESLint configured yet)
- **Formatting**: Use editor formatters (Prettier recommended)
- **Path aliases**: Use `~/*` for `./src/*` imports

### TypeScript Configuration
From `tsconfig.json`:
- **Target**: ES2022
- **Strict mode**: Enabled
- **JSX**: `preserve` with `jsxImportSource: "solid-js"`
- **Unused variables**: Error
- **No fallthrough cases**: Error
- **Path mapping**: `~/*` → `src/*`

### Best Practices
1. **Use TypeScript strict mode** - No implicit `any`, strict null checks
2. **Prefer function components** - SolidJS components are plain functions
3. **SolidJS Router** - Route definitions in `src/index.tsx`
4. **TanStack Solid Query** - Server state management with `createQuery`/`createMutation`
5. **Signals for client state** - Use `createSignal` and `createStore` for reactive state
6. **Tailwind CSS** - Utility-first styling, use `cn()` helper for conditional classes
7. **Component composition** - Kobalte + shadcn-solid patterns
8. **Path imports** - Use `~/components/...` instead of relative paths

### SolidJS Conventions
- **Components**: PascalCase filenames (e.g., `UserProfile.tsx`)
- **Signals**: Destructure as `[getter, setter]` (e.g., `const [count, setCount] = createSignal(0)`)
- **Derived state**: Use functions, not memoization by default
- **Props**: Use `splitProps` for separating component props from pass-through props
- **Conditional rendering**: Use `<Show>` component with `when` and `fallback` props
- **List rendering**: Use `<For>` component with `each` prop
- **Types**: Define in same file or `types.ts` if shared

## Testing

### Test Locations
- **Unit tests**: `src/lib/__tests__/` (colocated with code)
- **Component tests**: `src/components/**/*.test.tsx` (when needed)
- **E2E tests**: `e2e/*.spec.ts`
- **Test setup**: `src/test/setup.ts`

### Running Tests
```bash
pnpm test                # Run unit tests
pnpm test:e2e            # Run e2e tests headless
pnpm test:e2e:ui         # Run e2e with Playwright UI
pnpm test:e2e:headed     # Run e2e in headed mode
```

### Test Configuration
- **Unit tests**: `vitest.config.ts` (jsdom environment, excludes e2e/)
- **E2E tests**: `playwright.config.ts`
- **Test utilities**: `src/test/setup.ts`

## Key Libraries

### @solidjs/router
- **Declarative routing**: Routes defined in `src/index.tsx` with `<Router>` and `<Route>`
- **Type-safe**: Full TypeScript support for routes and params
- **Navigation**: Use `<A>` component or `useNavigate()` hook

### TanStack Solid Query
- **Server state**: Use `createQuery` for all API calls
- **Mutations**: Use `createMutation` for POST/PUT/DELETE
- **Caching**: Automatic background refetching
- **Query keys**: Defined in `src/lib/query-keys.ts`

### Kobalte + shadcn-solid
- **Component registry**: `components.json`
- **Primitives**: Kobalte provides accessible, unstyled primitives
- **Styling**: shadcn-solid adds Tailwind styles on top
- **Customization**: Edit components directly in `src/components/ui/`

### SolidJS Stores
- **Auth store**: `src/stores/auth.ts` - Token and user state management
- **Signals**: Fine-grained reactivity without re-renders

## Development URLs
- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000 (see `/api` folder)
- **API Docs**: http://localhost:8000/docs

## Responsive Design Conventions

The app supports phone (≤640px), tablet (641–1024px), and desktop (>1024px). Adaptation lives in shared primitives, not in route files.

### Rules

1. **Pages contain almost no `md:` / `lg:` / `sm:` classes.** Route files describe layout in terms of primitives; the primitives decide breakpoints internally.
2. **Primitives use container queries** (`@container`, `@sm:`, `@lg:` Tailwind v4 native) so they adapt to their parent's width, not the viewport. This makes them work correctly inside narrow contexts (modals, sidebars).
3. **Viewport breakpoints (`md:`, `lg:`) are reserved for app-chrome layout decisions** — sidebar drawer toggle, top-level grid splits — never for component-internal responsiveness.
4. **Fluid typography is global** (see `styles.css` `@theme` `--text-*` tokens). Don't override `font-size` per breakpoint.

### Mobile-friendly primitives

| Primitive | Location | Purpose |
|-----------|----------|---------|
| `<FormGrid>` | `~/components/ui/form-grid` | Auto-stacks form fields by container width |
| `<PageActions>` | `~/components/layout/PageActions` | Collapses secondary actions into `⋯` menu on narrow containers |
| `<ResponsiveTable>` | `~/components/ui/responsive-table` | Renders 12-col table on tablet+, stacked cards on phone |
| `<KpiStrip>` | `~/components/ui/kpi-card` | 2×2 on phone, 1×N on tablet+ |

If you find yourself writing `class="grid grid-cols-2 md:grid-cols-3"` in a route file, that's a sign the primitive needs to grow — extend it, don't branch in the page.
