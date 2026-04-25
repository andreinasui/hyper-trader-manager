import { type Component, Show, For, Suspense, createSignal } from "solid-js";
import { createQuery, createMutation, useQueryClient } from "@tanstack/solid-query";
import { A } from "@solidjs/router";
import { Play, Square, Trash2, Loader2, AlertCircle, RefreshCw, Inbox } from "lucide-solid";
import { ProtectedRoute } from "~/components/auth/ProtectedRoute";
import { AppShell } from "~/components/layout/AppShell";
import { PageHeader } from "~/components/layout/PageHeader";
import { PageContent } from "~/components/layout/PageContent";
import { PageTitle } from "~/components/layout/PageTitle";
import { Button } from "~/components/ui/button";
import { IconButton } from "~/components/ui/icon-button";
import { KpiCard, KpiStrip } from "~/components/ui/kpi-card";
import { EmptyState } from "~/components/ui/empty-state";
import { DataTable, DataTableRow } from "~/components/ui/data-table";
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

// Relative time helper — MUST be preserved
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
      <DataTableRow>
        {/* Name column */}
        <div class="col-span-3 flex items-center gap-2.5">
          <StatusDot status={props.trader.status} />
          <div class="min-w-0">
            <A
              href={`/traders/${props.trader.id}`}
              class="text-sm font-medium text-text-base hover:text-primary transition-colors"
            >
              {props.trader.display_name}
            </A>
            <Show when={props.trader.description}>
              <div class="text-xs text-text-subtle truncate">
                {props.trader.description}
              </div>
            </Show>
          </div>
        </div>

        {/* Wallet column */}
        <div class="col-span-3 font-mono text-sm text-text-subtle">
          {props.trader.wallet_address.slice(0, 6)}…{props.trader.wallet_address.slice(-4)}
        </div>

        {/* Status column */}
        <div class="col-span-2">
          <StatusIndicator status={props.trader.status} />
        </div>

        {/* Version column */}
        <div class="col-span-2 font-mono text-sm text-text-subtle">
          {props.trader.image_tag}
        </div>

        {/* Last activity + actions column */}
        <div class="col-span-2 flex items-center justify-between">
          <span class="text-sm text-text-subtle">{relTime(props.trader.created_at)}</span>

          <div class="row-actions flex items-center gap-1">
            <Show when={needsUpdate()}>
              <IconButton
                icon={RefreshCw}
                tooltip={`Update to ${imageQuery.data?.latest_remote}`}
                onClick={() => updateImageMutation.mutate(imageQuery.data!.latest_remote!)}
                disabled={isLoading()}
                loading={updateImageMutation.isPending}
              />
            </Show>

            <Show when={canStart()}>
              <IconButton
                icon={Play}
                tooltip={props.trader.status === "failed" ? "Retry" : "Start"}
                onClick={() => startMutation.mutate()}
                disabled={isLoading()}
                loading={startMutation.isPending}
              />
            </Show>

            <Show when={canStop()}>
              <IconButton
                icon={Square}
                tooltip="Stop"
                onClick={() => stopMutation.mutate()}
                disabled={isLoading()}
                loading={stopMutation.isPending}
              />
            </Show>

            <AlertDialog open={deleteOpen()} onOpenChange={setDeleteOpen}>
              <AlertDialogTrigger
                as={(triggerProps: Record<string, unknown>) => (
                  <IconButton
                    {...triggerProps}
                    icon={Trash2}
                    tooltip="Delete"
                    variant="danger"
                    disabled={isLoading()}
                  />
                )}
              />
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
        </div>
      </DataTableRow>

      {/* Error row */}
      <Show when={props.trader.status === "failed" && props.trader.last_error}>
        <div class="col-span-12 bg-error-surface px-4 py-2 border-b border-border-default flex items-start gap-2">
          <AlertCircle class="h-4 w-4 text-error flex-shrink-0 mt-0.5" stroke-width={1.5} />
          <span class="text-sm text-error">{props.trader.last_error}</span>
        </div>
      </Show>
    </>
  );
}

// Loading skeleton component
function LoadingSkeleton() {
  return (
    <div class="bg-surface-raised border border-border-default rounded-md overflow-hidden">
      {/* Column headers */}
      <div class="border-b border-border-default px-4 py-3 grid grid-cols-12 gap-4">
        <div class="col-span-3 text-xs font-medium text-text-subtle uppercase tracking-wide">Name</div>
        <div class="col-span-3 text-xs font-medium text-text-subtle uppercase tracking-wide">Wallet</div>
        <div class="col-span-2 text-xs font-medium text-text-subtle uppercase tracking-wide">Status</div>
        <div class="col-span-2 text-xs font-medium text-text-subtle uppercase tracking-wide">Version</div>
        <div class="col-span-2 text-xs font-medium text-text-subtle uppercase tracking-wide">Last activity</div>
      </div>

      {/* Skeleton rows */}
      <For each={[1, 2, 3, 4, 5]}>
        {() => (
          <div class="border-b border-border-default last:border-b-0 px-4 py-3 grid grid-cols-12 gap-4 items-center">
            <div class="col-span-3">
              <div class="h-4 w-32 rounded bg-surface-overlay animate-pulse" />
            </div>
            <div class="col-span-3">
              <div class="h-4 w-24 rounded bg-surface-overlay animate-pulse" />
            </div>
            <div class="col-span-2">
              <div class="h-4 w-16 rounded bg-surface-overlay animate-pulse" />
            </div>
            <div class="col-span-2">
              <div class="h-4 w-20 rounded bg-surface-overlay animate-pulse" />
            </div>
            <div class="col-span-2">
              <div class="h-4 w-16 rounded bg-surface-overlay animate-pulse" />
            </div>
          </div>
        )}
      </For>
    </div>
  );
}

const columns = [
  { key: "name", label: "Name", span: 3 },
  { key: "wallet", label: "Wallet", span: 3 },
  { key: "status", label: "Status", span: 2 },
  { key: "version", label: "Version", span: 2 },
  { key: "activity", label: "Last activity", span: 2 },
];

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
        <PageHeader breadcrumbs={[{ label: "Traders" }]} />
        <PageContent>
          <PageTitle
            title="Traders"
            subtitle="Manage and monitor your trading bots"
            action={
              <A href="/traders/new">
                <Button>
                  <Play class="h-4 w-4 mr-2" stroke-width={1.5} />
                  New trader
                </Button>
              </A>
            }
          />

          <KpiStrip class="mb-6">
            <KpiCard label="Total" value={totalCount()} />
            <KpiCard label="Running" value={runningCount()} variant="success" />
            <KpiCard label="Failed" value={failedCount()} variant="error" />
          </KpiStrip>

          <Suspense fallback={<LoadingSkeleton />}>
            <Show
              when={tradersQuery.data && tradersQuery.data.length > 0}
              fallback={
                <EmptyState
                  icon={Inbox}
                  title="No traders yet"
                  description="Get started by creating your first trading bot"
                  action={
                    <A href="/traders/new">
                      <Button>
                        <Play class="h-4 w-4 mr-2" stroke-width={1.5} />
                        New trader
                      </Button>
                    </A>
                  }
                />
              }
            >
              <div class="space-y-4">
                <ImageVersionBanner traders={tradersQuery.data ?? []} />
                <DataTable columns={columns}>
                  <For each={tradersQuery.data}>
                    {(trader) => <TraderRow trader={trader} />}
                  </For>
                </DataTable>
              </div>
            </Show>
          </Suspense>
        </PageContent>
      </AppShell>
    </ProtectedRoute>
  );
};

export default TradersPage;
