import { Tabs as TabsPrimitive } from "@kobalte/core/tabs";
import { splitProps } from "solid-js";
import { cn } from "~/lib/utils";

export const Tabs = TabsPrimitive;

export function TabsList(props: TabsPrimitive.ListProps) {
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

export function TabsTrigger(props: TabsPrimitive.TriggerProps) {
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

export function TabsContent(props: TabsPrimitive.ContentProps) {
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
