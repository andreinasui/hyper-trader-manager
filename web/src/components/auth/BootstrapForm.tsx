import { createSignal, Show } from "solid-js";
import { useNavigate } from "@solidjs/router";
import { Button } from "~/components/ui/button";
import { Input } from "~/components/ui/input";
import { Label } from "~/components/ui/label";
import { Alert, AlertDescription } from "~/components/ui/alert";
import { authStore } from "~/stores/auth";

export function BootstrapForm() {
  const navigate = useNavigate();
  const [username, setUsername] = createSignal("");
  const [password, setPassword] = createSignal("");
  const [confirmPassword, setConfirmPassword] = createSignal("");
  const [error, setError] = createSignal<string | null>(null);
  const [loading, setLoading] = createSignal(false);

  async function handleSubmit(e: Event) {
    e.preventDefault();
    setError(null);

    if (password() !== confirmPassword()) {
      setError("Passwords do not match");
      return;
    }

    if (password().length < 8) {
      setError("Password must be at least 8 characters");
      return;
    }

    setLoading(true);

    try {
      await authStore.bootstrap(username(), password());
      navigate("/dashboard");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Setup failed");
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
        <Label for="username">Admin Username</Label>
        <Input
          id="username"
          type="text"
          value={username()}
          onInput={(e) => setUsername(e.currentTarget.value)}
          placeholder="Enter admin username"
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
          placeholder="Enter password (min 8 characters)"
          required
        />
      </div>

      <div class="space-y-2">
        <Label for="confirmPassword">Confirm Password</Label>
        <Input
          id="confirmPassword"
          type="password"
          value={confirmPassword()}
          onInput={(e) => setConfirmPassword(e.currentTarget.value)}
          placeholder="Confirm password"
          required
        />
      </div>

      <Button type="submit" class="w-full" disabled={loading()}>
        {loading() ? "Creating account..." : "Create Admin Account"}
      </Button>
    </form>
  );
}
