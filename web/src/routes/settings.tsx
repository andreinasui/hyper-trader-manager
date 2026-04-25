import { type Component, Show } from "solid-js";
import { ProtectedRoute } from "~/components/auth/ProtectedRoute";
import { AppShell } from "~/components/layout/AppShell";
import { authStore } from "~/stores/auth";

const SettingsPage: Component = () => {
  const user = () => authStore.user();

  return (
    <ProtectedRoute>
      <AppShell>
        {/* Top bar strip — REQUIRED first child */}
        <div class="h-14 border-b border-[#222426] flex items-center justify-between px-6 bg-[#08090a] sticky top-0 z-20">
          <div class="flex items-center gap-2 text-sm">
            <span class="text-zinc-500">Workspace</span>
            <span class="text-zinc-600">/</span>
            <span class="text-zinc-300 font-medium">Settings</span>
          </div>
          {/* ⌘K button */}
          <button class="flex items-center gap-2 px-3 py-1.5 rounded-md border border-[#222426] text-zinc-400 hover:text-zinc-200 hover:bg-[#111214] transition-all text-sm">
            <span class="text-zinc-500">⌘</span>
            <span class="font-mono text-xs text-zinc-400">K</span>
          </button>
        </div>

        {/* Page content */}
        <div class="p-6 max-w-2xl space-y-8">
          {/* Account Card */}
          <div class="bg-[#111214] border border-[#222426] rounded-md overflow-hidden">
            {/* Header */}
            <div class="px-5 py-4 border-b border-[#222426]">
              <div class="text-sm font-semibold text-zinc-300">Account</div>
              <div class="text-xs text-zinc-500 mt-0.5">Your account information</div>
            </div>

            {/* Rows */}
            <div class="px-5 py-4 border-b border-[#222426] flex justify-between items-center">
              <span class="text-sm text-zinc-500">Username</span>
              <span class="text-sm text-zinc-200 font-medium">{user()?.username}</span>
            </div>

            <div class="px-5 py-4 border-b border-[#222426] flex justify-between items-center">
              <span class="text-sm text-zinc-500">Role</span>
              <Show
                when={user()?.is_admin}
                fallback={
                  <span class="inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-xs font-medium bg-zinc-800 text-zinc-400">
                    <span class="h-1 w-1 rounded-full bg-zinc-500" />
                    User
                  </span>
                }
              >
                <span class="inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-xs font-medium bg-[#5e6ad2]/20 text-[#5e6ad2]">
                  <span class="h-1 w-1 rounded-full bg-[#5e6ad2]" />
                  Admin
                </span>
              </Show>
            </div>

            <div class="px-5 py-4 flex justify-between items-center">
              <span class="text-sm text-zinc-500">Account created</span>
              <span class="text-sm text-zinc-400">
                {user()?.created_at ? new Date(user()!.created_at).toLocaleDateString() : "—"}
              </span>
            </div>
          </div>
        </div>
      </AppShell>
    </ProtectedRoute>
  );
};

export default SettingsPage;
