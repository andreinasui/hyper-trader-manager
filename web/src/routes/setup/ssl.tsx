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

    let hasRedirected = false;

    timeoutTimer = setTimeout(() => {
      clearInterval(pollTimer);
      setPhase("error");
    }, POLL_TIMEOUT_MS);

    pollTimer = setInterval(async () => {
      try {
        const resp = await fetch(httpUrl, { redirect: "manual" });
        if ((resp.type === "opaqueredirect" || resp.ok) && !hasRedirected) {
          hasRedirected = true;
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
                    autocomplete="off"
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
              <div class="flex flex-col items-center text-center py-8 gap-4" role="status">
                <Loader2 class="h-9 w-9 animate-spin text-primary" />
                <div>
                  <p class="text-sm font-medium text-text-base">Configuring SSL…</p>
                  <p class="text-sm text-text-subtle mt-1">
                    Server is restarting. This takes about 10 seconds.
                  </p>
                </div>
                <div
                  role="alert"
                  class="w-full p-3 bg-amber-950 border border-amber-800 rounded-md flex gap-2 text-xs text-amber-200"
                >
                  <span aria-hidden="true">⚠</span>
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
