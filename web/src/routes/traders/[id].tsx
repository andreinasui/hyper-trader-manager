import { type Component, Show, Suspense, createSignal, createEffect } from "solid-js";
import { useParams, useNavigate, A } from "@solidjs/router";
import { createQuery, createMutation, useQueryClient } from "@tanstack/solid-query";
import { Trash2, RefreshCw, Play, Square, Loader2, AlertCircle } from "lucide-solid";
import { ProtectedRoute } from "~/components/auth/ProtectedRoute";
import { AppShell } from "~/components/layout/AppShell";
import { Button } from "~/components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "~/components/ui/tabs";
import { Toast } from "~/components/ui/toast";
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
import { StatusDot, StatusIndicator, getStatusColor, getStatusLabel } from "~/components/ui/status-badge";
import { LogViewer } from "~/components/traders/LogViewer";
import { TraderConfigForm } from "~/components/traders/TraderConfigForm";
import { api } from "~/lib/api";
import { traderKeys, imageKeys } from "~/lib/query-keys";
import type { Trader, RuntimeStatus } from "~/lib/types";
import type { CreateTraderForm, TraderConfig } from "~/lib/schemas/trader-config";

/** Ensure config has required defaults (for legacy DB data) */
function normalizeConfig(config: TraderConfig): TraderConfig {
  return {
    ...config,
    trader_settings: {
      ...config.trader_settings,
      trading_strategy: {
        ...config.trader_settings.trading_strategy,
        bucket_config: config.trader_settings.trading_strategy.bucket_config ?? {
          pricing_strategy: "vwap",
        },
      },
    },
  };
}

type AnyStatus = Trader["status"] | RuntimeStatus["state"];

function relDate(iso: string): string {
  return new Date(iso).toLocaleDateString(undefined, { year: 'numeric', month: 'short', day: 'numeric' });
}

function LoadingSkeleton() {
  return (
    <div class="p-6 space-y-6">
      <div class="flex items-start justify-between">
        <div class="space-y-2">
          <div class="h-8 w-48 bg-[#111214] rounded-md animate-pulse" />
          <div class="h-4 w-64 bg-[#111214] rounded-md animate-pulse" />
          <div class="h-3 w-96 bg-[#111214] rounded-md animate-pulse mt-3" />
        </div>
        <div class="flex gap-2">
          <div class="h-9 w-20 bg-[#111214] rounded-md animate-pulse" />
          <div class="h-9 w-20 bg-[#111214] rounded-md animate-pulse" />
        </div>
      </div>
      <div class="border-b border-[#222426] pb-0">
        <div class="h-10 w-64 bg-[#111214] rounded-md animate-pulse" />
      </div>
      <div class="grid gap-6 md:grid-cols-2">
        <div class="bg-[#111214] border border-[#222426] rounded-md p-5 h-64" />
        <div class="bg-[#111214] border border-[#222426] rounded-md p-5 h-64" />
      </div>
    </div>
  );
}

const TraderDetailPage: Component = () => {
  const params = useParams<{ id: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [deleteOpen, setDeleteOpen] = createSignal(false);
  const [showSavedToast, setShowSavedToast] = createSignal(false);
  const [editName, setEditName] = createSignal<string>("");
  const [editDescription, setEditDescription] = createSignal<string>("");
  const [infoChanged, setInfoChanged] = createSignal(false);
  const [infoError, setInfoError] = createSignal<string | null>(null);

  const traderQuery = createQuery(() => ({
    queryKey: traderKeys.detail(params.id),
    queryFn: () => api.getTrader(params.id),
  }));

  // Initialize edit values when trader data loads (only if no unsaved changes)
  createEffect(() => {
    const t = traderQuery.data;
    if (t && !infoChanged()) {
      setEditName(t.name || "");
      setEditDescription(t.description || "");
    }
  });

  const statusQuery = createQuery(() => {
    const status = traderQuery.data?.status;
    return {
      queryKey: traderKeys.status(params.id),
      queryFn: () => api.getTraderStatus(params.id),
      refetchInterval: status === "starting" ? 2000 : status === "running" ? 10000 : false,
      enabled: status === "running" || status === "starting",
    };
  });

  const restartMutation = createMutation(() => ({
    mutationFn: () => api.restartTrader(params.id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: traderKeys.detail(params.id) });
      queryClient.invalidateQueries({ queryKey: traderKeys.status(params.id) });
    },
  }));

  const deleteMutation = createMutation(() => ({
    mutationFn: () => api.deleteTrader(params.id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: traderKeys.all });
      navigate("/traders");
    },
  }));

  const startMutation = createMutation(() => ({
    mutationFn: () => api.startTrader(params.id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: traderKeys.detail(params.id) });
      queryClient.invalidateQueries({ queryKey: traderKeys.status(params.id) });
    },
  }));

  const stopMutation = createMutation(() => ({
    mutationFn: () => api.stopTrader(params.id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: traderKeys.detail(params.id) });
      queryClient.invalidateQueries({ queryKey: traderKeys.status(params.id) });
    },
  }));

  const updateMutation = createMutation(() => ({
    mutationFn: (config: TraderConfig) => api.updateTrader(params.id, { config }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: traderKeys.detail(params.id) });
      setShowSavedToast(true);
    },
  }));

  const updateInfoMutation = createMutation(() => ({
    mutationFn: (data: { name?: string; description?: string }) =>
      api.updateTraderInfo(params.id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: traderKeys.detail(params.id) });
      setInfoError(null);
      setInfoChanged(false);
    },
    onError: (error: Error) => {
      setInfoError(error.message || "Failed to update trader info");
    },
  }));

  const imageQuery = createQuery(() => ({
    queryKey: imageKeys.versions(),
    queryFn: () => api.getImageVersions(),
  }));

  const updateImageMutation = createMutation(() => ({
    mutationFn: (newTag: string) => api.updateTraderImage(params.id, newTag),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: traderKeys.detail(params.id) });
      queryClient.invalidateQueries({ queryKey: imageKeys.versions() });
    },
  }));

  const needsImageUpdate = () => {
    const remote = imageQuery.data?.latest_remote;
    const current = traderQuery.data?.image_tag;
    if (!remote || !current) return false;
    const [rMaj, rMin, rPat] = remote.split(".").map(Number);
    const [cMaj, cMin, cPat] = current.split(".").map(Number);
    if (rMaj !== cMaj) return rMaj > cMaj;
    if (rMin !== cMin) return rMin > cMin;
    return rPat > cPat;
  };

  const formatUptime = (startedAt: string): string => {
    const seconds = Math.floor((Date.now() - new Date(startedAt).getTime()) / 1000);
    if (seconds < 60) return `${seconds}s`;
    const minutes = Math.floor(seconds / 60);
    if (minutes < 60) return `${minutes}m ${seconds % 60}s`;
    const hours = Math.floor(minutes / 60);
    if (hours < 24) return `${hours}h ${minutes % 60}m`;
    const days = Math.floor(hours / 24);
    return `${days}d ${hours % 24}h ${minutes % 60}m`;
  };

  const handleInfoSave = () => {
    const data: { name?: string; description?: string } = {};
    const currentName = editName().trim();
    const currentDesc = editDescription().trim();
    
    if (currentName) data.name = currentName;
    if (currentDesc) data.description = currentDesc;
    
    updateInfoMutation.mutate(data);
  };

  const handleNameChange = (value: string) => {
    setEditName(value);
    setInfoChanged(true);
    setInfoError(null);
  };

  const handleDescriptionChange = (value: string) => {
    setEditDescription(value);
    setInfoChanged(true);
    setInfoError(null);
  };

  return (
    <ProtectedRoute>
      <AppShell>
        <Suspense fallback={<LoadingSkeleton />}>
          <Show when={traderQuery.data}>
            {(trader) => {
              const currentStatus = () => statusQuery.data?.runtime_status?.state ?? trader().status;
              
              return (
                <>
                  {/* Top bar breadcrumb */}
                  <div class="h-14 border-b border-[#222426] flex items-center justify-between px-6 bg-[#08090a] sticky top-0 z-20">
                    <div class="flex items-center gap-2 text-sm">
                      <A href="/traders" class="text-zinc-500 hover:text-zinc-300 transition-colors">
                        Traders
                      </A>
                      <span class="text-zinc-600">/</span>
                      <span class="text-zinc-300 font-medium">{trader().display_name}</span>
                    </div>
                  </div>

                  {/* Main content */}
                  <div class="p-6 space-y-6">
                    {/* Page header */}
                    <div class="flex items-start justify-between">
                      <div class="space-y-3">
                        <div class="flex items-center gap-2.5">
                          <StatusDot status={currentStatus()} />
                          <h1 class="text-2xl font-semibold text-zinc-50">{trader().display_name}</h1>
                        </div>
                        <Show when={trader().description}>
                          <p class="text-sm text-zinc-500 mt-0.5">{trader().description}</p>
                        </Show>
                        <div class="flex items-center gap-4 text-xs text-zinc-500">
                          <span class="font-mono">
                            {trader().wallet_address.slice(0, 6)}...{trader().wallet_address.slice(-4)}
                          </span>
                          <span>v{trader().image_tag}</span>
                          <span>Created {relDate(trader().created_at)}</span>
                        </div>
                      </div>

                      {/* Action buttons */}
                      <div class="flex items-center gap-2">
                        <Show when={["configured", "stopped", "failed"].includes(trader().status)}>
                          <button
                            onClick={() => startMutation.mutate()}
                            disabled={startMutation.isPending}
                            class="inline-flex items-center gap-2 px-3 py-2 text-sm font-medium rounded-md transition-all bg-[#5e6ad2] text-white hover:bg-[#6b76d9] disabled:opacity-50 disabled:cursor-not-allowed"
                          >
                            <Show
                              when={startMutation.isPending}
                              fallback={<Play class="h-4 w-4" stroke-width={1.5} />}
                            >
                              <Loader2 class="h-4 w-4 animate-spin" stroke-width={1.5} />
                            </Show>
                            {trader().status === "failed" ? "Retry" : "Start"}
                          </button>
                        </Show>

                        <Show when={["running", "starting"].includes(trader().status)}>
                          <button
                            onClick={() => stopMutation.mutate()}
                            disabled={stopMutation.isPending}
                            class="inline-flex items-center gap-2 px-3 py-2 text-sm font-medium rounded-md transition-all border border-[#222426] text-zinc-300 hover:bg-[#1a1b1e] disabled:opacity-50 disabled:cursor-not-allowed"
                          >
                            <Show
                              when={stopMutation.isPending}
                              fallback={<Square class="h-4 w-4" stroke-width={1.5} />}
                            >
                              <Loader2 class="h-4 w-4 animate-spin" stroke-width={1.5} />
                            </Show>
                            Stop
                          </button>
                        </Show>

                        <Show when={trader().status === "running"}>
                          <button
                            onClick={() => restartMutation.mutate()}
                            disabled={restartMutation.isPending}
                            class="inline-flex items-center gap-2 px-3 py-2 text-sm font-medium rounded-md transition-all border border-[#222426] text-zinc-300 hover:bg-[#1a1b1e] disabled:opacity-50 disabled:cursor-not-allowed"
                          >
                            <RefreshCw
                              class={`h-4 w-4 ${restartMutation.isPending ? "animate-spin" : ""}`}
                              stroke-width={1.5}
                            />
                            Restart
                          </button>
                        </Show>

                        <Show when={needsImageUpdate()}>
                          <button
                            onClick={() => updateImageMutation.mutate(imageQuery.data!.latest_remote!)}
                            disabled={updateImageMutation.isPending}
                            class="inline-flex items-center gap-2 px-3 py-2 text-sm font-medium rounded-md transition-all border border-[#222426] text-zinc-300 hover:bg-[#1a1b1e] disabled:opacity-50 disabled:cursor-not-allowed"
                          >
                            <Show
                              when={updateImageMutation.isPending}
                              fallback={<RefreshCw class="h-4 w-4" stroke-width={1.5} />}
                            >
                              <Loader2 class="h-4 w-4 animate-spin" stroke-width={1.5} />
                            </Show>
                            Update Image
                          </button>
                        </Show>

                        <AlertDialog open={deleteOpen()} onOpenChange={setDeleteOpen}>
                          <AlertDialogTrigger
                            as={(props: any) => (
                              <button
                                {...props}
                                class="inline-flex items-center gap-2 px-3 py-2 text-sm font-medium rounded-md transition-all border border-red-900 text-red-400 hover:bg-red-950/30"
                              >
                                <Trash2 class="h-4 w-4" stroke-width={1.5} />
                                Delete
                              </button>
                            )}
                          />
                          <AlertDialogContent>
                            <AlertDialogHeader>
                              <AlertDialogTitle>Delete Trader</AlertDialogTitle>
                              <AlertDialogDescription>
                                This will permanently delete "{trader().display_name}" and all its configuration.
                                This action cannot be undone.
                              </AlertDialogDescription>
                            </AlertDialogHeader>
                            <AlertDialogFooter>
                              <AlertDialogCancel>Cancel</AlertDialogCancel>
                              <AlertDialogAction onClick={() => deleteMutation.mutate()}>
                                {deleteMutation.isPending ? "Deleting..." : "Delete"}
                              </AlertDialogAction>
                            </AlertDialogFooter>
                          </AlertDialogContent>
                        </AlertDialog>
                      </div>
                    </div>

                    {/* Tabs */}
                    <Tabs defaultValue="overview" class="space-y-6">
                      <TabsList class="inline-flex gap-1 border-b border-[#222426] w-full">
                        <TabsTrigger 
                          value="overview"
                          class="px-4 py-2 text-sm font-medium text-zinc-400 hover:text-zinc-200 border-b-2 border-transparent transition-all data-[selected]:text-zinc-100 data-[selected]:border-[#5e6ad2]"
                        >
                          Overview
                        </TabsTrigger>
                        <TabsTrigger 
                          value="logs"
                          class="px-4 py-2 text-sm font-medium text-zinc-400 hover:text-zinc-200 border-b-2 border-transparent transition-all data-[selected]:text-zinc-100 data-[selected]:border-[#5e6ad2]"
                        >
                          Logs
                        </TabsTrigger>
                        <TabsTrigger 
                          value="configuration"
                          class="px-4 py-2 text-sm font-medium text-zinc-400 hover:text-zinc-200 border-b-2 border-transparent transition-all data-[selected]:text-zinc-100 data-[selected]:border-[#5e6ad2]"
                        >
                          Configuration
                        </TabsTrigger>
                      </TabsList>

                      {/* Overview Tab */}
                      <TabsContent value="overview" class="space-y-0">
                        <div class="grid gap-6 md:grid-cols-2">
                          {/* Status Card */}
                          <div class="bg-[#111214] border border-[#222426] rounded-md p-5">
                            <h2 class="text-sm font-semibold text-zinc-300 mb-4">Status</h2>
                            <div class="space-y-0">
                              <div class="flex justify-between items-center border-b border-[#222426] pb-3 mb-3">
                                <span class="text-sm text-zinc-500">Status</span>
                                <StatusIndicator status={currentStatus()} />
                              </div>
                              <Show when={trader().status === "running" && statusQuery.data?.runtime_status?.started_at}>
                                <div class="flex justify-between items-center border-b border-[#222426] pb-3 mb-3">
                                  <span class="text-sm text-zinc-500">Uptime</span>
                                  <span class="text-sm text-zinc-300">
                                    {formatUptime(statusQuery.data!.runtime_status.started_at!)}
                                  </span>
                                </div>
                              </Show>
                              <div class="flex justify-between items-center border-b border-[#222426] pb-3 mb-3">
                                <span class="text-sm text-zinc-500">Image version</span>
                                <div class="flex items-center gap-2">
                                  <span class="font-mono text-sm text-zinc-300">{trader().image_tag}</span>
                                  <Show when={needsImageUpdate()}>
                                    <span class="text-xs text-amber-400">
                                      → {imageQuery.data?.latest_remote} available
                                    </span>
                                  </Show>
                                </div>
                              </div>
                              <Show when={statusQuery.data?.runtime_status?.error || trader().last_error}>
                                <div class="bg-red-950/20 rounded p-3">
                                  <div class="flex items-center gap-2 text-red-400 text-sm mb-1">
                                    <AlertCircle class="h-4 w-4" stroke-width={1.5} />
                                    <span class="font-medium">Error</span>
                                  </div>
                                  <p class="text-sm text-red-400 break-all">
                                    {statusQuery.data?.runtime_status?.error || trader().last_error}
                                  </p>
                                </div>
                              </Show>
                            </div>
                          </div>

                          {/* Trader Info Card */}
                          <div class="bg-[#111214] border border-[#222426] rounded-md p-5">
                            <h2 class="text-sm font-semibold text-zinc-300 mb-4">Trader info</h2>
                            <div class="space-y-4">
                              <div class="space-y-2">
                                <label class="text-sm font-medium text-zinc-400">Name</label>
                                <input
                                  type="text"
                                  value={editName()}
                                  onInput={(e) => handleNameChange(e.currentTarget.value)}
                                  placeholder="Enter a name for this trader"
                                  class="bg-[#08090a] border border-[#222426] rounded-md px-3 py-2 text-sm text-zinc-100 placeholder:text-zinc-600 focus:outline-none focus:border-[#5e6ad2] transition-colors w-full"
                                  maxLength={50}
                                />
                              </div>
                              <div class="space-y-2">
                                <label class="text-sm font-medium text-zinc-400">Description</label>
                                <textarea
                                  value={editDescription()}
                                  onInput={(e) => handleDescriptionChange(e.currentTarget.value)}
                                  placeholder="Optional notes about this trader"
                                  class="bg-[#08090a] border border-[#222426] rounded-md px-3 py-2 text-sm text-zinc-100 placeholder:text-zinc-600 focus:outline-none focus:border-[#5e6ad2] transition-colors w-full min-h-[60px]"
                                  maxLength={255}
                                  rows={2}
                                />
                              </div>
                              <Show when={infoError()}>
                                <p class="text-sm text-red-400">{infoError()}</p>
                              </Show>
                              <Show when={infoChanged()}>
                                <button
                                  onClick={handleInfoSave}
                                  disabled={updateInfoMutation.isPending}
                                  class="inline-flex items-center px-3 py-2 text-sm font-medium rounded-md transition-all bg-[#5e6ad2] text-white hover:bg-[#6b76d9] disabled:opacity-50 disabled:cursor-not-allowed"
                                >
                                  {updateInfoMutation.isPending ? "Saving..." : "Save"}
                                </button>
                              </Show>
                              <div class="border-t border-[#222426] pt-4 mt-4 space-y-2">
                                <div class="flex items-center justify-between">
                                  <span class="text-sm text-zinc-500">Created</span>
                                  <span class="text-sm text-zinc-400">{relDate(trader().created_at)}</span>
                                </div>
                                <div class="flex items-center justify-between">
                                  <span class="text-sm text-zinc-500">Last updated</span>
                                  <span class="text-sm text-zinc-400">{relDate(trader().updated_at)}</span>
                                </div>
                              </div>
                            </div>
                          </div>
                        </div>
                      </TabsContent>

                      {/* Logs Tab */}
                      <TabsContent value="logs">
                        <div class="bg-[#111214] border border-[#222426] rounded-md overflow-hidden">
                          <LogViewer traderId={params.id} />
                        </div>
                      </TabsContent>

                      {/* Configuration Tab */}
                      <TabsContent value="configuration">
                        <Show
                          when={trader().latest_config}
                          fallback={
                            <div class="bg-[#111214] border border-[#222426] rounded-md p-8 text-center">
                              <p class="text-sm text-zinc-500">No configuration available for this trader.</p>
                            </div>
                          }
                        >
                          {(config) => (
                            <div class="bg-[#111214] border border-[#222426] rounded-md p-6">
                              <TraderConfigForm
                                initialValues={{
                                  wallet_address: trader().wallet_address,
                                  private_key: "",
                                  config: normalizeConfig(config() as TraderConfig),
                                }}
                                onSubmit={async (data: CreateTraderForm) => {
                                  await updateMutation.mutateAsync(data.config);
                                }}
                                isEditing={true}
                                isSubmitting={updateMutation.isPending}
                                submitLabel="Save Configuration"
                              />
                            </div>
                          )}
                        </Show>
                      </TabsContent>
                    </Tabs>
                  </div>
                </>
              );
            }}
          </Show>
        </Suspense>
        <Toast
          message="Saved."
          show={showSavedToast()}
          onClose={() => setShowSavedToast(false)}
          duration={2000}
          variant="success"
        />
      </AppShell>
    </ProtectedRoute>
  );
};

export default TraderDetailPage;
