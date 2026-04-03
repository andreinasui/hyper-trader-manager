# SolidStart Migration Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Migrate web frontend from Vite SPA to SolidStart with API proxy, making API container internal-only.

**Architecture:** SolidStart CSR app with Vinxi server middleware proxying `/api/*` to internal API container. Traefik routes all traffic to web container.

**Tech Stack:** SolidStart, Vinxi, Node.js runtime, TanStack Solid Query, Tailwind CSS v4

---

## Task 1: Update Dependencies

**Files:**
- Modify: `web/package.json`

**Step 1: Update package.json**

Replace the entire package.json with SolidStart dependencies:

```json
{
  "name": "hyper-trader-manager-web",
  "private": true,
  "version": "0.0.0",
  "type": "module",
  "scripts": {
    "dev": "vinxi dev",
    "build": "vinxi build",
    "start": "vinxi start",
    "test": "vitest run",
    "test:watch": "vitest",
    "test:e2e": "playwright test"
  },
  "dependencies": {
    "@solidjs/router": "^0.15.0",
    "@solidjs/start": "^1.0.0",
    "solid-js": "^1.9.12",
    "@tanstack/solid-query": "^5.66.0",
    "@kobalte/core": "^0.13.0",
    "@modular-forms/solid": "^0.23.0",
    "zod": "^3.25.0",
    "lucide-solid": "^0.469.0",
    "class-variance-authority": "^0.7.1",
    "clsx": "^2.1.1",
    "tailwind-merge": "^3.0.2",
    "vinxi": "^0.5.0"
  },
  "devDependencies": {
    "typescript": "^5.7.2",
    "tailwindcss": "^4.0.6",
    "@playwright/test": "^1.58.1",
    "vitest": "^3.0.5",
    "@solidjs/testing-library": "^0.8.10",
    "jsdom": "^26.0.0"
  }
}
```

**Step 2: Reinstall dependencies**

Run:
```bash
cd web && rm -rf node_modules pnpm-lock.yaml && pnpm install
```

Expected: Dependencies install successfully

**Step 3: Commit**

```bash
git add web/package.json web/pnpm-lock.yaml
git commit -m "web: update dependencies for SolidStart migration"
```

---

## Task 2: Create SolidStart Configuration

**Files:**
- Create: `web/app.config.ts`
- Delete: `web/vite.config.ts`

**Step 1: Create app.config.ts**

```typescript
import { defineConfig } from "@solidjs/start/config";

const apiTarget = process.env.API_URL || "http://localhost:8000";

export default defineConfig({
  ssr: false,
  server: {
    preset: "node-server",
    routeRules: {
      "/api/**": {
        proxy: { to: `${apiTarget}/**` }
      }
    }
  },
  vite: {
    resolve: {
      alias: {
        "~": "./src"
      }
    }
  }
});
```

**Step 2: Delete vite.config.ts**

Run:
```bash
rm web/vite.config.ts
```

**Step 3: Commit**

```bash
git add web/app.config.ts
git rm web/vite.config.ts
git commit -m "web: add SolidStart config, remove Vite config"
```

---

## Task 3: Create Entry Files

**Files:**
- Create: `web/src/entry-client.tsx`
- Create: `web/src/app.tsx`
- Delete: `web/src/index.tsx`
- Modify: `web/src/index.html` → `web/index.html`

**Step 1: Create entry-client.tsx**

```tsx
// @refresh reload
import { mount, StartClient } from "@solidjs/start/client";

mount(() => <StartClient />, document.getElementById("root")!);
```

**Step 2: Create app.tsx (root layout)**

```tsx
import { type ParentProps, Suspense, onMount, createSignal, Show } from "solid-js";
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
    <div class="min-h-screen flex items-center justify-center bg-background">
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

export default function App() {
  return (
    <MetaProvider>
      <QueryClientProvider client={queryClient}>
        <AuthGuard>
          <Router root={(props) => <Suspense>{props.children}</Suspense>}>
            <FileRoutes />
          </Router>
        </AuthGuard>
      </QueryClientProvider>
    </MetaProvider>
  );
}
```

**Step 3: Move and update index.html**

Move `web/src/index.html` to `web/index.html` and ensure it has:

```html
<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Hyper Trader Manager</title>
  </head>
  <body>
    <div id="root"></div>
    <script src="./src/entry-client.tsx" type="module"></script>
  </body>
</html>
```

**Step 4: Delete old entry files**

Run:
```bash
rm web/src/index.tsx web/src/App.tsx
```

**Step 5: Commit**

```bash
git add web/src/entry-client.tsx web/src/app.tsx web/index.html
git rm web/src/index.tsx web/src/App.tsx web/src/index.html 2>/dev/null || true
git commit -m "web: add SolidStart entry files"
```

---

## Task 4: Migrate Routes - Public Pages

**Files:**
- Create: `web/src/routes/index.tsx` (login)
- Modify: `web/src/routes/setup.tsx`
- Create: `web/src/routes/setup/ssl.tsx`
- Delete: `web/src/routes/login.tsx`
- Delete: `web/src/routes/setup-ssl.tsx`

**Step 1: Create routes/index.tsx (login page)**

```tsx
import { type Component } from "solid-js";
import { useNavigate } from "@solidjs/router";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "~/components/ui/card";
import { LoginForm } from "~/components/auth/LoginForm";
import { authStore } from "~/stores/auth";

export default function LoginPage() {
  const navigate = useNavigate();

  // Redirect to setup if not initialized
  if (!authStore.isInitialized()) {
    navigate("/setup", { replace: true });
    return null;
  }

  // Redirect to dashboard if already authenticated
  if (authStore.authenticated()) {
    navigate("/dashboard", { replace: true });
    return null;
  }

  return (
    <div class="min-h-screen flex items-center justify-center bg-background p-4">
      <Card class="w-full max-w-md">
        <CardHeader class="text-center">
          <CardTitle class="text-2xl">Hyper Trader Manager</CardTitle>
          <CardDescription>Sign in to your account</CardDescription>
        </CardHeader>
        <CardContent>
          <LoginForm />
        </CardContent>
      </Card>
    </div>
  );
}
```

**Step 2: Create routes/setup directory and ssl.tsx**

Run:
```bash
mkdir -p web/src/routes/setup
```

Copy content from `setup-ssl.tsx` to `web/src/routes/setup/ssl.tsx`, updating imports.

**Step 3: Update setup.tsx**

Keep the existing `setup.tsx` content - the file path already matches the route.

**Step 4: Delete old files**

Run:
```bash
rm web/src/routes/login.tsx web/src/routes/setup-ssl.tsx
```

**Step 5: Commit**

```bash
git add web/src/routes/index.tsx web/src/routes/setup/ web/src/routes/setup.tsx
git rm web/src/routes/login.tsx web/src/routes/setup-ssl.tsx
git commit -m "web: migrate public route pages to file-based routing"
```

---

## Task 5: Migrate Routes - Protected Pages

**Files:**
- Keep: `web/src/routes/dashboard.tsx`
- Keep: `web/src/routes/settings.tsx`
- Create: `web/src/routes/traders/index.tsx`
- Create: `web/src/routes/traders/new.tsx`
- Create: `web/src/routes/traders/[id].tsx`
- Delete: `web/src/routes/traders.tsx`
- Delete: `web/src/routes/traders-new.tsx`
- Delete: `web/src/routes/trader-detail.tsx`

**Step 1: Create traders directory**

Run:
```bash
mkdir -p web/src/routes/traders
```

**Step 2: Move traders.tsx to traders/index.tsx**

Run:
```bash
mv web/src/routes/traders.tsx web/src/routes/traders/index.tsx
```

**Step 3: Move traders-new.tsx to traders/new.tsx**

Run:
```bash
mv web/src/routes/traders-new.tsx web/src/routes/traders/new.tsx
```

**Step 4: Move trader-detail.tsx to traders/[id].tsx**

Run:
```bash
mv web/src/routes/trader-detail.tsx "web/src/routes/traders/[id].tsx"
```

Update the dynamic param access in `[id].tsx`:

Change:
```typescript
const params = useParams();
// params.id
```

To (SolidStart uses same syntax, no change needed):
```typescript
const params = useParams();
// params.id still works
```

**Step 5: Commit**

```bash
git add web/src/routes/traders/
git rm web/src/routes/traders.tsx web/src/routes/traders-new.tsx web/src/routes/trader-detail.tsx 2>/dev/null || true
git commit -m "web: migrate protected route pages to file-based routing"
```

---

## Task 6: Add Auth Guard to Protected Routes

**Files:**
- Modify: `web/src/routes/dashboard.tsx`
- Modify: `web/src/routes/settings.tsx`
- Modify: `web/src/routes/traders/index.tsx`
- Modify: `web/src/routes/traders/new.tsx`
- Modify: `web/src/routes/traders/[id].tsx`

**Step 1: Create a route guard wrapper**

Add to each protected route file at the top:

```tsx
import { useNavigate } from "@solidjs/router";
import { onMount } from "solid-js";
import { authStore } from "~/stores/auth";

// Inside component, add:
const navigate = useNavigate();

onMount(() => {
  if (!authStore.authenticated()) {
    navigate("/", { replace: true });
  }
});
```

Alternatively, create a shared guard component in `web/src/components/auth/ProtectedRoute.tsx`:

```tsx
import { type ParentProps, onMount, Show } from "solid-js";
import { useNavigate } from "@solidjs/router";
import { authStore } from "~/stores/auth";

export function ProtectedRoute(props: ParentProps) {
  const navigate = useNavigate();

  onMount(() => {
    if (!authStore.authenticated()) {
      navigate("/", { replace: true });
    }
  });

  return (
    <Show when={authStore.authenticated()}>
      {props.children}
    </Show>
  );
}
```

Then wrap each protected page's content with `<ProtectedRoute>`.

**Step 2: Commit**

```bash
git add web/src/routes/ web/src/components/auth/ProtectedRoute.tsx
git commit -m "web: add auth guard to protected routes"
```

---

## Task 7: Update TypeScript Config

**Files:**
- Modify: `web/tsconfig.json`

**Step 1: Update tsconfig.json for SolidStart**

```json
{
  "compilerOptions": {
    "target": "ES2020",
    "module": "ESNext",
    "moduleResolution": "bundler",
    "allowSyntheticDefaultImports": true,
    "esModuleInterop": true,
    "jsx": "preserve",
    "jsxImportSource": "solid-js",
    "strict": true,
    "noEmit": true,
    "skipLibCheck": true,
    "types": ["vinxi/types/client"],
    "paths": {
      "~/*": ["./src/*"]
    }
  },
  "include": ["src/**/*", "app.config.ts"]
}
```

**Step 2: Commit**

```bash
git add web/tsconfig.json
git commit -m "web: update TypeScript config for SolidStart"
```

---

## Task 8: Update Dockerfile

**Files:**
- Modify: `web/Dockerfile`

**Step 1: Replace Dockerfile with Node.js runtime**

```dockerfile
# HyperTrader Web Dockerfile
# Multi-stage build: SolidStart with Node.js runtime

# ============================================
# Build stage
# ============================================
FROM node:22-alpine AS builder

WORKDIR /app

# Install pnpm
RUN npm install -g pnpm@10

# Copy package files
COPY package.json pnpm-lock.yaml ./

# Install dependencies
RUN pnpm install --frozen-lockfile

# Copy source code
COPY . .

# Build the SolidStart application
RUN pnpm build

# ============================================
# Runtime stage
# ============================================
FROM node:22-alpine AS runner

WORKDIR /app

# Copy built output from builder
COPY --from=builder /app/.output /app/.output

# Set environment variables
ENV NODE_ENV=production
ENV API_URL=http://api:8000

# Expose port
EXPOSE 3000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD wget --no-verbose --tries=1 --spider http://localhost:3000/ || exit 1

# Run the server
CMD ["node", ".output/server/index.mjs"]
```

**Step 2: Delete nginx.conf (no longer needed)**

Run:
```bash
rm web/nginx.conf
```

**Step 3: Commit**

```bash
git add web/Dockerfile
git rm web/nginx.conf
git commit -m "web: update Dockerfile for SolidStart Node.js runtime"
```

---

## Task 9: Update Traefik Configuration

**Files:**
- Modify: `data/traefik/dynamic.yml`

**Step 1: Update dynamic.yml**

Remove API routing, route all traffic to web:

```yaml
http:
  routers:
    health:
      rule: "Path(`/health`)"
      service: web
      entryPoints:
        - web
      priority: 20
    web:
      rule: "PathPrefix(`/`)"
      service: web
      entryPoints:
        - web
      priority: 1

  services:
    web:
      loadBalancer:
        servers:
          - url: "http://web:3000"
        healthCheck:
          path: /
          interval: "10s"
          timeout: "5s"
```

**Step 2: Commit**

```bash
git add data/traefik/dynamic.yml
git commit -m "infra: update Traefik to route all traffic through web container"
```

---

## Task 10: Update Docker Compose

**Files:**
- Modify: `deploy/docker-compose.dev.yml`
- Modify: `deploy/docker-compose.prod.yml`

**Step 1: Update docker-compose.dev.yml**

Update web service:

```yaml
web:
  build:
    context: ../web
    dockerfile: Dockerfile
  container_name: hypertrader-web
  restart: unless-stopped
  environment:
    - API_URL=http://api:8000
  networks:
    - hypertrader
  healthcheck:
    test: ["CMD", "wget", "--no-verbose", "--tries=1", "--spider", "http://localhost:3000/"]
    interval: 30s
    timeout: 10s
    retries: 3
    start_period: 10s
  depends_on:
    api:
      condition: service_healthy
```

Remove traefik dependency from web, add api dependency.

Update API service to remove traefik dependency (API is now internal):

```yaml
api:
  # ... keep existing config
  depends_on: []  # Remove traefik dependency
```

**Step 2: Apply same changes to docker-compose.prod.yml**

**Step 3: Commit**

```bash
git add deploy/docker-compose.dev.yml deploy/docker-compose.prod.yml
git commit -m "infra: update Docker Compose for SolidStart architecture"
```

---

## Task 11: Test Local Development

**Step 1: Start API locally**

Run:
```bash
cd api && uv run uvicorn hyper_trader_api.main:app --reload --port 8000
```

**Step 2: Start web dev server**

Run:
```bash
cd web && API_URL=http://localhost:8000 pnpm dev
```

Expected: App loads at http://localhost:3000, API calls proxied to localhost:8000

**Step 3: Test API proxy**

Run:
```bash
curl http://localhost:3000/api/v1/auth/setup-status
```

Expected: `{"initialized":true}` or `{"initialized":false}`

---

## Task 12: Test Docker Build

**Step 1: Rebuild containers**

Run:
```bash
docker compose -f deploy/docker-compose.dev.yml down
docker compose -f deploy/docker-compose.dev.yml up -d --build
```

**Step 2: Verify services are healthy**

Run:
```bash
docker ps
```

Expected: All containers healthy

**Step 3: Test through Traefik**

Run:
```bash
curl http://localhost:3080/api/v1/auth/setup-status
```

Expected: Response from API (proxied through web container)

**Step 4: Verify API is not directly accessible**

Run:
```bash
curl http://localhost:8000/health 2>&1
```

Expected: Connection refused (API only accessible within Docker network)

**Step 5: Commit any final fixes**

```bash
git add -A
git commit -m "web: complete SolidStart migration"
```

---

## Summary

| Task | Description | Est. Time |
|------|-------------|-----------|
| 1 | Update dependencies | 5 min |
| 2 | Create SolidStart config | 5 min |
| 3 | Create entry files | 10 min |
| 4 | Migrate public routes | 15 min |
| 5 | Migrate protected routes | 15 min |
| 6 | Add auth guards | 15 min |
| 7 | Update TypeScript config | 5 min |
| 8 | Update Dockerfile | 10 min |
| 9 | Update Traefik config | 5 min |
| 10 | Update Docker Compose | 10 min |
| 11 | Test local development | 15 min |
| 12 | Test Docker build | 15 min |
| **Total** | | **~2 hours** |
