import { type Component, Show, createSignal } from "solid-js";
import { createQuery, createMutation, useQueryClient } from "@tanstack/solid-query";
import { RefreshCw, Loader2 } from "lucide-solid";
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

  // Semver comparison: returns true if a > b
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
      // Call updateTraderImage for each trader
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
      <div class="flex items-center justify-between rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm dark:border-amber-800 dark:bg-amber-950">
        <div class="flex items-center gap-2">
          <RefreshCw class="h-4 w-4 text-amber-600 dark:text-amber-400" />
          <span class="text-amber-800 dark:text-amber-200">
            Update available:{" "}
            <span class="font-mono font-medium">
              {imageQuery.data?.latest_local} → {imageQuery.data?.latest_remote}
            </span>
          </span>
          <Show when={updateError()}>
            <span class="text-destructive text-xs ml-2">{updateError()}</span>
          </Show>
        </div>
        <Button
          size="sm"
          variant="outline"
          onClick={() => updateAllMutation.mutate()}
          disabled={updateAllMutation.isPending || props.traders.length === 0}
          class="border-amber-300 text-amber-800 hover:bg-amber-100 dark:border-amber-700 dark:text-amber-200 dark:hover:bg-amber-900"
        >
          <Show
            when={updateAllMutation.isPending}
            fallback={<RefreshCw class="h-3.5 w-3.5 mr-1.5" />}
          >
            <Loader2 class="h-3.5 w-3.5 mr-1.5 animate-spin" />
          </Show>
          Update All
        </Button>
      </div>
    </Show>
  );
};
