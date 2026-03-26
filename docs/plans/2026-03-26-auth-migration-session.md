# Auth Migration Session Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Remove Privy from frontend bootstrap and add setup/login flows (Task 8 of self-hosted-v1-implementation).

**Architecture:** React Context + localStorage + FastAPI (local auth).

**Tech Stack:** React 19, TypeScript, TanStack Router.

---

### Task 1: Create Auth Components and Routes

**Files:**
- Create: `web/src/components/auth/LoginForm.tsx`
- Create: `web/src/components/auth/BootstrapForm.tsx`
- Create: `web/src/routes/setup.tsx`

**Step 1: Create BootstrapForm**
- Username, Password, Confirm Password fields.
- Calls `POST /api/v1/auth/bootstrap`.

**Step 2: Create LoginForm**
- Username, Password fields.
- Calls `POST /api/v1/auth/login`.

**Step 3: Create Setup Route**
- Checks `/api/v1/auth/setup-status`.
- Renders `BootstrapForm`.

### Task 2: Implement Local Auth Hook

**Files:**
- Modify: `web/src/hooks/useAuth.ts`
- Delete: `web/src/hooks/useAuthWithWalletSetup.ts`
- Delete: `web/src/hooks/useWalletSetup.ts`

**Step 1: Rewrite useAuth**
- Remove Privy dependencies.
- Implement `login`, `logout`, `checkAuth`.
- Use `localStorage` for token.

### Task 3: Update Main Entry and Routes

**Files:**
- Modify: `web/src/main.tsx`
- Modify: `web/src/routes/index.tsx`
- Modify: `web/src/routes/_authenticated.tsx`
- Modify: `web/src/routes/__root.tsx`

**Step 1: Update main.tsx**
- Remove `PrivyProvider`.

**Step 2: Update index.tsx**
- Use `LoginForm`.
- Redirect if authenticated.

**Step 3: Update protected routes**
- Check `isAuthenticated` from new hook.

### Task 4: Fix Tests

**Files:**
- Test: `web/e2e/auth/login.spec.ts`
- Test: `web/e2e/authenticated/dashboard.spec.ts`

**Step 1: Update E2E tests**
- Remove wallet login steps.
- Add username/password login steps.

**Step 2: Run tests**
- `pnpm test:e2e`

