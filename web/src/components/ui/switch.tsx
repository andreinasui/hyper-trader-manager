import { cn } from "~/lib/utils";

export interface SwitchProps {
  checked?: boolean;
  onChange?: (checked: boolean) => void;
  disabled?: boolean;
  class?: string;
  id?: string;
}

export function Switch(props: SwitchProps) {
  return (
    <button
      type="button"
      role="switch"
      id={props.id}
      aria-checked={props.checked ?? false}
      disabled={props.disabled}
      class={cn(
        "relative flex h-5 w-9 shrink-0 cursor-pointer items-center rounded-full p-[2px]",
        "transition-colors duration-200 ease-in-out",
        "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-border-ring focus-visible:ring-offset-1 focus-visible:ring-offset-surface-base",
        props.checked
          ? "bg-primary"
          : "bg-surface-overlay ring-1 ring-inset ring-border-default",
        props.disabled && "cursor-not-allowed opacity-50",
        props.class
      )}
      onClick={() => !props.disabled && props.onChange?.(!props.checked)}
    >
      <span
        class={cn(
          "block h-4 w-4 rounded-full shadow transition-transform duration-200",
          props.checked ? "translate-x-4 bg-white" : "translate-x-0 bg-text-subtle"
        )}
      />
    </button>
  );
}
