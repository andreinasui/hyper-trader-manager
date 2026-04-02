import { type JSX, splitProps } from "solid-js";
import { cn } from "~/lib/utils";

export function Table(props: JSX.HTMLAttributes<HTMLTableElement>) {
  const [local, others] = splitProps(props, ["class"]);
  return (
    <div class="relative w-full overflow-auto">
      <table class={cn("w-full caption-bottom text-sm", local.class)} {...others} />
    </div>
  );
}

export function TableHeader(props: JSX.HTMLAttributes<HTMLTableSectionElement>) {
  const [local, others] = splitProps(props, ["class"]);
  return <thead class={cn("[&_tr]:border-b", local.class)} {...others} />;
}

export function TableBody(props: JSX.HTMLAttributes<HTMLTableSectionElement>) {
  const [local, others] = splitProps(props, ["class"]);
  return <tbody class={cn("[&_tr:last-child]:border-0", local.class)} {...others} />;
}

export function TableFooter(props: JSX.HTMLAttributes<HTMLTableSectionElement>) {
  const [local, others] = splitProps(props, ["class"]);
  return <tfoot class={cn("border-t bg-muted/50 font-medium [&>tr]:last:border-b-0", local.class)} {...others} />;
}

export function TableRow(props: JSX.HTMLAttributes<HTMLTableRowElement>) {
  const [local, others] = splitProps(props, ["class"]);
  return (
    <tr
      class={cn("border-b transition-colors hover:bg-muted/50 data-[state=selected]:bg-muted", local.class)}
      {...others}
    />
  );
}

export function TableHead(props: JSX.ThHTMLAttributes<HTMLTableCellElement>) {
  const [local, others] = splitProps(props, ["class"]);
  return (
    <th
      class={cn(
        "h-10 px-2 text-left align-middle font-medium text-muted-foreground [&:has([role=checkbox])]:pr-0 [&>[role=checkbox]]:translate-y-[2px]",
        local.class
      )}
      {...others}
    />
  );
}

export function TableCell(props: JSX.TdHTMLAttributes<HTMLTableCellElement>) {
  const [local, others] = splitProps(props, ["class"]);
  return (
    <td
      class={cn("p-2 align-middle [&:has([role=checkbox])]:pr-0 [&>[role=checkbox]]:translate-y-[2px]", local.class)}
      {...others}
    />
  );
}

export function TableCaption(props: JSX.HTMLAttributes<HTMLTableCaptionElement>) {
  const [local, others] = splitProps(props, ["class"]);
  return <caption class={cn("mt-4 text-sm text-muted-foreground", local.class)} {...others} />;
}
