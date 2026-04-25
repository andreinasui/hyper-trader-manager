import { type JSX, splitProps } from "solid-js";
import { cn } from "~/lib/utils";

export type KpiVariant = "default" | "success" | "warning" | "error";

export interface KpiCardProps {
  label: string;
  value: number | string;
  variant?: KpiVariant;
  class?: string;
}

const dotColors: Record<KpiVariant, string> = {
  default: "bg-text-subtle",
  success: "bg-success",
  warning: "bg-warning",
  error: "bg-error",
};

export function KpiCard(props: KpiCardProps) {
  const variant = () => props.variant ?? "default";
  return (
    <div
      class={cn(
        "bg-surface-raised border border-border-default rounded-md p-4 hover:bg-surface-overlay transition-all",
        props.class
      )}
    >
      <div class="flex items-center gap-2 mb-2">
        <div class={cn("w-1.5 h-1.5 rounded-full", dotColors[variant()])} />
        <span class="text-xs font-medium text-text-subtle uppercase tracking-wide">
          {props.label}
        </span>
      </div>
      <div class="text-2xl font-semibold tabular-nums text-text-base">
        {props.value}
      </div>
    </div>
  );
}

export interface KpiStripProps extends JSX.HTMLAttributes<HTMLDivElement> {}

export function KpiStrip(props: KpiStripProps) {
  const [local, others] = splitProps(props, ["class", "children"]);
  return (
    <div class={cn("grid grid-cols-3 gap-4", local.class)} {...others}>
      {local.children}
    </div>
  );
}
