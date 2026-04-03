import { type Component, Show, For, Suspense } from "solid-js";
import { createQuery } from "@tanstack/solid-query";
import { A } from "@solidjs/router";
import { Plus } from "lucide-solid";
import { ProtectedRoute } from "~/components/auth/ProtectedRoute";
import { AppShell } from "~/components/layout/AppShell";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "~/components/ui/card";
import { Button } from "~/components/ui/button";
import { Badge } from "~/components/ui/badge";
import { Skeleton } from "~/components/ui/skeleton";
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

function TraderCard(props: { trader: Trader }) {
  return (
    <A href={`/traders/${props.trader.id}`}>
      <Card class="hover:bg-secondary/50 transition-colors cursor-pointer">
        <CardHeader class="pb-2">
          <div class="flex items-center justify-between">
            <CardTitle class="text-lg">{props.trader.name}</CardTitle>
            <StatusBadge status={props.trader.status} />
          </div>
          <CardDescription class="font-mono text-xs truncate">
            {props.trader.wallet_address}
          </CardDescription>
        </CardHeader>
        <CardContent>
          <p class="text-sm text-muted-foreground">
            Created {new Date(props.trader.created_at).toLocaleDateString()}
          </p>
        </CardContent>
      </Card>
    </A>
  );
}

function LoadingSkeleton() {
  return (
    <div class="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
      <For each={[1, 2, 3]}>
        {() => (
          <Card>
            <CardHeader>
              <Skeleton class="h-6 w-32" />
              <Skeleton class="h-4 w-48 mt-2" />
            </CardHeader>
            <CardContent>
              <Skeleton class="h-4 w-24" />
            </CardContent>
          </Card>
        )}
      </For>
    </div>
  );
}

const DashboardPage: Component = () => {
  const tradersQuery = createQuery(() => ({
    queryKey: traderKeys.lists(),
    queryFn: () => api.listTraders(),
  }));

  return (
    <ProtectedRoute>
      <AppShell>
        <div class="space-y-6">
          <div class="flex items-center justify-between">
            <div>
              <h1 class="text-2xl font-bold">Dashboard</h1>
              <p class="text-muted-foreground">Manage your trading bots</p>
            </div>
            <A href="/traders/new">
              <Button>
                <Plus class="h-4 w-4 mr-2" />
                New Trader
              </Button>
            </A>
          </div>

          <Suspense fallback={<LoadingSkeleton />}>
            <Show
              when={tradersQuery.data && tradersQuery.data.length > 0}
              fallback={
                <Card>
                  <CardContent class="py-12 text-center">
                    <p class="text-muted-foreground mb-4">No traders yet</p>
                    <A href="/traders/new">
                      <Button>Create your first trader</Button>
                    </A>
                  </CardContent>
                </Card>
              }
            >
              <div class="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
                <For each={tradersQuery.data}>
                  {(trader) => <TraderCard trader={trader} />}
                </For>
              </div>
            </Show>
          </Suspense>
        </div>
      </AppShell>
    </ProtectedRoute>
  );
};

export default DashboardPage;
