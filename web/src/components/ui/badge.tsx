import { type JSX, splitProps } from "solid-js";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "~/lib/utils";

const badgeVariants = cva(
  "inline-flex items-center rounded-md border px-2.5 py-0.5 text-xs font-semibold transition-colors focus:outline-none focus:ring-2 focus:ring-border-ring focus:ring-offset-2",
  {
    variants: {
      variant: {
        default: "border-transparent bg-primary text-white shadow hover:bg-primary-hover",
        secondary: "border-transparent bg-surface-overlay text-text-secondary hover:bg-surface-subtle",
        destructive: "border-transparent bg-error text-white shadow hover:bg-error/80",
        outline: "border-border-default text-text-secondary",
        success: "border-transparent bg-success/20 text-success",
        warning: "border-transparent bg-warning/20 text-warning",
      },
    },
    defaultVariants: {
      variant: "default",
    },
  }
);

export interface BadgeProps
  extends JSX.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof badgeVariants> {}

export function Badge(props: BadgeProps) {
  const [local, others] = splitProps(props, ["class", "variant"]);
  return <div class={cn(badgeVariants({ variant: local.variant }), local.class)} {...others} />;
}
