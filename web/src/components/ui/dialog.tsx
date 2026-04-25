import { Dialog as DialogPrimitive } from "@kobalte/core/dialog";
import { type JSX, type ParentProps, splitProps } from "solid-js";
import { cn } from "~/lib/utils";

export const Dialog = DialogPrimitive;
export const DialogTrigger = DialogPrimitive.Trigger;
export const DialogClose = DialogPrimitive.CloseButton;
export const DialogPortal = DialogPrimitive.Portal;

export interface DialogOverlayProps {
  class?: string;
}

export function DialogOverlay(props: DialogOverlayProps) {
  const [local, others] = splitProps(props, ["class"]);
  return (
    <DialogPrimitive.Overlay
      class={cn(
        "fixed inset-0 z-50 bg-black/80 data-[expanded]:animate-in data-[closed]:animate-out data-[closed]:fade-out-0 data-[expanded]:fade-in-0",
        local.class
      )}
      {...others}
    />
  );
}

export interface DialogContentProps extends ParentProps {
  class?: string;
}

export function DialogContent(props: DialogContentProps) {
  const [local, others] = splitProps(props, ["class", "children"]);
  return (
    <DialogPortal>
      <DialogOverlay />
      <DialogPrimitive.Content
        class={cn(
          "fixed left-1/2 top-1/2 z-50 grid w-full max-w-lg -translate-x-1/2 -translate-y-1/2 gap-4 border bg-background p-6 shadow-lg duration-200 data-[expanded]:animate-in data-[closed]:animate-out data-[closed]:fade-out-0 data-[expanded]:fade-in-0 data-[closed]:zoom-out-95 data-[expanded]:zoom-in-95 data-[closed]:slide-out-to-left-1/2 data-[closed]:slide-out-to-top-[48%] data-[expanded]:slide-in-from-left-1/2 data-[expanded]:slide-in-from-top-[48%] sm:rounded-lg",
          local.class
        )}
        {...others}
      >
        {local.children}
      </DialogPrimitive.Content>
    </DialogPortal>
  );
}

export function DialogHeader(props: JSX.HTMLAttributes<HTMLDivElement>) {
  const [local, others] = splitProps(props, ["class"]);
  return <div class={cn("flex flex-col space-y-1.5 text-center sm:text-left", local.class)} {...others} />;
}

export function DialogFooter(props: JSX.HTMLAttributes<HTMLDivElement>) {
  const [local, others] = splitProps(props, ["class"]);
  return <div class={cn("flex flex-col-reverse sm:flex-row sm:justify-end sm:space-x-2", local.class)} {...others} />;
}

export interface DialogTitleProps extends ParentProps {
  class?: string;
}

export function DialogTitle(props: DialogTitleProps) {
  const [local, others] = splitProps(props, ["class"]);
  return <DialogPrimitive.Title class={cn("text-lg font-semibold leading-none tracking-tight", local.class)} {...others} />;
}

export interface DialogDescriptionProps extends ParentProps {
  class?: string;
}

export function DialogDescription(props: DialogDescriptionProps) {
  const [local, others] = splitProps(props, ["class"]);
  return <DialogPrimitive.Description class={cn("text-sm text-muted-foreground", local.class)} {...others} />;
}
