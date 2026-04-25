import { cn } from "~/lib/utils";

export interface SectionLabelProps {
  label: string;
  class?: string;
}

export function SectionLabel(props: SectionLabelProps) {
  return (
    <div class={cn("flex items-center gap-3 pt-1 pb-0.5", props.class)}>
      <span class="text-[10px] font-semibold text-text-subtle uppercase tracking-widest shrink-0">
        {props.label}
      </span>
      <div class="flex-1 h-px bg-border-default" />
    </div>
  );
}
