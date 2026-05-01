import { type JSX, type Component, splitProps, Show } from "solid-js";
import { Loader2 } from "lucide-solid";
import { Tooltip, TooltipContent, TooltipTrigger } from "./tooltip";
import { cn } from "~/lib/utils";

export interface IconButtonProps
  extends JSX.ButtonHTMLAttributes<HTMLButtonElement> {
  icon: Component<{ class?: string }>;
  tooltip: string;
  variant?: "ghost" | "danger";
  loading?: boolean;
}

export function IconButton(props: IconButtonProps) {
  const [local, others] = splitProps(props, [
    "icon",
    "tooltip",
    "variant",
    "loading",
    "class",
    "disabled",
  ]);

  const variant = () => local.variant ?? "ghost";

  return (
    <Tooltip>
      <TooltipTrigger
        as="button"
        type="button"
        // Provide accessible name + native title fallback for icon-only buttons.
        // Kobalte tooltips render visually on hover but don't set the accessible
        // name on the trigger, leaving these buttons unnamed for screen readers.
        aria-label={local.tooltip}
        title={local.tooltip}
        disabled={local.disabled || local.loading}
        class={cn(
          "p-1.5 rounded transition-colors disabled:opacity-50",
          variant() === "ghost" &&
            "hover:bg-surface-overlay text-text-muted hover:text-text-secondary",
          variant() === "danger" &&
            "hover:bg-surface-overlay text-text-muted hover:text-error",
          local.class
        )}
        {...others}
      >
        <Show
          when={local.loading}
          fallback={<local.icon class="h-4 w-4" />}
        >
          <Loader2 class="h-4 w-4 animate-spin" />
        </Show>
      </TooltipTrigger>
      <TooltipContent>{local.tooltip}</TooltipContent>
    </Tooltip>
  );
}
