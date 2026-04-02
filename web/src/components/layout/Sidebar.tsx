import { type Component, Show, createSignal, For } from "solid-js";
import { A, useLocation, useNavigate } from "@solidjs/router";
import { LayoutDashboard, Bot, Settings, LogOut, Menu, X } from "lucide-solid";
import { Button } from "~/components/ui/button";
import { Separator } from "~/components/ui/separator";
import { authStore } from "~/stores/auth";
import { cn } from "~/lib/utils";

const navItems = [
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { href: "/traders", label: "Traders", icon: Bot },
  { href: "/settings", label: "Settings", icon: Settings },
];

export const Sidebar: Component = () => {
  const location = useLocation();
  const navigate = useNavigate();
  const [mobileOpen, setMobileOpen] = createSignal(false);

  async function handleLogout() {
    await authStore.logout();
    navigate("/");
  }

  const NavContent = () => (
    <div class="flex flex-col h-full">
      <div class="p-4">
        <h1 class="text-lg font-bold">Hyper Trader</h1>
      </div>

      <Separator />

      <nav class="flex-1 p-4 space-y-1">
        <For each={navItems}>
          {(item) => (
            <A
              href={item.href}
              class={cn(
                "flex items-center gap-3 px-3 py-2 rounded-md text-sm transition-colors",
                location.pathname === item.href || location.pathname.startsWith(item.href + "/")
                  ? "bg-secondary text-secondary-foreground"
                  : "hover:bg-secondary/50"
              )}
              onClick={() => setMobileOpen(false)}
            >
              <item.icon class="h-4 w-4" />
              {item.label}
            </A>
          )}
        </For>
      </nav>

      <Separator />

      <div class="p-4">
        <div class="flex items-center gap-3 mb-4">
          <div class="h-8 w-8 rounded-full bg-primary/20 flex items-center justify-center text-sm font-medium">
            {authStore.user()?.username?.charAt(0).toUpperCase()}
          </div>
          <div class="flex-1 truncate">
            <p class="text-sm font-medium truncate">{authStore.user()?.username}</p>
            <Show when={authStore.user()?.is_admin}>
              <p class="text-xs text-muted-foreground">Admin</p>
            </Show>
          </div>
        </div>

        <Button variant="outline" class="w-full" onClick={handleLogout}>
          <LogOut class="h-4 w-4 mr-2" />
          Sign Out
        </Button>
      </div>
    </div>
  );

  return (
    <>
      {/* Mobile menu button */}
      <div class="lg:hidden fixed top-4 left-4 z-50">
        <Button variant="outline" size="icon" onClick={() => setMobileOpen(!mobileOpen())}>
          <Show when={mobileOpen()} fallback={<Menu class="h-4 w-4" />}>
            <X class="h-4 w-4" />
          </Show>
        </Button>
      </div>

      {/* Mobile overlay */}
      <Show when={mobileOpen()}>
        <div
          class="lg:hidden fixed inset-0 bg-black/50 z-40"
          onClick={() => setMobileOpen(false)}
        />
      </Show>

      {/* Mobile sidebar */}
      <aside
        class={cn(
          "lg:hidden fixed inset-y-0 left-0 z-40 w-64 bg-background border-r transform transition-transform duration-200",
          mobileOpen() ? "translate-x-0" : "-translate-x-full"
        )}
      >
        <NavContent />
      </aside>

      {/* Desktop sidebar */}
      <aside class="hidden lg:flex lg:w-64 lg:flex-col lg:fixed lg:inset-y-0 border-r bg-background">
        <NavContent />
      </aside>
    </>
  );
};
