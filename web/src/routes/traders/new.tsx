import { type Component } from "solid-js";
import { A, useNavigate } from "@solidjs/router";
import { createMutation, useQueryClient } from "@tanstack/solid-query";
import { ProtectedRoute } from "~/components/auth/ProtectedRoute";
import { AppShell } from "~/components/layout/AppShell";
import { TraderConfigForm } from "~/components/traders/TraderConfigForm";
import { api } from "~/lib/api";
import { traderKeys } from "~/lib/query-keys";
import type { CreateTraderForm } from "~/lib/schemas/trader-config";
import type { CreateTraderRequest } from "~/lib/types";

const NewTraderPage: Component = () => {
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const createTraderMutation = createMutation(() => ({
    mutationFn: (data: CreateTraderForm) => {
      const payload: CreateTraderRequest = {
        wallet_address: data.wallet_address,
        private_key: data.private_key,
        config: data.config,
      };

      // Include name and description if provided
      if (data.name?.trim()) {
        payload.name = data.name.trim();
      }
      if (data.description?.trim()) {
        payload.description = data.description.trim();
      }

      return api.createTrader(payload);
    },
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: traderKeys.all });
      navigate("/traders");
    },
  }));

  const handleSubmit = async (data: CreateTraderForm) => {
    await createTraderMutation.mutateAsync(data);
  };

  return (
    <ProtectedRoute>
      <AppShell>
        {/* Top bar strip — REQUIRED first child */}
        <div class="h-14 border-b border-[#222426] flex items-center justify-between px-6 bg-[#08090a] sticky top-0 z-20">
          <div class="flex items-center gap-2 text-sm">
            <A href="/traders" class="text-zinc-500 hover:text-zinc-300 transition-colors">
              Traders
            </A>
            <span class="text-zinc-600">/</span>
            <span class="text-zinc-300 font-medium">New trader</span>
          </div>
          {/* ⌘K button */}
          <button class="flex items-center gap-2 px-3 py-1.5 rounded-md border border-[#222426] text-zinc-400 hover:text-zinc-200 hover:bg-[#111214] transition-all text-sm">
            <span class="text-zinc-500">⌘</span>
            <span class="font-mono text-xs text-zinc-400">K</span>
          </button>
        </div>

        {/* Page content */}
        <div class="p-6 max-w-4xl space-y-6">
          <div>
            <h1 class="text-2xl font-semibold tracking-tight text-zinc-50">New trader</h1>
            <p class="text-sm text-zinc-500 mt-1">Configure and deploy a new trading bot</p>
          </div>

          <div class="bg-[#111214] border border-[#222426] rounded-md overflow-hidden p-6">
            <TraderConfigForm
              onSubmit={handleSubmit}
              isSubmitting={createTraderMutation.isPending}
              submitLabel="Create Trader"
            />
          </div>
        </div>
      </AppShell>
    </ProtectedRoute>
  );
};

export default NewTraderPage;
