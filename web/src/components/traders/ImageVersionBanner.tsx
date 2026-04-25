import { type Component, Show, createSignal } from "solid-js";
import { createQuery, createMutation, useQueryClient } from "@tanstack/solid-query";
import { RefreshCw, Loader2 } from "lucide-solid";
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
      <div class="flex items-center justify-between bg-[#111214] border border-amber-900/50 rounded-md px-4 py-3">
        <div class="flex items-center gap-3">
          <span class="h-1.5 w-1.5 rounded-full bg-amber-400 animate-pulse" />
          <span class="text-sm text-zinc-300">
            Update available{" "}
            <span class="font-mono text-amber-400">
              {imageQuery.data?.latest_local} → {imageQuery.data?.latest_remote}
            </span>
          </span>
          <Show when={updateError()}>
            <span class="text-xs text-red-400">{updateError()}</span>
          </Show>
        </div>
        <button
          onClick={() => updateAllMutation.mutate()}
          disabled={updateAllMutation.isPending || props.traders.length === 0}
          class="flex items-center gap-1.5 px-3 py-1.5 rounded-md border border-amber-900/50 text-amber-400 hover:bg-amber-950/30 transition-all text-sm font-medium disabled:opacity-50"
        >
          <Show when={updateAllMutation.isPending} fallback={<RefreshCw size={14} stroke-width={1.5} />}>
            <Loader2 size={14} stroke-width={1.5} class="animate-spin" />
          </Show>
          Update all
        </button>
      </div>
    </Show>
  );
};
