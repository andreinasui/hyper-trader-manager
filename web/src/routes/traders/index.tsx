import { type Component, Show, For, Suspense, createSignal } from "solid-js";
import { createQuery, createMutation, useQueryClient } from "@tanstack/solid-query";
import { A } from "@solidjs/router";
import { Plus, Play, Square, Trash2, Loader2, AlertCircle, RefreshCw } from "lucide-solid";
import { ProtectedRoute } from "~/components/auth/ProtectedRoute";
import { AppShell } from "~/components/layout/AppShell";
import { Button } from "~/components/ui/button";
import { Badge } from "~/components/ui/badge";
import { Skeleton } from "~/components/ui/skeleton";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "~/components/ui/alert-dialog";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "~/components/ui/table";
import { api } from "~/lib/api";
import { traderKeys, imageKeys } from "~/lib/query-keys";
import type { Trader } from "~/lib/types";
import { ImageVersionBanner } from "~/components/traders/ImageVersionBanner";

function StatusBadge(props: { status: Trader["status"] }) {
  const variant = () => {
    switch (props.status) {
      case "running":
        return "success";
      case "configured":
        return "secondary";
      case "stopped":
        return "outline";
      case "starting":
        return "default";
      case "failed":
        return "destructive";
      case "pending":
        return "outline";
      default:
        return "outline";
    }
  };

  const label = () => {
    if (props.status === "starting") {
      return (
        <span class="flex items-center gap-1">
          <Loader2 class="h-3 w-3 animate-spin" />
          starting
        </span>
      );
    }
    return props.status;
  };

  return <Badge variant={variant()}>{label()}</Badge>;
}

function TraderActions(props: { trader: Trader }) {
  const queryClient = useQueryClient();
  const [deleteOpen, setDeleteOpen] = createSignal(false);

  const imageQuery = createQuery(() => ({
    queryKey: imageKeys.versions(),
    queryFn: () => api.getImageVersions(),
  }));

  const startMutation = createMutation(() => ({
    mutationFn: () => api.startTrader(props.trader.id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: traderKeys.lists() });
    },
  }));

  const stopMutation = createMutation(() => ({
    mutationFn: () => api.stopTrader(props.trader.id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: traderKeys.lists() });
    },
  }));

  const deleteMutation = createMutation(() => ({
    mutationFn: () => api.deleteTrader(props.trader.id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: traderKeys.lists() });
    },
  }));

  const updateImageMutation = createMutation(() => ({
    mutationFn: (newTag: string) => api.updateTraderImage(props.trader.id, newTag),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: traderKeys.lists() });
      queryClient.invalidateQueries({ queryKey: imageKeys.versions() });
    },
  }));

  const needsUpdate = () => {
    const remote = imageQuery.data?.latest_remote;
    if (!remote) return false;
    const current = props.trader.image_tag;
    if (!current) return false;
    // semver compare: remote > current
    const [rMaj, rMin, rPat] = remote.split(".").map(Number);
    const [cMaj, cMin, cPat] = current.split(".").map(Number);
    if (rMaj !== cMaj) return rMaj > cMaj;
    if (rMin !== cMin) return rMin > cMin;
    return rPat > cPat;
  };

  const canStart = () =>
    ["configured", "stopped", "failed"].includes(props.trader.status);
  const canStop = () =>
    ["running", "starting"].includes(props.trader.status);
  const isLoading = () =>
    startMutation.isPending || stopMutation.isPending || deleteMutation.isPending || updateImageMutation.isPending;

  return (
    <div class="flex items-center gap-1">
      <Show when={needsUpdate()}>
        <Button
          variant="ghost"
          size="sm"
          onClick={() => updateImageMutation.mutate(imageQuery.data!.latest_remote!)}
          disabled={isLoading()}
          title={`Update to ${imageQuery.data?.latest_remote}`}
        >
          <Show when={updateImageMutation.isPending} fallback={<RefreshCw class="h-4 w-4" />}>
            <Loader2 class="h-4 w-4 animate-spin" />
          </Show>
        </Button>
      </Show>

      <Show when={canStart()}>
        <Button
          variant="ghost"
          size="sm"
          onClick={() => startMutation.mutate()}
          disabled={isLoading()}
          title={props.trader.status === "failed" ? "Retry" : "Start"}
        >
          <Show when={startMutation.isPending} fallback={<Play class="h-4 w-4" />}>
            <Loader2 class="h-4 w-4 animate-spin" />
          </Show>
        </Button>
      </Show>

      <Show when={canStop()}>
        <Button
          variant="ghost"
          size="sm"
          onClick={() => stopMutation.mutate()}
          disabled={isLoading()}
          title="Stop"
        >
          <Show when={stopMutation.isPending} fallback={<Square class="h-4 w-4" />}>
            <Loader2 class="h-4 w-4 animate-spin" />
          </Show>
        </Button>
      </Show>

      <AlertDialog open={deleteOpen()} onOpenChange={setDeleteOpen}>
        <AlertDialogTrigger
          as={Button}
          variant="ghost"
          size="sm"
          disabled={isLoading()}
          title="Delete"
        >
          <Trash2 class="h-4 w-4 text-destructive" />
        </AlertDialogTrigger>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete Trader</AlertDialogTitle>
            <AlertDialogDescription>
              This will permanently delete the trader and all its configuration.
              This action cannot be undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction onClick={() => deleteMutation.mutate()}>
              {deleteMutation.isPending ? "Deleting..." : "Delete"}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}

function LoadingSkeleton() {
  return (
    <div class="space-y-2">
      <For each={[1, 2, 3, 4, 5]}>
        {() => <Skeleton class="h-12 w-full" />}
      </For>
    </div>
  );
}

const TradersPage: Component = () => {
  const tradersQuery = createQuery(() => ({
    queryKey: traderKeys.lists(),
    queryFn: () => api.listTraders(),
    refetchInterval: (query) => {
      const data = query.state.data;
      if (Array.isArray(data) && data.some((t) => t.status === "starting")) {
        return 2000; // Poll every 2s when starting
      }
      return false; // No auto-refresh otherwise
    },
  }));

  return (
    <ProtectedRoute>
      <AppShell>
        <div class="space-y-6">
          <div class="flex items-center justify-between">
            <div>
              <h1 class="text-2xl font-bold">Traders</h1>
              <p class="text-muted-foreground">All your trading bots</p>
            </div>
            <A href="/traders/new">
              <Button>
                <Plus class="h-4 w-4 mr-2" />
                New Trader
              </Button>
            </A>
          </div>

          <Suspense fallback={<LoadingSkeleton />}>
            <Show
              when={tradersQuery.data && tradersQuery.data.length > 0}
              fallback={
                <div class="text-center py-12 text-muted-foreground">
                  <p class="mb-4">No traders found</p>
                  <A href="/traders/new">
                    <Button>Create your first trader</Button>
                  </A>
                </div>
              }
            >
              <div class="space-y-4">
                <ImageVersionBanner traders={tradersQuery.data ?? []} />
                
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Name</TableHead>
                      <TableHead>Wallet</TableHead>
                      <TableHead>Status</TableHead>
                      <TableHead>Version</TableHead>
                      <TableHead>Created</TableHead>
                      <TableHead class="text-right">Actions</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    <For each={tradersQuery.data}>
                      {(trader) => (
                        <>
                          <TableRow>
                            <TableCell>
                              <A
                                href={`/traders/${trader.id}`}
                                class="font-medium hover:underline"
                              >
                                {trader.display_name}
                              </A>
                            </TableCell>
                            <TableCell class="font-mono text-xs truncate max-w-[200px]">
                              {trader.wallet_address}
                            </TableCell>
                            <TableCell>
                              <StatusBadge status={trader.status} />
                            </TableCell>
                            <TableCell class="font-mono text-xs">
                              {trader.image_tag}
                            </TableCell>
                            <TableCell>
                              {new Date(trader.created_at).toLocaleDateString()}
                            </TableCell>
                            <TableCell class="text-right">
                              <TraderActions trader={trader} />
                            </TableCell>
                          </TableRow>
                          <Show when={trader.status === "failed" && trader.last_error}>
                            <TableRow>
                              <TableCell colspan={6} class="bg-destructive/10 py-2">
                                <div class="flex items-start gap-2 text-sm">
                                  <AlertCircle class="h-4 w-4 text-destructive flex-shrink-0 mt-0.5" />
                                  <div class="text-destructive">
                                    <span class="font-medium">Error: </span>
                                    {trader.last_error}
                                  </div>
                                </div>
                              </TableCell>
                            </TableRow>
                          </Show>
                        </>
                      )}
                    </For>
                  </TableBody>
                </Table>
              </div>
            </Show>
          </Suspense>
        </div>
      </AppShell>
    </ProtectedRoute>
  );
};

export default TradersPage;
