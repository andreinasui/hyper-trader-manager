import { Tooltip as TooltipPrimitive } from "@kobalte/core/tooltip";
import { splitProps } from "solid-js";
import { cn } from "~/lib/utils";

export const Tooltip = TooltipPrimitive;
export const TooltipTrigger = TooltipPrimitive.Trigger;

export function TooltipContent(props: TooltipPrimitive.ContentProps) {
  const [local, others] = splitProps(props, ["class"]);
  return (
    <TooltipPrimitive.Portal>
      <TooltipPrimitive.Content
        class={cn(
          "z-50 overflow-hidden rounded-md bg-primary px-3 py-1.5 text-xs text-primary-foreground animate-in fade-in-0 zoom-in-95 data-[closed]:animate-out data-[closed]:fade-out-0 data-[closed]:zoom-out-95",
          local.class
        )}
        {...others}
      />
    </TooltipPrimitive.Portal>
  );
}
