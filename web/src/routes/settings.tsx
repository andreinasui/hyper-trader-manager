import { type Component, Show } from "solid-js";
import { AppShell } from "~/components/layout/AppShell";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "~/components/ui/card";
import { Badge } from "~/components/ui/badge";
import { Separator } from "~/components/ui/separator";
import { authStore } from "~/stores/auth";

const SettingsPage: Component = () => {
  const user = () => authStore.user();

  return (
    <AppShell>
      <div class="space-y-6 max-w-2xl">
        <div>
          <h1 class="text-2xl font-bold">Settings</h1>
          <p class="text-muted-foreground">Manage your account settings</p>
        </div>

        <Card>
          <CardHeader>
            <CardTitle>Account</CardTitle>
            <CardDescription>Your account information</CardDescription>
          </CardHeader>
          <CardContent class="space-y-4">
            <div class="flex items-center justify-between">
              <span class="text-muted-foreground">Username</span>
              <span class="font-medium">{user()?.username}</span>
            </div>
            <Separator />
            <div class="flex items-center justify-between">
              <span class="text-muted-foreground">Role</span>
              <Show
                when={user()?.is_admin}
                fallback={<Badge variant="secondary">User</Badge>}
              >
                <Badge>Admin</Badge>
              </Show>
            </div>
            <Separator />
            <div class="flex items-center justify-between">
              <span class="text-muted-foreground">Account Created</span>
              <span>{user()?.created_at ? new Date(user()!.created_at).toLocaleDateString() : "—"}</span>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Application</CardTitle>
            <CardDescription>Application information</CardDescription>
          </CardHeader>
          <CardContent class="space-y-4">
            <div class="flex items-center justify-between">
              <span class="text-muted-foreground">Version</span>
              <span class="font-mono text-sm">1.0.0</span>
            </div>
            <Separator />
            <div class="flex items-center justify-between">
              <span class="text-muted-foreground">Framework</span>
              <span class="font-mono text-sm">SolidJS 2.0</span>
            </div>
          </CardContent>
        </Card>
      </div>
    </AppShell>
  );
};

export default SettingsPage;
