import { type Component, Show, For, Suspense } from "solid-js";
import { createQuery } from "@tanstack/solid-query";
import { A } from "@solidjs/router";
import { Plus } from "lucide-solid";
import { AppShell } from "~/components/layout/AppShell";
import { Button } from "~/components/ui/button";
import { Badge } from "~/components/ui/badge";
import { Skeleton } from "~/components/ui/skeleton";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "~/components/ui/table";
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
    <div class="space-y-2">
      <For each={[1, 2, 3, 4, 5]}>
        {() => <Skeleton class="h-12 w-full" />}
      </For>
    </div>
  );
}

const TradersPage: Component = () => {
  const tradersQuery = createQuery(() => ({
    queryKey: traderKeys.lists(),
    queryFn: () => api.listTraders(),
  }));

  return (
    <AppShell>
      <div class="space-y-6">
        <div class="flex items-center justify-between">
          <div>
            <h1 class="text-2xl font-bold">Traders</h1>
            <p class="text-muted-foreground">All your trading bots</p>
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
              <div class="text-center py-12 text-muted-foreground">
                <p class="mb-4">No traders found</p>
                <A href="/traders/new">
                  <Button>Create your first trader</Button>
                </A>
              </div>
            }
          >
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Name</TableHead>
                  <TableHead>Wallet</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Created</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                <For each={tradersQuery.data}>
                  {(trader) => (
                    <TableRow>
                      <TableCell>
                        <A
                          href={`/traders/${trader.id}`}
                          class="font-medium hover:underline"
                        >
                          {trader.name}
                        </A>
                      </TableCell>
                      <TableCell class="font-mono text-xs truncate max-w-[200px]">
                        {trader.wallet_address}
                      </TableCell>
                      <TableCell>
                        <StatusBadge status={trader.status} />
                      </TableCell>
                      <TableCell>
                        {new Date(trader.created_at).toLocaleDateString()}
                      </TableCell>
                    </TableRow>
                  )}
                </For>
              </TableBody>
            </Table>
          </Show>
        </Suspense>
      </div>
    </AppShell>
  );
};

export default TradersPage;
