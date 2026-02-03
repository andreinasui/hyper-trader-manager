# Frontend Web - Agent Guide

## Technology Stack

- **Language**: TypeScript 5.7+
- **Framework**: React 19
- **Routing**: TanStack Router v1
- **State Management**: TanStack Query v5 (server state)
- **Styling**: Tailwind CSS v4
- **UI Components**: Radix UI primitives + shadcn/ui
- **Build Tool**: Vite 7
- **Package Manager**: `pnpm` (NOT npm/yarn)
- **Node Version**: >=22.12.0

## Project Structure

```
web/
├── src/
│   ├── routes/          # Route components (TanStack Router file-based)
│   │   ├── admin/       # Admin section routes
│   │   ├── traders/     # Trader management routes
│   │   └── settings/    # Settings routes
│   ├── components/      # React components
│   │   └── ui/          # shadcn/ui components
│   ├── lib/             # Utilities and helpers
│   │   └── __tests__/   # Unit tests for lib
│   ├── test/            # Test setup and utilities
│   └── ...
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
- **Path aliases**: Use `@/*` for `./src/*` imports

### TypeScript Configuration
From `tsconfig.json`:
- **Target**: ES2022
- **Strict mode**: Enabled
- **Unused variables**: Error
- **No fallthrough cases**: Error
- **Path mapping**: `@/*` → `src/*`

### Best Practices
1. **Use TypeScript strict mode** - No implicit `any`, strict null checks
2. **Prefer function components** - Use React 19 features (use hook, etc.)
3. **TanStack Router** - File-based routing in `src/routes/`
4. **TanStack Query** - Server state management, not useState for API data
5. **Tailwind CSS** - Utility-first styling, use `cn()` helper for conditional classes
6. **Component composition** - Radix UI + shadcn/ui patterns
7. **Path imports** - Use `@/components/...` instead of relative paths

### React Conventions
- **Components**: PascalCase filenames (e.g., `UserProfile.tsx`)
- **Hooks**: Custom hooks start with `use` (e.g., `useAuth.ts`)
- **Types**: Define in same file or `types.ts` if shared
- **Props**: Use TypeScript interfaces for component props

## Testing

### Test Locations
- **Unit tests**: `src/lib/__tests__/` (colocated with code)
- **Component tests**: `src/components/**/*.test.tsx` (when needed)
- **E2E tests**: `e2e/*.spec.ts`
- **Test setup**: `src/test/setup.ts`

### Unit Tests (Vitest)
```typescript
// src/lib/__tests__/example.test.ts
import { describe, it, expect } from 'vitest'

describe('Feature', () => {
  it('should work correctly', () => {
    expect(true).toBe(true)
  })
})
```

### E2E Tests (Playwright)
```typescript
// e2e/example.spec.ts
import { test, expect } from '@playwright/test'

test('user can login', async ({ page }) => {
  await page.goto('http://localhost:3000')
  // ... test steps
})
```

### Running Tests
```bash
pnpm test                # Run unit tests
pnpm test:e2e            # Run e2e tests headless
pnpm test:e2e:ui         # Run e2e with Playwright UI
pnpm test:e2e:headed     # Run e2e in headed mode
```

### Test Configuration
- **Unit tests**: `vitest.config.ts` (jsdom environment)
- **E2E tests**: `playwright.config.ts`
- **Test utilities**: `src/test/setup.ts`

## Key Libraries

### TanStack Router
- **File-based routing**: Routes defined in `src/routes/`
- **Type-safe**: Full TypeScript support for routes and params
- **Devtools**: Enabled in development

### TanStack Query
- **Server state**: Use for all API calls
- **Caching**: Automatic background refetching
- **Devtools**: Enabled in development

### shadcn/ui
- **Component registry**: `components.json`
- **Add components**: Copy from shadcn/ui docs (components live in `src/components/ui/`)
- **Customization**: Edit components directly, they're your code

## Development URLs
- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000 (see `/api` folder)
- **API Docs**: http://localhost:8000/docs
