# Auth Migration Design

## Context
Migrating from Privy (SaaS wallet auth) to self-hosted username/password authentication.

## Goals
- Remove all Privy dependencies.
- Implement local username/password login.
- Implement first-run bootstrap flow.
- Secure routes.

## Architecture

### 1. API Client
- Modify `web/src/lib/api/client.ts` to read the JWT from `localStorage` ('auth_token').

### 2. Auth State (`useAuth.ts`)
- **State**:
  - `user`: `AuthUser | null`
  - `isLoading`: `boolean`
  - `isAuthenticated`: `boolean`
  - `isInitialized`: `boolean` (setup status)
- **Actions**:
  - `login(username, password)`: POST /login, save token, set user.
  - `bootstrap(username, password)`: POST /bootstrap.
  - `logout()`: Remove token, set user null.
- **Initialization**:
  - Check `/api/v1/auth/setup-status`
  - Check `/api/v1/auth/me` (if token exists)

### 3. Routing
- **`/` (Login)**:
  - If `!isInitialized`, redirect to `/setup`.
  - If `isAuthenticated`, redirect to `/dashboard`.
  - Render `LoginForm`.
- **`/setup` (Bootstrap)**:
  - If `isInitialized`, redirect to `/`.
  - Render `BootstrapForm`.
- **`/_authenticated`**:
  - If `!isAuthenticated`, redirect to `/`.

### 4. Components
- `LoginForm`: `username`, `password`.
- `BootstrapForm`: `username`, `password`, `confirmPassword`.

## Test Plan
- Unit tests for `useAuth`.
- E2E tests for:
  - Redirect to setup on fresh install.
  - Successful bootstrap.
  - Login flow.
  - Protected route access.
