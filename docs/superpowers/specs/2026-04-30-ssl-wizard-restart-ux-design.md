# SSL Wizard Restart UX — Design Spec

**Date:** 2026-04-30  
**Status:** Approved

---

## Problem

When a user submits the SSL wizard, the backend writes Traefik config and restarts the Traefik container (~5–10 seconds). Currently the frontend immediately calls `window.location.replace(redirect_url)`, which fires before Traefik is back up. This results in a browser error page if the restart hasn't completed.

The page is served over HTTP before SSL is configured. After SSL is applied, the redirect URL is `https://`. The frontend JS stays alive in memory through the restart — only a manual page refresh during restart would cause a browser error.

---

## Goal

Show a clear waiting state while the server restarts, then automatically redirect to `https://{domain}/` once Traefik is back and responding.

---

## Design: Inline Card Replacement (Option A)

When the user submits the form, the card body is replaced in-place with a waiting state. No overlay. No separate page.

### Waiting State UI

The card header (lock icon, title, subtitle) stays unchanged. The form area is replaced with:

- Spinning loader (`animate-spin`, matching the app's existing `LoadingScreen` pattern)
- Primary message: **"Configuring SSL…"**
- Secondary message: "Server is restarting. This takes about 10 seconds."
- Warning banner (amber): **"Do not close or refresh this page"**
- The submit button is gone — no way to re-submit

### Polling Mechanism

After the `POST /v1/setup/ssl` response arrives successfully:

1. Save `redirect_url` from the response (e.g. `https://example.com/`)
2. Derive the HTTP health poll URL from `redirect_url` — replace `https://` with `http://` and append `/health` (e.g. `https://example.com/` → `http://example.com/health`)
3. Start polling with `setInterval` every 1500ms
4. Each poll: `fetch(httpHealthUrl, { redirect: 'manual' })`
   - `response.type === 'opaqueredirect'` means Traefik responded with HTTP→HTTPS 301, confirming it is back up and SSL is active
   - Network errors (`TypeError: Failed to fetch`) = still down, keep polling
5. On success: `window.location.href = redirect_url`
6. On timeout (90 seconds): show error message and a "Try opening manually" link to `redirect_url`

**Why `redirect: 'manual'`:** Prevents the browser from following the HTTP→HTTPS redirect, which would require a valid TLS cert (not yet issued). The `opaqueredirect` status is sufficient to confirm Traefik is alive.

### Error Handling

| Case | Behavior |
|------|----------|
| `POST /v1/setup/ssl` fails | Show existing error alert in the form (unchanged behavior) |
| Poll times out (>90s) | Replace spinner with error message + manual link |
| User navigates away / refreshes during wait | Browser error (expected — warned against with the banner) |

### State Machine

```
FORM → (submit) → WAITING → (poll succeeds) → REDIRECTING
                           → (timeout 90s)  → ERROR
```

`REDIRECTING` is a transient state — just `window.location.href = redirect_url`, no visible state needed.

---

## Implementation Scope

**Frontend only.** No backend changes required.

File to modify: `web/src/routes/setup/ssl.tsx`

Changes:
1. Add `phase` signal: `"form" | "waiting" | "error"`
2. Add `redirectUrl` signal
3. On successful `POST` response: set phase to `"waiting"`, save `redirect_url`, start polling interval
4. Clear interval on unmount (`onCleanup`)
5. Replace `<Show>` on form with `<Switch>`/`<Match>` blocks for form vs waiting vs error
6. Waiting view: spinner + messages + warning banner (inline, no new component)

---

## Out of Scope

- Step-by-step progress indicator (added complexity, polling can't distinguish restart vs cert issuance)
- Full-screen overlay (overkill for a 10-second wait)
- Subsequent domain changes without restart (separate feature)
- Backend changes
