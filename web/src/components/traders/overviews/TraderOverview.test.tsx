import { render, screen } from "@solidjs/testing-library";
import type { UseQueryResult } from "@tanstack/solid-query";
import { describe, expect, it } from "vitest";
import type { Trader, TraderStatusResponse } from "~/lib/types";
import TraderOverview from "./TraderOverview";

const trader: Trader = {
  id: "trader-1",
  user_id: "user-1",
  wallet_address: "0x1111111111111111111111111111111111111111",
  runtime_name: "runtime",
  status: "configured",
  image_tag: "1.0.0",
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-02T00:00:00Z",
  latest_config: null,
  start_attempts: 0,
  last_error: null,
  stopped_at: null,
  name: "Alpha",
  description: "Copies BTC",
  display_name: "Alpha",
};

describe("TraderOverview", () => {
  it("does not render metadata edit fields", () => {
    render(() => (
      <TraderOverview
        trader={trader}
        currentStatus={() => trader.status}
        statusQuery={{} as UseQueryResult<TraderStatusResponse, Error>}
        needsImageUpdate={() => false}
        imageQuery={{}}
        formatUptime={() => "1m"}
      />
    ));

    expect(screen.queryByLabelText("Name")).not.toBeInTheDocument();
    expect(screen.queryByLabelText("Description")).not.toBeInTheDocument();
  });
});
