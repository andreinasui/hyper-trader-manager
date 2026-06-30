import { fireEvent, render, screen, waitFor } from "@solidjs/testing-library";
import { describe, expect, it, vi } from "vitest";
import { TraderForm } from "./TraderConfigForm";
import { buildInitialTraderForm } from "./trader-form-model";
import type { Trader } from "~/lib/types";

const trader: Trader = {
  id: "trader-1",
  user_id: "user-1",
  wallet_address: "0x1111111111111111111111111111111111111111",
  runtime_name: "runtime",
  status: "configured",
  image_tag: "1.0.0",
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-02T00:00:00Z",
  latest_config: {
    provider_settings: {
      exchange: "hyperliquid",
      network: "testnet",
      self_account: {
        address: "0x1111111111111111111111111111111111111111",
        is_sub: true,
      },
      copy_account: {
        address: "0x2222222222222222222222222222222222222222",
      },
      slippage_bps: 42,
      risk_parameters: {
        allowed_assets: ["BTC"],
        blocked_assets: ["ETH"],
        max_leverage: 10,
      },
    },
    trader_settings: {
      trading_strategy: {
        type: "order_based",
        risk_parameters: {
          self_proportionality_multiplier: 2,
          open_on_low_pnl: { enabled: true, max_pnl: 0.07 },
        },
        bucket_config: {
          type: "manual",
          width_percent: 0.03,
          pricing_strategy: "aggressive",
        },
      },
    },
  },
  start_attempts: 0,
  last_error: null,
  stopped_at: null,
  name: "Alpha",
  description: "Copies BTC",
  display_name: "Alpha",
};

describe("TraderConfigForm", () => {
  it("shows order based strategy as static text", async () => {
    render(() => <TraderForm mode="create" onSubmit={vi.fn()} />);

    fireEvent.click(screen.getByRole("button", { name: /advanced settings/i }));

    expect(screen.getByText("Order Based")).toBeInTheDocument();
    expect(screen.queryByLabelText("Strategy Type")).not.toBeInTheDocument();
  });

  it("shows credentials only in create mode", () => {
    const onSubmit = vi.fn();
    const { unmount } = render(() => <TraderForm mode="create" onSubmit={onSubmit} />);

    expect(screen.getByLabelText("Wallet Address")).toBeInTheDocument();
    expect(screen.getByLabelText("Private Key")).toBeInTheDocument();

    unmount();

    render(() => <TraderForm mode="edit" onSubmit={onSubmit} initialValues={buildInitialTraderForm("edit", trader)} />);

    expect(screen.getByLabelText("Name")).toBeInTheDocument();
    expect(screen.queryByLabelText("Private Key")).not.toBeInTheDocument();
  });

  it("shows asset selector parsing help on allowed and blocked fields", async () => {
    render(() => <TraderForm mode="create" onSubmit={vi.fn()} />);

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

  it("shows existing edit config instead of defaults", async () => {
    render(() => <TraderForm mode="edit" onSubmit={vi.fn()} initialValues={buildInitialTraderForm("edit", trader)} />);

    expect(screen.getByLabelText("Network")).toHaveValue("testnet");
    expect(screen.getByLabelText("Copy Account Address")).toHaveValue("0x2222222222222222222222222222222222222222");
    expect(screen.getByRole("switch", { name: /is subaccount/i })).toHaveAttribute("aria-checked", "true");

    fireEvent.click(screen.getByRole("button", { name: /advanced settings/i }));

    expect(screen.getByText("BTC")).toBeInTheDocument();
    expect(screen.getByText("ETH")).toBeInTheDocument();
    expect(screen.getByLabelText("Slippage (%)")).toHaveValue(0.42);
    expect(screen.getByLabelText("Size Multiplier")).toHaveValue(2);
    expect(screen.getByLabelText("Max PnL Threshold (%)")).toHaveValue(7);
    expect(screen.getByRole("button", { name: "Manual" })).toHaveClass("bg-surface-overlay");
    expect(screen.getByLabelText("Pricing Strategy")).toHaveValue("aggressive");
  });

  it("shows slippage as percent and submits bps", async () => {
    const onSubmit = vi.fn();
    render(() => <TraderForm mode="create" onSubmit={onSubmit} />);

    fireEvent.click(screen.getByRole("button", { name: /advanced settings/i }));

    const slippage = screen.getByLabelText("Slippage (%)");
    expect(slippage).toHaveValue(2);

    fireEvent.input(slippage, { target: { value: "1.5" } });
    fireEvent.input(screen.getByLabelText("Wallet Address"), { target: { value: "0x1111111111111111111111111111111111111111" } });
    fireEvent.input(screen.getByLabelText("Private Key"), { target: { value: "0x1111111111111111111111111111111111111111111111111111111111111111" } });
    fireEvent.input(screen.getByLabelText("Copy Account Address"), { target: { value: "0x2222222222222222222222222222222222222222" } });
    fireEvent.click(screen.getByRole("button", { name: "Create Trader" }));

    await waitFor(() => {
      expect(onSubmit).toHaveBeenCalledWith(
        expect.objectContaining({
          config: expect.objectContaining({
            provider_settings: expect.objectContaining({ slippage_bps: 150 }),
          }),
        })
      );
    });
  });

  it("submits null max leverage after disabled field unmounts", async () => {
    const onSubmit = vi.fn();
    const { container } = render(() => (
      <TraderForm
        mode="edit"
        onSubmit={onSubmit}
        initialValues={buildInitialTraderForm("edit", trader)}
        submitLabel="Save Trader"
      />
    ));

    fireEvent.click(screen.getByRole("button", { name: /advanced settings/i }));
    fireEvent.click(screen.getByRole("switch", { name: /set max leverage/i }));
    await waitFor(() => expect(container.querySelector("#max_leverage")).not.toBeInTheDocument());
    await new Promise((resolve) => setTimeout(resolve, 0));
    fireEvent.click(screen.getByRole("button", { name: "Save Trader" }));

    await waitFor(() => {
      expect(onSubmit).toHaveBeenCalledWith(
        expect.objectContaining({
          config: expect.objectContaining({
            provider_settings: expect.objectContaining({
              risk_parameters: expect.objectContaining({ max_leverage: null }),
            }),
          }),
        })
      );
    });
  });
});
