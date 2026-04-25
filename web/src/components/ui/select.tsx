import { type JSX, splitProps, For } from "solid-js";
import { cn } from "~/lib/utils";

export interface SelectOption {
  value: string;
  label: string;
}

export interface SelectProps
  extends Omit<JSX.SelectHTMLAttributes<HTMLSelectElement>, "onChange"> {
  options: SelectOption[];
  onChange?: (value: string) => void;
  placeholder?: string;
}

export function Select(props: SelectProps) {
  const [local, others] = splitProps(props, [
    "class",
    "options",
    "onChange",
    "placeholder",
  ]);

  return (
    <select
      class={cn(
        "flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50",
        local.class
      )}
      onChange={(e) => local.onChange?.(e.currentTarget.value)}
      {...others}
    >
      {local.placeholder && (
        <option value="" disabled>
          {local.placeholder}
        </option>
      )}
      <For each={local.options}>
        {(option) => <option value={option.value}>{option.label}</option>}
      </For>
    </select>
  );
}
