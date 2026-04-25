import { type Component, For, createSignal, Show } from "solid-js";
import { createQuery } from "@tanstack/solid-query";
import { RefreshCw } from "lucide-solid";
import { Button } from "~/components/ui/button";
import { api } from "~/lib/api";
import { traderKeys } from "~/lib/query-keys";

interface LogViewerProps {
  traderId: string;
}

export const LogViewer: Component<LogViewerProps> = (props) => {
  const [lines] = createSignal(100);

  const logsQuery = createQuery(() => ({
    queryKey: traderKeys.logs(props.traderId),
    queryFn: () => api.getTraderLogs(props.traderId, lines()),
    refetchInterval: 5000,
  }));

  return (
    <div>
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
