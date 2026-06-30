import { fireEvent, render, screen, waitFor } from "@solidjs/testing-library";
import { describe, expect, it, vi } from "vitest";
import { TraderConfigForm } from "./TraderConfigForm";
import type { CreateTraderForm } from "~/lib/schemas/trader-config";

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

  it("shows existing edit config instead of defaults", async () => {
    const initialValues: Partial<CreateTraderForm> = {
      wallet_address: "0x1111111111111111111111111111111111111111",
      private_key: "",
      config: {
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
    };

    render(() => <TraderConfigForm onSubmit={vi.fn()} initialValues={initialValues} isEditing />);

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
    render(() => <TraderConfigForm onSubmit={onSubmit} />);

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
});
