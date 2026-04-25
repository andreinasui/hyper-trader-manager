import { type JSX, splitProps, For } from "solid-js";
import { cn } from "~/lib/utils";

export interface Column {
  key: string;
  label: string;
  span: number;
}

export interface DataTableProps {
  columns: Column[];
  children: JSX.Element;
  class?: string;
}

const colSpanClasses: Record<number, string> = {
  1: "col-span-1",
  2: "col-span-2",
  3: "col-span-3",
  4: "col-span-4",
  5: "col-span-5",
  6: "col-span-6",
  7: "col-span-7",
  8: "col-span-8",
  9: "col-span-9",
  10: "col-span-10",
  11: "col-span-11",
  12: "col-span-12",
};

export function DataTable(props: DataTableProps) {
  return (
    <div
      class={cn(
        "bg-surface-raised border border-border-default rounded-md overflow-hidden",
        props.class
      )}
    >
      {/* Header */}
      <div class="border-b border-border-default px-4 py-3 grid grid-cols-12 gap-4">
        <For each={props.columns}>
          {(col) => (
            <div
              class={cn(
                colSpanClasses[col.span],
                "text-xs font-medium text-text-subtle uppercase tracking-wide"
              )}
            >
              {col.label}
            </div>
          )}
        </For>
      </div>
      {/* Body */}
      {props.children}
    </div>
  );
}

export interface DataTableRowProps extends JSX.HTMLAttributes<HTMLDivElement> {
  selected?: boolean;
}

export function DataTableRow(props: DataTableRowProps) {
  const [local, others] = splitProps(props, ["class", "children", "selected"]);
  return (
    <div
      class={cn(
        "border-b border-border-default last:border-b-0 px-4 py-3 grid grid-cols-12 gap-4 items-center",
        "border-l-2 border-l-transparent transition-all",
        "hover:bg-surface-raised hover:border-l-primary",
        "[&_.row-actions]:opacity-0 [&:hover_.row-actions]:opacity-100",
        local.selected && "bg-surface-raised border-l-primary",
        local.class
      )}
      {...others}
    >
      {local.children}
    </div>
  );
}
