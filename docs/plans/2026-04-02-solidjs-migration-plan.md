# SolidJS v2 Migration Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Complete rewrite of web dashboard from React/TanStack to SolidJS v2 with Kobalte + shadcn-solid UI.

**Architecture:** Clean-slate rewrite. Delete existing React src/, scaffold SolidJS 2.0 project, rebuild all pages and components using Solid primitives (signals, stores, createAsync). Auth via signal-based store, routing via @solidjs/router, data fetching via @tanstack/solid-query.

**Tech Stack:** SolidJS 2.0, @solidjs/router, @tanstack/solid-query, Kobalte, shadcn-solid, @modular-forms/solid, zod, Tailwind CSS 4, Vite, vitest, Playwright

**Design Doc:** `docs/plans/2026-04-02-solidjs-migration-design.md`

---

## Phase 1: Project Foundation

### Task 1.1: Backup and Clean Slate

**Files:**
- Delete: `web/src/` (entire directory)
- Keep: `web/e2e/`, `web/public/`, `web/playwright.config.ts`

**Step 1: Create backup branch**

```bash
git checkout -b backup/react-web-dashboard
git push origin backup/react-web-dashboard
git checkout main
```

**Step 2: Delete React source directory**

```bash
rm -rf web/src
```

**Step 3: Commit clean slate**

```bash
git add -A
git commit -m "chore: remove React source for SolidJS migration"
```

---

### Task 1.2: Initialize SolidJS Project

**Files:**
- Create: `web/src/index.tsx`
- Create: `web/src/App.tsx`
- Modify: `web/package.json`
- Modify: `web/tsconfig.json`
- Create: `web/vite.config.ts`

**Step 1: Update package.json with SolidJS dependencies**

Replace `web/package.json` with:

```json
{
  "name": "hyper-trader-manager-web",
  "private": true,
  "version": "0.0.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "vite build",
    "preview": "vite preview",
    "test": "vitest run",
    "test:watch": "vitest",
    "test:e2e": "playwright test",
    "generate-api": "openapi-ts"
  },
  "dependencies": {
    "solid-js": "^1.9.0",
    "@solidjs/router": "^0.15.0",
    "@tanstack/solid-query": "^5.66.0",
    "@kobalte/core": "^0.13.0",
    "@modular-forms/solid": "^0.23.0",
    "zod": "^3.25.0",
    "lucide-solid": "^0.469.0",
    "class-variance-authority": "^0.7.1",
    "clsx": "^2.1.1",
    "tailwind-merge": "^3.0.2",
    "@hey-api/client-fetch": "^0.13.1"
  },
  "devDependencies": {
    "vite": "^6.2.0",
    "vite-plugin-solid": "^2.11.0",
    "typescript": "^5.7.2",
    "@hey-api/openapi-ts": "^0.91.1",
    "tailwindcss": "^4.0.6",
    "@tailwindcss/vite": "^4.0.6",
    "@playwright/test": "^1.58.1",
    "vitest": "^3.0.5",
    "@solidjs/testing-library": "^0.8.10",
    "jsdom": "^26.0.0"
  }
}
```

**Step 2: Install dependencies**

Run: `cd web && pnpm install`

**Step 3: Create vite.config.ts**

Create `web/vite.config.ts`:

```typescript
import { defineConfig } from "vite";
import solid from "vite-plugin-solid";
import tailwindcss from "@tailwindcss/vite";
import { resolve } from "path";

export default defineConfig({
  plugins: [solid(), tailwindcss()],
  resolve: {
    alias: {
      "~": resolve(__dirname, "./src"),
    },
  },
  server: {
    port: 3000,
    proxy: {
      "/api": {
        target: "http://localhost:8000",
        changeOrigin: true,
      },
    },
  },
});
```

**Step 4: Update tsconfig.json**

Replace `web/tsconfig.json`:

```json
{
  "compilerOptions": {
    "target": "ES2020",
    "useDefineForClassFields": true,
    "module": "ESNext",
    "lib": ["ES2020", "DOM", "DOM.Iterable"],
    "skipLibCheck": true,
    "moduleResolution": "bundler",
    "allowImportingTsExtensions": true,
    "resolveJsonModule": true,
    "isolatedModules": true,
    "noEmit": true,
    "jsx": "preserve",
    "jsxImportSource": "solid-js",
    "strict": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "noFallthroughCasesInSwitch": true,
    "paths": {
      "~/*": ["./src/*"]
    }
  },
  "include": ["src"]
}
```

**Step 5: Create vitest.config.ts**

Create `web/vitest.config.ts`:

```typescript
import { defineConfig } from "vitest/config";
import solid from "vite-plugin-solid";
import { resolve } from "path";

export default defineConfig({
  plugins: [solid()],
  resolve: {
    alias: {
      "~": resolve(__dirname, "./src"),
    },
  },
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["./src/test/setup.ts"],
    deps: {
      optimizer: {
        web: {
          include: ["solid-js"],
        },
      },
    },
  },
});
```

**Step 6: Commit**

```bash
git add -A
git commit -m "chore: configure SolidJS project with Vite and Tailwind"
```

---

### Task 1.3: Create Entry Point and Base Structure

**Files:**
- Create: `web/src/index.tsx`
- Create: `web/src/App.tsx`
- Create: `web/src/styles.css`
- Create: `web/src/test/setup.ts`
- Modify: `web/index.html`

**Step 1: Create styles.css with Tailwind**

Create `web/src/styles.css`:

```css
@import "tailwindcss";

@theme {
  --color-background: hsl(240 10% 3.9%);
  --color-foreground: hsl(0 0% 98%);
  --color-card: hsl(240 10% 3.9%);
  --color-card-foreground: hsl(0 0% 98%);
  --color-popover: hsl(240 10% 3.9%);
  --color-popover-foreground: hsl(0 0% 98%);
  --color-primary: hsl(0 0% 98%);
  --color-primary-foreground: hsl(240 5.9% 10%);
  --color-secondary: hsl(240 3.7% 15.9%);
  --color-secondary-foreground: hsl(0 0% 98%);
  --color-muted: hsl(240 3.7% 15.9%);
  --color-muted-foreground: hsl(240 5% 64.9%);
  --color-accent: hsl(240 3.7% 15.9%);
  --color-accent-foreground: hsl(0 0% 98%);
  --color-destructive: hsl(0 62.8% 30.6%);
  --color-destructive-foreground: hsl(0 0% 98%);
  --color-border: hsl(240 3.7% 15.9%);
  --color-input: hsl(240 3.7% 15.9%);
  --color-ring: hsl(240 4.9% 83.9%);
  --radius-sm: 0.25rem;
  --radius-md: 0.375rem;
  --radius-lg: 0.5rem;
}

html {
  color-scheme: dark;
}

body {
  @apply bg-background text-foreground;
  font-family: system-ui, -apple-system, sans-serif;
}
```

**Step 2: Create App.tsx**

Create `web/src/App.tsx`:

```typescript
import type { Component } from "solid-js";

const App: Component = () => {
  return (
    <div class="min-h-screen flex items-center justify-center">
      <h1 class="text-2xl font-bold">Hyper Trader Manager</h1>
    </div>
  );
};

export default App;
```

**Step 3: Create index.tsx entry point**

Create `web/src/index.tsx`:

```typescript
/* @refresh reload */
import { render } from "solid-js/web";
import "./styles.css";
import App from "./App";

const root = document.getElementById("root");

if (!root) {
  throw new Error("Root element not found");
}

render(() => <App />, root);
```

**Step 4: Update index.html**

Replace `web/index.html`:

```html
<!doctype html>
<html lang="en" class="dark">
  <head>
    <meta charset="UTF-8" />
    <link rel="icon" type="image/svg+xml" href="/vite.svg" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Hyper Trader Manager</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/index.tsx"></script>
  </body>
</html>
```

**Step 5: Create test setup**

Create `web/src/test/setup.ts`:

```typescript
import "@solidjs/testing-library";
```

**Step 6: Verify dev server starts**

Run: `cd web && pnpm dev`
Expected: Server starts on http://localhost:3000, shows "Hyper Trader Manager"

**Step 7: Commit**

```bash
git add -A
git commit -m "feat: add SolidJS entry point and base structure"
```

---

### Task 1.4: Port Utility Functions and Types

**Files:**
- Create: `web/src/lib/utils.ts`
- Create: `web/src/lib/types.ts`
- Create: `web/src/lib/query-keys.ts`
- Create: `web/src/config.ts`

**Step 1: Create utils.ts**

Create `web/src/lib/utils.ts`:

```typescript
import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}
```

**Step 2: Create types.ts**

Create `web/src/lib/types.ts`:

```typescript
export interface User {
  id: string;
  username: string;
  is_admin: boolean;
  created_at: string;
}

export interface Trader {
  id: string;
  name: string;
  wallet_address: string;
  status: "running" | "stopped" | "error";
  created_at: string;
  updated_at: string;
  user_id: string;
}

export interface TraderStatusResponse {
  status: "running" | "stopped" | "error";
  uptime_seconds?: number;
  last_error?: string;
}

export interface CreateTraderRequest {
  name: string;
  wallet_address: string;
  private_key: string;
}

export interface SystemStats {
  total_users: number;
  total_traders: number;
  active_traders: number;
}

export interface LoginRequest {
  username: string;
  password: string;
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
}

export interface SetupStatusResponse {
  initialized: boolean;
}

export interface SSLStatusResponse {
  configured: boolean;
  mode?: "domain" | "ip";
  domain?: string;
}
```

**Step 3: Create query-keys.ts**

Create `web/src/lib/query-keys.ts`:

```typescript
export const traderKeys = {
  all: ["traders"] as const,
  lists: () => [...traderKeys.all, "list"] as const,
  detail: (id: string) => [...traderKeys.all, "detail", id] as const,
  logs: (id: string) => [...traderKeys.detail(id), "logs"] as const,
  status: (id: string) => [...traderKeys.detail(id), "status"] as const,
};

export const userKeys = {
  all: ["users"] as const,
  me: () => [...userKeys.all, "me"] as const,
};

export const adminKeys = {
  all: ["admin"] as const,
  stats: () => [...adminKeys.all, "stats"] as const,
  users: () => [...adminKeys.all, "users"] as const,
  traders: () => [...adminKeys.all, "traders"] as const,
};

export const setupKeys = {
  all: ["setup"] as const,
  status: () => [...setupKeys.all, "status"] as const,
  ssl: () => [...setupKeys.all, "ssl"] as const,
};
```

**Step 4: Create config.ts**

Create `web/src/config.ts`:

```typescript
import { z } from "zod";

const configSchema = z.object({
  VITE_API_URL: z.string().default("/api"),
});

export const config = configSchema.parse({
  VITE_API_URL: import.meta.env.VITE_API_URL,
});
```

**Step 5: Commit**

```bash
git add -A
git commit -m "feat: add utility functions, types, and query keys"
```

---

### Task 1.5: Configure API Client

**Files:**
- Create: `web/src/lib/api/client.ts`
- Create: `web/src/lib/api.ts`
- Create: `web/openapi-ts.config.ts`

**Step 1: Create openapi-ts config**

Create `web/openapi-ts.config.ts`:

```typescript
import { defineConfig } from "@hey-api/openapi-ts";

export default defineConfig({
  client: "@hey-api/client-fetch",
  input: "../api/openapi.json",
  output: {
    path: "src/lib/api/generated",
    format: "prettier",
  },
});
```

**Step 2: Generate API client (if openapi.json exists)**

Run: `cd web && pnpm generate-api` (skip if openapi.json doesn't exist yet)

**Step 3: Create API client configuration**

Create `web/src/lib/api/client.ts`:

```typescript
import { client } from "./generated/client.gen";
import { config } from "~/config";

let tokenGetter: (() => Promise<string | null>) | null = null;

export function setTokenGetter(getter: () => Promise<string | null>) {
  tokenGetter = getter;
}

// Configure base URL
client.setConfig({
  baseUrl: config.VITE_API_URL,
});

// Add auth interceptor
client.interceptors.request.use(async (request) => {
  if (tokenGetter) {
    const token = await tokenGetter();
    if (token) {
      request.headers.set("Authorization", `Bearer ${token}`);
    }
  }
  return request;
});

// Add 401 redirect interceptor
client.interceptors.response.use((response) => {
  if (response.status === 401 && window.location.pathname !== "/") {
    window.location.href = "/";
  }
  return response;
});

export { client };
```

**Step 4: Create typed API wrapper**

Create `web/src/lib/api.ts`:

```typescript
import { setTokenGetter } from "./api/client";
import type {
  User,
  Trader,
  TraderStatusResponse,
  CreateTraderRequest,
  SystemStats,
  LoginResponse,
  SetupStatusResponse,
  SSLStatusResponse,
} from "./types";
import { config } from "~/config";

const baseUrl = config.VITE_API_URL;

async function fetchJson<T>(
  path: string,
  options?: RequestInit
): Promise<T> {
  const token = localStorage.getItem("auth_token");
  const headers: HeadersInit = {
    "Content-Type": "application/json",
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...options?.headers,
  };

  const response = await fetch(`${baseUrl}${path}`, {
    ...options,
    headers,
  });

  if (!response.ok) {
    if (response.status === 401 && window.location.pathname !== "/") {
      window.location.href = "/";
    }
    const error = await response.json().catch(() => ({}));
    throw new Error(error.detail || `HTTP ${response.status}`);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return response.json();
}

export const api = {
  setAuthTokenGetter: setTokenGetter,

  // Auth
  async login(username: string, password: string): Promise<LoginResponse> {
    const formData = new URLSearchParams();
    formData.append("username", username);
    formData.append("password", password);

    const response = await fetch(`${baseUrl}/v1/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body: formData,
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      throw new Error(error.detail || "Login failed");
    }

    return response.json();
  },

  async logout(): Promise<void> {
    await fetchJson("/v1/auth/logout", { method: "POST" });
  },

  async me(): Promise<User> {
    return fetchJson("/v1/auth/me");
  },

  async getSetupStatus(): Promise<SetupStatusResponse> {
    return fetchJson("/v1/auth/setup-status");
  },

  async bootstrap(username: string, password: string): Promise<LoginResponse> {
    return fetchJson("/v1/auth/bootstrap", {
      method: "POST",
      body: JSON.stringify({ username, password }),
    });
  },

  // Traders
  async listTraders(): Promise<Trader[]> {
    return fetchJson("/v1/traders/");
  },

  async getTrader(id: string): Promise<Trader> {
    return fetchJson(`/v1/traders/${id}`);
  },

  async createTrader(data: CreateTraderRequest): Promise<Trader> {
    return fetchJson("/v1/traders/", {
      method: "POST",
      body: JSON.stringify(data),
    });
  },

  async deleteTrader(id: string): Promise<void> {
    return fetchJson(`/v1/traders/${id}`, { method: "DELETE" });
  },

  async restartTrader(id: string): Promise<void> {
    return fetchJson(`/v1/traders/${id}/restart`, { method: "POST" });
  },

  async getTraderStatus(id: string): Promise<TraderStatusResponse> {
    return fetchJson(`/v1/traders/${id}/status`);
  },

  async getTraderLogs(id: string, lines = 100): Promise<string[]> {
    return fetchJson(`/v1/traders/${id}/logs?lines=${lines}`);
  },

  // SSL Setup
  async getSSLStatus(): Promise<SSLStatusResponse> {
    return fetchJson("/v1/setup/ssl-status");
  },

  async configureSSL(mode: "domain" | "ip", domain?: string): Promise<void> {
    return fetchJson("/v1/setup/ssl", {
      method: "POST",
      body: JSON.stringify({ mode, domain }),
    });
  },

  // Admin
  async adminListUsers(skip = 0, limit = 100): Promise<User[]> {
    return fetchJson(`/v1/admin/users?skip=${skip}&limit=${limit}`);
  },

  async adminListTraders(skip = 0, limit = 100): Promise<Trader[]> {
    return fetchJson(`/v1/admin/traders?skip=${skip}&limit=${limit}`);
  },

  async adminGetStats(): Promise<SystemStats> {
    return fetchJson("/v1/admin/stats");
  },
};
```

**Step 5: Commit**

```bash
git add -A
git commit -m "feat: configure API client with typed wrapper"
```

---

## Phase 2: UI Components

### Task 2.1: Install shadcn-solid Base Components

**Files:**
- Create: `web/components.json`
- Create: `web/src/components/ui/button.tsx`
- Create: `web/src/components/ui/card.tsx`
- Create: `web/src/components/ui/input.tsx`
- Create: `web/src/components/ui/label.tsx`

**Step 1: Create components.json**

Create `web/components.json`:

```json
{
  "$schema": "https://shadcn-solid.com/schema.json",
  "tailwind": {
    "config": "",
    "css": "src/styles.css",
    "baseColor": "zinc"
  },
  "tsx": true,
  "componentDir": "src/components/ui"
}
```

**Step 2: Create button.tsx**

Create `web/src/components/ui/button.tsx`:

```typescript
import { type JSX, splitProps } from "solid-js";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "~/lib/utils";

const buttonVariants = cva(
  "inline-flex items-center justify-center whitespace-nowrap rounded-md text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:pointer-events-none disabled:opacity-50",
  {
    variants: {
      variant: {
        default: "bg-primary text-primary-foreground shadow hover:bg-primary/90",
        destructive: "bg-destructive text-destructive-foreground shadow-sm hover:bg-destructive/90",
        outline: "border border-input bg-background shadow-sm hover:bg-accent hover:text-accent-foreground",
        secondary: "bg-secondary text-secondary-foreground shadow-sm hover:bg-secondary/80",
        ghost: "hover:bg-accent hover:text-accent-foreground",
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
```

**Step 3: Create card.tsx**

Create `web/src/components/ui/card.tsx`:

```typescript
import { type JSX, splitProps } from "solid-js";
import { cn } from "~/lib/utils";

export function Card(props: JSX.HTMLAttributes<HTMLDivElement>) {
  const [local, others] = splitProps(props, ["class"]);
  return (
    <div
      class={cn("rounded-xl border bg-card text-card-foreground shadow", local.class)}
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
  return <h3 class={cn("font-semibold leading-none tracking-tight", local.class)} {...others} />;
}

export function CardDescription(props: JSX.HTMLAttributes<HTMLParagraphElement>) {
  const [local, others] = splitProps(props, ["class"]);
  return <p class={cn("text-sm text-muted-foreground", local.class)} {...others} />;
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

**Step 4: Create input.tsx**

Create `web/src/components/ui/input.tsx`:

```typescript
import { type JSX, splitProps } from "solid-js";
import { cn } from "~/lib/utils";

export interface InputProps extends JSX.InputHTMLAttributes<HTMLInputElement> {}

export function Input(props: InputProps) {
  const [local, others] = splitProps(props, ["class", "type"]);
  return (
    <input
      type={local.type}
      class={cn(
        "flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm transition-colors file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50",
        local.class
      )}
      {...others}
    />
  );
}
```

**Step 5: Create label.tsx**

Create `web/src/components/ui/label.tsx`:

```typescript
import { type JSX, splitProps } from "solid-js";
import { cn } from "~/lib/utils";

export interface LabelProps extends JSX.LabelHTMLAttributes<HTMLLabelElement> {}

export function Label(props: LabelProps) {
  const [local, others] = splitProps(props, ["class"]);
  return (
    <label
      class={cn(
        "text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70",
        local.class
      )}
      {...others}
    />
  );
}
```

**Step 6: Commit**

```bash
git add -A
git commit -m "feat: add base UI components (button, card, input, label)"
```

---

### Task 2.2: Add Remaining UI Components

**Files:**
- Create: `web/src/components/ui/alert.tsx`
- Create: `web/src/components/ui/badge.tsx`
- Create: `web/src/components/ui/skeleton.tsx`
- Create: `web/src/components/ui/separator.tsx`
- Create: `web/src/components/ui/table.tsx`

**Step 1: Create alert.tsx**

Create `web/src/components/ui/alert.tsx`:

```typescript
import { type JSX, splitProps } from "solid-js";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "~/lib/utils";

const alertVariants = cva(
  "relative w-full rounded-lg border px-4 py-3 text-sm [&>svg+div]:translate-y-[-3px] [&>svg]:absolute [&>svg]:left-4 [&>svg]:top-4 [&>svg]:text-foreground [&>svg~*]:pl-7",
  {
    variants: {
      variant: {
        default: "bg-background text-foreground",
        destructive: "border-destructive/50 text-destructive dark:border-destructive [&>svg]:text-destructive",
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

**Step 2: Create badge.tsx**

Create `web/src/components/ui/badge.tsx`:

```typescript
import { type JSX, splitProps } from "solid-js";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "~/lib/utils";

const badgeVariants = cva(
  "inline-flex items-center rounded-md border px-2.5 py-0.5 text-xs font-semibold transition-colors focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2",
  {
    variants: {
      variant: {
        default: "border-transparent bg-primary text-primary-foreground shadow hover:bg-primary/80",
        secondary: "border-transparent bg-secondary text-secondary-foreground hover:bg-secondary/80",
        destructive: "border-transparent bg-destructive text-destructive-foreground shadow hover:bg-destructive/80",
        outline: "text-foreground",
        success: "border-transparent bg-green-500/20 text-green-400",
        warning: "border-transparent bg-yellow-500/20 text-yellow-400",
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

**Step 3: Create skeleton.tsx**

Create `web/src/components/ui/skeleton.tsx`:

```typescript
import { type JSX, splitProps } from "solid-js";
import { cn } from "~/lib/utils";

export function Skeleton(props: JSX.HTMLAttributes<HTMLDivElement>) {
  const [local, others] = splitProps(props, ["class"]);
  return <div class={cn("animate-pulse rounded-md bg-primary/10", local.class)} {...others} />;
}
```

**Step 4: Create separator.tsx**

Create `web/src/components/ui/separator.tsx`:

```typescript
import { type JSX, splitProps } from "solid-js";
import { cn } from "~/lib/utils";

export interface SeparatorProps extends JSX.HTMLAttributes<HTMLDivElement> {
  orientation?: "horizontal" | "vertical";
  decorative?: boolean;
}

export function Separator(props: SeparatorProps) {
  const [local, others] = splitProps(props, ["class", "orientation", "decorative"]);
  const orientation = () => local.orientation ?? "horizontal";

  return (
    <div
      role={local.decorative ? "none" : "separator"}
      aria-orientation={local.decorative ? undefined : orientation()}
      class={cn(
        "shrink-0 bg-border",
        orientation() === "horizontal" ? "h-[1px] w-full" : "h-full w-[1px]",
        local.class
      )}
      {...others}
    />
  );
}
```

**Step 5: Create table.tsx**

Create `web/src/components/ui/table.tsx`:

```typescript
import { type JSX, splitProps } from "solid-js";
import { cn } from "~/lib/utils";

export function Table(props: JSX.HTMLAttributes<HTMLTableElement>) {
  const [local, others] = splitProps(props, ["class"]);
  return (
    <div class="relative w-full overflow-auto">
      <table class={cn("w-full caption-bottom text-sm", local.class)} {...others} />
    </div>
  );
}

export function TableHeader(props: JSX.HTMLAttributes<HTMLTableSectionElement>) {
  const [local, others] = splitProps(props, ["class"]);
  return <thead class={cn("[&_tr]:border-b", local.class)} {...others} />;
}

export function TableBody(props: JSX.HTMLAttributes<HTMLTableSectionElement>) {
  const [local, others] = splitProps(props, ["class"]);
  return <tbody class={cn("[&_tr:last-child]:border-0", local.class)} {...others} />;
}

export function TableFooter(props: JSX.HTMLAttributes<HTMLTableSectionElement>) {
  const [local, others] = splitProps(props, ["class"]);
  return <tfoot class={cn("border-t bg-muted/50 font-medium [&>tr]:last:border-b-0", local.class)} {...others} />;
}

export function TableRow(props: JSX.HTMLAttributes<HTMLTableRowElement>) {
  const [local, others] = splitProps(props, ["class"]);
  return (
    <tr
      class={cn("border-b transition-colors hover:bg-muted/50 data-[state=selected]:bg-muted", local.class)}
      {...others}
    />
  );
}

export function TableHead(props: JSX.ThHTMLAttributes<HTMLTableCellElement>) {
  const [local, others] = splitProps(props, ["class"]);
  return (
    <th
      class={cn(
        "h-10 px-2 text-left align-middle font-medium text-muted-foreground [&:has([role=checkbox])]:pr-0 [&>[role=checkbox]]:translate-y-[2px]",
        local.class
      )}
      {...others}
    />
  );
}

export function TableCell(props: JSX.TdHTMLAttributes<HTMLTableCellElement>) {
  const [local, others] = splitProps(props, ["class"]);
  return (
    <td
      class={cn("p-2 align-middle [&:has([role=checkbox])]:pr-0 [&>[role=checkbox]]:translate-y-[2px]", local.class)}
      {...others}
    />
  );
}

export function TableCaption(props: JSX.HTMLAttributes<HTMLTableCaptionElement>) {
  const [local, others] = splitProps(props, ["class"]);
  return <caption class={cn("mt-4 text-sm text-muted-foreground", local.class)} {...others} />;
}
```

**Step 6: Commit**

```bash
git add -A
git commit -m "feat: add alert, badge, skeleton, separator, and table components"
```

---

### Task 2.3: Add Kobalte-based Components

**Files:**
- Create: `web/src/components/ui/dialog.tsx`
- Create: `web/src/components/ui/alert-dialog.tsx`
- Create: `web/src/components/ui/dropdown-menu.tsx`
- Create: `web/src/components/ui/tabs.tsx`
- Create: `web/src/components/ui/tooltip.tsx`

**Step 1: Create dialog.tsx**

Create `web/src/components/ui/dialog.tsx`:

```typescript
import { Dialog as DialogPrimitive } from "@kobalte/core/dialog";
import { type JSX, splitProps } from "solid-js";
import { cn } from "~/lib/utils";

export const Dialog = DialogPrimitive;
export const DialogTrigger = DialogPrimitive.Trigger;
export const DialogClose = DialogPrimitive.CloseButton;

export function DialogPortal(props: DialogPrimitive.PortalProps) {
  return <DialogPrimitive.Portal {...props} />;
}

export function DialogOverlay(props: DialogPrimitive.OverlayProps) {
  const [local, others] = splitProps(props, ["class"]);
  return (
    <DialogPrimitive.Overlay
      class={cn(
        "fixed inset-0 z-50 bg-black/80 data-[expanded]:animate-in data-[closed]:animate-out data-[closed]:fade-out-0 data-[expanded]:fade-in-0",
        local.class
      )}
      {...others}
    />
  );
}

export function DialogContent(props: DialogPrimitive.ContentProps) {
  const [local, others] = splitProps(props, ["class", "children"]);
  return (
    <DialogPortal>
      <DialogOverlay />
      <DialogPrimitive.Content
        class={cn(
          "fixed left-1/2 top-1/2 z-50 grid w-full max-w-lg -translate-x-1/2 -translate-y-1/2 gap-4 border bg-background p-6 shadow-lg duration-200 data-[expanded]:animate-in data-[closed]:animate-out data-[closed]:fade-out-0 data-[expanded]:fade-in-0 data-[closed]:zoom-out-95 data-[expanded]:zoom-in-95 data-[closed]:slide-out-to-left-1/2 data-[closed]:slide-out-to-top-[48%] data-[expanded]:slide-in-from-left-1/2 data-[expanded]:slide-in-from-top-[48%] sm:rounded-lg",
          local.class
        )}
        {...others}
      >
        {local.children}
      </DialogPrimitive.Content>
    </DialogPortal>
  );
}

export function DialogHeader(props: JSX.HTMLAttributes<HTMLDivElement>) {
  const [local, others] = splitProps(props, ["class"]);
  return <div class={cn("flex flex-col space-y-1.5 text-center sm:text-left", local.class)} {...others} />;
}

export function DialogFooter(props: JSX.HTMLAttributes<HTMLDivElement>) {
  const [local, others] = splitProps(props, ["class"]);
  return <div class={cn("flex flex-col-reverse sm:flex-row sm:justify-end sm:space-x-2", local.class)} {...others} />;
}

export function DialogTitle(props: DialogPrimitive.TitleProps) {
  const [local, others] = splitProps(props, ["class"]);
  return <DialogPrimitive.Title class={cn("text-lg font-semibold leading-none tracking-tight", local.class)} {...others} />;
}

export function DialogDescription(props: DialogPrimitive.DescriptionProps) {
  const [local, others] = splitProps(props, ["class"]);
  return <DialogPrimitive.Description class={cn("text-sm text-muted-foreground", local.class)} {...others} />;
}
```

**Step 2: Create alert-dialog.tsx**

Create `web/src/components/ui/alert-dialog.tsx`:

```typescript
import { AlertDialog as AlertDialogPrimitive } from "@kobalte/core/alert-dialog";
import { type JSX, splitProps } from "solid-js";
import { cn } from "~/lib/utils";
import { buttonVariants } from "./button";

export const AlertDialog = AlertDialogPrimitive;
export const AlertDialogTrigger = AlertDialogPrimitive.Trigger;

export function AlertDialogPortal(props: AlertDialogPrimitive.PortalProps) {
  return <AlertDialogPrimitive.Portal {...props} />;
}

export function AlertDialogOverlay(props: AlertDialogPrimitive.OverlayProps) {
  const [local, others] = splitProps(props, ["class"]);
  return (
    <AlertDialogPrimitive.Overlay
      class={cn(
        "fixed inset-0 z-50 bg-black/80 data-[expanded]:animate-in data-[closed]:animate-out data-[closed]:fade-out-0 data-[expanded]:fade-in-0",
        local.class
      )}
      {...others}
    />
  );
}

export function AlertDialogContent(props: AlertDialogPrimitive.ContentProps) {
  const [local, others] = splitProps(props, ["class", "children"]);
  return (
    <AlertDialogPortal>
      <AlertDialogOverlay />
      <AlertDialogPrimitive.Content
        class={cn(
          "fixed left-1/2 top-1/2 z-50 grid w-full max-w-lg -translate-x-1/2 -translate-y-1/2 gap-4 border bg-background p-6 shadow-lg duration-200 data-[expanded]:animate-in data-[closed]:animate-out data-[closed]:fade-out-0 data-[expanded]:fade-in-0 data-[closed]:zoom-out-95 data-[expanded]:zoom-in-95 sm:rounded-lg",
          local.class
        )}
        {...others}
      >
        {local.children}
      </AlertDialogPrimitive.Content>
    </AlertDialogPortal>
  );
}

export function AlertDialogHeader(props: JSX.HTMLAttributes<HTMLDivElement>) {
  const [local, others] = splitProps(props, ["class"]);
  return <div class={cn("flex flex-col space-y-2 text-center sm:text-left", local.class)} {...others} />;
}

export function AlertDialogFooter(props: JSX.HTMLAttributes<HTMLDivElement>) {
  const [local, others] = splitProps(props, ["class"]);
  return <div class={cn("flex flex-col-reverse sm:flex-row sm:justify-end sm:space-x-2", local.class)} {...others} />;
}

export function AlertDialogTitle(props: AlertDialogPrimitive.TitleProps) {
  const [local, others] = splitProps(props, ["class"]);
  return <AlertDialogPrimitive.Title class={cn("text-lg font-semibold", local.class)} {...others} />;
}

export function AlertDialogDescription(props: AlertDialogPrimitive.DescriptionProps) {
  const [local, others] = splitProps(props, ["class"]);
  return <AlertDialogPrimitive.Description class={cn("text-sm text-muted-foreground", local.class)} {...others} />;
}

export function AlertDialogAction(props: AlertDialogPrimitive.CloseButtonProps) {
  const [local, others] = splitProps(props, ["class"]);
  return <AlertDialogPrimitive.CloseButton class={cn(buttonVariants(), local.class)} {...others} />;
}

export function AlertDialogCancel(props: AlertDialogPrimitive.CloseButtonProps) {
  const [local, others] = splitProps(props, ["class"]);
  return <AlertDialogPrimitive.CloseButton class={cn(buttonVariants({ variant: "outline" }), "mt-2 sm:mt-0", local.class)} {...others} />;
}
```

**Step 3: Create dropdown-menu.tsx**

Create `web/src/components/ui/dropdown-menu.tsx`:

```typescript
import { DropdownMenu as DropdownMenuPrimitive } from "@kobalte/core/dropdown-menu";
import { splitProps } from "solid-js";
import { cn } from "~/lib/utils";

export const DropdownMenu = DropdownMenuPrimitive;
export const DropdownMenuTrigger = DropdownMenuPrimitive.Trigger;
export const DropdownMenuGroup = DropdownMenuPrimitive.Group;
export const DropdownMenuSub = DropdownMenuPrimitive.Sub;
export const DropdownMenuRadioGroup = DropdownMenuPrimitive.RadioGroup;

export function DropdownMenuContent(props: DropdownMenuPrimitive.ContentProps) {
  const [local, others] = splitProps(props, ["class"]);
  return (
    <DropdownMenuPrimitive.Portal>
      <DropdownMenuPrimitive.Content
        class={cn(
          "z-50 min-w-[8rem] overflow-hidden rounded-md border bg-popover p-1 text-popover-foreground shadow-md data-[expanded]:animate-in data-[closed]:animate-out data-[closed]:fade-out-0 data-[expanded]:fade-in-0 data-[closed]:zoom-out-95 data-[expanded]:zoom-in-95",
          local.class
        )}
        {...others}
      />
    </DropdownMenuPrimitive.Portal>
  );
}

export function DropdownMenuItem(props: DropdownMenuPrimitive.ItemProps) {
  const [local, others] = splitProps(props, ["class"]);
  return (
    <DropdownMenuPrimitive.Item
      class={cn(
        "relative flex cursor-default select-none items-center rounded-sm px-2 py-1.5 text-sm outline-none transition-colors focus:bg-accent focus:text-accent-foreground data-[disabled]:pointer-events-none data-[disabled]:opacity-50",
        local.class
      )}
      {...others}
    />
  );
}

export function DropdownMenuSeparator(props: DropdownMenuPrimitive.SeparatorProps) {
  const [local, others] = splitProps(props, ["class"]);
  return <DropdownMenuPrimitive.Separator class={cn("-mx-1 my-1 h-px bg-muted", local.class)} {...others} />;
}

export function DropdownMenuLabel(props: DropdownMenuPrimitive.GroupLabelProps) {
  const [local, others] = splitProps(props, ["class"]);
  return <DropdownMenuPrimitive.GroupLabel class={cn("px-2 py-1.5 text-sm font-semibold", local.class)} {...others} />;
}
```

**Step 4: Create tabs.tsx**

Create `web/src/components/ui/tabs.tsx`:

```typescript
import { Tabs as TabsPrimitive } from "@kobalte/core/tabs";
import { splitProps } from "solid-js";
import { cn } from "~/lib/utils";

export const Tabs = TabsPrimitive;

export function TabsList(props: TabsPrimitive.ListProps) {
  const [local, others] = splitProps(props, ["class"]);
  return (
    <TabsPrimitive.List
      class={cn(
        "inline-flex h-9 items-center justify-center rounded-lg bg-muted p-1 text-muted-foreground",
        local.class
      )}
      {...others}
    />
  );
}

export function TabsTrigger(props: TabsPrimitive.TriggerProps) {
  const [local, others] = splitProps(props, ["class"]);
  return (
    <TabsPrimitive.Trigger
      class={cn(
        "inline-flex items-center justify-center whitespace-nowrap rounded-md px-3 py-1 text-sm font-medium ring-offset-background transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 data-[selected]:bg-background data-[selected]:text-foreground data-[selected]:shadow",
        local.class
      )}
      {...others}
    />
  );
}

export function TabsContent(props: TabsPrimitive.ContentProps) {
  const [local, others] = splitProps(props, ["class"]);
  return (
    <TabsPrimitive.Content
      class={cn(
        "mt-2 ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2",
        local.class
      )}
      {...others}
    />
  );
}
```

**Step 5: Create tooltip.tsx**

Create `web/src/components/ui/tooltip.tsx`:

```typescript
import { Tooltip as TooltipPrimitive } from "@kobalte/core/tooltip";
import { splitProps } from "solid-js";
import { cn } from "~/lib/utils";

export const Tooltip = TooltipPrimitive;
export const TooltipTrigger = TooltipPrimitive.Trigger;

export function TooltipContent(props: TooltipPrimitive.ContentProps) {
  const [local, others] = splitProps(props, ["class"]);
  return (
    <TooltipPrimitive.Portal>
      <TooltipPrimitive.Content
        class={cn(
          "z-50 overflow-hidden rounded-md bg-primary px-3 py-1.5 text-xs text-primary-foreground animate-in fade-in-0 zoom-in-95 data-[closed]:animate-out data-[closed]:fade-out-0 data-[closed]:zoom-out-95",
          local.class
        )}
        {...others}
      />
    </TooltipPrimitive.Portal>
  );
}
```

**Step 6: Commit**

```bash
git add -A
git commit -m "feat: add Kobalte-based dialog, alert-dialog, dropdown-menu, tabs, tooltip"
```

---

### Task 2.4: Create Component Index

**Files:**
- Create: `web/src/components/ui/index.ts`

**Step 1: Create index.ts**

Create `web/src/components/ui/index.ts`:

```typescript
export * from "./alert";
export * from "./alert-dialog";
export * from "./badge";
export * from "./button";
export * from "./card";
export * from "./dialog";
export * from "./dropdown-menu";
export * from "./input";
export * from "./label";
export * from "./separator";
export * from "./skeleton";
export * from "./table";
export * from "./tabs";
export * from "./tooltip";
```

**Step 2: Commit**

```bash
git add -A
git commit -m "feat: add UI component index for clean imports"
```

---

## Phase 3: Core Infrastructure

### Task 3.1: Create Auth Store

**Files:**
- Create: `web/src/stores/auth.ts`

**Step 1: Create auth.ts**

Create `web/src/stores/auth.ts`:

```typescript
import { createSignal, createRoot, createEffect } from "solid-js";
import { api } from "~/lib/api";
import type { User } from "~/lib/types";

function createAuthStore() {
  const [user, setUser] = createSignal<User | null>(null);
  const [token, setToken] = createSignal<string | null>(localStorage.getItem("auth_token"));
  const [loading, setLoading] = createSignal(true);
  const [isInitialized, setIsInitialized] = createSignal(false);

  const authenticated = () => !!user() && !!token();
  const ready = () => !loading();

  // Persist token to localStorage
  createEffect(() => {
    const currentToken = token();
    if (currentToken) {
      localStorage.setItem("auth_token", currentToken);
    } else {
      localStorage.removeItem("auth_token");
    }
  });

  async function checkSetup(): Promise<boolean> {
    try {
      const status = await api.getSetupStatus();
      setIsInitialized(status.initialized);
      return status.initialized;
    } catch {
      setIsInitialized(false);
      return false;
    }
  }

  async function checkAuth(): Promise<void> {
    const currentToken = token();
    if (!currentToken) {
      setLoading(false);
      return;
    }

    try {
      const userData = await api.me();
      setUser(userData);
    } catch {
      setToken(null);
      setUser(null);
    } finally {
      setLoading(false);
    }
  }

  async function login(username: string, password: string): Promise<void> {
    const response = await api.login(username, password);
    setToken(response.access_token);
    const userData = await api.me();
    setUser(userData);
  }

  async function logout(): Promise<void> {
    try {
      await api.logout();
    } finally {
      setToken(null);
      setUser(null);
    }
  }

  async function bootstrap(username: string, password: string): Promise<void> {
    const response = await api.bootstrap(username, password);
    setToken(response.access_token);
    setIsInitialized(true);
    const userData = await api.me();
    setUser(userData);
  }

  // Save return URL for redirect after login
  function saveReturnUrl(url: string): void {
    sessionStorage.setItem("auth_return_url", url);
  }

  function getReturnUrl(): string | null {
    const url = sessionStorage.getItem("auth_return_url");
    sessionStorage.removeItem("auth_return_url");
    return url;
  }

  return {
    user,
    token,
    loading,
    ready,
    authenticated,
    isInitialized,
    checkSetup,
    checkAuth,
    login,
    logout,
    bootstrap,
    saveReturnUrl,
    getReturnUrl,
  };
}

export const authStore = createRoot(createAuthStore);
```

**Step 2: Commit**

```bash
git add -A
git commit -m "feat: add signal-based auth store"
```

---

### Task 3.2: Setup Router and Query Provider

**Files:**
- Modify: `web/src/index.tsx`
- Modify: `web/src/App.tsx`

**Step 1: Update index.tsx with providers**

Replace `web/src/index.tsx`:

```typescript
/* @refresh reload */
import { render } from "solid-js/web";
import { Router } from "@solidjs/router";
import { QueryClient, QueryClientProvider } from "@tanstack/solid-query";
import "./styles.css";
import App from "./App";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 1000 * 60, // 1 minute
      retry: 1,
    },
  },
});

const root = document.getElementById("root");

if (!root) {
  throw new Error("Root element not found");
}

render(
  () => (
    <QueryClientProvider client={queryClient}>
      <Router>
        <App />
      </Router>
    </QueryClientProvider>
  ),
  root
);
```

**Step 2: Update App.tsx with routes**

Replace `web/src/App.tsx`:

```typescript
import { type Component, Suspense, onMount, createSignal } from "solid-js";
import { Route, Routes, Navigate } from "@solidjs/router";
import { authStore } from "~/stores/auth";

// Lazy load pages
import LoginPage from "~/routes/login";
import SetupPage from "~/routes/setup";
import SSLSetupPage from "~/routes/setup-ssl";
import DashboardPage from "~/routes/dashboard";
import SettingsPage from "~/routes/settings";
import TradersPage from "~/routes/traders";
import NewTraderPage from "~/routes/traders-new";
import TraderDetailPage from "~/routes/trader-detail";

// Loading screen component
function LoadingScreen() {
  return (
    <div class="min-h-screen flex items-center justify-center bg-background">
      <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
    </div>
  );
}

// Auth guard component
function AuthGuard(props: { children: any }) {
  return (
    <>
      {authStore.authenticated() ? (
        props.children
      ) : (
        <Navigate href="/" />
      )}
    </>
  );
}

const App: Component = () => {
  const [initialized, setInitialized] = createSignal(false);

  onMount(async () => {
    await authStore.checkSetup();
    await authStore.checkAuth();
    setInitialized(true);
  });

  return (
    <Suspense fallback={<LoadingScreen />}>
      {!initialized() ? (
        <LoadingScreen />
      ) : (
        <Routes>
          {/* Public routes */}
          <Route path="/" component={LoginPage} />
          <Route path="/setup" component={SetupPage} />
          <Route path="/setup/ssl" component={SSLSetupPage} />

          {/* Protected routes */}
          <Route path="/dashboard" component={() => <AuthGuard><DashboardPage /></AuthGuard>} />
          <Route path="/settings" component={() => <AuthGuard><SettingsPage /></AuthGuard>} />
          <Route path="/traders" component={() => <AuthGuard><TradersPage /></AuthGuard>} />
          <Route path="/traders/new" component={() => <AuthGuard><NewTraderPage /></AuthGuard>} />
          <Route path="/traders/:id" component={() => <AuthGuard><TraderDetailPage /></AuthGuard>} />
        </Routes>
      )}
    </Suspense>
  );
};

export default App;
```

**Step 3: Commit**

```bash
git add -A
git commit -m "feat: setup router and query client providers"
```

---

## Phase 4: Pages

### Task 4.1: Create Login Page

**Files:**
- Create: `web/src/routes/login.tsx`
- Create: `web/src/components/auth/LoginForm.tsx`

**Step 1: Create LoginForm.tsx**

Create `web/src/components/auth/LoginForm.tsx`:

```typescript
import { createSignal } from "solid-js";
import { useNavigate } from "@solidjs/router";
import { Button } from "~/components/ui/button";
import { Input } from "~/components/ui/input";
import { Label } from "~/components/ui/label";
import { Alert, AlertDescription } from "~/components/ui/alert";
import { authStore } from "~/stores/auth";

export function LoginForm() {
  const navigate = useNavigate();
  const [username, setUsername] = createSignal("");
  const [password, setPassword] = createSignal("");
  const [error, setError] = createSignal<string | null>(null);
  const [loading, setLoading] = createSignal(false);

  async function handleSubmit(e: Event) {
    e.preventDefault();
    setError(null);
    setLoading(true);

    try {
      await authStore.login(username(), password());
      const returnUrl = authStore.getReturnUrl() || "/dashboard";
      navigate(returnUrl);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Login failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} class="space-y-4">
      {error() && (
        <Alert variant="destructive">
          <AlertDescription>{error()}</AlertDescription>
        </Alert>
      )}

      <div class="space-y-2">
        <Label for="username">Username</Label>
        <Input
          id="username"
          type="text"
          value={username()}
          onInput={(e) => setUsername(e.currentTarget.value)}
          placeholder="Enter username"
          required
        />
      </div>

      <div class="space-y-2">
        <Label for="password">Password</Label>
        <Input
          id="password"
          type="password"
          value={password()}
          onInput={(e) => setPassword(e.currentTarget.value)}
          placeholder="Enter password"
          required
        />
      </div>

      <Button type="submit" class="w-full" disabled={loading()}>
        {loading() ? "Signing in..." : "Sign In"}
      </Button>
    </form>
  );
}
```

**Step 2: Create login.tsx page**

Create `web/src/routes/login.tsx`:

```typescript
import { type Component, Show } from "solid-js";
import { Navigate } from "@solidjs/router";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "~/components/ui/card";
import { LoginForm } from "~/components/auth/LoginForm";
import { authStore } from "~/stores/auth";

const LoginPage: Component = () => {
  // Redirect to setup if not initialized
  if (!authStore.isInitialized()) {
    return <Navigate href="/setup" />;
  }

  // Redirect to dashboard if already authenticated
  if (authStore.authenticated()) {
    return <Navigate href="/dashboard" />;
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
};

export default LoginPage;
```

**Step 3: Commit**

```bash
git add -A
git commit -m "feat: add login page with LoginForm component"
```

---

### Task 4.2: Create Setup Pages

**Files:**
- Create: `web/src/routes/setup.tsx`
- Create: `web/src/routes/setup-ssl.tsx`
- Create: `web/src/components/auth/BootstrapForm.tsx`

**Step 1: Create BootstrapForm.tsx**

Create `web/src/components/auth/BootstrapForm.tsx`:

```typescript
import { createSignal } from "solid-js";
import { useNavigate } from "@solidjs/router";
import { Button } from "~/components/ui/button";
import { Input } from "~/components/ui/input";
import { Label } from "~/components/ui/label";
import { Alert, AlertDescription } from "~/components/ui/alert";
import { authStore } from "~/stores/auth";

export function BootstrapForm() {
  const navigate = useNavigate();
  const [username, setUsername] = createSignal("");
  const [password, setPassword] = createSignal("");
  const [confirmPassword, setConfirmPassword] = createSignal("");
  const [error, setError] = createSignal<string | null>(null);
  const [loading, setLoading] = createSignal(false);

  async function handleSubmit(e: Event) {
    e.preventDefault();
    setError(null);

    if (password() !== confirmPassword()) {
      setError("Passwords do not match");
      return;
    }

    if (password().length < 8) {
      setError("Password must be at least 8 characters");
      return;
    }

    setLoading(true);

    try {
      await authStore.bootstrap(username(), password());
      navigate("/dashboard");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Setup failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} class="space-y-4">
      {error() && (
        <Alert variant="destructive">
          <AlertDescription>{error()}</AlertDescription>
        </Alert>
      )}

      <div class="space-y-2">
        <Label for="username">Admin Username</Label>
        <Input
          id="username"
          type="text"
          value={username()}
          onInput={(e) => setUsername(e.currentTarget.value)}
          placeholder="Enter admin username"
          required
        />
      </div>

      <div class="space-y-2">
        <Label for="password">Password</Label>
        <Input
          id="password"
          type="password"
          value={password()}
          onInput={(e) => setPassword(e.currentTarget.value)}
          placeholder="Enter password (min 8 characters)"
          required
        />
      </div>

      <div class="space-y-2">
        <Label for="confirmPassword">Confirm Password</Label>
        <Input
          id="confirmPassword"
          type="password"
          value={confirmPassword()}
          onInput={(e) => setConfirmPassword(e.currentTarget.value)}
          placeholder="Confirm password"
          required
        />
      </div>

      <Button type="submit" class="w-full" disabled={loading()}>
        {loading() ? "Creating account..." : "Create Admin Account"}
      </Button>
    </form>
  );
}
```

**Step 2: Create setup.tsx page**

Create `web/src/routes/setup.tsx`:

```typescript
import { type Component } from "solid-js";
import { Navigate } from "@solidjs/router";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "~/components/ui/card";
import { BootstrapForm } from "~/components/auth/BootstrapForm";
import { authStore } from "~/stores/auth";

const SetupPage: Component = () => {
  // Redirect to login if already initialized
  if (authStore.isInitialized()) {
    return <Navigate href="/" />;
  }

  return (
    <div class="min-h-screen flex items-center justify-center bg-background p-4">
      <Card class="w-full max-w-md">
        <CardHeader class="text-center">
          <CardTitle class="text-2xl">Welcome to Hyper Trader</CardTitle>
          <CardDescription>Create your admin account to get started</CardDescription>
        </CardHeader>
        <CardContent>
          <BootstrapForm />
        </CardContent>
      </Card>
    </div>
  );
};

export default SetupPage;
```

**Step 3: Create setup-ssl.tsx page**

Create `web/src/routes/setup-ssl.tsx`:

```typescript
import { type Component, createSignal } from "solid-js";
import { useNavigate } from "@solidjs/router";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "~/components/ui/card";
import { Button } from "~/components/ui/button";
import { Input } from "~/components/ui/input";
import { Label } from "~/components/ui/label";
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
    <div class="min-h-screen flex items-center justify-center bg-background p-4">
      <Card class="w-full max-w-md">
        <CardHeader class="text-center">
          <CardTitle class="text-2xl">SSL Configuration</CardTitle>
          <CardDescription>Configure SSL for secure connections</CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} class="space-y-4">
            {error() && (
              <Alert variant="destructive">
                <AlertDescription>{error()}</AlertDescription>
              </Alert>
            )}

            <div class="space-y-2">
              <Label>SSL Mode</Label>
              <div class="flex gap-4">
                <label class="flex items-center gap-2">
                  <input
                    type="radio"
                    name="mode"
                    value="domain"
                    checked={mode() === "domain"}
                    onChange={() => setMode("domain")}
                    class="text-primary"
                  />
                  Domain (Let's Encrypt)
                </label>
                <label class="flex items-center gap-2">
                  <input
                    type="radio"
                    name="mode"
                    value="ip"
                    checked={mode() === "ip"}
                    onChange={() => setMode("ip")}
                    class="text-primary"
                  />
                  IP Only (Self-signed)
                </label>
              </div>
            </div>

            {mode() === "domain" && (
              <div class="space-y-2">
                <Label for="domain">Domain Name</Label>
                <Input
                  id="domain"
                  type="text"
                  value={domain()}
                  onInput={(e) => setDomain(e.currentTarget.value)}
                  placeholder="example.com"
                  required
                />
              </div>
            )}

            <Button type="submit" class="w-full" disabled={loading()}>
              {loading() ? "Configuring..." : "Configure SSL"}
            </Button>
          </form>
        </CardContent>
      </Card>
    </div>
  );
};

export default SSLSetupPage;
```

**Step 4: Commit**

```bash
git add -A
git commit -m "feat: add setup and SSL configuration pages"
```

---

### Task 4.3: Create Layout Components

**Files:**
- Create: `web/src/components/layout/AppShell.tsx`
- Create: `web/src/components/layout/Sidebar.tsx`

**Step 1: Create Sidebar.tsx**

Create `web/src/components/layout/Sidebar.tsx`:

```typescript
import { type Component, Show, createSignal } from "solid-js";
import { A, useLocation, useNavigate } from "@solidjs/router";
import { LayoutDashboard, Bot, Settings, LogOut, Menu, X } from "lucide-solid";
import { Button } from "~/components/ui/button";
import { Separator } from "~/components/ui/separator";
import { authStore } from "~/stores/auth";
import { cn } from "~/lib/utils";

const navItems = [
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { href: "/traders", label: "Traders", icon: Bot },
  { href: "/settings", label: "Settings", icon: Settings },
];

export const Sidebar: Component = () => {
  const location = useLocation();
  const navigate = useNavigate();
  const [mobileOpen, setMobileOpen] = createSignal(false);

  async function handleLogout() {
    await authStore.logout();
    navigate("/");
  }

  const NavContent = () => (
    <div class="flex flex-col h-full">
      <div class="p-4">
        <h1 class="text-lg font-bold">Hyper Trader</h1>
      </div>

      <Separator />

      <nav class="flex-1 p-4 space-y-1">
        {navItems.map((item) => (
          <A
            href={item.href}
            class={cn(
              "flex items-center gap-3 px-3 py-2 rounded-md text-sm transition-colors",
              location.pathname === item.href || location.pathname.startsWith(item.href + "/")
                ? "bg-secondary text-secondary-foreground"
                : "hover:bg-secondary/50"
            )}
            onClick={() => setMobileOpen(false)}
          >
            <item.icon class="h-4 w-4" />
            {item.label}
          </A>
        ))}
      </nav>

      <Separator />

      <div class="p-4">
        <div class="flex items-center gap-3 mb-4">
          <div class="h-8 w-8 rounded-full bg-primary/20 flex items-center justify-center text-sm font-medium">
            {authStore.user()?.username?.charAt(0).toUpperCase()}
          </div>
          <div class="flex-1 truncate">
            <p class="text-sm font-medium truncate">{authStore.user()?.username}</p>
            <Show when={authStore.user()?.is_admin}>
              <p class="text-xs text-muted-foreground">Admin</p>
            </Show>
          </div>
        </div>

        <Button variant="outline" class="w-full" onClick={handleLogout}>
          <LogOut class="h-4 w-4 mr-2" />
          Sign Out
        </Button>
      </div>
    </div>
  );

  return (
    <>
      {/* Mobile menu button */}
      <div class="lg:hidden fixed top-4 left-4 z-50">
        <Button variant="outline" size="icon" onClick={() => setMobileOpen(!mobileOpen())}>
          <Show when={mobileOpen()} fallback={<Menu class="h-4 w-4" />}>
            <X class="h-4 w-4" />
          </Show>
        </Button>
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
          "lg:hidden fixed inset-y-0 left-0 z-40 w-64 bg-background border-r transform transition-transform duration-200",
          mobileOpen() ? "translate-x-0" : "-translate-x-full"
        )}
      >
        <NavContent />
      </aside>

      {/* Desktop sidebar */}
      <aside class="hidden lg:flex lg:w-64 lg:flex-col lg:fixed lg:inset-y-0 border-r bg-background">
        <NavContent />
      </aside>
    </>
  );
};
```

**Step 2: Create AppShell.tsx**

Create `web/src/components/layout/AppShell.tsx`:

```typescript
import { type Component, type JSX } from "solid-js";
import { Sidebar } from "./Sidebar";

interface AppShellProps {
  children: JSX.Element;
}

export const AppShell: Component<AppShellProps> = (props) => {
  return (
    <div class="min-h-screen bg-background">
      <Sidebar />
      <main class="lg:pl-64">
        <div class="p-6 lg:p-8">{props.children}</div>
      </main>
    </div>
  );
};
```

**Step 3: Commit**

```bash
git add -A
git commit -m "feat: add AppShell and Sidebar layout components"
```

---

### Task 4.4: Create Dashboard Page

**Files:**
- Create: `web/src/routes/dashboard.tsx`

**Step 1: Create dashboard.tsx**

Create `web/src/routes/dashboard.tsx`:

```typescript
import { type Component, Show, For, Suspense } from "solid-js";
import { createQuery } from "@tanstack/solid-query";
import { A } from "@solidjs/router";
import { Plus } from "lucide-solid";
import { AppShell } from "~/components/layout/AppShell";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "~/components/ui/card";
import { Button } from "~/components/ui/button";
import { Badge } from "~/components/ui/badge";
import { Skeleton } from "~/components/ui/skeleton";
import { api } from "~/lib/api";
import { traderKeys } from "~/lib/query-keys";
import type { Trader } from "~/lib/types";

function StatusBadge(props: { status: Trader["status"] }) {
  const variant = () => {
    switch (props.status) {
      case "running":
        return "success";
      case "stopped":
        return "secondary";
      case "error":
        return "destructive";
      default:
        return "outline";
    }
  };

  return <Badge variant={variant()}>{props.status}</Badge>;
}

function TraderCard(props: { trader: Trader }) {
  return (
    <A href={`/traders/${props.trader.id}`}>
      <Card class="hover:bg-secondary/50 transition-colors cursor-pointer">
        <CardHeader class="pb-2">
          <div class="flex items-center justify-between">
            <CardTitle class="text-lg">{props.trader.name}</CardTitle>
            <StatusBadge status={props.trader.status} />
          </div>
          <CardDescription class="font-mono text-xs truncate">
            {props.trader.wallet_address}
          </CardDescription>
        </CardHeader>
        <CardContent>
          <p class="text-sm text-muted-foreground">
            Created {new Date(props.trader.created_at).toLocaleDateString()}
          </p>
        </CardContent>
      </Card>
    </A>
  );
}

function LoadingSkeleton() {
  return (
    <div class="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
      <For each={[1, 2, 3]}>
        {() => (
          <Card>
            <CardHeader>
              <Skeleton class="h-6 w-32" />
              <Skeleton class="h-4 w-48 mt-2" />
            </CardHeader>
            <CardContent>
              <Skeleton class="h-4 w-24" />
            </CardContent>
          </Card>
        )}
      </For>
    </div>
  );
}

const DashboardPage: Component = () => {
  const tradersQuery = createQuery(() => ({
    queryKey: traderKeys.lists(),
    queryFn: () => api.listTraders(),
  }));

  return (
    <AppShell>
      <div class="space-y-6">
        <div class="flex items-center justify-between">
          <div>
            <h1 class="text-2xl font-bold">Dashboard</h1>
            <p class="text-muted-foreground">Manage your trading bots</p>
          </div>
          <A href="/traders/new">
            <Button>
              <Plus class="h-4 w-4 mr-2" />
              New Trader
            </Button>
          </A>
        </div>

        <Suspense fallback={<LoadingSkeleton />}>
          <Show
            when={tradersQuery.data && tradersQuery.data.length > 0}
            fallback={
              <Card>
                <CardContent class="py-12 text-center">
                  <p class="text-muted-foreground mb-4">No traders yet</p>
                  <A href="/traders/new">
                    <Button>Create your first trader</Button>
                  </A>
                </CardContent>
              </Card>
            }
          >
            <div class="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
              <For each={tradersQuery.data}>
                {(trader) => <TraderCard trader={trader} />}
              </For>
            </div>
          </Show>
        </Suspense>
      </div>
    </AppShell>
  );
};

export default DashboardPage;
```

**Step 2: Commit**

```bash
git add -A
git commit -m "feat: add dashboard page with trader cards"
```

---

### Task 4.5: Create Traders List Page

**Files:**
- Create: `web/src/routes/traders.tsx`

**Step 1: Create traders.tsx**

Create `web/src/routes/traders.tsx`:

```typescript
import { type Component, Show, For, Suspense } from "solid-js";
import { createQuery } from "@tanstack/solid-query";
import { A } from "@solidjs/router";
import { Plus } from "lucide-solid";
import { AppShell } from "~/components/layout/AppShell";
import { Button } from "~/components/ui/button";
import { Badge } from "~/components/ui/badge";
import { Skeleton } from "~/components/ui/skeleton";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "~/components/ui/table";
import { api } from "~/lib/api";
import { traderKeys } from "~/lib/query-keys";
import type { Trader } from "~/lib/types";

function StatusBadge(props: { status: Trader["status"] }) {
  const variant = () => {
    switch (props.status) {
      case "running":
        return "success";
      case "stopped":
        return "secondary";
      case "error":
        return "destructive";
      default:
        return "outline";
    }
  };

  return <Badge variant={variant()}>{props.status}</Badge>;
}

function LoadingSkeleton() {
  return (
    <div class="space-y-2">
      <For each={[1, 2, 3, 4, 5]}>
        {() => <Skeleton class="h-12 w-full" />}
      </For>
    </div>
  );
}

const TradersPage: Component = () => {
  const tradersQuery = createQuery(() => ({
    queryKey: traderKeys.lists(),
    queryFn: () => api.listTraders(),
  }));

  return (
    <AppShell>
      <div class="space-y-6">
        <div class="flex items-center justify-between">
          <div>
            <h1 class="text-2xl font-bold">Traders</h1>
            <p class="text-muted-foreground">All your trading bots</p>
          </div>
          <A href="/traders/new">
            <Button>
              <Plus class="h-4 w-4 mr-2" />
              New Trader
            </Button>
          </A>
        </div>

        <Suspense fallback={<LoadingSkeleton />}>
          <Show
            when={tradersQuery.data && tradersQuery.data.length > 0}
            fallback={
              <div class="text-center py-12 text-muted-foreground">
                <p class="mb-4">No traders found</p>
                <A href="/traders/new">
                  <Button>Create your first trader</Button>
                </A>
              </div>
            }
          >
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Name</TableHead>
                  <TableHead>Wallet</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Created</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                <For each={tradersQuery.data}>
                  {(trader) => (
                    <TableRow>
                      <TableCell>
                        <A
                          href={`/traders/${trader.id}`}
                          class="font-medium hover:underline"
                        >
                          {trader.name}
                        </A>
                      </TableCell>
                      <TableCell class="font-mono text-xs truncate max-w-[200px]">
                        {trader.wallet_address}
                      </TableCell>
                      <TableCell>
                        <StatusBadge status={trader.status} />
                      </TableCell>
                      <TableCell>
                        {new Date(trader.created_at).toLocaleDateString()}
                      </TableCell>
                    </TableRow>
                  )}
                </For>
              </TableBody>
            </Table>
          </Show>
        </Suspense>
      </div>
    </AppShell>
  );
};

export default TradersPage;
```

**Step 2: Commit**

```bash
git add -A
git commit -m "feat: add traders list page with table view"
```

---

### Task 4.6: Create New Trader Page

**Files:**
- Create: `web/src/routes/traders-new.tsx`

**Step 1: Create traders-new.tsx**

Create `web/src/routes/traders-new.tsx`:

```typescript
import { type Component, createSignal } from "solid-js";
import { useNavigate } from "@solidjs/router";
import { createMutation, useQueryClient } from "@tanstack/solid-query";
import { AppShell } from "~/components/layout/AppShell";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "~/components/ui/card";
import { Button } from "~/components/ui/button";
import { Input } from "~/components/ui/input";
import { Label } from "~/components/ui/label";
import { Alert, AlertDescription } from "~/components/ui/alert";
import { api } from "~/lib/api";
import { traderKeys } from "~/lib/query-keys";

const NewTraderPage: Component = () => {
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const [name, setName] = createSignal("");
  const [walletAddress, setWalletAddress] = createSignal("");
  const [privateKey, setPrivateKey] = createSignal("");
  const [error, setError] = createSignal<string | null>(null);

  const createMutation = createMutation(() => ({
    mutationFn: () =>
      api.createTrader({
        name: name(),
        wallet_address: walletAddress(),
        private_key: privateKey(),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: traderKeys.all });
      navigate("/traders");
    },
    onError: (err: Error) => {
      setError(err.message);
    },
  }));

  function handleSubmit(e: Event) {
    e.preventDefault();
    setError(null);

    // Basic validation
    if (!name().trim()) {
      setError("Name is required");
      return;
    }

    // Validate Ethereum address format
    const addressRegex = /^0x[a-fA-F0-9]{40}$/;
    if (!addressRegex.test(walletAddress())) {
      setError("Invalid Ethereum wallet address");
      return;
    }

    if (!privateKey().trim()) {
      setError("Private key is required");
      return;
    }

    createMutation.mutate();
  }

  return (
    <AppShell>
      <div class="max-w-2xl mx-auto">
        <Card>
          <CardHeader>
            <CardTitle>Create New Trader</CardTitle>
            <CardDescription>
              Set up a new trading bot with your wallet credentials
            </CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSubmit} class="space-y-4">
              {error() && (
                <Alert variant="destructive">
                  <AlertDescription>{error()}</AlertDescription>
                </Alert>
              )}

              <div class="space-y-2">
                <Label for="name">Trader Name</Label>
                <Input
                  id="name"
                  type="text"
                  value={name()}
                  onInput={(e) => setName(e.currentTarget.value)}
                  placeholder="My Trading Bot"
                  required
                />
              </div>

              <div class="space-y-2">
                <Label for="walletAddress">Wallet Address</Label>
                <Input
                  id="walletAddress"
                  type="text"
                  value={walletAddress()}
                  onInput={(e) => setWalletAddress(e.currentTarget.value)}
                  placeholder="0x..."
                  class="font-mono"
                  required
                />
              </div>

              <div class="space-y-2">
                <Label for="privateKey">Private Key</Label>
                <Input
                  id="privateKey"
                  type="password"
                  value={privateKey()}
                  onInput={(e) => setPrivateKey(e.currentTarget.value)}
                  placeholder="Enter private key"
                  class="font-mono"
                  required
                />
                <p class="text-xs text-muted-foreground">
                  Your private key is encrypted and stored securely
                </p>
              </div>

              <div class="flex gap-4 pt-4">
                <Button
                  type="button"
                  variant="outline"
                  onClick={() => navigate("/traders")}
                >
                  Cancel
                </Button>
                <Button type="submit" disabled={createMutation.isPending}>
                  {createMutation.isPending ? "Creating..." : "Create Trader"}
                </Button>
              </div>
            </form>
          </CardContent>
        </Card>
      </div>
    </AppShell>
  );
};

export default NewTraderPage;
```

**Step 2: Commit**

```bash
git add -A
git commit -m "feat: add new trader creation page"
```

---

### Task 4.7: Create Trader Detail Page

**Files:**
- Create: `web/src/routes/trader-detail.tsx`
- Create: `web/src/components/traders/LogViewer.tsx`

**Step 1: Create LogViewer.tsx**

Create `web/src/components/traders/LogViewer.tsx`:

```typescript
import { type Component, For, createSignal } from "solid-js";
import { createQuery } from "@tanstack/solid-query";
import { RefreshCw } from "lucide-solid";
import { Button } from "~/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "~/components/ui/card";
import { Skeleton } from "~/components/ui/skeleton";
import { api } from "~/lib/api";
import { traderKeys } from "~/lib/query-keys";

interface LogViewerProps {
  traderId: string;
}

export const LogViewer: Component<LogViewerProps> = (props) => {
  const [lines, setLines] = createSignal(100);

  const logsQuery = createQuery(() => ({
    queryKey: traderKeys.logs(props.traderId),
    queryFn: () => api.getTraderLogs(props.traderId, lines()),
    refetchInterval: 5000, // Auto-refresh every 5 seconds
  }));

  return (
    <Card>
      <CardHeader class="flex flex-row items-center justify-between">
        <CardTitle>Logs</CardTitle>
        <Button
          variant="outline"
          size="sm"
          onClick={() => logsQuery.refetch()}
          disabled={logsQuery.isFetching}
        >
          <RefreshCw class={`h-4 w-4 mr-2 ${logsQuery.isFetching ? "animate-spin" : ""}`} />
          Refresh
        </Button>
      </CardHeader>
      <CardContent>
        {logsQuery.isLoading ? (
          <div class="space-y-2">
            <For each={[1, 2, 3, 4, 5]}>
              {() => <Skeleton class="h-4 w-full" />}
            </For>
          </div>
        ) : (
          <div class="bg-muted rounded-md p-4 max-h-96 overflow-auto">
            <pre class="text-xs font-mono whitespace-pre-wrap">
              {logsQuery.data?.length ? (
                <For each={logsQuery.data}>
                  {(line) => <div>{line}</div>}
                </For>
              ) : (
                <span class="text-muted-foreground">No logs available</span>
              )}
            </pre>
          </div>
        )}
      </CardContent>
    </Card>
  );
};
```

**Step 2: Create trader-detail.tsx**

Create `web/src/routes/trader-detail.tsx`:

```typescript
import { type Component, Show, Suspense, createSignal } from "solid-js";
import { useParams, useNavigate } from "@solidjs/router";
import { createQuery, createMutation, useQueryClient } from "@tanstack/solid-query";
import { Play, Trash2, RefreshCw } from "lucide-solid";
import { AppShell } from "~/components/layout/AppShell";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "~/components/ui/card";
import { Button } from "~/components/ui/button";
import { Badge } from "~/components/ui/badge";
import { Skeleton } from "~/components/ui/skeleton";
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
import { LogViewer } from "~/components/traders/LogViewer";
import { api } from "~/lib/api";
import { traderKeys } from "~/lib/query-keys";
import type { Trader } from "~/lib/types";

function StatusBadge(props: { status: Trader["status"] }) {
  const variant = () => {
    switch (props.status) {
      case "running":
        return "success";
      case "stopped":
        return "secondary";
      case "error":
        return "destructive";
      default:
        return "outline";
    }
  };

  return <Badge variant={variant()}>{props.status}</Badge>;
}

function LoadingSkeleton() {
  return (
    <div class="space-y-6">
      <Skeleton class="h-8 w-48" />
      <Card>
        <CardHeader>
          <Skeleton class="h-6 w-32" />
        </CardHeader>
        <CardContent class="space-y-4">
          <Skeleton class="h-4 w-full" />
          <Skeleton class="h-4 w-3/4" />
        </CardContent>
      </Card>
    </div>
  );
}

const TraderDetailPage: Component = () => {
  const params = useParams<{ id: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [deleteOpen, setDeleteOpen] = createSignal(false);

  const traderQuery = createQuery(() => ({
    queryKey: traderKeys.detail(params.id),
    queryFn: () => api.getTrader(params.id),
  }));

  const statusQuery = createQuery(() => ({
    queryKey: traderKeys.status(params.id),
    queryFn: () => api.getTraderStatus(params.id),
    refetchInterval: 10000,
  }));

  const restartMutation = createMutation(() => ({
    mutationFn: () => api.restartTrader(params.id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: traderKeys.detail(params.id) });
      queryClient.invalidateQueries({ queryKey: traderKeys.status(params.id) });
    },
  }));

  const deleteMutation = createMutation(() => ({
    mutationFn: () => api.deleteTrader(params.id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: traderKeys.all });
      navigate("/traders");
    },
  }));

  return (
    <AppShell>
      <Suspense fallback={<LoadingSkeleton />}>
        <Show when={traderQuery.data}>
          {(trader) => (
            <div class="space-y-6">
              <div class="flex items-center justify-between">
                <div>
                  <h1 class="text-2xl font-bold">{trader().name}</h1>
                  <p class="text-muted-foreground font-mono text-sm">
                    {trader().wallet_address}
                  </p>
                </div>
                <div class="flex items-center gap-2">
                  <Button
                    variant="outline"
                    onClick={() => restartMutation.mutate()}
                    disabled={restartMutation.isPending}
                  >
                    <RefreshCw class={`h-4 w-4 mr-2 ${restartMutation.isPending ? "animate-spin" : ""}`} />
                    Restart
                  </Button>

                  <AlertDialog open={deleteOpen()} onOpenChange={setDeleteOpen}>
                    <AlertDialogTrigger as={Button} variant="destructive">
                      <Trash2 class="h-4 w-4 mr-2" />
                      Delete
                    </AlertDialogTrigger>
                    <AlertDialogContent>
                      <AlertDialogHeader>
                        <AlertDialogTitle>Delete Trader</AlertDialogTitle>
                        <AlertDialogDescription>
                          Are you sure you want to delete "{trader().name}"? This action cannot be undone.
                        </AlertDialogDescription>
                      </AlertDialogHeader>
                      <AlertDialogFooter>
                        <AlertDialogCancel>Cancel</AlertDialogCancel>
                        <AlertDialogAction
                          onClick={() => deleteMutation.mutate()}
                        >
                          {deleteMutation.isPending ? "Deleting..." : "Delete"}
                        </AlertDialogAction>
                      </AlertDialogFooter>
                    </AlertDialogContent>
                  </AlertDialog>
                </div>
              </div>

              <div class="grid gap-6 md:grid-cols-2">
                <Card>
                  <CardHeader>
                    <CardTitle>Status</CardTitle>
                  </CardHeader>
                  <CardContent class="space-y-4">
                    <div class="flex items-center justify-between">
                      <span class="text-muted-foreground">Current Status</span>
                      <StatusBadge status={trader().status} />
                    </div>
                    <Show when={statusQuery.data?.uptime_seconds}>
                      <div class="flex items-center justify-between">
                        <span class="text-muted-foreground">Uptime</span>
                        <span>{Math.floor(statusQuery.data!.uptime_seconds! / 60)} minutes</span>
                      </div>
                    </Show>
                    <Show when={statusQuery.data?.last_error}>
                      <div class="pt-2 border-t">
                        <span class="text-muted-foreground text-sm">Last Error:</span>
                        <p class="text-destructive text-sm mt-1">{statusQuery.data!.last_error}</p>
                      </div>
                    </Show>
                  </CardContent>
                </Card>

                <Card>
                  <CardHeader>
                    <CardTitle>Details</CardTitle>
                  </CardHeader>
                  <CardContent class="space-y-4">
                    <div class="flex items-center justify-between">
                      <span class="text-muted-foreground">Created</span>
                      <span>{new Date(trader().created_at).toLocaleString()}</span>
                    </div>
                    <div class="flex items-center justify-between">
                      <span class="text-muted-foreground">Last Updated</span>
                      <span>{new Date(trader().updated_at).toLocaleString()}</span>
                    </div>
                  </CardContent>
                </Card>
              </div>

              <LogViewer traderId={params.id} />
            </div>
          )}
        </Show>
      </Suspense>
    </AppShell>
  );
};

export default TraderDetailPage;
```

**Step 3: Commit**

```bash
git add -A
git commit -m "feat: add trader detail page with logs and status"
```

---

### Task 4.8: Create Settings Page

**Files:**
- Create: `web/src/routes/settings.tsx`

**Step 1: Create settings.tsx**

Create `web/src/routes/settings.tsx`:

```typescript
import { type Component, Show } from "solid-js";
import { AppShell } from "~/components/layout/AppShell";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "~/components/ui/card";
import { Badge } from "~/components/ui/badge";
import { Separator } from "~/components/ui/separator";
import { authStore } from "~/stores/auth";

const SettingsPage: Component = () => {
  const user = () => authStore.user();

  return (
    <AppShell>
      <div class="space-y-6 max-w-2xl">
        <div>
          <h1 class="text-2xl font-bold">Settings</h1>
          <p class="text-muted-foreground">Manage your account settings</p>
        </div>

        <Card>
          <CardHeader>
            <CardTitle>Account</CardTitle>
            <CardDescription>Your account information</CardDescription>
          </CardHeader>
          <CardContent class="space-y-4">
            <div class="flex items-center justify-between">
              <span class="text-muted-foreground">Username</span>
              <span class="font-medium">{user()?.username}</span>
            </div>
            <Separator />
            <div class="flex items-center justify-between">
              <span class="text-muted-foreground">Role</span>
              <Show
                when={user()?.is_admin}
                fallback={<Badge variant="secondary">User</Badge>}
              >
                <Badge>Admin</Badge>
              </Show>
            </div>
            <Separator />
            <div class="flex items-center justify-between">
              <span class="text-muted-foreground">Account Created</span>
              <span>{user()?.created_at ? new Date(user()!.created_at).toLocaleDateString() : "—"}</span>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Application</CardTitle>
            <CardDescription>Application information</CardDescription>
          </CardHeader>
          <CardContent class="space-y-4">
            <div class="flex items-center justify-between">
              <span class="text-muted-foreground">Version</span>
              <span class="font-mono text-sm">1.0.0</span>
            </div>
            <Separator />
            <div class="flex items-center justify-between">
              <span class="text-muted-foreground">Framework</span>
              <span class="font-mono text-sm">SolidJS 2.0</span>
            </div>
          </CardContent>
        </Card>
      </div>
    </AppShell>
  );
};

export default SettingsPage;
```

**Step 2: Commit**

```bash
git add -A
git commit -m "feat: add settings page with account info"
```

---

## Phase 5: Testing & Polish

### Task 5.1: Fix Button Export for Alert Dialog

**Files:**
- Modify: `web/src/components/ui/button.tsx`

**Step 1: Export buttonVariants**

In `web/src/components/ui/button.tsx`, the `buttonVariants` is already used but needs to be exported for the alert-dialog component.

Update the export line:

```typescript
// At the end of button.tsx, ensure buttonVariants is exported
export { buttonVariants };
```

**Step 2: Commit**

```bash
git add -A
git commit -m "fix: export buttonVariants for alert-dialog component"
```

---

### Task 5.2: Verify Build

**Step 1: Run build**

Run: `cd web && pnpm build`
Expected: Build succeeds with no errors

**Step 2: Fix any type errors**

If there are type errors, fix them incrementally.

**Step 3: Commit any fixes**

```bash
git add -A
git commit -m "fix: resolve build errors"
```

---

### Task 5.3: Update Playwright E2E Tests

**Files:**
- Modify: `web/e2e/auth.spec.ts` (update selectors if needed)

**Step 1: Review e2e tests**

Check existing e2e tests and update selectors if component structure changed significantly.

**Step 2: Run e2e tests**

Run: `cd web && pnpm test:e2e`

**Step 3: Fix failing tests**

Update selectors and assertions as needed.

**Step 4: Commit**

```bash
git add -A
git commit -m "test: update e2e tests for SolidJS migration"
```

---

### Task 5.4: Add Unit Tests

**Files:**
- Create: `web/src/stores/__tests__/auth.test.ts`
- Create: `web/src/components/ui/__tests__/button.test.tsx`

**Step 1: Create auth store test**

Create `web/src/stores/__tests__/auth.test.ts`:

```typescript
import { describe, it, expect, vi, beforeEach } from "vitest";
import { createRoot } from "solid-js";

// Mock the api module
vi.mock("~/lib/api", () => ({
  api: {
    getSetupStatus: vi.fn(),
    me: vi.fn(),
    login: vi.fn(),
    logout: vi.fn(),
    bootstrap: vi.fn(),
  },
}));

describe("authStore", () => {
  beforeEach(() => {
    localStorage.clear();
    vi.clearAllMocks();
  });

  it("starts with loading state", async () => {
    // Dynamic import to get fresh instance
    const { authStore } = await import("../auth");
    
    createRoot((dispose) => {
      expect(authStore.loading()).toBe(true);
      expect(authStore.authenticated()).toBe(false);
      dispose();
    });
  });
});
```

**Step 2: Create button test**

Create `web/src/components/ui/__tests__/button.test.tsx`:

```typescript
import { describe, it, expect } from "vitest";
import { render, screen } from "@solidjs/testing-library";
import { Button } from "../button";

describe("Button", () => {
  it("renders with children", () => {
    render(() => <Button>Click me</Button>);
    expect(screen.getByRole("button")).toHaveTextContent("Click me");
  });

  it("applies variant classes", () => {
    render(() => <Button variant="destructive">Delete</Button>);
    const button = screen.getByRole("button");
    expect(button.className).toContain("bg-destructive");
  });

  it("can be disabled", () => {
    render(() => <Button disabled>Disabled</Button>);
    expect(screen.getByRole("button")).toBeDisabled();
  });
});
```

**Step 3: Run tests**

Run: `cd web && pnpm test`

**Step 4: Commit**

```bash
git add -A
git commit -m "test: add unit tests for auth store and button component"
```

---

### Task 5.5: Final Cleanup

**Step 1: Remove any remaining React references**

Search for any "react" imports or references and remove them.

**Step 2: Verify dev server works**

Run: `cd web && pnpm dev`
Expected: Server starts and app loads correctly

**Step 3: Final commit**

```bash
git add -A
git commit -m "chore: complete SolidJS v2 migration"
```

---

## Summary

This plan migrates the web dashboard from React to SolidJS v2 in 5 phases:

1. **Foundation** - Project setup, dependencies, utilities
2. **UI Components** - 15 shadcn-solid components
3. **Core Infrastructure** - Auth store, router, query provider
4. **Pages** - All 8 routes rebuilt
5. **Testing & Polish** - Build verification, e2e updates, unit tests

Total tasks: ~20 discrete implementation steps with frequent commits.
