import { type JSX, splitProps } from "solid-js";
import { cn } from "~/lib/utils";

export interface InputProps extends JSX.InputHTMLAttributes<HTMLInputElement> {}

export function Input(props: InputProps) {
  const [local, others] = splitProps(props, ["class", "type"]);
  return (
    <input
      type={local.type}
      class={cn(
        "flex h-9 w-full rounded-md border border-border-default bg-transparent px-3 py-1 text-sm text-text-base shadow-sm transition-colors",
        "file:border-0 file:bg-transparent file:text-sm file:font-medium",
        "placeholder:text-text-faint",
        "focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-border-ring",
        "disabled:cursor-not-allowed disabled:opacity-50",
        local.class
      )}
      {...others}
    />
  );
}
