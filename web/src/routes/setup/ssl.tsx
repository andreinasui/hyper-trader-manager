import { type Component, createSignal, onMount, Show } from "solid-js";
import { useNavigate } from "@solidjs/router";
import { Lock, AlertCircle } from "lucide-solid";
import { Button } from "~/components/ui/button";
import { Input } from "~/components/ui/input";
import { Alert, AlertDescription } from "~/components/ui/alert";
import { api } from "~/lib/api";
import { authStore } from "~/stores/auth";
import { evaluateSetupGuard } from "~/lib/setupGuard";

const DOMAIN_REGEX = /^(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}$/;

const SSLSetupPage: Component = () => {
  const navigate = useNavigate();
  const [shouldRender, setShouldRender] = createSignal(false);
  const [domain, setDomain] = createSignal("");
  const [email, setEmail] = createSignal("");
  const [error, setError] = createSignal<string | null>(null);
  const [loading, setLoading] = createSignal(false);
  const [domainError, setDomainError] = createSignal<string | null>(null);

  // Apply guard after mount: if SSL is already configured, redirect away.
  onMount(() => {
    const decision = evaluateSetupGuard(
      window.location.pathname,
      window.isSecureContext,
      {
        sslConfigured: authStore.sslConfigured(),
        isInitialized: authStore.isInitialized(),
      },
    );

    if (decision.type === "redirect-route") {
      navigate(decision.to, { replace: true });
      return;
    }

    if (decision.type === "redirect-https") {
      window.location.replace(decision.url);
      return;
    }

    setShouldRender(true);
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

  async function handleSubmit(e: Event) {
    e.preventDefault();
    setError(null);

    if (!validateDomain(domain())) {
      return;
    }

    setLoading(true);

    try {
      const response = await api.configureSSL(domain(), email());
      // Full-page navigation required to switch from HTTP to HTTPS
      window.location.replace(response.redirect_url);
    } catch (err) {
      setError(err instanceof Error ? err.message : "SSL configuration failed");
      setLoading(false);
    }
  }

  return (
    <Show when={shouldRender()}>
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

        {/* Form area */}
        <div class="px-8 py-6">
          {/* Prerequisites callout */}
          <div class="mb-6 p-4 bg-blue-50 dark:bg-blue-950 border border-blue-200 dark:border-blue-800 rounded-md">
            <div class="flex gap-3">
              <AlertCircle size={16} class="text-blue-600 dark:text-blue-400 flex-shrink-0 mt-0.5" />
              <div class="text-sm">
                <p class="font-medium text-blue-900 dark:text-blue-100 mb-2">Prerequisites</p>
                <ul class="space-y-1 text-blue-800 dark:text-blue-200">
                  <li>• DNS A-record points to this server</li>
                  <li>• Ports 80 & 443 open to the internet</li>
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
        </div>
      </div>
    </div>
    </Show>
  );
};

export default SSLSetupPage;
