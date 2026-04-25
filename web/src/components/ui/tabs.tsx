import { Tabs as TabsPrimitive } from "@kobalte/core/tabs";
import { type ParentProps, splitProps } from "solid-js";
import { cn } from "~/lib/utils";

export const Tabs = TabsPrimitive;

export interface TabsListProps extends ParentProps {
  class?: string;
}

export function TabsList(props: TabsListProps) {
  const [local, others] = splitProps(props, ["class"]);
  return (
    <TabsPrimitive.List
      class={cn(
        "inline-flex h-9 items-center justify-center rounded-lg bg-muted p-1 text-muted-foreground",
        local.class
      )}
      {...others}
    />
  );
}

export interface TabsTriggerProps extends ParentProps {
  class?: string;
  value: string;
}

export function TabsTrigger(props: TabsTriggerProps) {
  const [local, others] = splitProps(props, ["class"]);
  return (
    <TabsPrimitive.Trigger
      class={cn(
        "inline-flex items-center justify-center whitespace-nowrap rounded-md px-3 py-1 text-sm font-medium ring-offset-background transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 data-[selected]:bg-background data-[selected]:text-foreground data-[selected]:shadow",
        local.class
      )}
      {...others}
    />
  );
}

export interface TabsContentProps extends ParentProps {
  class?: string;
  value: string;
}

export function TabsContent(props: TabsContentProps) {
  const [local, others] = splitProps(props, ["class"]);
  return (
    <TabsPrimitive.Content
      class={cn(
        "mt-2 ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2",
        local.class
      )}
      {...others}
    />
  );
}
