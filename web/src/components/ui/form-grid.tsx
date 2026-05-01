import { type ParentProps } from "solid-js";
import { cn } from "~/lib/utils";

export interface FormGridProps extends ParentProps {
  /**
   * Maximum number of columns at the widest container size.
   * - `2` (default): 1 col under 480px container, 2 cols at ≥480px
   * - `3`: 1 col under 480px, 2 cols at 480-1024px, 3 cols at ≥1024px
   */
  cols?: 2 | 3;
  class?: string;
  /** Gap between grid items. Defaults to "gap-4". */
  gap?: string;
}

/**
 * Form-field grid container. Uses Tailwind v4 container queries so it adapts
 * to its parent's width, not the viewport. Drop-in replacement for
 * `<div class="grid grid-cols-2 gap-4">` in form layouts.
 *
 * Example:
 *   <FormGrid>
 *     <Field name="..." />
 *     <Field name="..." />
 *   </FormGrid>
 */
export function FormGrid(props: FormGridProps) {
  const cols = () => props.cols ?? 2;
  const gap = () => props.gap ?? "gap-4";

  return (
    <div class="@container">
      <div
        data-form-grid
        class={cn(
          "grid grid-cols-1",
          cols() === 2 && "@sm:grid-cols-2",
          cols() === 3 && "@sm:grid-cols-2 @lg:grid-cols-3",
          gap(),
          props.class
        )}
      >
        {props.children}
      </div>
    </div>
  );
}
