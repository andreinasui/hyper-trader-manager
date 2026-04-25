import { type JSX, splitProps } from "solid-js";
import { cn } from "~/lib/utils";

export interface PageContentProps extends JSX.HTMLAttributes<HTMLDivElement> {
  maxWidth?: "sm" | "md" | "lg" | "xl" | "2xl" | "3xl" | "7xl" | "full";
}

const maxWidthClasses: Record<string, string> = {
  sm: "max-w-sm",
  md: "max-w-md",
  lg: "max-w-lg",
  xl: "max-w-xl",
  "2xl": "max-w-2xl",
  "3xl": "max-w-3xl",
  "7xl": "max-w-7xl",
  full: "max-w-full",
};

export function PageContent(props: PageContentProps) {
  const [local, others] = splitProps(props, ["class", "children", "maxWidth"]);
  const width = () => local.maxWidth ?? "7xl";

  return (
    <div
      class={cn("p-6", maxWidthClasses[width()], local.class)}
      {...others}
    >
      {local.children}
    </div>
  );
}
