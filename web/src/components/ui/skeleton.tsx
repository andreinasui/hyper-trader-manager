import { type JSX, splitProps } from "solid-js";
import { cn } from "~/lib/utils";

export function Skeleton(props: JSX.HTMLAttributes<HTMLDivElement>) {
  const [local, others] = splitProps(props, ["class"]);
  return <div class={cn("animate-pulse rounded-md bg-primary/10", local.class)} {...others} />;
}
