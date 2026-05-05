import { createSignal, createEffect, Show } from "solid-js";
import { createQuery, createMutation, useQueryClient } from "@tanstack/solid-query";
import { api } from "~/lib/api";
import { updateKeys } from "~/lib/query-keys";
import { UpdateProgressOverlay } from "~/components/UpdateProgressOverlay";

export function UpdateBanner() {
  const queryClient = useQueryClient();
  const [dismissed, setDismissed] = createSignal(false);
  const [showOverlay, setShowOverlay] = createSignal(false);

  const statusQuery = createQuery(() => ({
    queryKey: updateKeys.status(),
    queryFn: () => api.updates.getStatus(),
    refetchInterval: 30_000,
    retry: false,
  }));

  const applyMutation = createMutation(() => ({
    mutationFn: () => api.updates.apply(),
    onSuccess: () => setShowOverlay(true),
  }));

  const acknowledgeMutation = createMutation(() => ({
    mutationFn: () => api.updates.acknowledge(),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: updateKeys.all }),
  }));

  // Show the overlay whenever the backend reports an active update — handles
  // the page-reload-during-update case where the status query is the first
  // thing to detect the in-progress state.
  createEffect(() => {
    if (statusQuery.data?.status === "updating") {
      setShowOverlay(true);
    }
  });

  return (
    <>
      <Show when={showOverlay()}>
        <UpdateProgressOverlay />
      </Show>
      <Show when={statusQuery.data}>
        {(data) => {
          const d = data();

          // Don't show if not configured
          if (!d.configured) return null;

          // Overlay is handling the updating state
          if (d.status === "updating") return null;

          // Show error/rolled-back banner
          if (d.status === "failed" || d.status === "rolled_back") {
            const isRolledBack = d.status === "rolled_back";
            return (
              <div class="flex items-center justify-between bg-red-950 border border-red-800 px-4 py-3 text-sm">
                <span class="text-red-300">
                  {isRolledBack
                    ? "Update rolled back"
                    : `Update failed: ${d.error_message ?? "unknown error"}`}
                </span>
                <button
                  class="ml-4 px-3 py-1 rounded border border-red-700 text-red-300 hover:bg-red-900 disabled:opacity-50"
                  onClick={() => acknowledgeMutation.mutate()}
                  disabled={acknowledgeMutation.isPending}
                >
                  Acknowledge
                </button>
              </div>
            );
          }

          // Show update-available banner.
          if (d.update_available && d.status === "idle") {
            return (
              <Show when={!dismissed()}>
                <div class="flex items-center justify-between bg-amber-950 border border-amber-700 px-4 py-3 text-sm">
                  <span class="text-amber-300">
                    Update available
                    {d.latest_version ? (
                      <span class="font-mono ml-1">
                        {d.current_version} → {d.latest_version}
                      </span>
                    ) : null}
                  </span>
                  <div class="flex items-center gap-2 ml-4">
                    <button
                      class="px-3 py-1 rounded bg-amber-700 text-amber-100 hover:bg-amber-600 disabled:opacity-50"
                      onClick={() => applyMutation.mutate()}
                      disabled={applyMutation.isPending}
                    >
                      {applyMutation.isPending ? "Starting…" : "Update now"}
                    </button>
                    <button
                      class="px-3 py-1 rounded border border-amber-700 text-amber-400 hover:bg-amber-900"
                      onClick={() => setDismissed(true)}
                    >
                      Dismiss
                    </button>
                  </div>
                </div>
              </Show>
            );
          }

          return null;
        }}
      </Show>
    </>
  );
}
