import { type Component, Show, Suspense, createSignal } from "solid-js";
import { useParams, useNavigate } from "@solidjs/router";
import { createQuery, createMutation, useQueryClient } from "@tanstack/solid-query";
import { Trash2, RefreshCw } from "lucide-solid";
import { ProtectedRoute } from "~/components/auth/ProtectedRoute";
import { AppShell } from "~/components/layout/AppShell";
import { Card, CardContent, CardHeader, CardTitle } from "~/components/ui/card";
import { Button } from "~/components/ui/button";
import { Badge } from "~/components/ui/badge";
import { Skeleton } from "~/components/ui/skeleton";
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
import { api } from "~/lib/api";
import { traderKeys } from "~/lib/query-keys";
import type { Trader } from "~/lib/types";

function StatusBadge(props: { status: Trader["status"] }) {
  const variant = () => {
    switch (props.status) {
      case "running":
        return "success";
      case "stopped":
        return "secondary";
      case "error":
        return "destructive";
      default:
        return "outline";
    }
  };

  return <Badge variant={variant()}>{props.status}</Badge>;
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

  const traderQuery = createQuery(() => ({
    queryKey: traderKeys.detail(params.id),
    queryFn: () => api.getTrader(params.id),
  }));

  const statusQuery = createQuery(() => ({
    queryKey: traderKeys.status(params.id),
    queryFn: () => api.getTraderStatus(params.id),
    refetchInterval: 10000,
  }));

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

  return (
    <ProtectedRoute>
      <AppShell>
        <Suspense fallback={<LoadingSkeleton />}>
          <Show when={traderQuery.data}>
            {(trader) => (
              <div class="space-y-6">
                <div class="flex items-center justify-between">
                  <div>
                    <h1 class="text-2xl font-bold">{trader().name}</h1>
                    <p class="text-muted-foreground font-mono text-sm">
                      {trader().wallet_address}
                    </p>
                  </div>
                  <div class="flex items-center gap-2">
                    <Button
                      variant="outline"
                      onClick={() => restartMutation.mutate()}
                      disabled={restartMutation.isPending}
                    >
                      <RefreshCw class={`h-4 w-4 mr-2 ${restartMutation.isPending ? "animate-spin" : ""}`} />
                      Restart
                    </Button>

                    <AlertDialog open={deleteOpen()} onOpenChange={setDeleteOpen}>
                      <AlertDialogTrigger as={Button} variant="destructive">
                        <Trash2 class="h-4 w-4 mr-2" />
                        Delete
                      </AlertDialogTrigger>
                      <AlertDialogContent>
                        <AlertDialogHeader>
                          <AlertDialogTitle>Delete Trader</AlertDialogTitle>
                          <AlertDialogDescription>
                            Are you sure you want to delete "{trader().name}"? This action cannot be undone.
                          </AlertDialogDescription>
                        </AlertDialogHeader>
                        <AlertDialogFooter>
                          <AlertDialogCancel>Cancel</AlertDialogCancel>
                          <AlertDialogAction
                            onClick={() => deleteMutation.mutate()}
                          >
                            {deleteMutation.isPending ? "Deleting..." : "Delete"}
                          </AlertDialogAction>
                        </AlertDialogFooter>
                      </AlertDialogContent>
                    </AlertDialog>
                  </div>
                </div>

                <div class="grid gap-6 md:grid-cols-2">
                  <Card>
                    <CardHeader>
                      <CardTitle>Status</CardTitle>
                    </CardHeader>
                    <CardContent class="space-y-4">
                      <div class="flex items-center justify-between">
                        <span class="text-muted-foreground">Current Status</span>
                        <StatusBadge status={trader().status} />
                      </div>
                      <Show when={statusQuery.data?.uptime_seconds}>
                        <div class="flex items-center justify-between">
                          <span class="text-muted-foreground">Uptime</span>
                          <span>{Math.floor(statusQuery.data!.uptime_seconds! / 60)} minutes</span>
                        </div>
                      </Show>
                      <Show when={statusQuery.data?.last_error}>
                        <div class="pt-2 border-t">
                          <span class="text-muted-foreground text-sm">Last Error:</span>
                          <p class="text-destructive text-sm mt-1">{statusQuery.data!.last_error}</p>
                        </div>
                      </Show>
                    </CardContent>
                  </Card>

                  <Card>
                    <CardHeader>
                      <CardTitle>Details</CardTitle>
                    </CardHeader>
                    <CardContent class="space-y-4">
                      <div class="flex items-center justify-between">
                        <span class="text-muted-foreground">Created</span>
                        <span>{new Date(trader().created_at).toLocaleString()}</span>
                      </div>
                      <div class="flex items-center justify-between">
                        <span class="text-muted-foreground">Last Updated</span>
                        <span>{new Date(trader().updated_at).toLocaleString()}</span>
                      </div>
                    </CardContent>
                  </Card>
                </div>

                <LogViewer traderId={params.id} />
              </div>
            )}
          </Show>
        </Suspense>
      </AppShell>
    </ProtectedRoute>
  );
};

export default TraderDetailPage;
