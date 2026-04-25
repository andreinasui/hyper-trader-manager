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
        "flex w-full border-b border-border-default",
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
        "relative px-4 py-2.5 text-sm font-medium text-text-subtle hover:text-text-secondary",
        "border-b-2 border-transparent -mb-px transition-colors duration-150 cursor-pointer",
        "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2",
        "disabled:pointer-events-none disabled:opacity-40",
        "data-[selected]:text-text-base data-[selected]:border-primary",
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
        "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2",
        local.class
      )}
      {...others}
    />
  );
}
