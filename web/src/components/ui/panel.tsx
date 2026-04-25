import { type JSX, type Component, splitProps } from "solid-js";
import { cn } from "~/lib/utils";

export interface PanelProps extends JSX.HTMLAttributes<HTMLDivElement> {}

export function Panel(props: PanelProps) {
  const [local, others] = splitProps(props, ["class", "children"]);
  return (
    <div
      class={cn(
        "bg-surface-raised border border-border-default rounded-md overflow-hidden",
        "shadow-[0_1px_3px_rgba(0,0,0,0.3)]",
        local.class
      )}
      {...others}
    >
      {local.children}
    </div>
  );
}

export interface PanelHeaderProps {
  icon?: Component<{ class?: string }>;
  title: string;
  description?: string;
  class?: string;
}

export function PanelHeader(props: PanelHeaderProps) {
  return (
    <div
      class={cn(
        "px-5 py-3.5 border-b border-border-default flex items-center gap-2.5",
        "bg-gradient-to-b from-surface-raised to-surface-base/50",
        props.class
      )}
    >
      {props.icon && <props.icon class="w-4 h-4 text-text-subtle shrink-0" />}
      <span class="text-sm font-medium text-text-secondary tracking-tight">{props.title}</span>
      {props.description && (
        <span class="ml-auto text-xs text-text-faint hidden sm:block font-mono">
          {props.description}
        </span>
      )}
    </div>
  );
}

export interface PanelBodyProps extends JSX.HTMLAttributes<HTMLDivElement> {}

export function PanelBody(props: PanelBodyProps) {
  const [local, others] = splitProps(props, ["class", "children"]);
  return (
    <div class={cn("px-5 py-5", local.class)} {...others}>
      {local.children}
    </div>
  );
}

export interface PanelRowProps {
  label: string;
  children: JSX.Element;
  border?: boolean;
  class?: string;
}

export function PanelRow(props: PanelRowProps) {
  const showBorder = props.border ?? true;
  return (
    <div
      class={cn(
        "flex justify-between items-center py-3 gap-4",
        showBorder && "border-b border-border-default last:border-b-0",
        "transition-colors duration-150 hover:bg-surface-overlay/30",
        props.class
      )}
    >
      <span class="text-sm text-text-subtle font-medium tracking-tight">{props.label}</span>
      <div class="text-sm text-text-secondary font-mono tabular-nums">{props.children}</div>
    </div>
  );
}
