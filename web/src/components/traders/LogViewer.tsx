import { type Component, For, createSignal, Show } from "solid-js";
import { createQuery } from "@tanstack/solid-query";
import { RefreshCw, Download } from "lucide-solid";
import { Button } from "~/components/ui/button";
import { api } from "~/lib/api";
import { traderKeys } from "~/lib/query-keys";

interface LogViewerProps {
  traderId: string;
}

type LogMode = "live" | "range";

const PRESETS = [
  { label: "1h", hours: 1 },
  { label: "6h", hours: 6 },
  { label: "24h", hours: 24 },
  { label: "7d", hours: 24 * 7 },
] as const;

export const LogViewer: Component<LogViewerProps> = (props) => {
  const [mode, setMode] = createSignal<LogMode>("live");
  const [since, setSince] = createSignal("");
  const [until, setUntil] = createSignal("");
  const [activePreset, setActivePreset] = createSignal<string | null>(null);
  const [downloading, setDownloading] = createSignal(false);

  const logsQuery = createQuery(() => ({
    queryKey: traderKeys.logs(
      props.traderId,
      mode() === "range" ? since() : undefined,
      mode() === "range" ? until() : undefined,
    ),
    queryFn: () =>
      mode() === "live"
        ? api.getTraderLogs(props.traderId)
        : api.getTraderLogs(props.traderId, { since: since(), until: until() }),
    refetchInterval: mode() === "live" ? 5000 : false,
  }));

  function applyPreset(label: string, hours: number) {
    const now = new Date();
    const from = new Date(now.getTime() - hours * 60 * 60 * 1000);
    setSince(from.toISOString());
    setUntil(now.toISOString());
    setMode("range");
    setActivePreset(label);
  }

  function resetToLive() {
    setMode("live");
    setSince("");
    setUntil("");
    setActivePreset(null);
  }

  async function handleDownload() {
    setDownloading(true);
    try {
      const sinceVal =
        mode() === "range" && since()
          ? since()
          : new Date(Date.now() - 24 * 60 * 60 * 1000).toISOString();
      const untilVal =
        mode() === "range" && until() ? until() : new Date().toISOString();
      await api.downloadTraderLogs(props.traderId, sinceVal, untilVal);
    } finally {
      setDownloading(false);
    }
  }

  return (
    <div>
      {/* Header */}
      <div class="flex items-center justify-between px-5 py-3.5 border-b border-border-default">
        <h3 class="text-sm font-medium text-text-secondary">Logs</h3>
        <Button
          variant="outline"
          size="sm"
          onClick={() => logsQuery.refetch()}
          disabled={logsQuery.isFetching}
        >
          <RefreshCw class={`h-4 w-4 mr-2 ${logsQuery.isFetching ? "animate-spin" : ""}`} />
          Refresh
        </Button>
      </div>

      {/* Time range controls */}
      <div class="px-5 py-3 border-b border-border-default space-y-2">
        <div class="flex items-center gap-2 flex-wrap">
          <span class="text-xs text-text-muted">Range:</span>
          <For each={PRESETS}>
            {(preset) => (
              <Button
                variant={activePreset() === preset.label ? "default" : "outline"}
                size="sm"
                class="h-6 px-2 text-xs"
                onClick={() => applyPreset(preset.label, preset.hours)}
              >
                {preset.label}
              </Button>
            )}
          </For>
          <Show when={mode() === "range"}>
            <Button
              variant="ghost"
              size="sm"
              class="h-6 px-2 text-xs text-text-muted"
              onClick={resetToLive}
            >
              Live
            </Button>
          </Show>
        </div>
        <div class="flex items-center gap-2 flex-wrap">
          <input
            type="datetime-local"
            class="text-xs border border-border-default rounded px-2 py-1 bg-surface-base text-text-primary"
            value={since() ? since().slice(0, 16) : ""}
            onChange={(e) => {
              setSince(e.target.value ? new Date(e.target.value).toISOString() : "");
              if (e.target.value) {
                setMode("range");
                setActivePreset(null);
              }
            }}
          />
          <span class="text-xs text-text-muted">→</span>
          <input
            type="datetime-local"
            class="text-xs border border-border-default rounded px-2 py-1 bg-surface-base text-text-primary"
            value={until() ? until().slice(0, 16) : ""}
            onChange={(e) => {
              setUntil(e.target.value ? new Date(e.target.value).toISOString() : "");
              if (e.target.value) {
                setMode("range");
                setActivePreset(null);
              }
            }}
          />
          <Button
            variant="outline"
            size="sm"
            class="h-7 px-3 text-xs ml-auto"
            onClick={handleDownload}
            disabled={downloading()}
          >
            <Download class="h-3 w-3 mr-1" />
            {downloading() ? "Downloading..." : "Download"}
          </Button>
        </div>
      </div>

      {/* Log output */}
      <div class="p-4">
        <Show
          when={!logsQuery.isLoading}
          fallback={
            <div class="space-y-2">
              <For each={[1, 2, 3, 4, 5]}>
                {() => <div class="h-4 w-full bg-surface-overlay rounded animate-pulse" />}
              </For>
            </div>
          }
        >
          <div class="bg-surface-base rounded-md p-4 max-h-96 overflow-auto">
            <pre class="text-xs font-mono whitespace-pre-wrap text-text-muted">
              <Show
                when={logsQuery.data?.length}
                fallback={<span class="text-text-subtle">No logs available</span>}
              >
                <For each={logsQuery.data}>
                  {(line) => <div>{line}</div>}
                </For>
              </Show>
            </pre>
          </div>
        </Show>
      </div>
    </div>
  );
};
