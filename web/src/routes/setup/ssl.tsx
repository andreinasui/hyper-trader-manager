import { type Component, createSignal, Show } from "solid-js";
import { useNavigate } from "@solidjs/router";
import { Lock } from "lucide-solid";
import { Button } from "~/components/ui/button";
import { Input } from "~/components/ui/input";
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
    <div class="min-h-screen bg-surface-base flex items-center justify-center p-4">
      <div class="w-full max-w-md bg-surface-raised border border-border-default rounded-md overflow-hidden">
        {/* Header strip */}
        <div class="px-8 pt-8 pb-6 border-b border-border-default">
          <div class="w-10 h-10 rounded-md bg-primary flex items-center justify-center mb-5">
            <Lock size={18} stroke-width={1.5} class="text-white" />
          </div>
          <h1 class="text-xl font-semibold text-text-base">SSL Configuration</h1>
          <p class="text-sm text-text-subtle mt-1">Configure SSL for secure connections</p>
        </div>

        {/* Form area */}
        <div class="px-8 py-6">
          <form onSubmit={handleSubmit} class="space-y-6">
            <Show when={error()}>
              <Alert variant="destructive">
                <AlertDescription>{error()}</AlertDescription>
              </Alert>
            </Show>

            <div class="space-y-3">
              <label class="text-sm font-medium text-text-tertiary block">SSL Mode</label>
              <div class="grid grid-cols-2 gap-3">
                <button
                  type="button"
                  onClick={() => setMode("domain")}
                  class={`border rounded-md px-4 py-2.5 text-sm cursor-pointer transition-all ${
                    mode() === "domain"
                      ? "border-primary bg-primary-muted text-text-base"
                      : "border-border-default text-text-muted hover:border-text-faint"
                  }`}
                >
                  Domain (Let's Encrypt)
                </button>
                <button
                  type="button"
                  onClick={() => setMode("ip")}
                  class={`border rounded-md px-4 py-2.5 text-sm cursor-pointer transition-all ${
                    mode() === "ip"
                      ? "border-primary bg-primary-muted text-text-base"
                      : "border-border-default text-text-muted hover:border-text-faint"
                  }`}
                >
                  IP Only (Self-signed)
                </button>
              </div>
            </div>

            <Show when={mode() === "domain"}>
              <div class="space-y-2">
                <label for="domain" class="text-sm font-medium text-text-tertiary block">
                  Domain Name
                </label>
                <Input
                  id="domain"
                  type="text"
                  value={domain()}
                  onInput={(e) => setDomain(e.currentTarget.value)}
                  placeholder="example.com"
                  required
                />
              </div>
            </Show>

            <Button type="submit" class="w-full" disabled={loading()}>
              {loading() ? "Configuring..." : "Configure SSL"}
            </Button>
          </form>
        </div>
      </div>
    </div>
  );
};

export default SSLSetupPage;
