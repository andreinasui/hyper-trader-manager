import { type Component, Show } from "solid-js";
import { ProtectedRoute } from "~/components/auth/ProtectedRoute";
import { AppShell } from "~/components/layout/AppShell";
import { PageHeader } from "~/components/layout/PageHeader";
import { PageContent } from "~/components/layout/PageContent";
import { PageTitle } from "~/components/layout/PageTitle";
import { Panel, PanelHeader, PanelBody, PanelRow } from "~/components/ui/panel";
import { Badge } from "~/components/ui/badge";
import { authStore } from "~/stores/auth";

const SettingsPage: Component = () => {
  const user = () => authStore.user();

  return (
    <ProtectedRoute>
      <AppShell>
        <PageHeader breadcrumbs={[{ label: "Settings" }]} />
        <PageContent maxWidth="2xl">
          <PageTitle title="Settings" subtitle="Your account information" />

          <Panel>
            <PanelHeader title="Account" description="Your account details" />
            <PanelBody class="py-0">
              <PanelRow label="Username">
                <span class="font-medium">{user()?.username}</span>
              </PanelRow>
              <PanelRow label="Role">
                <Show
                  when={user()?.is_admin}
                  fallback={<Badge variant="secondary">User</Badge>}
                >
                  <Badge>Admin</Badge>
                </Show>
              </PanelRow>
              <PanelRow label="Account created" border={false}>
                {user()?.created_at
                  ? new Date(user()!.created_at).toLocaleDateString()
                  : "—"}
              </PanelRow>
            </PanelBody>
          </Panel>
        </PageContent>
      </AppShell>
    </ProtectedRoute>
  );
};

export default SettingsPage;
