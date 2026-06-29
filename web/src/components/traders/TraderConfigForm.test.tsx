import { fireEvent, render, screen } from "@solidjs/testing-library";
import { describe, expect, it, vi } from "vitest";
import { TraderConfigForm } from "./TraderConfigForm";

describe("TraderConfigForm", () => {
  it("only exposes order based strategy in the UI", async () => {
    render(() => <TraderConfigForm onSubmit={vi.fn()} />);

    fireEvent.click(screen.getByRole("button", { name: /advanced settings/i }));

    const strategy = screen.getByLabelText("Strategy Type") as HTMLSelectElement;
    expect([...strategy.options].map((option) => option.value)).toEqual(["order_based"]);
  });

  it("shows asset selector parsing help on allowed and blocked fields", async () => {
    render(() => <TraderConfigForm onSubmit={vi.fn()} />);

    fireEvent.click(screen.getByRole("button", { name: /advanced settings/i }));

    expect(screen.getByLabelText("Allowed Assets help")).toHaveAttribute(
      "title",
      expect.stringContaining('"*" loads all markets')
    );
    expect(screen.getByLabelText("Blocked Assets help")).toHaveAttribute(
      "title",
      expect.stringContaining("Block wins over allow")
    );
  });
});
