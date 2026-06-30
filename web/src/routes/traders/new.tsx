import { type Component } from "solid-js";
import { useNavigate } from "@solidjs/router";
import { createMutation, useQueryClient } from "@tanstack/solid-query";
import { ProtectedRoute } from "~/components/auth/ProtectedRoute";
import { AppShell } from "~/components/layout/AppShell";
import { PageHeader } from "~/components/layout/PageHeader";
import { PageContent } from "~/components/layout/PageContent";
import { PageTitle } from "~/components/layout/PageTitle";
import { TraderForm } from "~/components/traders/TraderConfigForm";
import { toCreateTraderRequest, type TraderFormValues } from "~/components/traders/trader-form-model";
import { api } from "~/lib/api";
import { traderKeys } from "~/lib/query-keys";

const NewTraderPage: Component = () => {
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const createTraderMutation = createMutation(() => ({
    mutationFn: (data: TraderFormValues) => api.createTrader(toCreateTraderRequest(data)),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: traderKeys.all });
      navigate("/traders");
    },
  }));

  const handleSubmit = async (data: TraderFormValues) => {
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

          <TraderForm
            mode="create"
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
