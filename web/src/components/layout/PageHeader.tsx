import { type Component, For, Show } from "solid-js";
import { A } from "@solidjs/router";
import { cn } from "~/lib/utils";

export interface Breadcrumb {
  label: string;
  href?: string;
}

export interface PageHeaderProps {
  breadcrumbs: Breadcrumb[];
  class?: string;
}

export const PageHeader: Component<PageHeaderProps> = (props) => {
  return (
    <div
      class={cn(
        "sticky top-0 z-20 h-14 border-b border-border-default bg-surface-base flex items-center px-6",
        props.class
      )}
    >
      <div class="flex items-center gap-2 text-sm">
        <For each={props.breadcrumbs}>
          {(crumb, index) => (
            <>
              <Show when={index() > 0}>
                <span class="text-text-faint">/</span>
              </Show>
              <Show
                when={crumb.href}
                fallback={
                  <span class="text-text-tertiary font-medium">
                    {crumb.label}
                  </span>
                }
              >
                <A
                  href={crumb.href!}
                  class="text-text-subtle hover:text-text-tertiary transition-colors"
                >
                  {crumb.label}
                </A>
              </Show>
            </>
          )}
        </For>
      </div>
    </div>
  );
};
