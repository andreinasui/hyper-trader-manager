import { type Component, createSignal, Show } from "solid-js";
import { useNavigate } from "@solidjs/router";
import { createMutation, useQueryClient } from "@tanstack/solid-query";
import { AppShell } from "~/components/layout/AppShell";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "~/components/ui/card";
import { Button } from "~/components/ui/button";
import { Input } from "~/components/ui/input";
import { Label } from "~/components/ui/label";
import { Alert, AlertDescription } from "~/components/ui/alert";
import { api } from "~/lib/api";
import { traderKeys } from "~/lib/query-keys";

const NewTraderPage: Component = () => {
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const [name, setName] = createSignal("");
  const [walletAddress, setWalletAddress] = createSignal("");
  const [privateKey, setPrivateKey] = createSignal("");
  const [error, setError] = createSignal<string | null>(null);

  const createTraderMutation = createMutation(() => ({
    mutationFn: () =>
      api.createTrader({
        name: name(),
        wallet_address: walletAddress(),
        private_key: privateKey(),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: traderKeys.all });
      navigate("/traders");
    },
    onError: (err: Error) => {
      setError(err.message);
    },
  }));

  function handleSubmit(e: Event) {
    e.preventDefault();
    setError(null);

    // Basic validation
    if (!name().trim()) {
      setError("Name is required");
      return;
    }

    // Validate Ethereum address format
    const addressRegex = /^0x[a-fA-F0-9]{40}$/;
    if (!addressRegex.test(walletAddress())) {
      setError("Invalid Ethereum wallet address");
      return;
    }

    if (!privateKey().trim()) {
      setError("Private key is required");
      return;
    }

    createTraderMutation.mutate();
  }

  return (
    <AppShell>
      <div class="max-w-2xl mx-auto">
        <Card>
          <CardHeader>
            <CardTitle>Create New Trader</CardTitle>
            <CardDescription>
              Set up a new trading bot with your wallet credentials
            </CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSubmit} class="space-y-4">
              <Show when={error()}>
                <Alert variant="destructive">
                  <AlertDescription>{error()}</AlertDescription>
                </Alert>
              </Show>

              <div class="space-y-2">
                <Label for="name">Trader Name</Label>
                <Input
                  id="name"
                  type="text"
                  value={name()}
                  onInput={(e) => setName(e.currentTarget.value)}
                  placeholder="My Trading Bot"
                  required
                />
              </div>

              <div class="space-y-2">
                <Label for="walletAddress">Wallet Address</Label>
                <Input
                  id="walletAddress"
                  type="text"
                  value={walletAddress()}
                  onInput={(e) => setWalletAddress(e.currentTarget.value)}
                  placeholder="0x..."
                  class="font-mono"
                  required
                />
              </div>

              <div class="space-y-2">
                <Label for="privateKey">Private Key</Label>
                <Input
                  id="privateKey"
                  type="password"
                  value={privateKey()}
                  onInput={(e) => setPrivateKey(e.currentTarget.value)}
                  placeholder="Enter private key"
                  class="font-mono"
                  required
                />
                <p class="text-xs text-muted-foreground">
                  Your private key is encrypted and stored securely
                </p>
              </div>

              <div class="flex gap-4 pt-4">
                <Button
                  type="button"
                  variant="outline"
                  onClick={() => navigate("/traders")}
                >
                  Cancel
                </Button>
                <Button type="submit" disabled={createTraderMutation.isPending}>
                  {createTraderMutation.isPending ? "Creating..." : "Create Trader"}
                </Button>
              </div>
            </form>
          </CardContent>
        </Card>
      </div>
    </AppShell>
  );
};

export default NewTraderPage;
