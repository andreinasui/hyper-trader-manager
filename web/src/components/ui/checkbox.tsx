import { type JSX, splitProps } from "solid-js";
import { cn } from "~/lib/utils";

export interface CheckboxProps
  extends Omit<JSX.InputHTMLAttributes<HTMLInputElement>, "type" | "onChange"> {
  onChange?: (checked: boolean) => void;
}

export function Checkbox(props: CheckboxProps) {
  const [local, others] = splitProps(props, ["class", "onChange"]);

  return (
    <input
      type="checkbox"
      class={cn(
        "h-4 w-4 rounded border border-input bg-transparent text-primary shadow-sm transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50",
        local.class
      )}
      onChange={(e) => local.onChange?.(e.currentTarget.checked)}
      {...others}
    />
  );
}
