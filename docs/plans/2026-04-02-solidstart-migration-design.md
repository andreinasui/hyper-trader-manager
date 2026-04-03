# SolidStart Migration Design

**Date:** 2026-04-02  
**Status:** Approved  
**Estimated Effort:** 2-3 hours

## Overview

Migrate the web frontend from Vite SPA (served by nginx) to SolidStart, enabling the web container to serve the application AND proxy API requests internally. This removes direct public access to the API container.

## Goals

1. Web container serves SPA and proxies `/api/*` to API container
2. API container is only accessible within Docker network
3. Traefik routes all traffic to web container only
4. Minimal changes to existing components and API client code

## Architecture

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                              Docker Network                                  │
│                                                                              │
│  ┌─────────────────┐      ┌─────────────────────────┐      ┌──────────────┐ │
│  │                 │      │     Web Container       │      │              │ │
│  │     Traefik     │──/*─▶│     (SolidStart)        │─/api─▶│ API Container│ │
│  │   (port 3080)   │      │                         │      │  (internal)  │ │
│  │                 │      │  - Serves SPA (CSR)     │      │              │ │
│  └─────────────────┘      │  - Proxies /api/* to    │      │  - FastAPI   │ │
│         ▲                 │    http://api:8000      │      │  - Port 8000 │ │
│         │                 └─────────────────────────┘      │  - No public │ │
│         │                                                  │    exposure  │ │
└─────────│──────────────────────────────────────────────────┴──────────────┘
          │
    ┌─────┴─────┐
    │  Browser  │
    └───────────┘
```

## Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Rendering mode | CSR (Client-Side Rendering) | Keeps behavior identical to current SPA, simpler setup |
| API proxy method | Vinxi server middleware | Built into SolidStart, no custom code needed |
| Migration scope | Full migration | File-based routing is cleaner long-term |
| API exposure | Internal only | Security: API only reachable through web proxy |

## File Structure

### Current (Vite SPA)

```
web/src/
├── index.tsx          # Manual route definitions
├── App.tsx            # Root component with auth guard
├── routes/
│   ├── login.tsx
│   ├── setup.tsx
│   ├── setup-ssl.tsx
│   ├── dashboard.tsx
│   ├── traders.tsx
│   ├── traders-new.tsx
│   ├── trader-detail.tsx
│   └── settings.tsx
├── components/
├── lib/
└── stores/
```

### New (SolidStart)

```
web/
├── app.config.ts              # SolidStart config (proxy, CSR mode)
├── src/
│   ├── entry-client.tsx       # Client entry
│   ├── app.tsx                # Root component (layout + auth guard)
│   ├── routes/
│   │   ├── index.tsx          # / → login page
│   │   ├── setup.tsx          # /setup
│   │   ├── setup/
│   │   │   └── ssl.tsx        # /setup/ssl
│   │   ├── dashboard.tsx      # /dashboard
│   │   ├── traders/
│   │   │   ├── index.tsx      # /traders
│   │   │   ├── new.tsx        # /traders/new
│   │   │   └── [id].tsx       # /traders/:id
│   │   └── settings.tsx       # /settings
│   ├── components/            # Unchanged
│   ├── lib/                   # Unchanged
│   └── stores/                # Unchanged
└── package.json
```

### Route Mapping

| URL Path | Current File | New File |
|----------|--------------|----------|
| `/` | `routes/login.tsx` | `routes/index.tsx` |
| `/setup` | `routes/setup.tsx` | `routes/setup.tsx` |
| `/setup/ssl` | `routes/setup-ssl.tsx` | `routes/setup/ssl.tsx` |
| `/dashboard` | `routes/dashboard.tsx` | `routes/dashboard.tsx` |
| `/traders` | `routes/traders.tsx` | `routes/traders/index.tsx` |
| `/traders/new` | `routes/traders-new.tsx` | `routes/traders/new.tsx` |
| `/traders/:id` | `routes/trader-detail.tsx` | `routes/traders/[id].tsx` |
| `/settings` | `routes/settings.tsx` | `routes/settings.tsx` |

## Configuration

### app.config.ts

```typescript
import { defineConfig } from "@solidjs/start/config";

const apiTarget = process.env.API_URL || "http://api:8000";

export default defineConfig({
  ssr: false,  // CSR mode
  server: {
    preset: "node-server",
    routeRules: {
      "/api/**": {
        proxy: { to: `${apiTarget}/**` }
      }
    }
  }
});
```

### Dockerfile (web)

```dockerfile
FROM node:22-alpine AS builder
WORKDIR /app
RUN npm install -g pnpm@10
COPY package.json pnpm-lock.yaml ./
RUN pnpm install --frozen-lockfile
COPY . .
RUN pnpm build

FROM node:22-alpine AS runner
WORKDIR /app
COPY --from=builder /app/.output /app/.output
ENV NODE_ENV=production
ENV API_URL=http://api:8000
EXPOSE 3000
CMD ["node", ".output/server/index.mjs"]
```

### Traefik dynamic.yml

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

## Migration Phases

### Phase 1: Setup SolidStart
- Update package.json with SolidStart dependencies
- Create app.config.ts with CSR mode and API proxy
- Create entry-client.tsx and app.tsx

### Phase 2: Migrate Routes
- Convert route files to file-based routing structure
- Update imports to use SolidStart conventions
- Move auth guard logic to app.tsx

### Phase 3: Update Infrastructure
- Replace Dockerfile (nginx → Node.js)
- Update Traefik dynamic.yml
- Update docker-compose files

### Phase 4: Verify
- Test local development
- Test Docker build and proxy
- Verify API isolation

## Risk Areas

1. **TanStack Query integration** - Should work with SolidStart CSR, but needs verification
2. **Auth store reactivity** - Ensure signals work across route transitions
3. **Path aliases** - `~/` alias may need reconfiguration in new setup

## Dependencies

### New
- `@solidjs/start` - SolidStart framework
- `vinxi` - Build system (peer dep of SolidStart)

### Removed
- nginx (Dockerfile only, not a package)

### Unchanged
- solid-js, @solidjs/router, @tanstack/solid-query, etc.
