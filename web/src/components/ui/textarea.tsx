import { type JSX, splitProps } from "solid-js";
import { cn } from "~/lib/utils";

export interface TextareaProps
  extends JSX.TextareaHTMLAttributes<HTMLTextAreaElement> {}

export function Textarea(props: TextareaProps) {
  const [local, others] = splitProps(props, ["class"]);
  return (
    <textarea
      class={cn(
        "flex min-h-[60px] w-full rounded-md border border-border-default bg-transparent px-3 py-2 text-sm text-text-base placeholder:text-text-faint",
        "focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-border-ring",
        "disabled:cursor-not-allowed disabled:opacity-50 resize-none",
        local.class
      )}
      {...others}
    />
  );
}
