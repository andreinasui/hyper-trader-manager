import { type Component, type JSX, Show, createEffect, onCleanup } from "solid-js";
import { Portal } from "solid-js/web";
import { cn } from "~/lib/utils";

export interface ToastProps {
  message: string;
  show: boolean;
  duration?: number;
  onClose: () => void;
  variant?: "default" | "success" | "error";
}

export const Toast: Component<ToastProps> = (props) => {
  let timeoutId: NodeJS.Timeout | undefined;

  createEffect(() => {
    if (props.show && props.duration) {
      timeoutId = setTimeout(() => {
        props.onClose();
      }, props.duration);
    }
  });

  onCleanup(() => {
    if (timeoutId) clearTimeout(timeoutId);
  });

  const variantStyles = () => {
    switch (props.variant) {
      case "success":
        return "bg-green-600 text-white";
      case "error":
        return "bg-destructive text-destructive-foreground";
      default:
        return "bg-primary text-primary-foreground";
    }
  };

  return (
    <Portal>
      <Show when={props.show}>
        <div class="fixed top-4 left-1/2 -translate-x-1/2 z-50 animate-in fade-in slide-in-from-top-2">
          <div
            class={cn(
              "rounded-md px-4 py-3 shadow-lg transition-all",
              variantStyles()
            )}
          >
            <p class="text-sm font-medium">{props.message}</p>
          </div>
        </div>
      </Show>
    </Portal>
  );
};
