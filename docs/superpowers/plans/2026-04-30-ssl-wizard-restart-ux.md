# SSL Wizard Restart UX — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the immediate `window.location.replace()` in the SSL wizard with a polling wait loop that shows an inline waiting state and auto-redirects once Traefik is back up.

**Architecture:** Add a `phase` signal (`"form" | "waiting" | "error"`) to `ssl.tsx`. On successful POST, switch to `"waiting"` phase and start polling `http://{domain}/health` with `redirect: 'manual'` every 1500ms. On `opaqueredirect` response (Traefik back up and redirecting HTTP→HTTPS), navigate to `redirect_url`. On 90-second timeout, switch to `"error"` phase showing a manual link. No backend changes required.

**Tech Stack:** SolidJS signals, native `fetch`, `setInterval`/`setTimeout`, `@solidjs/testing-library`, `vitest`

---

### Files

- Modify: `web/src/routes/setup/ssl.tsx` — add phase state, polling logic, and waiting/error JSX
- Create: `web/src/routes/setup/ssl.test.tsx` — component tests for the new states

---

### Task 1: Write failing tests for the waiting and error states

**Files:**
- Create: `web/src/routes/setup/ssl.test.tsx`

- [ ] **Step 1: Create the test file**

```tsx
// web/src/routes/setup/ssl.test.tsx
import { render, screen, fireEvent } from "@solidjs/testing-library";
import { vi, describe, it, expect, beforeEach, afterEach } from "vitest";
import SSLSetupPage from "./ssl";

vi.mock("~/lib/api", () => ({
  api: {
    configureSSL: vi.fn(),
  },
}));

async function flushMicrotasks() {
  // Flush promise chains inside async handlers (e.g. handleSubmit's await)
  await vi.advanceTimersByTimeAsync(0);
}

async function fillAndSubmitForm() {
  fireEvent.input(screen.getByLabelText("Domain Name"), {
    target: { value: "example.com" },
  });
  fireEvent.input(screen.getByLabelText("Email Address"), {
    target: { value: "admin@example.com" },
  });
  const form = screen.getByRole("button", { name: /configure ssl/i }).closest("form")!;
  fireEvent.submit(form);
  await flushMicrotasks();
}

describe("SSLSetupPage", () => {
  beforeEach(async () => {
    vi.useFakeTimers();
    const { api } = await import("~/lib/api");
    vi.mocked(api.configureSSL).mockResolvedValue({
      success: true,
      message: "ok",
      redirect_url: "https://example.com/",
    });
    // Default: fetch keeps failing (server still down)
    vi.stubGlobal(
      "fetch",
      vi.fn().mockRejectedValue(new TypeError("Failed to fetch"))
    );
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.unstubAllGlobals();
    vi.clearAllMocks();
  });

  it("renders the form initially", () => {
    render(() => <SSLSetupPage />);
    expect(screen.getByLabelText("Domain Name")).toBeInTheDocument();
    expect(screen.getByLabelText("Email Address")).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Configure SSL" })
    ).toBeInTheDocument();
  });

  it("shows waiting state after successful form submission", async () => {
    render(() => <SSLSetupPage />);
    await fillAndSubmitForm();

    expect(screen.getByText("Configuring SSL…")).toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: /configure ssl/i })
    ).not.toBeInTheDocument();
    expect(
      screen.getByText(/do not close or refresh this page/i)
    ).toBeInTheDocument();
  });

  it("redirects to https url when poll returns opaqueredirect", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({ type: "opaqueredirect" } as Response)
    );
    // Capture location.href changes
    let capturedHref = "";
    const originalDescriptor = Object.getOwnPropertyDescriptor(window, "location");
    Object.defineProperty(window, "location", {
      writable: true,
      value: {
        ...window.location,
        get href() { return capturedHref; },
        set href(v: string) { capturedHref = v; },
      },
    });

    render(() => <SSLSetupPage />);
    await fillAndSubmitForm();

    // Fire first poll interval
    await vi.advanceTimersByTimeAsync(1500);

    expect(capturedHref).toBe("https://example.com/");

    // Restore location
    if (originalDescriptor) {
      Object.defineProperty(window, "location", originalDescriptor);
    }
  });

  it("shows error state after 90-second timeout", async () => {
    render(() => <SSLSetupPage />);
    await fillAndSubmitForm();

    // Advance past the 90-second timeout
    await vi.advanceTimersByTimeAsync(90_000);

    expect(screen.getByText(/could not connect to server/i)).toBeInTheDocument();
    expect(
      screen.getByRole("link", { name: /open.*manually/i })
    ).toHaveAttribute("href", "https://example.com/");
    // Waiting spinner should be gone
    expect(screen.queryByText("Configuring SSL…")).not.toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run the tests and confirm they all fail**

```bash
cd web && pnpm test --run 2>&1 | tail -30
```

Expected: 3 tests fail (the new ones — `SSLSetupPage` describe block), 1 passes (renders form). The 1 passing test is fine because the form markup already exists.

---

### Task 2: Implement the waiting state in ssl.tsx

**Files:**
- Modify: `web/src/routes/setup/ssl.tsx`

- [ ] **Step 1: Replace the entire file with the new implementation**

```tsx
// web/src/routes/setup/ssl.tsx
import { type Component, createSignal, Show, Switch, Match, onCleanup } from "solid-js";
import { Lock, AlertCircle, Loader2 } from "lucide-solid";
import { Button } from "~/components/ui/button";
import { Input } from "~/components/ui/input";
import { Alert, AlertDescription } from "~/components/ui/alert";
import { api } from "~/lib/api";

const DOMAIN_REGEX = /^(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}$/;

const POLL_INTERVAL_MS = 1500;
const POLL_TIMEOUT_MS = 90_000;

type Phase = "form" | "waiting" | "error";

const SSLSetupPage: Component = () => {
  const [domain, setDomain] = createSignal("");
  const [email, setEmail] = createSignal("");
  const [error, setError] = createSignal<string | null>(null);
  const [loading, setLoading] = createSignal(false);
  const [domainError, setDomainError] = createSignal<string | null>(null);
  const [phase, setPhase] = createSignal<Phase>("form");
  const [redirectUrl, setRedirectUrl] = createSignal("");

  let pollTimer: ReturnType<typeof setInterval> | undefined;
  let timeoutTimer: ReturnType<typeof setTimeout> | undefined;

  onCleanup(() => {
    clearInterval(pollTimer);
    clearTimeout(timeoutTimer);
  });

  function validateDomain(value: string): boolean {
    if (!value) {
      setDomainError(null);
      return false;
    }
    if (!DOMAIN_REGEX.test(value)) {
      setDomainError("Please enter a valid domain name (e.g., example.com)");
      return false;
    }
    setDomainError(null);
    return true;
  }

  function startPolling(httpsUrl: string): void {
    const httpUrl =
      httpsUrl.replace(/^https:\/\//, "http://").replace(/\/$/, "") + "/health";

    timeoutTimer = setTimeout(() => {
      clearInterval(pollTimer);
      setPhase("error");
    }, POLL_TIMEOUT_MS);

    pollTimer = setInterval(async () => {
      try {
        const resp = await fetch(httpUrl, { redirect: "manual" });
        if (resp.type === "opaqueredirect") {
          clearInterval(pollTimer);
          clearTimeout(timeoutTimer);
          window.location.href = httpsUrl;
        }
      } catch {
        // Network error — server still restarting, keep polling
      }
    }, POLL_INTERVAL_MS);
  }

  async function handleSubmit(e: Event) {
    e.preventDefault();
    setError(null);

    if (!validateDomain(domain())) {
      return;
    }

    setLoading(true);

    try {
      const response = await api.configureSSL(domain(), email());
      setRedirectUrl(response.redirect_url);
      setLoading(false);
      setPhase("waiting");
      startPolling(response.redirect_url);
    } catch (err) {
      setError(err instanceof Error ? err.message : "SSL configuration failed");
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
          <p class="text-sm text-text-subtle mt-1">Configure HTTPS with Let's Encrypt</p>
        </div>

        {/* Body */}
        <div class="px-8 py-6">
          <Switch>
            <Match when={phase() === "form"}>
              {/* Prerequisites callout */}
              <div class="mb-6 p-4 bg-blue-50 dark:bg-blue-950 border border-blue-200 dark:border-blue-800 rounded-md">
                <div class="flex gap-3">
                  <AlertCircle
                    size={16}
                    class="text-blue-600 dark:text-blue-400 flex-shrink-0 mt-0.5"
                  />
                  <div class="text-sm">
                    <p class="font-medium text-blue-900 dark:text-blue-100 mb-2">
                      Prerequisites
                    </p>
                    <ul class="space-y-1 text-blue-800 dark:text-blue-200">
                      <li>• DNS A-record points to this server</li>
                      <li>• Ports 80 &amp; 443 open to the internet</li>
                      <li>• Certificate issuance takes ~60 seconds</li>
                    </ul>
                  </div>
                </div>
              </div>

              <form onSubmit={handleSubmit} class="space-y-6">
                <Show when={error()}>
                  <Alert variant="destructive">
                    <AlertDescription>{error()}</AlertDescription>
                  </Alert>
                </Show>

                <div class="space-y-2">
                  <label for="domain" class="text-sm font-medium text-text-tertiary block">
                    Domain Name
                  </label>
                  <Input
                    id="domain"
                    type="text"
                    value={domain()}
                    onInput={(e) => {
                      const val = e.currentTarget.value;
                      setDomain(val);
                      if (val) validateDomain(val);
                    }}
                    onBlur={() => domain() && validateDomain(domain())}
                    placeholder="example.com"
                    required
                    aria-invalid={!!domainError()}
                    aria-describedby={domainError() ? "domain-error" : undefined}
                  />
                  <Show when={domainError()}>
                    <p id="domain-error" class="text-sm text-error">
                      {domainError()}
                    </p>
                  </Show>
                </div>

                <div class="space-y-2">
                  <label for="email" class="text-sm font-medium text-text-tertiary block">
                    Email Address
                  </label>
                  <Input
                    id="email"
                    type="email"
                    value={email()}
                    onInput={(e) => setEmail(e.currentTarget.value)}
                    placeholder="admin@example.com"
                    required
                  />
                  <p class="text-xs text-text-muted">
                    Used for Let's Encrypt certificate notifications
                  </p>
                </div>

                <Button type="submit" class="w-full" disabled={loading() || !!domainError()}>
                  {loading() ? "Configuring..." : "Configure SSL"}
                </Button>
              </form>
            </Match>

            <Match when={phase() === "waiting"}>
              <div class="flex flex-col items-center text-center py-8 gap-4">
                <Loader2 class="h-9 w-9 animate-spin text-primary" />
                <div>
                  <p class="text-sm font-medium text-text-base">Configuring SSL…</p>
                  <p class="text-sm text-text-subtle mt-1">
                    Server is restarting. This takes about 10 seconds.
                  </p>
                </div>
                <div class="w-full p-3 bg-amber-950 border border-amber-800 rounded-md flex gap-2 text-xs text-amber-200">
                  <span>⚠</span>
                  <span>Do not close or refresh this page</span>
                </div>
              </div>
            </Match>

            <Match when={phase() === "error"}>
              <div class="flex flex-col items-center text-center py-8 gap-4">
                <AlertCircle class="h-9 w-9 text-error" />
                <div>
                  <p class="text-sm font-medium text-text-base">
                    Could not connect to server
                  </p>
                  <p class="text-sm text-text-subtle mt-1">
                    The server did not come back within 90 seconds. SSL may still be
                    configured.
                  </p>
                </div>
                <a
                  href={redirectUrl()}
                  class="text-sm text-primary underline underline-offset-2"
                >
                  Open {redirectUrl()} manually
                </a>
              </div>
            </Match>
          </Switch>
        </div>
      </div>
    </div>
  );
};

export default SSLSetupPage;
```

- [ ] **Step 2: Run the tests — they should now pass**

```bash
cd web && pnpm test --run 2>&1 | tail -20
```

Expected output:
```
 ✓ src/routes/setup/ssl.test.tsx (4 tests)
 ✓ src/lib/setupGuard.test.ts (9 tests)

 Test Files  2 passed (2)
      Tests  13 passed (13)
```

If the `redirects to https url` test fails with an error about `window.location` being read-only in jsdom, see the note below in Step 3.

- [ ] **Step 3: If the location test fails — fix the test's location mock**

jsdom's `window.location` is not writable by default. If Step 2's redirect test fails with `TypeError: Cannot set property href of #<Location>`, update just that test's setup to use `Object.defineProperty` before render:

```tsx
it("redirects to https url when poll returns opaqueredirect", async () => {
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue({ type: "opaqueredirect" } as Response)
  );

  let capturedHref = "";
  Object.defineProperty(window, "location", {
    configurable: true,
    writable: true,
    value: new Proxy(window.location, {
      set(target, key, value) {
        if (key === "href") capturedHref = value as string;
        return Reflect.set(target, key, value);
      },
    }),
  });

  render(() => <SSLSetupPage />);
  await fillAndSubmitForm();
  await vi.advanceTimersByTimeAsync(1500);

  expect(capturedHref).toBe("https://example.com/");
});
```

Re-run tests after the fix:

```bash
cd web && pnpm test --run 2>&1 | tail -20
```

Expected: 13 passed (or same count as step 2).

---

### Task 3: Typecheck

**Files:** no changes

- [ ] **Step 1: Run TypeScript type check**

```bash
cd web && pnpm exec tsc --noEmit 2>&1
```

Expected: no output (zero errors). If errors appear, fix them before committing.

---

### Task 4: Commit

- [ ] **Step 1: Stage and commit**

```bash
cd web && git add src/routes/setup/ssl.tsx src/routes/setup/ssl.test.tsx
git commit -m "web: add SSL wizard waiting state with restart polling"
```

- [ ] **Step 2: Verify commit**

```bash
git log --oneline -3
```

Expected: commit appears as most recent on `feature/ssl-wizard-restart-ux`.
