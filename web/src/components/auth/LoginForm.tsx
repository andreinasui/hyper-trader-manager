import { createSignal, Show } from "solid-js";
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
      <Show when={error()}>
        <Alert variant="destructive">
          <AlertDescription>{error()}</AlertDescription>
        </Alert>
      </Show>

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
