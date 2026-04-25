import { type Component } from "solid-js";
import { useNavigate } from "@solidjs/router";
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
        <div class="max-w-4xl mx-auto">
          <h1 class="text-2xl font-bold mb-6">Create New Trader</h1>

          <TraderConfigForm
            onSubmit={handleSubmit}
            isSubmitting={createTraderMutation.isPending}
            submitLabel="Create Trader"
          />
        </div>
      </AppShell>
    </ProtectedRoute>
  );
};

export default NewTraderPage;
