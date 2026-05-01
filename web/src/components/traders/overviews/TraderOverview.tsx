import { Show, type Component, type JSX, createSignal } from "solid-js";
import type { Trader, TraderStatusResponse, RuntimeStatus } from "~/lib/types";
import { Panel, PanelBody } from "~/components/ui/panel";
import { Input } from "~/components/ui/input";
import { Textarea } from "~/components/ui/textarea";
import { Button } from "~/components/ui/button";
import { StatusDot } from "~/components/ui/status-badge";
import { AlertCircle, Clock, Tag, Wallet, Copy, Check } from "lucide-solid";
import type { UseQueryResult } from "@tanstack/solid-query";

export interface OverviewDesignProps {
  trader: Trader;
  currentStatus: () => Trader["status"] | RuntimeStatus["state"];
  statusQuery: UseQueryResult<TraderStatusResponse, Error>;
  editName: () => string;
  editDescription: () => string;
  handleNameChange: (v: string) => void;
  handleDescriptionChange: (v: string) => void;
  infoChanged: () => boolean;
  infoError: () => string | null;
  handleInfoSave: () => void;
  updateInfoMutation: { isPending: boolean };
  needsImageUpdate: () => boolean;
  imageQuery: { data?: { latest_remote?: string | null } };
  formatUptime: (startedAt: string) => string;
}

function relDate(iso: string): string {
  return new Date(iso).toLocaleDateString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

function truncateAddress(address: string): string {
  if (address.length <= 16) return address;
  return `${address.slice(0, 8)}...${address.slice(-6)}`;
}

function getStatusTextClass(status: string): string {
  switch (status) {
    case "running": return "text-emerald-400";
    case "failed": case "error": return "text-red-400";
    case "starting": case "pending": case "restarting": return "text-amber-400";
    default: return "text-zinc-400";
  }
}

function getStatusLabel(status: string): string {
  const labels: Record<string, string> = {
    configured: "Configured", starting: "Starting", running: "Running",
    stopped: "Stopped", failed: "Failed", pending: "Pending",
    restarting: "Restarting", error: "Error", not_found: "Not Found", unknown: "Unknown",
  };
  return labels[status] ?? status;
}

interface MetricTileProps {
  label: string;
  value: JSX.Element;
  accent?: boolean;
  icon?: Component<{ class?: string }>;
}

function MetricTile(props: MetricTileProps) {
  return (
    <div
      class={`flex-1 px-6 py-4 border-r border-border-default last:border-r-0 transition-colors hover:bg-surface-overlay/40 ${props.accent ? "border-l-2 border-l-primary bg-primary/5" : ""}`}
    >
      <div class="flex items-center gap-2 mb-2">
        {props.icon?.({ class: "w-3.5 h-3.5 text-text-subtle" })}
        <div class="text-[10px] text-text-subtle font-medium uppercase tracking-wider">
          {props.label}
        </div>
      </div>
      <div class="font-mono text-sm text-text-secondary">{props.value}</div>
    </div>
  );
}

const TraderOverview: Component<OverviewDesignProps> = (props) => {
  const status = () => props.currentStatus();
  const [walletCopied, setWalletCopied] = createSignal(false);

  const copyWallet = () => {
    navigator.clipboard.writeText(props.trader.wallet_address).then(() => {
      setWalletCopied(true);
      setTimeout(() => setWalletCopied(false), 1500);
    });
  };

  const uptimeOrCreated = () => {
    const startedAt = props.statusQuery.data?.runtime_status?.started_at;
    if (status() === "running" && startedAt) {
      return props.formatUptime(startedAt);
    }
    return relDate(props.trader.created_at);
  };

  const uptimeLabel = () => {
    const startedAt = props.statusQuery.data?.runtime_status?.started_at;
    return status() === "running" && startedAt ? "Uptime" : "Created";
  };

  const imageVersion = () => {
    const current = props.trader.image_tag;
    if (props.needsImageUpdate() && props.imageQuery.data?.latest_remote) {
      return (
        <span class="flex items-center gap-2">
          <span class="text-text-muted">{current}</span>
          <span class="text-warning text-xs">→ {props.imageQuery.data.latest_remote}</span>
        </span>
      ) as JSX.Element;
    }
    return <span>{current || "—"}</span>;
  };

  return (
    <div class="space-y-6">
      {/* Metric Strip - Trading Terminal Style */}
      <div class="bg-surface-raised border border-border-default rounded-lg overflow-hidden">
        <div class="flex divide-x divide-border-default">
          <MetricTile
            label="Status"
            accent={true}
            value={
              <div class="flex items-center gap-2">
                <StatusDot status={status()} />
                <span class={`font-semibold ${getStatusTextClass(status())}`}>
                  {getStatusLabel(status())}
                </span>
                <Show when={props.statusQuery.data?.runtime_status?.error}>
                  <AlertCircle class="w-4 h-4 text-error ml-1" />
                </Show>
              </div>
            }
          />

          <MetricTile
            label={uptimeLabel()}
            icon={Clock}
            value={<span>{uptimeOrCreated()}</span>}
          />

          <MetricTile
            label="Image Version"
            icon={Tag}
            value={imageVersion()}
          />

          <MetricTile
            label="Wallet Address"
            icon={Wallet}
            value={
              <div class="flex items-center gap-2">
                <span title={props.trader.wallet_address}>
                  {truncateAddress(props.trader.wallet_address)}
                </span>
                <button
                  onClick={copyWallet}
                  title={walletCopied() ? "Copied!" : "Copy address"}
                  class="flex items-center justify-center w-5 h-5 rounded text-text-subtle hover:text-text-secondary hover:bg-surface-overlay transition-colors cursor-pointer"
                >
                  <Show
                    when={walletCopied()}
                    fallback={<Copy class="w-3 h-3" stroke-width={1.5} />}
                  >
                    <Check class="w-3 h-3 text-success" stroke-width={2} />
                  </Show>
                </button>
              </div>
            }
          />
        </div>
      </div>

      {/* Error Display */}
      <Show when={props.statusQuery.data?.runtime_status?.error}>
        <div class="bg-error/10 border border-error/30 rounded-lg p-4">
          <div class="flex items-start gap-3">
            <AlertCircle class="w-5 h-5 text-error flex-shrink-0 mt-0.5" />
            <div class="flex-1 min-w-0">
              <div class="text-sm font-medium text-error mb-1">Runtime Error</div>
              <div class="text-sm text-text-secondary font-mono break-all">
                {props.statusQuery.data?.runtime_status?.error}
              </div>
            </div>
          </div>
        </div>
      </Show>

      {/* Persisted last_error (e.g., crash/start-failure recorded in DB).
          Shown only when no live runtime_status.error is available, to avoid
          duplicating the same message. */}
      <Show
        when={
          props.trader.status === "failed" &&
          props.trader.last_error &&
          !props.statusQuery.data?.runtime_status?.error
        }
      >
        <div class="bg-error/10 border border-error/30 rounded-lg p-4">
          <div class="flex items-start gap-3">
            <AlertCircle class="w-5 h-5 text-error flex-shrink-0 mt-0.5" />
            <div class="flex-1 min-w-0">
              <div class="text-sm font-medium text-error mb-1">Last error</div>
              <div class="text-sm text-text-secondary font-mono break-all">
                {props.trader.last_error}
              </div>
            </div>
          </div>
        </div>
      </Show>

      {/* Trader Info Panel */}
      <Panel>
        <div class="px-5 py-3.5 border-b border-border-default">
          <span class="text-sm font-medium text-text-secondary">Trader Information</span>
        </div>
        <PanelBody>
          <div class="space-y-4">
            <div>
              <label class="block text-sm font-medium text-text-secondary mb-2">Name</label>
              <Input
                value={props.editName()}
                onInput={(e) => props.handleNameChange(e.currentTarget.value)}
                placeholder="Enter trader name"
                maxLength={50}
              />
            </div>

            <div>
              <label class="block text-sm font-medium text-text-secondary mb-2">Description</label>
              <Textarea
                value={props.editDescription()}
                onInput={(e) => props.handleDescriptionChange(e.currentTarget.value)}
                placeholder="Optional description"
                rows={3}
                maxLength={255}
              />
            </div>

            <Show when={props.infoError()}>
              <div class="bg-error/10 border border-error/30 rounded px-3 py-2">
                <div class="flex items-center gap-2">
                  <AlertCircle class="w-4 h-4 text-error flex-shrink-0" />
                  <span class="text-sm text-error">{props.infoError()}</span>
                </div>
              </div>
            </Show>

            <Show when={props.infoChanged()}>
              <div class="flex justify-end pt-2">
                <Button
                  onClick={props.handleInfoSave}
                  disabled={props.updateInfoMutation.isPending}
                >
                  {props.updateInfoMutation.isPending ? "Saving..." : "Save"}
                </Button>
              </div>
            </Show>
          </div>
        </PanelBody>
      </Panel>

      {/* Timestamps */}
      <div class="flex items-center gap-6 text-xs text-text-muted font-mono">
        <div class="flex items-center gap-2">
          <span class="text-text-subtle">Created:</span>
          <span>{relDate(props.trader.created_at)}</span>
        </div>
        <div class="flex items-center gap-2">
          <span class="text-text-subtle">Updated:</span>
          <span>{relDate(props.trader.updated_at)}</span>
        </div>
      </div>
    </div>
  );
};

export default TraderOverview;
