import { type JSX, For, splitProps } from "solid-js";
import { cn } from "~/lib/utils";

export interface ToggleOption {
  value: string;
  label: string;
}

export interface ToggleGroupProps {
  options: ToggleOption[];
  value: string;
  onChange: (value: string) => void;
  class?: string;
}

export function ToggleGroup(props: ToggleGroupProps) {
  return (
    <div
      class={cn(
        "flex h-7 w-fit rounded border border-border-default overflow-hidden text-xs",
        props.class
      )}
    >
      <For each={props.options}>
        {(option, index) => (
          <>
            {index() > 0 && <div class="w-px bg-border-default" />}
            <button
              type="button"
              class={cn(
                "px-4 h-full transition-colors",
                props.value === option.value
                  ? "bg-surface-overlay text-text-base font-medium"
                  : "text-text-subtle hover:text-text-tertiary"
              )}
              onClick={() => props.onChange(option.value)}
            >
              {option.label}
            </button>
          </>
        )}
      </For>
    </div>
  );
}
