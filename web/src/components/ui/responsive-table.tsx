import { For, Show, type JSX } from "solid-js";
import { cn } from "~/lib/utils";

export interface ResponsiveTableColumn<T> {
  key: string;
  label: string;
  /** Grid span in the 12-col desktop layout (must sum to 12 across visible cols). */
  span: number;
  /** Identifies the column shown as the title in the phone card layout. */
  primary?: boolean;
  /** Hide this column entirely on phone (card layout). */
  hideOnPhone?: boolean;
  /** Right-align cell content (typical for "Actions"). */
  align?: "start" | "end";
  /** Cell renderer. Header label is shown above on phone unless primary. */
  render: (row: T) => JSX.Element;
}

export interface ResponsiveTableProps<T> {
  data: T[];
  columns: ResponsiveTableColumn<T>[];
  rowKey: (row: T) => string;
  /** Optional row-level extra slot (e.g. error banner) rendered below each row in both layouts. */
  rowExtra?: (row: T) => JSX.Element;
  /** Optional className passed to row wrapper for styling per-row state (e.g. status border). */
  rowClass?: (row: T) => string | undefined;
  emptyState?: JSX.Element;
  class?: string;
}

/**
 * 12-col grid table on tablet+, stacked cards on phone.
 *
 * Layout decision lives entirely inside this component. Pages do not
 * duplicate JSX or branch on viewport. Each row's desktop and phone
 * markup is rendered into the DOM; CSS (container queries) toggles which
 * one is visible.
 */
export function ResponsiveTable<T>(props: ResponsiveTableProps<T>) {
  const phoneVisibleCols = () => props.columns.filter((c) => !c.hideOnPhone);

  return (
    <Show
      when={props.data.length > 0}
      fallback={props.emptyState}
    >
      <div class={cn("@container", props.class)}>
        <div class="bg-surface-raised border border-border-default rounded-md overflow-hidden">
          {/* Desktop header — hidden on phone container */}
          <div
            data-rt-header
            class="hidden @md:grid border-b border-border-default px-4 py-2 grid-cols-12 gap-3"
          >
            <For each={props.columns}>
              {(col) => (
                <div
                  class={cn(
                    "text-[10px] font-medium text-text-subtle uppercase tracking-widest",
                    col.align === "end" && "text-right",
                    spanClass(col.span)
                  )}
                >
                  {col.label}
                </div>
              )}
            </For>
          </div>

          <For each={props.data}>
            {(row) => (
              <div
                data-rt-row
                data-rt-row-key={props.rowKey(row)}
                class={cn("border-b border-border-default last:border-b-0", props.rowClass?.(row))}
              >
                {/* Desktop layout */}
                <div
                  data-rt-row-desktop
                  class="hidden @md:grid px-4 py-2.5 grid-cols-12 gap-3 items-center"
                >
                  <For each={props.columns}>
                    {(col) => (
                      <div class={cn(spanClass(col.span), col.align === "end" && "flex justify-end")}>
                        {col.render(row)}
                      </div>
                    )}
                  </For>
                </div>

                {/* Phone layout */}
                <div data-rt-row-phone class="@md:hidden p-4 space-y-2">
                  <For each={phoneVisibleCols()}>
                    {(col) => (
                      <Show
                        when={col.primary}
                        fallback={
                          <div class="flex items-baseline justify-between gap-3">
                            <span class="text-[10px] font-medium text-text-subtle uppercase tracking-widest">
                              {col.label}
                            </span>
                            <div class={cn("text-sm", col.align === "end" && "text-right")}>
                              {col.render(row)}
                            </div>
                          </div>
                        }
                      >
                        <div class="text-sm font-medium text-text-base">
                          {col.render(row)}
                        </div>
                      </Show>
                    )}
                  </For>
                </div>

                <Show when={props.rowExtra}>{props.rowExtra!(row)}</Show>
              </div>
            )}
          </For>
        </div>
      </div>
    </Show>
  );
}

// Helper: map numeric span to a static Tailwind class string so JIT picks it up.
function spanClass(span: number): string {
  switch (span) {
    case 1:  return "col-span-1";
    case 2:  return "col-span-2";
    case 3:  return "col-span-3";
    case 4:  return "col-span-4";
    case 5:  return "col-span-5";
    case 6:  return "col-span-6";
    case 7:  return "col-span-7";
    case 8:  return "col-span-8";
    case 9:  return "col-span-9";
    case 10: return "col-span-10";
    case 11: return "col-span-11";
    case 12: return "col-span-12";
    default: return "col-span-1";
  }
}
