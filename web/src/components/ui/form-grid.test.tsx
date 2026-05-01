import { render } from "@solidjs/testing-library";
import { describe, expect, it } from "vitest";
import { FormGrid } from "./form-grid";

describe("FormGrid", () => {
  it("renders children inside an @container element", () => {
    const { container } = render(() => (
      <FormGrid>
        <div>field-a</div>
        <div>field-b</div>
      </FormGrid>
    ));
    const root = container.firstElementChild as HTMLElement;
    expect(root.className).toContain("@container");
    expect(root.textContent).toBe("field-afield-b");
  });

  it("applies cols=2 container-query classes by default", () => {
    const { container } = render(() => (
      <FormGrid>
        <div>a</div>
      </FormGrid>
    ));
    const grid = container.querySelector("[data-form-grid]") as HTMLElement;
    expect(grid.className).toContain("grid-cols-1");
    expect(grid.className).toContain("@sm:grid-cols-2");
  });

  it("applies cols=3 container-query classes when cols=3", () => {
    const { container } = render(() => (
      <FormGrid cols={3}>
        <div>a</div>
      </FormGrid>
    ));
    const grid = container.querySelector("[data-form-grid]") as HTMLElement;
    expect(grid.className).toContain("@sm:grid-cols-2");
    expect(grid.className).toContain("@lg:grid-cols-3");
  });

  it("merges user class onto the grid element", () => {
    const { container } = render(() => (
      <FormGrid class="custom-class">
        <div>a</div>
      </FormGrid>
    ));
    const grid = container.querySelector("[data-form-grid]") as HTMLElement;
    expect(grid.className).toContain("custom-class");
  });
});
