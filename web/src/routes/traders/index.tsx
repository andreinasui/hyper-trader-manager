import { type Component, Show, For, Suspense, createSignal } from "solid-js";
import { createQuery, createMutation, useQueryClient } from "@tanstack/solid-query";
import { A } from "@solidjs/router";
import { Play, Square, Trash2, RefreshCw, AlertCircle, Inbox } from "lucide-solid";
import { ProtectedRoute } from "~/components/auth/ProtectedRoute";
import { AppShell } from "~/components/layout/AppShell";
import { PageHeader } from "~/components/layout/PageHeader";
import { PageContent } from "~/components/layout/PageContent";
import { PageTitle } from "~/components/layout/PageTitle";
import { KpiCard } from "~/components/ui/kpi-card";
import { EmptyState } from "~/components/ui/empty-state";
import { StatusDot, StatusIndicator } from "~/components/ui/status-badge";
import { Button } from "~/components/ui/button";
import { IconButton } from "~/components/ui/icon-button";
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
import {
  relTime,
  semverGt,
  shortWallet,
  canStart,
  canStop,
} from "~/components/traders/trader-page-utils";

// ── Row ───────────────────────────────────────────────────────────────────────

function TraderRow(props: { trader: Trader }) {
  const qc = useQueryClient();
  const [deleteOpen, setDeleteOpen] = createSignal(false);

  const imageQuery = createQuery(() => ({
    queryKey: imageKeys.versions(),
    queryFn: () => api.getImageVersions(),
  }));

  const invalidate = () => qc.invalidateQueries({ queryKey: traderKeys.lists() });

  const startMut = createMutation(() => ({ mutationFn: () => api.startTrader(props.trader.id), onSuccess: invalidate }));
  const stopMut  = createMutation(() => ({ mutationFn: () => api.stopTrader(props.trader.id),  onSuccess: invalidate }));
  const delMut   = createMutation(() => ({ mutationFn: () => api.deleteTrader(props.trader.id), onSuccess: invalidate }));
  const updMut   = createMutation(() => ({
    mutationFn: (tag: string) => api.updateTraderImage(props.trader.id, tag),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: traderKeys.lists() });
      qc.invalidateQueries({ queryKey: imageKeys.versions() });
    },
  }));

  const remote = () => imageQuery.data?.latest_remote;
  const needsUpdate = () => {
    const r = remote();
    return r ? semverGt(r, props.trader.image_tag) : false;
  };

  const busy = () =>
    startMut.isPending || stopMut.isPending || delMut.isPending || updMut.isPending;

  const activity = () => {
    const t = props.trader;
    if (t.status === "running") return relTime(t.updated_at);
    if ((t.status === "stopped" || t.status === "failed") && t.stopped_at)
      return relTime(t.stopped_at);
    return relTime(t.created_at);
  };

  const t = props.trader;

  return (
    <>
      {/* Row */}
      <div
        class={`
          border-b border-border-default last:border-b-0
          px-4 py-2.5 grid grid-cols-12 gap-3 items-center
          border-l-2 transition-colors
          ${t.status === "running"  ? "border-l-success bg-success/[0.02]"  : ""}
          ${t.status === "failed"   ? "border-l-error  bg-error/[0.03]"     : ""}
          ${t.status === "starting" ? "border-l-warning bg-warning/[0.03]"  : ""}
          ${!["running", "failed", "starting"].includes(t.status) ? "border-l-transparent hover:border-l-primary" : ""}
          hover:bg-surface-overlay/40
        `}
      >
        {/* Name (3) */}
        <div class="col-span-3 min-w-0">
          <div class="flex items-center gap-2">
            <StatusDot status={t.status} />
            <A
              href={`/traders/${t.id}`}
              class="text-sm font-medium text-text-base hover:text-primary transition-colors truncate"
            >
              {t.display_name}
            </A>

          </div>
          <Show when={t.description}>
            <div class="text-xs text-text-subtle truncate pl-4 mt-0.5">{t.description}</div>
          </Show>
        </div>

        {/* Status (2) */}
        <div class="col-span-2">
          <StatusIndicator status={t.status} />
        </div>

        {/* Wallet (2) */}
        <div class="col-span-2 font-mono text-xs text-text-subtle">
          {shortWallet(t.wallet_address)}
        </div>

        {/* Activity (2) */}
        <div class="col-span-2 text-xs text-text-subtle">{activity()}</div>

        {/* Version (1) */}
        <div class="col-span-1 flex items-center gap-1">
          <span class="font-mono text-xs text-text-subtle">{t.image_tag}</span>
          <Show when={needsUpdate()}>
            <span
              class="h-1.5 w-1.5 rounded-full bg-warning flex-shrink-0"
              title={`Update to ${remote()}`}
            />
          </Show>
        </div>

        {/* Actions (2) — always visible */}
        <div class="col-span-2 flex items-center gap-1 justify-end">
          <Show when={needsUpdate()}>
            <IconButton
              icon={RefreshCw}
              tooltip={`Update to ${remote()}`}
              onClick={() => updMut.mutate(remote()!)}
              disabled={busy()}
              loading={updMut.isPending}
            />
          </Show>
          <Show when={canStart(t)}>
            <IconButton
              icon={Play}
              tooltip={t.status === "failed" ? "Retry" : "Start"}
              onClick={() => startMut.mutate()}
              disabled={busy()}
              loading={startMut.isPending}
            />
          </Show>
          <Show when={canStop(t)}>
            <IconButton
              icon={Square}
              tooltip="Stop"
              onClick={() => stopMut.mutate()}
              disabled={busy()}
              loading={stopMut.isPending}
            />
          </Show>
          <AlertDialog open={deleteOpen()} onOpenChange={setDeleteOpen}>
            <AlertDialogTrigger
              as={(p: Record<string, unknown>) => (
                <IconButton {...p} icon={Trash2} tooltip="Delete" variant="danger" disabled={busy()} />
              )}
            />
            <AlertDialogContent>
              <AlertDialogHeader>
                <AlertDialogTitle>Delete Trader</AlertDialogTitle>
                <AlertDialogDescription>
                  Permanently deletes this trader and all configuration. Cannot be undone.
                </AlertDialogDescription>
              </AlertDialogHeader>
              <AlertDialogFooter>
                <AlertDialogCancel>Cancel</AlertDialogCancel>
                <AlertDialogAction onClick={() => delMut.mutate()}>
                  {delMut.isPending ? "Deleting…" : "Delete"}
                </AlertDialogAction>
              </AlertDialogFooter>
            </AlertDialogContent>
          </AlertDialog>
        </div>
      </div>

      {/* Error row */}
      <Show when={t.status === "failed" && t.last_error}>
        <div class="col-span-12 border-b border-border-default bg-error/[0.06] px-4 py-2 flex items-start gap-2">
          <AlertCircle class="h-3.5 w-3.5 text-error flex-shrink-0 mt-0.5" stroke-width={1.5} />
          <span class="text-xs text-error font-mono">{t.last_error}</span>
        </div>
      </Show>
    </>
  );
}

// ── Skeleton ──────────────────────────────────────────────────────────────────

function LoadingSkeleton() {
  const cols = [
    { label: "Name",     span: 3 },
    { label: "Status",   span: 2 },
    { label: "Wallet",   span: 2 },
    { label: "Activity", span: 2 },
    { label: "Ver",      span: 1 },
    { label: "Actions",  span: 2 },
  ];
  return (
    <div class="bg-surface-raised border border-border-default rounded-md overflow-hidden">
      <div class="border-b border-border-default px-4 py-2 grid grid-cols-12 gap-3">
        <For each={cols}>
          {(col) => (
            <div
              class={`col-span-${col.span} text-[10px] font-medium text-text-subtle uppercase tracking-widest ${col.label === "Actions" ? "text-right" : ""}`}
            >
              {col.label}
            </div>
          )}
        </For>
      </div>
      <For each={[1, 2, 3, 4]}>
        {() => (
          <div class="border-b border-border-default last:border-b-0 px-4 py-2.5 grid grid-cols-12 gap-3 items-center">
            <div class="col-span-3"><div class="h-3.5 w-28 rounded bg-surface-overlay animate-pulse" /></div>
            <div class="col-span-2"><div class="h-3.5 w-16 rounded bg-surface-overlay animate-pulse" /></div>
            <div class="col-span-2"><div class="h-3.5 w-20 rounded bg-surface-overlay animate-pulse" /></div>
            <div class="col-span-2"><div class="h-3.5 w-14 rounded bg-surface-overlay animate-pulse" /></div>
            <div class="col-span-1"><div class="h-3.5 w-10 rounded bg-surface-overlay animate-pulse" /></div>
            <div class="col-span-2"><div class="h-3.5 w-16 rounded bg-surface-overlay animate-pulse ml-auto" /></div>
          </div>
        )}
      </For>
    </div>
  );
}

// ── Table header columns ──────────────────────────────────────────────────────

const columns = [
  { label: "Name",     span: 3 },
  { label: "Status",   span: 2 },
  { label: "Wallet",   span: 2 },
  { label: "Activity", span: 2 },
  { label: "Ver",      span: 1 },
  { label: "Actions",  span: 2 },
];

// ── Page ──────────────────────────────────────────────────────────────────────

const TradersPage: Component = () => {
  const tradersQuery = createQuery(() => ({
    queryKey: traderKeys.lists(),
    queryFn: () => api.listTraders(),
    refetchInterval: (q) =>
      Array.isArray(q.state.data) && q.state.data.some((t) => t.status === "starting")
        ? 2000
        : false,
  }));

  const traders = () => tradersQuery.data ?? [];
  const total   = () => traders().length;
  const running = () => traders().filter((t) => t.status === "running").length;
  const failed  = () => traders().filter((t) => t.status === "failed").length;
  const stopped = () => traders().filter((t) => t.status === "stopped").length;

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

          <div class="space-y-6">
            {/* KPI strip — 4 cards */}
            <div class="grid grid-cols-4 gap-4">
              <KpiCard label="Total"   value={total()}   />
              <KpiCard label="Running" value={running()}  variant="success" />
              <KpiCard label="Failed"  value={failed()}   variant="error"   />
              <KpiCard label="Stopped" value={stopped()}  />
            </div>

            <Suspense fallback={<LoadingSkeleton />}>
              <Show
                when={traders().length > 0}
                fallback={
                  <EmptyState
                    icon={Inbox}
                    title="No traders yet"
                    description="Create your first trading bot to get started"
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
                <div class="space-y-3">
                  <ImageVersionBanner traders={traders()} />

                  {/* Table */}
                  <div class="bg-surface-raised border border-border-default rounded-md overflow-hidden">
                    {/* Header */}
                    <div class="border-b border-border-default px-4 py-2 grid grid-cols-12 gap-3">
                      <For each={columns}>
                        {(col) => (
                          <div
                            class={`col-span-${col.span} text-[10px] font-medium text-text-subtle uppercase tracking-widest ${col.label === "Actions" ? "text-right" : ""}`}
                          >
                            {col.label}
                          </div>
                        )}
                      </For>
                    </div>
                    {/* Rows */}
                    <For each={traders()}>
                      {(trader) => <TraderRow trader={trader} />}
                    </For>
                  </div>
                </div>
              </Show>
            </Suspense>
          </div>
        </PageContent>
      </AppShell>
    </ProtectedRoute>
  );
};

export default TradersPage;
