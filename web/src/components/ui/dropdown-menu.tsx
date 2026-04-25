import { DropdownMenu as DropdownMenuPrimitive } from "@kobalte/core/dropdown-menu";
import { type ParentProps, splitProps } from "solid-js";
import { cn } from "~/lib/utils";

export const DropdownMenu = DropdownMenuPrimitive;
export const DropdownMenuTrigger = DropdownMenuPrimitive.Trigger;
export const DropdownMenuGroup = DropdownMenuPrimitive.Group;
export const DropdownMenuSub = DropdownMenuPrimitive.Sub;
export const DropdownMenuRadioGroup = DropdownMenuPrimitive.RadioGroup;

export interface DropdownMenuContentProps {
  class?: string;
}

export function DropdownMenuContent(props: DropdownMenuContentProps) {
  const [local, others] = splitProps(props, ["class"]);
  return (
    <DropdownMenuPrimitive.Portal>
      <DropdownMenuPrimitive.Content
        class={cn(
          "z-50 min-w-[8rem] overflow-hidden rounded-md border bg-popover p-1 text-popover-foreground shadow-md data-[expanded]:animate-in data-[closed]:animate-out data-[closed]:fade-out-0 data-[expanded]:fade-in-0 data-[closed]:zoom-out-95 data-[expanded]:zoom-in-95",
          local.class
        )}
        {...others}
      />
    </DropdownMenuPrimitive.Portal>
  );
}

export interface DropdownMenuItemProps extends ParentProps {
  class?: string;
  onSelect?: () => void;
}

export function DropdownMenuItem(props: DropdownMenuItemProps) {
  const [local, others] = splitProps(props, ["class"]);
  return (
    <DropdownMenuPrimitive.Item
      class={cn(
        "relative flex cursor-default select-none items-center rounded-sm px-2 py-1.5 text-sm outline-none transition-colors focus:bg-accent focus:text-accent-foreground data-[disabled]:pointer-events-none data-[disabled]:opacity-50",
        local.class
      )}
      {...others}
    />
  );
}

export interface DropdownMenuSeparatorProps {
  class?: string;
}

export function DropdownMenuSeparator(props: DropdownMenuSeparatorProps) {
  const [local, others] = splitProps(props, ["class"]);
  return <DropdownMenuPrimitive.Separator class={cn("-mx-1 my-1 h-px bg-muted", local.class)} {...others} />;
}

export interface DropdownMenuLabelProps extends ParentProps {
  class?: string;
}

export function DropdownMenuLabel(props: DropdownMenuLabelProps) {
  const [local, others] = splitProps(props, ["class"]);
  return <DropdownMenuPrimitive.GroupLabel class={cn("px-2 py-1.5 text-sm font-semibold", local.class)} {...others} />;
}
