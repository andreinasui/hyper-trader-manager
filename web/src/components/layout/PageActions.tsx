import { type Component, For, Show } from "solid-js";
import { MoreHorizontal, type LucideIcon } from "lucide-solid";
import { Button } from "~/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuTrigger,
  DropdownMenuContent,
  DropdownMenuItem,
} from "~/components/ui/dropdown-menu";
import { cn } from "~/lib/utils";

export interface PageAction {
  label: string;
  icon?: LucideIcon;
  onClick: () => void;
  priority: "primary" | "secondary";
  disabled?: boolean;
  loading?: boolean;
  variant?: "default" | "danger";
}

export interface PageActionsProps {
  actions: PageAction[];
  class?: string;
}

/**
 * Page-level action bar. On wide containers (>= @md ≈ 28rem) all actions render inline.
 * On narrow containers, secondary actions collapse into a single overflow `⋯` dropdown.
 * Primary actions always stay inline.
 *
 * Uses container queries on its own wrapper so it adapts inside narrow contexts
 * (modals, sidebar panels) too — not just the viewport.
 */
export const PageActions: Component<PageActionsProps> = (props) => {
  const primary = () => props.actions.filter((a) => a.priority === "primary");
  const secondary = () => props.actions.filter((a) => a.priority === "secondary");

  return (
    <div class={cn("@container", props.class)}>
      <div class="flex items-center gap-2 justify-end">
        {/* Primaries: always inline */}
        <div data-page-actions-inline class="flex items-center gap-2">
          <For each={primary()}>{(a) => <ActionButton action={a} />}</For>
        </div>

        {/* Secondaries inline: only on wide containers */}
        <Show when={secondary().length > 0}>
          <div data-page-actions-secondary-inline class="hidden @md:flex items-center gap-2">
            <For each={secondary()}>{(a) => <ActionButton action={a} />}</For>
          </div>
        </Show>

        {/* Secondaries overflow: only on narrow containers */}
        <Show when={secondary().length > 0}>
          <div data-page-actions-overflow class="@md:hidden">
            <DropdownMenu>
              <DropdownMenuTrigger
                as={(p: Record<string, unknown>) => (
                  <Button {...p} variant="outline" size="icon" aria-label="More actions">
                    <MoreHorizontal class="h-4 w-4" stroke-width={1.5} />
                  </Button>
                )}
              />
              <DropdownMenuContent>
                <For each={secondary()}>
                  {(a) => (
                    <DropdownMenuItem
                      onSelect={() => a.onClick()}
                      class={cn(a.variant === "danger" && "text-destructive focus:text-destructive")}
                    >
                      <Show when={a.icon} keyed>
                        {(Icon) => <Icon class="h-4 w-4 mr-2" stroke-width={1.5} />}
                      </Show>
                      {a.label}
                    </DropdownMenuItem>
                  )}
                </For>
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
        </Show>
      </div>
    </div>
  );
};

function ActionButton(props: { action: PageAction }) {
  const a = () => props.action;
  return (
    <Button
      variant={a().variant === "danger" ? "destructive" : "default"}
      onClick={() => a().onClick()}
      disabled={a().disabled || a().loading}
    >
      <Show when={a().icon} keyed>
        {(Icon) => <Icon class="h-4 w-4 mr-2" stroke-width={1.5} />}
      </Show>
      {a().label}
    </Button>
  );
}
