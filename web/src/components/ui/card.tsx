import { type JSX, splitProps } from "solid-js";
import { cn } from "~/lib/utils";

export function Card(props: JSX.HTMLAttributes<HTMLDivElement>) {
  const [local, others] = splitProps(props, ["class"]);
  return (
    <div
      class={cn("rounded-xl border bg-card text-card-foreground shadow", local.class)}
      {...others}
    />
  );
}

export function CardHeader(props: JSX.HTMLAttributes<HTMLDivElement>) {
  const [local, others] = splitProps(props, ["class"]);
  return <div class={cn("flex flex-col space-y-1.5 p-6", local.class)} {...others} />;
}

export function CardTitle(props: JSX.HTMLAttributes<HTMLHeadingElement>) {
  const [local, others] = splitProps(props, ["class"]);
  return <h3 class={cn("font-semibold leading-none tracking-tight", local.class)} {...others} />;
}

export function CardDescription(props: JSX.HTMLAttributes<HTMLParagraphElement>) {
  const [local, others] = splitProps(props, ["class"]);
  return <p class={cn("text-sm text-muted-foreground", local.class)} {...others} />;
}

export function CardContent(props: JSX.HTMLAttributes<HTMLDivElement>) {
  const [local, others] = splitProps(props, ["class"]);
  return <div class={cn("p-6 pt-0", local.class)} {...others} />;
}

export function CardFooter(props: JSX.HTMLAttributes<HTMLDivElement>) {
  const [local, others] = splitProps(props, ["class"]);
  return <div class={cn("flex items-center p-6 pt-0", local.class)} {...others} />;
}
