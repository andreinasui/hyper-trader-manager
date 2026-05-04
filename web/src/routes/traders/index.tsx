import { type Component, Show, For, Suspense, createSignal } from "solid-js";
import { createQuery, createMutation, useQueryClient } from "@tanstack/solid-query";
import { A } from "@solidjs/router";
import { Play, Square, Trash2, RefreshCw, AlertCircle, Inbox } from "lucide-solid";
import { ProtectedRoute } from "~/components/auth/ProtectedRoute";
import { AppShell } from "~/components/layout/AppShell";
import { PageHeader } from "~/components/layout/PageHeader";
import { PageContent } from "~/components/layout/PageContent";
import { PageTitle } from "~/components/layout/PageTitle";
import { KpiCard, KpiStrip } from "~/components/ui/kpi-card";
import { EmptyState } from "~/components/ui/empty-state";
import { StatusDot, StatusIndicator } from "~/components/ui/status-badge";
import { ResponsiveTable, type ResponsiveTableColumn } from "~/components/ui/responsive-table";
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
  formatUptime,
  semverGt,
  shortWallet,
  canStart,
  canStop,
} from "~/components/traders/trader-page-utils";

// ── Row cells ─────────────────────────────────────────────────────────────────

function NameCell(props: { trader: Trader }) {
  const t = props.trader;
  return (
    <div class="min-w-0">
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
  );
}

function VersionCell(props: { trader: Trader }) {
  const imageQuery = createQuery(() => ({
    queryKey: imageKeys.versions(),
    queryFn: () => api.getImageVersions(),
  }));

  const remote = () => imageQuery.data?.latest_remote;
  const needsUpdate = () => {
    const r = remote();
    return r ? semverGt(r, props.trader.image_tag) : false;
  };

  return (
    <span class="flex items-center gap-1">
      <span class="font-mono text-xs text-text-subtle">{props.trader.image_tag}</span>
      <Show when={needsUpdate()}>
        <span
          class="h-1.5 w-1.5 rounded-full bg-warning flex-shrink-0"
          title={`Update to ${remote()}`}
        />
      </Show>
    </span>
  );
}

function RowActions(props: { trader: Trader }) {
  const qc = useQueryClient();
  const [deleteOpen, setDeleteOpen] = createSignal(false);

  const imageQuery = createQuery(() => ({
    queryKey: imageKeys.versions(),
    queryFn: () => api.getImageVersions(),
  }));

  const invalidate = () => qc.invalidateQueries({ queryKey: traderKeys.all });

  const startMut = createMutation(() => ({ mutationFn: () => api.startTrader(props.trader.id), onSuccess: invalidate }));
  const stopMut  = createMutation(() => ({ mutationFn: () => api.stopTrader(props.trader.id),  onSuccess: invalidate }));
  const delMut   = createMutation(() => ({ mutationFn: () => api.deleteTrader(props.trader.id), onSuccess: invalidate }));
  const updMut   = createMutation(() => ({
    mutationFn: (tag: string) => api.updateTraderImage(props.trader.id, tag),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: traderKeys.all });
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

  const t = props.trader;

  return (
    <div class="flex items-center gap-1">
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
            <div class="flex items-start gap-3">
              <div class="flex shrink-0 items-center justify-center size-9 rounded-lg bg-destructive/10 border border-destructive/20 mt-0.5">
                <Trash2 class="size-4 text-destructive" stroke-width={1.5} />
              </div>
              <div>
                <AlertDialogTitle>Delete Trader</AlertDialogTitle>
                <AlertDialogDescription>
                  Permanently deletes this trader and all configuration. Cannot be undone.
                </AlertDialogDescription>
              </div>
            </div>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction variant="destructive" onClick={() => delMut.mutate()}>
              {delMut.isPending ? "Deleting…" : "Delete"}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}

function ActivityCell(props: { trader: Trader }) {
  const statusQuery = createQuery(() => ({
    queryKey: traderKeys.status(props.trader.id),
    queryFn: () => api.getTraderStatus(props.trader.id),
    enabled: props.trader.status === "running",
    staleTime: 30_000,
  }));

  const value = () => {
    if (props.trader.status === "running") {
      return formatUptime(statusQuery.data?.runtime_status?.started_at);
    }
    if ((props.trader.status === "stopped" || props.trader.status === "failed") && props.trader.stopped_at) {
      return relTime(props.trader.stopped_at);
    }
    return relTime(props.trader.created_at);
  };

  return <span class="text-xs text-text-subtle">{value()}</span>;
}

function statusBorderClass(t: Trader): string {
  if (t.status === "running")  return "border-l-2 border-l-success bg-success/[0.02]";
  if (t.status === "failed")   return "border-l-2 border-l-error  bg-error/[0.03]";
  if (t.status === "starting") return "border-l-2 border-l-warning bg-warning/[0.03]";
  return "border-l-2 border-l-transparent hover:border-l-primary";
}

function FailedErrorRow(props: { trader: Trader }) {
  return (
    <Show when={props.trader.status === "failed" && props.trader.last_error}>
      <div class="bg-error/[0.06] px-4 py-2 flex items-start gap-2">
        <AlertCircle class="h-3.5 w-3.5 text-error flex-shrink-0 mt-0.5" stroke-width={1.5} />
        <span class="text-xs text-error font-mono">{props.trader.last_error}</span>
      </div>
    </Show>
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
    <div class="@container">
      <div class="bg-surface-raised border border-border-default rounded-md overflow-hidden">
        {/* Desktop skeleton */}
        <div class="hidden @md:block">
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
        {/* Phone skeleton */}
        <div class="@md:hidden">
          <For each={[1, 2, 3, 4]}>
            {() => (
              <div class="border-b border-border-default last:border-b-0 p-4 space-y-2">
                <div class="h-4 w-40 rounded bg-surface-overlay animate-pulse" />
                <div class="h-3 w-24 rounded bg-surface-overlay animate-pulse" />
                <div class="h-3 w-32 rounded bg-surface-overlay animate-pulse" />
              </div>
            )}
          </For>
        </div>
      </div>
    </div>
  );
}

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
            {/* KPI strip */}
            <KpiStrip>
              <KpiCard label="Total"   value={total()}   />
              <KpiCard label="Running" value={running()}  variant="success" />
              <KpiCard label="Failed"  value={failed()}   variant="error"   />
              <KpiCard label="Stopped" value={stopped()}  />
            </KpiStrip>

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

                  <ResponsiveTable
                    data={traders()}
                    rowKey={(t) => t.id}
                    rowClass={(t) => statusBorderClass(t) + " hover:bg-surface-overlay/40 transition-colors"}
                    rowExtra={(t) => <FailedErrorRow trader={t} />}
                    columns={[
                      { key: "name",     label: "Name",     span: 3, primary: true,
                        render: (t) => <NameCell trader={t} /> },
                      { key: "status",   label: "Status",   span: 2,
                        render: (t) => <StatusIndicator status={t.status} /> },
                      { key: "wallet",   label: "Wallet",   span: 2, hideOnPhone: true,
                        render: (t) => <span class="font-mono text-xs text-text-subtle">{shortWallet(t.wallet_address)}</span> },
                      { key: "activity", label: "Activity", span: 2,
                        render: (t) => <ActivityCell trader={t} /> },
                      { key: "version",  label: "Ver",      span: 1, hideOnPhone: true,
                        render: (t) => <VersionCell trader={t} /> },
                      { key: "actions",  label: "Actions",  span: 2, align: "end",
                        render: (t) => <RowActions trader={t} /> },
                    ]}
                  />
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
