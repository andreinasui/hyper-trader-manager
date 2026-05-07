import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@solidjs/testing-library";
import { QueryClient, QueryClientProvider } from "@tanstack/solid-query";
import type { JSX } from "solid-js";
import { LogArchives } from "./LogArchives";

vi.mock("~/lib/api", () => ({
  api: {
    listTraderArchives: vi.fn().mockResolvedValue([
      {
        id: "archive-abc123",
        trader_id: "trader-1",
        run_started_at: "2026-01-01T10:00:00Z",
        run_ended_at: "2026-01-01T12:00:00Z",
        file_size_bytes: 12345,
        created_at: "2026-01-01T12:00:01Z",
      },
    ]),
    downloadTraderArchive: vi.fn().mockResolvedValue(undefined),
  },
}));

function renderWithQuery(ui: () => JSX.Element) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(() => (
    <QueryClientProvider client={queryClient}>{ui()}</QueryClientProvider>
  ));
}

describe("LogArchives", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders archive row with formatted size", async () => {
    renderWithQuery(() => <LogArchives traderId="trader-1" />);
    const sizeCell = await screen.findByText("12.1 KB");
    expect(sizeCell).toBeInTheDocument();
  });

  it("renders download button for archive", async () => {
    renderWithQuery(() => <LogArchives traderId="trader-1" />);
    const btn = await screen.findByRole("button", { name: /download/i });
    expect(btn).toBeInTheDocument();
  });

  it("calls downloadTraderArchive when download button is clicked", async () => {
    renderWithQuery(() => <LogArchives traderId="trader-1" />);
    const { api } = await import("~/lib/api");
    const btn = await screen.findByRole("button", { name: /download/i });
    btn.click();
    expect(vi.mocked(api.downloadTraderArchive)).toHaveBeenCalledWith(
      "trader-1",
      "archive-abc123"
    );
  });

  it("renders empty state when no archives", async () => {
    const { api } = await import("~/lib/api");
    vi.mocked(api.listTraderArchives).mockResolvedValueOnce([]);
    renderWithQuery(() => <LogArchives traderId="trader-1" />);
    const msg = await screen.findByText(/No archived logs yet/i);
    expect(msg).toBeInTheDocument();
  });
});
