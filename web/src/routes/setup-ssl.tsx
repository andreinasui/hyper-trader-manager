import { type Component, createSignal, Show } from "solid-js";
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
            <Show when={error()}>
              <Alert variant="destructive">
                <AlertDescription>{error()}</AlertDescription>
              </Alert>
            </Show>

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

            <Show when={mode() === "domain"}>
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
            </Show>

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
