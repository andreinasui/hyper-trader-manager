import { type JSX, splitProps } from "solid-js";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "~/lib/utils";

const alertVariants = cva(
  "relative w-full rounded-lg border px-4 py-3 text-sm [&>svg+div]:translate-y-[-3px] [&>svg]:absolute [&>svg]:left-4 [&>svg]:top-4 [&>svg]:text-foreground [&>svg~*]:pl-7",
  {
    variants: {
      variant: {
        default: "bg-background text-foreground",
        destructive: "border-destructive/50 text-destructive dark:border-destructive [&>svg]:text-destructive",
      },
    },
    defaultVariants: {
      variant: "default",
    },
  }
);

export interface AlertProps
  extends JSX.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof alertVariants> {}

export function Alert(props: AlertProps) {
  const [local, others] = splitProps(props, ["class", "variant"]);
  return (
    <div
      role="alert"
      class={cn(alertVariants({ variant: local.variant }), local.class)}
      {...others}
    />
  );
}

export function AlertTitle(props: JSX.HTMLAttributes<HTMLHeadingElement>) {
  const [local, others] = splitProps(props, ["class"]);
  return <h5 class={cn("mb-1 font-medium leading-none tracking-tight", local.class)} {...others} />;
}

export function AlertDescription(props: JSX.HTMLAttributes<HTMLParagraphElement>) {
  const [local, others] = splitProps(props, ["class"]);
  return <div class={cn("text-sm [&_p]:leading-relaxed", local.class)} {...others} />;
}
