import { type Component, type JSX, Show, createSignal, For } from "solid-js";
import { A, useLocation, useNavigate } from "@solidjs/router";
import { Bot, Settings, LogOut, ChevronLeft, Menu, X } from "lucide-solid";
import { authStore } from "~/stores/auth";
import { cn } from "~/lib/utils";

interface NavItem {
  href: string;
  label: string;
  icon: Component<{ class?: string }>;
}

const navItems: NavItem[] = [
  { href: "/traders", label: "Traders", icon: Bot },
  { href: "/settings", label: "Settings", icon: Settings },
];

interface SidebarProps {
  expanded: boolean;
  onToggle: () => void;
}

export const Sidebar: Component<SidebarProps> = (props) => {
  const location = useLocation();
  const navigate = useNavigate();
  const [mobileOpen, setMobileOpen] = createSignal(false);

  async function handleLogout() {
    await authStore.logout();
    navigate("/");
  }

  const isActive = (href: string): boolean => {
    return location.pathname === href || location.pathname.startsWith(href + "/");
  };

  const NavContent = (contentProps: { expanded: boolean; mobile?: boolean }): JSX.Element => (
    <div class="flex flex-col h-full bg-surface-raised border-r border-border-default">
      {/* Logo section */}
      <div
        class={cn(
          "flex items-center gap-3 p-4 border-b border-border-default",
          !contentProps.expanded && !contentProps.mobile && "justify-center"
        )}
        style={{ height: "56px" }}
      >
        <div class="w-8 h-8 rounded-md bg-primary flex items-center justify-center flex-shrink-0">
          <span class="text-white font-bold text-sm font-mono">HT</span>
        </div>
        <Show when={contentProps.expanded || contentProps.mobile}>
          <span class="text-text-base font-semibold text-base">HyperTrader</span>
        </Show>
      </div>

      {/* Navigation */}
      <nav class="flex-1 p-3 space-y-1">
        <For each={navItems}>
          {(item) => (
            <A
              href={item.href}
              class={cn(
                "flex items-center gap-3 px-3 py-2 rounded-md text-sm transition-all duration-150",
                isActive(item.href)
                  ? "text-primary bg-surface-overlay"
                  : "text-text-muted hover:text-text-secondary hover:bg-surface-raised",
                !contentProps.expanded && !contentProps.mobile && "justify-center"
              )}
              onClick={() => contentProps.mobile && setMobileOpen(false)}
              title={!contentProps.expanded && !contentProps.mobile ? item.label : undefined}
            >
              <item.icon class="h-4 w-4 flex-shrink-0" />
              <Show when={contentProps.expanded || contentProps.mobile}>
                <span>{item.label}</span>
              </Show>
            </A>
          )}
        </For>
      </nav>

      {/* Collapse toggle (desktop only) */}
      <Show when={!contentProps.mobile}>
        <div class="px-3 pb-3">
          <button
            onClick={props.onToggle}
            class={cn(
              "w-full flex items-center gap-3 px-3 py-2 rounded-md text-sm transition-all duration-150",
              "text-text-muted hover:text-text-secondary hover:bg-surface-raised",
              !contentProps.expanded && "justify-center"
            )}
            title={!contentProps.expanded ? "Expand sidebar" : undefined}
          >
            <ChevronLeft
              class={cn(
                "h-4 w-4 flex-shrink-0 transition-transform duration-150",
                !contentProps.expanded && "rotate-180"
              )}
            />
            <Show when={contentProps.expanded}>
              <span>Collapse</span>
            </Show>
          </button>
        </div>
      </Show>

      {/* User section */}
      <div class="border-t border-border-default p-3">
        <div
          class={cn(
            "flex items-center gap-3 mb-3",
            !contentProps.expanded && !contentProps.mobile && "justify-center"
          )}
        >
          <div class="h-8 w-8 rounded-full bg-primary-muted flex items-center justify-center text-sm font-medium text-primary flex-shrink-0">
            {authStore.user()?.username?.charAt(0).toUpperCase()}
          </div>
          <Show when={contentProps.expanded || contentProps.mobile}>
            <div class="flex-1 min-w-0">
              <p class="text-sm font-medium text-text-base truncate">
                {authStore.user()?.username}
              </p>
              <Show when={authStore.user()?.is_admin}>
                <span class="inline-block px-1.5 py-0.5 text-[10px] font-medium text-primary bg-primary-muted rounded mt-0.5">
                  ADMIN
                </span>
              </Show>
            </div>
          </Show>
        </div>

        {/* Logout button */}
        <button
          onClick={handleLogout}
          class={cn(
            "w-full flex items-center gap-3 px-3 py-2 rounded-md text-sm transition-all duration-150",
            "text-text-muted hover:text-text-secondary hover:bg-surface-raised border border-border-default",
            !contentProps.expanded && !contentProps.mobile && "justify-center px-2"
          )}
          title={!contentProps.expanded && !contentProps.mobile ? "Sign out" : undefined}
        >
          <LogOut class="h-4 w-4 flex-shrink-0" />
          <Show when={contentProps.expanded || contentProps.mobile}>
            <span>Sign Out</span>
          </Show>
        </button>
      </div>

      {/* Version footer */}
      <Show when={contentProps.expanded || contentProps.mobile}>
        <div class="px-3 pb-2">
          <p class="text-xs text-text-faint font-mono">v{__APP_VERSION__}</p>
        </div>
      </Show>
    </div>
  );

  return (
    <>
      {/* Mobile menu button */}
      <div class="lg:hidden fixed top-4 left-4 z-50">
        <button
          data-mobile-sidebar-trigger
          onClick={() => setMobileOpen(!mobileOpen())}
          class="h-10 w-10 rounded-md bg-surface-raised border border-border-default flex items-center justify-center text-text-muted hover:text-text-secondary hover:bg-surface-overlay transition-all duration-150"
        >
          <Show when={mobileOpen()} fallback={<Menu class="h-4 w-4" />}>
            <X class="h-4 w-4" />
          </Show>
        </button>
      </div>

      {/* Mobile overlay */}
      <Show when={mobileOpen()}>
        <div
          data-mobile-sidebar-backdrop
          class="lg:hidden fixed inset-0 bg-black/50 z-40"
          onClick={() => setMobileOpen(false)}
        />
      </Show>

      {/* Mobile sidebar */}
      <aside
        data-mobile-sidebar
        class={cn(
          "lg:hidden fixed inset-y-0 left-0 z-40 w-64 transform transition-transform duration-200",
          mobileOpen() ? "translate-x-0" : "-translate-x-full"
        )}
      >
        <NavContent expanded={true} mobile={true} />
      </aside>

      {/* Desktop sidebar */}
      <aside
        class="hidden lg:flex lg:flex-col lg:fixed lg:inset-y-0 transition-all duration-200"
        style={{ width: props.expanded ? "220px" : "64px" }}
      >
        <NavContent expanded={props.expanded} />
      </aside>
    </>
  );
};
