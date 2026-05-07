import { type Component, For, Show, createSignal } from "solid-js";
import { createQuery } from "@tanstack/solid-query";
import { Download } from "lucide-solid";
import { api } from "~/lib/api";
import { traderKeys } from "~/lib/query-keys";
import { IconButton } from "~/components/ui/icon-button";

interface LogArchivesProps {
  traderId: string;
}

function formatBytes(n: number): string {
  if (n < 1024) return `${n} B`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`;
  return `${(n / (1024 * 1024)).toFixed(1)} MB`;
}

function formatDateTime(iso: string): string {
  return new Date(iso).toLocaleString();
}

export const LogArchives: Component<LogArchivesProps> = (props) => {
  const [downloadingId, setDownloadingId] = createSignal<string | null>(null);

  const archivesQuery = createQuery(() => ({
    queryKey: traderKeys.archives(props.traderId),
    queryFn: () => api.listTraderArchives(props.traderId),
  }));

  async function handleDownload(archiveId: string) {
    if (downloadingId()) return;
    setDownloadingId(archiveId);
    try {
      await api.downloadTraderArchive(props.traderId, archiveId);
    } finally {
      setDownloadingId(null);
    }
  }

  return (
    <div>
      {/* Header */}
      <div class="flex items-center justify-between px-5 py-3.5 border-b border-border-default">
        <h3 class="text-sm font-medium text-text-secondary">Log Archives</h3>
      </div>

      {/* Content */}
      <div class="p-4">
        <Show
          when={!archivesQuery.isLoading}
          fallback={
            <div class="space-y-2">
              <For each={[1, 2, 3]}>
                {() => <div class="h-4 w-full bg-surface-overlay rounded animate-pulse" />}
              </For>
            </div>
          }
        >
          <Show
            when={archivesQuery.data && archivesQuery.data.length > 0}
            fallback={
              <p class="text-sm text-text-subtle py-4 text-center">
                No archived logs yet. Stopping or restarting the trader will archive its current logs here.
              </p>
            }
          >
            <div class="overflow-x-auto">
              <table class="w-full text-xs">
                <thead>
                  <tr class="border-b border-border-default">
                     <th class="text-left py-2 px-3 text-text-muted font-medium">Run started</th>
                     <th class="text-left py-2 px-3 text-text-muted font-medium">Run ended</th>
                     <th class="text-left py-2 px-3 text-text-muted font-medium">Size</th>
                     <th class="py-2 px-3 text-text-muted font-medium"></th>
                  </tr>
                </thead>
                <tbody>
                  <For each={archivesQuery.data}>
                    {(archive) => (
                      <tr class="border-b border-border-default last:border-0 hover:bg-surface-raised/50 transition-colors">
                         <td class="py-2 px-3 text-text-primary">{formatDateTime(archive.run_started_at)}</td>
                         <td class="py-2 px-3 text-text-primary">{formatDateTime(archive.run_ended_at)}</td>
                         <td class="py-2 px-3 text-text-muted">{formatBytes(archive.file_size_bytes)}</td>
                         <td class="py-2 px-3">
                           <IconButton
                             icon={Download}
                             tooltip="Download"
                             loading={downloadingId() === archive.id}
                             disabled={downloadingId() !== null}
                             onClick={() => handleDownload(archive.id)}
                           />
                         </td>
                      </tr>
                    )}
                  </For>
                </tbody>
              </table>
            </div>
          </Show>
        </Show>
      </div>
    </div>
  );
};
