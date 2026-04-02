import { type Component, For, createSignal } from "solid-js";
import { createQuery } from "@tanstack/solid-query";
import { RefreshCw } from "lucide-solid";
import { Button } from "~/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "~/components/ui/card";
import { Skeleton } from "~/components/ui/skeleton";
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
    refetchInterval: 5000, // Auto-refresh every 5 seconds
  }));

  return (
    <Card>
      <CardHeader class="flex flex-row items-center justify-between">
        <CardTitle>Logs</CardTitle>
        <Button
          variant="outline"
          size="sm"
          onClick={() => logsQuery.refetch()}
          disabled={logsQuery.isFetching}
        >
          <RefreshCw class={`h-4 w-4 mr-2 ${logsQuery.isFetching ? "animate-spin" : ""}`} />
          Refresh
        </Button>
      </CardHeader>
      <CardContent>
        {logsQuery.isLoading ? (
          <div class="space-y-2">
            <For each={[1, 2, 3, 4, 5]}>
              {() => <Skeleton class="h-4 w-full" />}
            </For>
          </div>
        ) : (
          <div class="bg-muted rounded-md p-4 max-h-96 overflow-auto">
            <pre class="text-xs font-mono whitespace-pre-wrap">
              {logsQuery.data?.length ? (
                <For each={logsQuery.data}>
                  {(line) => <div>{line}</div>}
                </For>
              ) : (
                <span class="text-muted-foreground">No logs available</span>
              )}
            </pre>
          </div>
        )}
      </CardContent>
    </Card>
  );
};
