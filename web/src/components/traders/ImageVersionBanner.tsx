import { type Component, Show, createSignal } from "solid-js";
import { createQuery, createMutation, useQueryClient } from "@tanstack/solid-query";
import { RefreshCw } from "lucide-solid";
import { Button } from "~/components/ui/button";
import { api } from "~/lib/api";
import { traderKeys, imageKeys } from "~/lib/query-keys";
import type { Trader } from "~/lib/types";

interface Props {
  traders: Trader[];
}

export const ImageVersionBanner: Component<Props> = (props) => {
  const queryClient = useQueryClient();
  const [updateError, setUpdateError] = createSignal<string | null>(null);

  const imageQuery = createQuery(() => ({
    queryKey: imageKeys.versions(),
    queryFn: () => api.getImageVersions(),
  }));

  const semverGt = (a: string, b: string): boolean => {
    const [aMaj, aMin, aPat] = a.split(".").map(Number);
    const [bMaj, bMin, bPat] = b.split(".").map(Number);
    if (aMaj !== bMaj) return aMaj > bMaj;
    if (aMin !== bMin) return aMin > bMin;
    return aPat > bPat;
  };

  const updateNeeded = () => {
    const data = imageQuery.data;
    if (!data?.latest_remote || !data?.latest_local) return false;
    return semverGt(data.latest_remote, data.latest_local);
  };

  const updateAllMutation = createMutation(() => ({
    mutationFn: async () => {
      const data = imageQuery.data;
      if (!data?.latest_remote) return;
      for (const trader of props.traders) {
        await api.updateTraderImage(trader.id, data.latest_remote);
      }
    },
    onSuccess: () => {
      setUpdateError(null);
      queryClient.invalidateQueries({ queryKey: traderKeys.lists() });
      queryClient.invalidateQueries({ queryKey: imageKeys.versions() });
    },
    onError: (error: Error) => {
      setUpdateError(error.message || "Failed to update some traders");
    },
  }));

  return (
    <Show when={updateNeeded()}>
      <div class="flex items-center justify-between bg-surface-raised border border-warning-muted rounded-md px-4 py-3">
        <div class="flex items-center gap-3">
          <span class="h-1.5 w-1.5 rounded-full bg-warning animate-pulse" />
          <span class="text-sm text-text-tertiary">
            Update available{" "}
            <span class="font-mono text-warning">
              {imageQuery.data?.latest_local} → {imageQuery.data?.latest_remote}
            </span>
          </span>
          <Show when={updateError()}>
            <span class="text-xs text-error">{updateError()}</span>
          </Show>
        </div>
        <Button
          variant="outline"
          size="sm"
          onClick={() => updateAllMutation.mutate()}
          disabled={updateAllMutation.isPending || props.traders.length === 0}
          class="border-warning-muted text-warning hover:bg-warning-surface"
        >
          <RefreshCw class={`h-4 w-4 mr-1.5 ${updateAllMutation.isPending ? "animate-spin" : ""}`} stroke-width={1.5} />
          Update all
        </Button>
      </div>
    </Show>
  );
};
