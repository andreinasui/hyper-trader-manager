import { type Component } from "solid-js";
import { useNavigate } from "@solidjs/router";
import { createMutation, useQueryClient } from "@tanstack/solid-query";
import { ProtectedRoute } from "~/components/auth/ProtectedRoute";
import { AppShell } from "~/components/layout/AppShell";
import { PageHeader } from "~/components/layout/PageHeader";
import { PageContent } from "~/components/layout/PageContent";
import { PageTitle } from "~/components/layout/PageTitle";
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
        <PageHeader
          breadcrumbs={[
            { label: "Traders", href: "/traders" },
            { label: "New trader" },
          ]}
        />
        <PageContent maxWidth="3xl">
          <PageTitle
            backLink={{ label: "Back to traders", href: "/traders" }}
            title="New trader"
            subtitle="Configure and deploy a new trading bot"
          />

          <TraderConfigForm
            onSubmit={handleSubmit}
            isSubmitting={createTraderMutation.isPending}
            submitLabel="Create Trader"
          />
        </PageContent>
      </AppShell>
    </ProtectedRoute>
  );
};

export default NewTraderPage;
