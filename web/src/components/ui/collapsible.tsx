import {
  type ParentComponent,
  type JSX,
  createSignal,
  Show,
  splitProps,
} from "solid-js";
import { ChevronDown, ChevronRight } from "lucide-solid";
import { cn } from "~/lib/utils";

export interface CollapsibleProps {
  title: string;
  defaultOpen?: boolean;
  class?: string;
  children: JSX.Element;
}

export const Collapsible: ParentComponent<CollapsibleProps> = (props) => {
  const [local, others] = splitProps(props, [
    "title",
    "defaultOpen",
    "class",
    "children",
  ]);
  const [isOpen, setIsOpen] = createSignal(local.defaultOpen ?? false);

  return (
    <div class={cn("border rounded-lg", local.class)} {...others}>
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen())}
        class="flex items-center justify-between w-full p-4 text-left font-medium hover:bg-muted/50 transition-colors"
      >
        <span>{local.title}</span>
        <Show
          when={isOpen()}
          fallback={<ChevronRight class="h-4 w-4" />}
        >
          <ChevronDown class="h-4 w-4" />
        </Show>
      </button>
      <Show when={isOpen()}>
        <div class="p-4 pt-0 border-t">{local.children}</div>
      </Show>
    </div>
  );
};
