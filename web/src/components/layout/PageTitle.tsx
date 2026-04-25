import { type JSX, Show } from "solid-js";
import { A } from "@solidjs/router";
import { ChevronLeft } from "lucide-solid";
import { cn } from "~/lib/utils";

export interface PageTitleProps {
  title: string;
  subtitle?: string;
  action?: JSX.Element;
  backLink?: { label: string; href: string };
  class?: string;
}

export function PageTitle(props: PageTitleProps) {
  return (
    <div class={cn("flex items-start justify-between mb-6", props.class)}>
      <div>
        <Show when={props.backLink}>
          <A
            href={props.backLink!.href}
            class="inline-flex items-center gap-1 text-xs text-text-faint hover:text-text-muted transition-colors mb-3 group"
          >
            <ChevronLeft class="w-3.5 h-3.5 transition-transform group-hover:-translate-x-0.5" />
            {props.backLink!.label}
          </A>
        </Show>
        <h1 class="text-2xl font-semibold tracking-tight text-text-base">
          {props.title}
        </h1>
        <Show when={props.subtitle}>
          <p class="text-sm text-text-subtle mt-1">{props.subtitle}</p>
        </Show>
      </div>
      <Show when={props.action}>{props.action}</Show>
    </div>
  );
}
