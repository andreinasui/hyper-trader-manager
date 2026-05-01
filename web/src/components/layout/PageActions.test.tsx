import { render, fireEvent } from "@solidjs/testing-library";
import { describe, expect, it, vi } from "vitest";
import { Play, Trash2 } from "lucide-solid";
import { PageActions } from "./PageActions";

describe("PageActions", () => {
  it("renders all actions inline by default", () => {
    const { getByText } = render(() => (
      <PageActions
        actions={[
          { label: "Start", icon: Play, onClick: () => {}, priority: "primary" },
          { label: "Delete", icon: Trash2, onClick: () => {}, priority: "secondary" },
        ]}
      />
    ));
    expect(getByText("Start")).toBeTruthy();
    expect(getByText("Delete")).toBeTruthy();
  });

  it("renders primary actions inline and secondary actions inside the overflow menu trigger group", () => {
    const { container } = render(() => (
      <PageActions
        actions={[
          { label: "Start", icon: Play, onClick: () => {}, priority: "primary" },
          { label: "Delete", icon: Trash2, onClick: () => {}, priority: "secondary" },
        ]}
      />
    ));
    const inline = container.querySelector("[data-page-actions-inline]") as HTMLElement;
    const overflow = container.querySelector("[data-page-actions-overflow]") as HTMLElement;
    expect(inline.textContent).toContain("Start");
    expect(inline.textContent).not.toContain("Delete");
    expect(overflow).toBeTruthy();
  });

  it("invokes onClick when an inline action is clicked", () => {
    const onClick = vi.fn();
    const { getByText } = render(() => (
      <PageActions
        actions={[
          { label: "Start", icon: Play, onClick, priority: "primary" },
        ]}
      />
    ));
    fireEvent.click(getByText("Start"));
    expect(onClick).toHaveBeenCalledOnce();
  });

  it("omits the overflow trigger entirely when no secondary actions exist", () => {
    const { container } = render(() => (
      <PageActions
        actions={[
          { label: "Start", icon: Play, onClick: () => {}, priority: "primary" },
        ]}
      />
    ));
    const overflow = container.querySelector("[data-page-actions-overflow]");
    expect(overflow).toBeNull();
  });

  it("applies destructive button variant to inline danger primary action", () => {
    const { getByText } = render(() => (
      <PageActions
        actions={[
          { label: "Delete", icon: Trash2, onClick: () => {}, priority: "primary", variant: "danger" },
        ]}
      />
    ));
    const btn = getByText("Delete").closest("button") as HTMLButtonElement;
    // Button's `variant: "destructive"` cva entry yields bg-error / hover:bg-error utilities.
    expect(btn.className).toContain("bg-error");
  });

  it("applies text-destructive to a danger secondary action's inline (wide-container) button", () => {
    // On wide containers the secondary action renders as an inline destructive button
    // (same cva variant as a danger primary). The overflow menu item also gets the
    // text-destructive class but Kobalte only mounts that subtree when opened, which
    // jsdom can't reliably trigger via synthetic events. Assert the inline path here;
    // the overflow-item styling is exercised by Playwright in Phase 4.
    const { container } = render(() => (
      <PageActions
        actions={[
          { label: "Start", icon: Play, onClick: () => {}, priority: "primary" },
          { label: "Delete", icon: Trash2, onClick: () => {}, priority: "secondary", variant: "danger" },
        ]}
      />
    ));
    const inlineSecondary = container.querySelector(
      "[data-page-actions-secondary-inline]"
    ) as HTMLElement;
    expect(inlineSecondary).toBeTruthy();
    const deleteBtn = Array.from(inlineSecondary.querySelectorAll("button")).find(
      (b) => b.textContent?.includes("Delete")
    ) as HTMLButtonElement | undefined;
    expect(deleteBtn).toBeTruthy();
    expect(deleteBtn!.className).toContain("bg-error");
  });
});
