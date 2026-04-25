import { type Component, Show, Suspense, createSignal, createEffect } from "solid-js";
import { useParams, useNavigate } from "@solidjs/router";
import { createQuery, createMutation, useQueryClient } from "@tanstack/solid-query";
import { Trash2, RefreshCw, Play, Square, Loader2, AlertCircle } from "lucide-solid";
import { ProtectedRoute } from "~/components/auth/ProtectedRoute";
import { AppShell } from "~/components/layout/AppShell";
import { Card, CardContent, CardHeader, CardTitle } from "~/components/ui/card";
import { Button } from "~/components/ui/button";
import { Badge } from "~/components/ui/badge";
import { Skeleton } from "~/components/ui/skeleton";
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

type StatusType = Trader["status"] | RuntimeStatus["state"];

function StatusBadge(props: { status: StatusType }) {
  const variant = () => {
    switch (props.status) {
      case "running":
        return "success";
      case "stopped":
      case "configured":
        return "secondary";
      case "failed":
      case "error":
      case "not_found":
      case "unknown":
        return "destructive";
      case "restarting":
        return "warning";
      case "starting":
      case "pending":
        return "outline";
      default:
        return "outline";
    }
  };

  return (
    <Badge variant={variant()} class="flex items-center gap-1.5">
      <Show when={props.status === "starting" || props.status === "pending" || props.status === "restarting"}>
        <Loader2 class="h-3 w-3 animate-spin" />
      </Show>
      {props.status}
    </Badge>
  );
}

function LoadingSkeleton() {
  return (
    <div class="space-y-6">
      <Skeleton class="h-8 w-48" />
      <Card>
        <CardHeader>
          <Skeleton class="h-6 w-32" />
        </CardHeader>
        <CardContent class="space-y-4">
          <Skeleton class="h-4 w-full" />
          <Skeleton class="h-4 w-3/4" />
        </CardContent>
      </Card>
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
            {(trader) => (
              <div class="space-y-6">
                <div class="flex items-center justify-between">
                  <div>
                    <h1 class="text-2xl font-bold">{trader().display_name}</h1>
                    <p class="text-muted-foreground font-mono text-sm">
                      {trader().wallet_address}
                    </p>
                  </div>
                  <div class="flex items-center gap-2">
                    <Show when={["configured", "stopped", "failed"].includes(trader().status)}>
                      <Button
                        variant="outline"
                        onClick={() => startMutation.mutate()}
                        disabled={startMutation.isPending}
                      >
                        <Show
                          when={startMutation.isPending}
                          fallback={<Play class="h-4 w-4 mr-2" />}
                        >
                          <Loader2 class="h-4 w-4 mr-2 animate-spin" />
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
                          fallback={<Square class="h-4 w-4 mr-2" />}
                        >
                          <Loader2 class="h-4 w-4 mr-2 animate-spin" />
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
                          fallback={<RefreshCw class="h-4 w-4 mr-2" />}
                        >
                          <Loader2 class="h-4 w-4 mr-2 animate-spin" />
                        </Show>
                        Update Image
                      </Button>
                    </Show>

                    <AlertDialog open={deleteOpen()} onOpenChange={setDeleteOpen}>
                      <AlertDialogTrigger as={Button} variant="destructive">
                        <Trash2 class="h-4 w-4 mr-2" />
                        Delete
                      </AlertDialogTrigger>
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

                <Tabs defaultValue="overview" class="space-y-6">
                  <TabsList>
                    <TabsTrigger value="overview">Overview</TabsTrigger>
                    <TabsTrigger value="logs">Logs</TabsTrigger>
                    <TabsTrigger value="configuration">Configuration</TabsTrigger>
                  </TabsList>

                  <TabsContent value="overview" class="space-y-6">
                    <div class="grid gap-6 md:grid-cols-2">
                      <Card>
                        <CardHeader>
                          <CardTitle>Status</CardTitle>
                        </CardHeader>
                        <CardContent class="space-y-4">
                          <div class="flex items-center justify-between">
                            <span class="text-muted-foreground">Current Status</span>
                            <StatusBadge status={statusQuery.data?.runtime_status?.state ?? trader().status} />
                          </div>
                          <Show when={statusQuery.data?.runtime_status?.started_at}>
                            <div class="flex items-center justify-between">
                              <span class="text-muted-foreground">Uptime</span>
                              <span>{formatUptime(statusQuery.data!.runtime_status.started_at!)}</span>
                            </div>
                          </Show>
                          <div class="flex items-center justify-between">
                            <span class="text-muted-foreground">Image Version</span>
                            <div class="flex items-center gap-2">
                              <span class="font-mono text-sm">{trader().image_tag}</span>
                              <Show when={needsImageUpdate()}>
                                <span class="text-xs text-amber-600 dark:text-amber-400">
                                  → {imageQuery.data?.latest_remote} available
                                </span>
                              </Show>
                            </div>
                          </div>
                          <Show when={statusQuery.data?.runtime_status?.error || trader().last_error}>
                            <div class="pt-2 border-t">
                              <div class="flex items-center gap-2 text-destructive text-sm">
                                <AlertCircle class="h-4 w-4" />
                                <span class="font-medium">Error:</span>
                              </div>
                              <p class="text-destructive text-sm mt-1 break-all">
                                {statusQuery.data?.runtime_status?.error || trader().last_error}
                              </p>
                            </div>
                          </Show>
                        </CardContent>
                      </Card>

                      <Card>
                        <CardHeader>
                          <CardTitle>Trader Info</CardTitle>
                        </CardHeader>
                        <CardContent class="space-y-4">
                          <div class="space-y-2">
                            <label class="text-sm font-medium">Name</label>
                            <input
                              type="text"
                              value={editName()}
                              onInput={(e) => handleNameChange(e.currentTarget.value)}
                              placeholder="Enter a name for this trader"
                              class="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm transition-colors placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
                              maxLength={50}
                            />
                          </div>
                          <div class="space-y-2">
                            <label class="text-sm font-medium">Description</label>
                            <textarea
                              value={editDescription()}
                              onInput={(e) => handleDescriptionChange(e.currentTarget.value)}
                              placeholder="Optional notes about this trader"
                              class="flex min-h-[60px] w-full rounded-md border border-input bg-transparent px-3 py-2 text-sm shadow-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
                              maxLength={255}
                              rows={2}
                            />
                          </div>
                          <Show when={infoError()}>
                            <p class="text-sm text-destructive">{infoError()}</p>
                          </Show>
                          <Show when={infoChanged()}>
                            <Button
                              onClick={handleInfoSave}
                              disabled={updateInfoMutation.isPending}
                              size="sm"
                            >
                              {updateInfoMutation.isPending ? "Saving..." : "Save"}
                            </Button>
                          </Show>
                          <div class="pt-4 border-t space-y-2">
                            <div class="flex items-center justify-between">
                              <span class="text-muted-foreground text-sm">Created</span>
                              <span class="text-sm">{new Date(trader().created_at).toLocaleString()}</span>
                            </div>
                            <div class="flex items-center justify-between">
                              <span class="text-muted-foreground text-sm">Last Updated</span>
                              <span class="text-sm">{new Date(trader().updated_at).toLocaleString()}</span>
                            </div>
                            <div class="flex items-center justify-between">
                              <span class="text-muted-foreground text-sm">Wallet</span>
                              <span class="font-mono text-xs truncate max-w-[200px]">{trader().wallet_address}</span>
                            </div>
                          </div>
                        </CardContent>
                      </Card>
                    </div>
                  </TabsContent>

                  <TabsContent value="logs">
                    <LogViewer traderId={params.id} />
                  </TabsContent>

                  <TabsContent value="configuration">
                    <Show
                      when={trader().latest_config}
                      fallback={
                        <Card>
                          <CardContent class="p-8 text-center text-muted-foreground">
                            No configuration available for this trader.
                          </CardContent>
                        </Card>
                      }
                    >
                      {(config) => (
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
                      )}
                    </Show>
                  </TabsContent>
                </Tabs>
              </div>
            )}
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
