import { type Component, Show, Suspense, createSignal, createEffect } from "solid-js";
import TraderOverview from "~/components/traders/overviews/TraderOverview";
import { useParams, useNavigate } from "@solidjs/router";
import { createQuery, createMutation, useQueryClient } from "@tanstack/solid-query";
import { Trash2, RefreshCw, Play, Square, Loader2, AlertCircle } from "lucide-solid";
import { ProtectedRoute } from "~/components/auth/ProtectedRoute";
import { AppShell } from "~/components/layout/AppShell";
import { PageHeader } from "~/components/layout/PageHeader";
import { PageContent } from "~/components/layout/PageContent";
import { Button } from "~/components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "~/components/ui/tabs";
import { Toast } from "~/components/ui/toast";
import { Panel, PanelBody } from "~/components/ui/panel";
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
import { StatusDot } from "~/components/ui/status-badge";
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


function LoadingSkeleton() {
  return (
    <div class="p-6 space-y-6">
      <div class="flex items-start justify-between">
        <div class="space-y-2">
          <div class="h-8 w-48 bg-surface-raised rounded-md animate-pulse" />
          <div class="h-4 w-64 bg-surface-raised rounded-md animate-pulse" />
          <div class="h-3 w-96 bg-surface-raised rounded-md animate-pulse mt-3" />
        </div>
        <div class="flex gap-2">
          <div class="h-9 w-20 bg-surface-raised rounded-md animate-pulse" />
          <div class="h-9 w-20 bg-surface-raised rounded-md animate-pulse" />
        </div>
      </div>
      <div class="border-b border-border-default pb-0">
        <div class="h-10 w-64 bg-surface-raised rounded-md animate-pulse" />
      </div>
      <div class="grid gap-6 md:grid-cols-2">
        <div class="bg-surface-raised border border-border-default rounded-md p-5 h-64" />
        <div class="bg-surface-raised border border-border-default rounded-md p-5 h-64" />
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
      refetchInterval: status === "starting" ? 500 : status === "running" ? 1000 : false,
      enabled: status === "running" || status === "starting",
    };
  });

  const restartMutation = createMutation(() => ({
    mutationFn: () => api.restartTrader(params.id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: traderKeys.detail(params.id) });
      queryClient.invalidateQueries({ queryKey: traderKeys.status(params.id) });
      // Invalidate all trader queries so list view updates when navigating back
      queryClient.invalidateQueries({ queryKey: traderKeys.all });
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
      // Invalidate all trader queries so list view updates when navigating back
      queryClient.invalidateQueries({ queryKey: traderKeys.all });
    },
  }));

  const stopMutation = createMutation(() => ({
    mutationFn: () => api.stopTrader(params.id),
    onSuccess: () => {
      // Optimistically mark trader as stopped so the UI reflects it immediately,
      // before the detail query refetches from the server.
      queryClient.setQueryData<Trader>(traderKeys.detail(params.id), (old) =>
        old ? { ...old, status: "stopped" } : old
      );
      // Remove stale runtime status data — the container is gone so the next
      // status poll would return "not_found", which we don't want to show.
      queryClient.removeQueries({ queryKey: traderKeys.status(params.id) });
      // Kick off a background refetch to confirm the server-side state.
      queryClient.invalidateQueries({ queryKey: traderKeys.detail(params.id) });
      // Invalidate all trader queries so list view updates when navigating back
      queryClient.invalidateQueries({ queryKey: traderKeys.all });
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
              // Only use live runtime status when the DB says the trader is actively
              // running or starting. In all other states (stopped, configured, failed)
              // the DB status is authoritative — the runtime may return "not_found"
              // for a freshly stopped container, which we must not display.
              const currentStatus = () => {
                const dbStatus = trader().status;
                if (dbStatus === "running" || dbStatus === "starting") {
                  return statusQuery.data?.runtime_status?.state ?? dbStatus;
                }
                return dbStatus;
              };

              return (
                <>
                  <PageHeader
                    breadcrumbs={[
                      { label: "Traders", href: "/traders" },
                      { label: trader().display_name },
                    ]}
                  />

                  <PageContent>
                    {/* Page header */}
                    <div class="flex items-start justify-between mb-6">
                      <div class="space-y-3">
                        <div class="flex items-center gap-2.5">
                          <StatusDot status={currentStatus()} />
                          <h1 class="text-2xl font-semibold text-text-base">{trader().display_name}</h1>


                        </div>
                        <Show when={trader().description}>
                          <p class="text-sm text-text-subtle mt-0.5">{trader().description}</p>
                        </Show>

                      </div>

                      {/* Action buttons */}
                      <div class="flex items-center gap-2">
                        <Show when={["configured", "stopped", "failed"].includes(trader().status)}>
                          <Button
                            onClick={() => startMutation.mutate()}
                            disabled={startMutation.isPending}
                          >
                            <Show
                              when={startMutation.isPending}
                              fallback={<Play class="h-4 w-4 mr-2" stroke-width={1.5} />}
                            >
                              <Loader2 class="h-4 w-4 mr-2 animate-spin" stroke-width={1.5} />
                            </Show>
                            {trader().status === "failed" ? "Retry" : "Start"}
                          </Button>
                        </Show>

                        <Show when={["running", "starting"].includes(trader().status)}>
                          <Button
                            variant="outline"
                            onClick={() => stopMutation.mutate()}
                            disabled={stopMutation.isPending}
                          >
                            <Show
                              when={stopMutation.isPending}
                              fallback={<Square class="h-4 w-4 mr-2" stroke-width={1.5} />}
                            >
                              <Loader2 class="h-4 w-4 mr-2 animate-spin" stroke-width={1.5} />
                            </Show>
                            Stop
                          </Button>
                        </Show>

                        <Show when={trader().status === "running"}>
                          <Button
                            variant="outline"
                            onClick={() => restartMutation.mutate()}
                            disabled={restartMutation.isPending}
                          >
                            <RefreshCw
                              class={`h-4 w-4 mr-2 ${restartMutation.isPending ? "animate-spin" : ""}`}
                              stroke-width={1.5}
                            />
                            Restart
                          </Button>
                        </Show>

                        <Show when={needsImageUpdate()}>
                          <Button
                            variant="outline"
                            onClick={() => updateImageMutation.mutate(imageQuery.data!.latest_remote!)}
                            disabled={updateImageMutation.isPending}
                          >
                            <Show
                              when={updateImageMutation.isPending}
                              fallback={<RefreshCw class="h-4 w-4 mr-2" stroke-width={1.5} />}
                            >
                              <Loader2 class="h-4 w-4 mr-2 animate-spin" stroke-width={1.5} />
                            </Show>
                            Update Image
                          </Button>
                        </Show>

                        <AlertDialog open={deleteOpen()} onOpenChange={setDeleteOpen}>
                          <AlertDialogTrigger
                            as={(triggerProps: Record<string, unknown>) => (
                              <Button
                                {...triggerProps}
                                variant="outline"
                                class="border-error-muted text-error hover:bg-error-surface"
                              >
                                <Trash2 class="h-4 w-4 mr-2" stroke-width={1.5} />
                                Delete
                              </Button>
                            )}
                          />
                          <AlertDialogContent>
                            <AlertDialogHeader>
                              <div class="flex items-start gap-3">
                                <div class="flex shrink-0 items-center justify-center size-9 rounded-lg bg-destructive/10 border border-destructive/20 mt-0.5">
                                  <Trash2 class="size-4 text-destructive" stroke-width={1.5} />
                                </div>
                                <div>
                                  <AlertDialogTitle>Delete Trader</AlertDialogTitle>
                                  <AlertDialogDescription>
                                    This will permanently delete "{trader().display_name}" and all its configuration.
                                    This action cannot be undone.
                                  </AlertDialogDescription>
                                </div>
                              </div>
                            </AlertDialogHeader>
                            <AlertDialogFooter>
                              <AlertDialogCancel>Cancel</AlertDialogCancel>
                              <AlertDialogAction variant="destructive" onClick={() => deleteMutation.mutate()}>
                                {deleteMutation.isPending ? "Deleting..." : "Delete"}
                              </AlertDialogAction>
                            </AlertDialogFooter>
                          </AlertDialogContent>
                        </AlertDialog>
                      </div>
                    </div>

                    {/* Tabs */}
                     <Tabs defaultValue="overview" class="space-y-6">
                       <TabsList>
                         <TabsTrigger value="overview">Overview</TabsTrigger>
                         <TabsTrigger value="logs">Logs</TabsTrigger>
                         <TabsTrigger value="configuration">Configuration</TabsTrigger>
                       </TabsList>

                      {/* Overview Tab */}
                      <TabsContent value="overview" class="space-y-0">
                        <TraderOverview
                          trader={trader()}
                          currentStatus={currentStatus}
                          statusQuery={statusQuery}
                          editName={editName}
                          editDescription={editDescription}
                          handleNameChange={handleNameChange}
                          handleDescriptionChange={handleDescriptionChange}
                          infoChanged={infoChanged}
                          infoError={infoError}
                          handleInfoSave={handleInfoSave}
                          updateInfoMutation={updateInfoMutation}
                          needsImageUpdate={needsImageUpdate}
                          imageQuery={imageQuery}
                          formatUptime={formatUptime}
                        />
                      </TabsContent>

                      {/* Logs Tab */}
                      <TabsContent value="logs">
                        <Panel>
                          <LogViewer traderId={params.id} />
                        </Panel>
                      </TabsContent>

                      {/* Configuration Tab */}
                      <TabsContent value="configuration">
                        <Show
                          when={trader().latest_config}
                          fallback={
                            <Panel class="p-8 text-center">
                              <p class="text-sm text-text-subtle">No configuration available for this trader.</p>
                            </Panel>
                          }
                        >
                          {(config) => (
                            <Panel>
                              <PanelBody>
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
                              </PanelBody>
                            </Panel>
                          )}
                        </Show>
                      </TabsContent>
                    </Tabs>
                  </PageContent>
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
