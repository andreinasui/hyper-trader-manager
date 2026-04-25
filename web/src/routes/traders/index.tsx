import { type Component, Show, For, Suspense, createSignal } from "solid-js";
import { createQuery, createMutation, useQueryClient } from "@tanstack/solid-query";
import { A } from "@solidjs/router";
import { Play, Square, Trash2, Loader2, AlertCircle, RefreshCw, Inbox, Command } from "lucide-solid";
import { ProtectedRoute } from "~/components/auth/ProtectedRoute";
import { AppShell } from "~/components/layout/AppShell";
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
import { api } from "~/lib/api";
import { traderKeys, imageKeys } from "~/lib/query-keys";
import type { Trader } from "~/lib/types";
import { ImageVersionBanner } from "~/components/traders/ImageVersionBanner";
import { StatusDot, StatusIndicator } from "~/components/ui/status-badge";

// Relative time helper
function relTime(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime();
  const m = Math.floor(diff / 60000);
  if (m < 1) return "just now";
  if (m < 60) return `${m}m ago`;
  const h = Math.floor(m / 60);
  if (h < 24) return `${h}h ago`;
  return `${Math.floor(h / 24)}d ago`;
}

// TraderRow component with all mutation logic
function TraderRow(props: { trader: Trader }) {
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
    <>
      <div class="v5-trader-row border-b border-[#222426] last:border-b-0 px-4 py-3 grid grid-cols-12 gap-4 items-center">
        {/* Name column */}
        <div class="col-span-3 flex items-center gap-2.5">
          <StatusDot status={props.trader.status} />
          <div class="min-w-0">
            <A
              href={`/traders/${props.trader.id}`}
              class="text-sm font-medium text-zinc-100 hover:text-[#5e6ad2] transition-colors"
            >
              {props.trader.display_name}
            </A>
            <Show when={props.trader.description}>
              <div class="text-xs text-zinc-500 truncate">
                {props.trader.description}
              </div>
            </Show>
          </div>
        </div>

        {/* Wallet column */}
        <div class="col-span-3 font-mono text-sm text-zinc-500">
          {props.trader.wallet_address.slice(0, 6)}…{props.trader.wallet_address.slice(-4)}
        </div>

        {/* Status column */}
        <div class="col-span-2">
          <StatusIndicator status={props.trader.status} />
        </div>

        {/* Version column */}
        <div class="col-span-2 font-mono text-sm text-zinc-500">
          {props.trader.image_tag}
        </div>

        {/* Last activity + actions column */}
        <div class="col-span-2 flex items-center justify-between">
          <span class="text-sm text-zinc-500">{relTime(props.trader.created_at)}</span>
          
          <div class="row-actions flex items-center gap-1">
            <Show when={needsUpdate()}>
              <button
                onClick={() => updateImageMutation.mutate(imageQuery.data!.latest_remote!)}
                disabled={isLoading()}
                title={`Update to ${imageQuery.data?.latest_remote}`}
                class="p-1.5 rounded hover:bg-[#1a1b1e] text-zinc-400 hover:text-zinc-200 transition-colors disabled:opacity-50"
              >
                <Show when={updateImageMutation.isPending} fallback={<RefreshCw class="h-4 w-4" stroke-width={1.5} />}>
                  <Loader2 class="h-4 w-4 animate-spin" stroke-width={1.5} />
                </Show>
              </button>
            </Show>

            <Show when={canStart()}>
              <button
                onClick={() => startMutation.mutate()}
                disabled={isLoading()}
                title={props.trader.status === "failed" ? "Retry" : "Start"}
                class="p-1.5 rounded hover:bg-[#1a1b1e] text-zinc-400 hover:text-zinc-200 transition-colors disabled:opacity-50"
              >
                <Show when={startMutation.isPending} fallback={<Play class="h-4 w-4" stroke-width={1.5} />}>
                  <Loader2 class="h-4 w-4 animate-spin" stroke-width={1.5} />
                </Show>
              </button>
            </Show>

            <Show when={canStop()}>
              <button
                onClick={() => stopMutation.mutate()}
                disabled={isLoading()}
                title="Stop"
                class="p-1.5 rounded hover:bg-[#1a1b1e] text-zinc-400 hover:text-zinc-200 transition-colors disabled:opacity-50"
              >
                <Show when={stopMutation.isPending} fallback={<Square class="h-4 w-4" stroke-width={1.5} />}>
                  <Loader2 class="h-4 w-4 animate-spin" stroke-width={1.5} />
                </Show>
              </button>
            </Show>

            <AlertDialog open={deleteOpen()} onOpenChange={setDeleteOpen}>
              <AlertDialogTrigger
                as={(props: any) => (
                  <button
                    {...props}
                    disabled={isLoading()}
                    title="Delete"
                    class="p-1.5 rounded hover:bg-[#1a1b1e] text-zinc-400 hover:text-red-400 transition-colors disabled:opacity-50"
                  >
                    <Trash2 class="h-4 w-4" stroke-width={1.5} />
                  </button>
                )}
              />
              <AlertDialogContent class="bg-[#111214] border border-[#222426]">
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
        </div>
      </div>

      {/* Error row */}
      <Show when={props.trader.status === "failed" && props.trader.last_error}>
        <div class="col-span-12 bg-red-950/20 px-4 py-2 border-b border-[#222426] flex items-start gap-2">
          <AlertCircle class="h-4 w-4 text-red-400 flex-shrink-0 mt-0.5" stroke-width={1.5} />
          <span class="text-sm text-red-400">{props.trader.last_error}</span>
        </div>
      </Show>
    </>
  );
}

// Loading skeleton component
function LoadingSkeleton() {
  return (
    <div class="bg-[#111214] border border-[#222426] rounded-md overflow-hidden">
      {/* Column headers */}
      <div class="border-b border-[#222426] px-4 py-3 grid grid-cols-12 gap-4">
        <div class="col-span-3 text-xs font-medium text-zinc-500 uppercase tracking-wide">Name</div>
        <div class="col-span-3 text-xs font-medium text-zinc-500 uppercase tracking-wide">Wallet</div>
        <div class="col-span-2 text-xs font-medium text-zinc-500 uppercase tracking-wide">Status</div>
        <div class="col-span-2 text-xs font-medium text-zinc-500 uppercase tracking-wide">Version</div>
        <div class="col-span-2 text-xs font-medium text-zinc-500 uppercase tracking-wide">Last activity</div>
      </div>
      
      {/* Skeleton rows */}
      <For each={[1, 2, 3, 4, 5]}>
        {() => (
          <div class="border-b border-[#222426] last:border-b-0 px-4 py-3 grid grid-cols-12 gap-4 items-center">
            <div class="col-span-3">
              <div class="h-4 w-32 rounded bg-[#1a1b1e] animate-pulse" />
            </div>
            <div class="col-span-3">
              <div class="h-4 w-24 rounded bg-[#1a1b1e] animate-pulse" />
            </div>
            <div class="col-span-2">
              <div class="h-4 w-16 rounded bg-[#1a1b1e] animate-pulse" />
            </div>
            <div class="col-span-2">
              <div class="h-4 w-20 rounded bg-[#1a1b1e] animate-pulse" />
            </div>
            <div class="col-span-2">
              <div class="h-4 w-16 rounded bg-[#1a1b1e] animate-pulse" />
            </div>
          </div>
        )}
      </For>
    </div>
  );
}

// Main page component
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

  // Compute KPI counts
  const totalCount = () => tradersQuery.data?.length ?? 0;
  const runningCount = () => tradersQuery.data?.filter(t => t.status === "running").length ?? 0;
  const failedCount = () => tradersQuery.data?.filter(t => t.status === "failed").length ?? 0;

  return (
    <ProtectedRoute>
      <AppShell>
        {/* Scoped styles for V5 hover interactions */}
        <style>{`
          .v5-trader-row {
            border-left: 2px solid transparent;
            transition: background-color 150ms ease, border-color 150ms ease;
          }
          .v5-trader-row:hover {
            background-color: #111214;
            border-left-color: #5e6ad2;
          }
          .v5-trader-row .row-actions {
            opacity: 0;
            transition: opacity 150ms ease;
          }
          .v5-trader-row:hover .row-actions {
            opacity: 1;
          }
        `}</style>

        {/* Top bar strip */}
        <div class="sticky top-0 z-20 h-14 border-b border-[#222426] bg-[#08090a] flex items-center justify-between px-6">
          {/* Breadcrumb */}
          <div class="flex items-center gap-2 text-sm">
            <span class="text-zinc-500">Workspace</span>
            <span class="text-zinc-500">/</span>
            <span class="text-zinc-300">Traders</span>
          </div>
          
          {/* Command button */}
          <button class="border border-[#222426] text-zinc-400 hover:text-zinc-200 hover:bg-[#111214] rounded-md px-3 py-1.5 text-sm transition-all inline-flex items-center gap-2">
            <Command class="h-3.5 w-3.5" stroke-width={1.5} />
            <span>K</span>
          </button>
        </div>

        {/* Page content */}
        <div class="p-6 max-w-7xl">
          {/* Page header */}
          <div class="flex items-start justify-between mb-6">
            <div>
              <h1 class="text-2xl font-semibold tracking-tight text-zinc-50">Traders</h1>
              <p class="text-sm text-zinc-500 mt-1">Manage and monitor your trading bots</p>
            </div>
            <A href="/traders/new">
              <button class="bg-[#5e6ad2] hover:bg-[#6b76d9] text-white rounded-md px-3 py-2 text-sm font-medium inline-flex items-center gap-2 transition-all">
                <Play class="h-4 w-4" stroke-width={1.5} />
                New trader
              </button>
            </A>
          </div>

          {/* KPI strip */}
          <div class="grid grid-cols-3 gap-4 mb-6">
            {/* Total */}
            <div class="bg-[#111214] border border-[#222426] rounded-md p-4 hover:bg-[#1a1b1e] transition-all">
              <div class="flex items-center gap-2 mb-2">
                <div class="w-1.5 h-1.5 rounded-full bg-zinc-500" />
                <span class="text-xs font-medium text-zinc-500 uppercase tracking-wide">Total</span>
              </div>
              <div class="text-2xl font-semibold tabular-nums text-zinc-50">{totalCount()}</div>
            </div>

            {/* Running */}
            <div class="bg-[#111214] border border-[#222426] rounded-md p-4 hover:bg-[#1a1b1e] transition-all">
              <div class="flex items-center gap-2 mb-2">
                <div class="w-1.5 h-1.5 rounded-full bg-emerald-400" />
                <span class="text-xs font-medium text-zinc-500 uppercase tracking-wide">Running</span>
              </div>
              <div class="text-2xl font-semibold tabular-nums text-zinc-50">{runningCount()}</div>
            </div>

            {/* Failed */}
            <div class="bg-[#111214] border border-[#222426] rounded-md p-4 hover:bg-[#1a1b1e] transition-all">
              <div class="flex items-center gap-2 mb-2">
                <div class="w-1.5 h-1.5 rounded-full bg-red-400" />
                <span class="text-xs font-medium text-zinc-500 uppercase tracking-wide">Failed</span>
              </div>
              <div class="text-2xl font-semibold tabular-nums text-zinc-50">{failedCount()}</div>
            </div>
          </div>

          {/* Main content */}
          <Suspense fallback={<LoadingSkeleton />}>
            <Show
              when={tradersQuery.data && tradersQuery.data.length > 0}
              fallback={
                <div class="bg-[#111214] border border-[#222426] rounded-md p-12 flex flex-col items-center justify-center text-center">
                  <div class="bg-[#1a1b1e] rounded-md p-3 mb-4">
                    <Inbox class="w-10 h-10 text-zinc-500" stroke-width={1.5} />
                  </div>
                  <h3 class="text-base font-semibold text-zinc-200 mb-1">No traders yet</h3>
                  <p class="text-sm text-zinc-500 mb-4">Get started by creating your first trading bot</p>
                  <A href="/traders/new">
                    <button class="bg-[#5e6ad2] hover:bg-[#6b76d9] text-white rounded-md px-3 py-2 text-sm font-medium inline-flex items-center gap-2 transition-all">
                      <Play class="h-4 w-4" stroke-width={1.5} />
                      New trader
                    </button>
                  </A>
                </div>
              }
            >
              <div class="space-y-4">
                {/* Image version banner */}
                <ImageVersionBanner traders={tradersQuery.data ?? []} />

                {/* Trader list */}
                <div class="bg-[#111214] border border-[#222426] rounded-md overflow-hidden">
                  {/* Column headers */}
                  <div class="border-b border-[#222426] px-4 py-3 grid grid-cols-12 gap-4">
                    <div class="col-span-3 text-xs font-medium text-zinc-500 uppercase tracking-wide">Name</div>
                    <div class="col-span-3 text-xs font-medium text-zinc-500 uppercase tracking-wide">Wallet</div>
                    <div class="col-span-2 text-xs font-medium text-zinc-500 uppercase tracking-wide">Status</div>
                    <div class="col-span-2 text-xs font-medium text-zinc-500 uppercase tracking-wide">Version</div>
                    <div class="col-span-2 text-xs font-medium text-zinc-500 uppercase tracking-wide">Last activity</div>
                  </div>

                  {/* Trader rows */}
                  <For each={tradersQuery.data}>
                    {(trader) => <TraderRow trader={trader} />}
                  </For>
                </div>
              </div>
            </Show>
          </Suspense>
        </div>
      </AppShell>
    </ProtectedRoute>
  );
};

export default TradersPage;
