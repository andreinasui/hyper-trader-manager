import { AlertDialog as AlertDialogPrimitive } from "@kobalte/core/alert-dialog";
import { type JSX, type ParentProps, splitProps } from "solid-js";
import { cn } from "~/lib/utils";
import { buttonVariants } from "./button";

export const AlertDialog = AlertDialogPrimitive;
export const AlertDialogTrigger = AlertDialogPrimitive.Trigger;
export const AlertDialogPortal = AlertDialogPrimitive.Portal;

export interface AlertDialogOverlayProps {
  class?: string;
}

export function AlertDialogOverlay(props: AlertDialogOverlayProps) {
  const [local, others] = splitProps(props, ["class"]);
  return (
    <AlertDialogPrimitive.Overlay
      class={cn(
        "fixed inset-0 z-50 bg-black/80 data-[expanded]:animate-in data-[closed]:animate-out data-[closed]:fade-out-0 data-[expanded]:fade-in-0",
        local.class
      )}
      {...others}
    />
  );
}

export interface AlertDialogContentProps extends ParentProps {
  class?: string;
}

export function AlertDialogContent(props: AlertDialogContentProps) {
  const [local, others] = splitProps(props, ["class", "children"]);
  return (
    <AlertDialogPortal>
      <AlertDialogOverlay />
      <AlertDialogPrimitive.Content
        class={cn(
          "fixed left-1/2 top-1/2 z-50 grid w-full max-w-lg -translate-x-1/2 -translate-y-1/2 gap-4 border bg-background p-6 shadow-lg duration-200 data-[expanded]:animate-in data-[closed]:animate-out data-[closed]:fade-out-0 data-[expanded]:fade-in-0 data-[closed]:zoom-out-95 data-[expanded]:zoom-in-95 sm:rounded-lg",
          local.class
        )}
        {...others}
      >
        {local.children}
      </AlertDialogPrimitive.Content>
    </AlertDialogPortal>
  );
}

export function AlertDialogHeader(props: JSX.HTMLAttributes<HTMLDivElement>) {
  const [local, others] = splitProps(props, ["class"]);
  return <div class={cn("flex flex-col space-y-2 text-center sm:text-left", local.class)} {...others} />;
}

export function AlertDialogFooter(props: JSX.HTMLAttributes<HTMLDivElement>) {
  const [local, others] = splitProps(props, ["class"]);
  return <div class={cn("flex flex-col-reverse sm:flex-row sm:justify-end sm:space-x-2", local.class)} {...others} />;
}

export interface AlertDialogTitleProps extends ParentProps {
  class?: string;
}

export function AlertDialogTitle(props: AlertDialogTitleProps) {
  const [local, others] = splitProps(props, ["class"]);
  return <AlertDialogPrimitive.Title class={cn("text-lg font-semibold", local.class)} {...others} />;
}

export interface AlertDialogDescriptionProps extends ParentProps {
  class?: string;
}

export function AlertDialogDescription(props: AlertDialogDescriptionProps) {
  const [local, others] = splitProps(props, ["class"]);
  return <AlertDialogPrimitive.Description class={cn("text-sm text-muted-foreground", local.class)} {...others} />;
}

export interface AlertDialogActionProps extends ParentProps {
  class?: string;
  onClick?: () => void;
}

export function AlertDialogAction(props: AlertDialogActionProps) {
  const [local, others] = splitProps(props, ["class"]);
  return <AlertDialogPrimitive.CloseButton class={cn(buttonVariants(), local.class)} {...others} />;
}

export interface AlertDialogCancelProps extends ParentProps {
  class?: string;
  onClick?: () => void;
}

export function AlertDialogCancel(props: AlertDialogCancelProps) {
  const [local, others] = splitProps(props, ["class"]);
  return <AlertDialogPrimitive.CloseButton class={cn(buttonVariants({ variant: "outline" }), "mt-2 sm:mt-0", local.class)} {...others} />;
}
