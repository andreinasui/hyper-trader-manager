import { type JSX, type Component } from "solid-js";
import { cn } from "~/lib/utils";

export interface EmptyStateProps {
  icon: Component<{ class?: string }>;
  title: string;
  description: string;
  action?: JSX.Element;
  class?: string;
}

export function EmptyState(props: EmptyStateProps) {
  return (
    <div
      class={cn(
        "bg-surface-raised border border-border-default rounded-md p-12 flex flex-col items-center justify-center text-center",
        props.class
      )}
    >
      <div class="bg-surface-overlay rounded-md p-3 mb-4">
        <props.icon class="w-10 h-10 text-text-subtle" />
      </div>
      <h3 class="text-base font-semibold text-text-secondary mb-1">
        {props.title}
      </h3>
      <p class="text-sm text-text-subtle mb-4">{props.description}</p>
      {props.action}
    </div>
  );
}
