import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@solidjs/testing-library";
import { QueryClient, QueryClientProvider } from "@tanstack/solid-query";
import type { JSX } from "solid-js";
import { LogViewer } from "./LogViewer";

// Mock the api module
vi.mock("~/lib/api", () => ({
  api: {
    getTraderLogs: vi.fn().mockResolvedValue([]),
    downloadTraderLogs: vi.fn().mockResolvedValue(undefined),
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

describe("LogViewer", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders preset time range buttons", () => {
    renderWithQuery(() => <LogViewer traderId="test-id" />);
    expect(screen.getByText("1h")).toBeInTheDocument();
    expect(screen.getByText("6h")).toBeInTheDocument();
    expect(screen.getByText("24h")).toBeInTheDocument();
    expect(screen.getByText("7d")).toBeInTheDocument();
  });

  it("renders download button", () => {
    renderWithQuery(() => <LogViewer traderId="test-id" />);
    expect(screen.getByText(/Download/i)).toBeInTheDocument();
  });

  it("renders From and To datetime inputs", () => {
    renderWithQuery(() => <LogViewer traderId="test-id" />);
    const inputs = document.querySelectorAll('input[type="datetime-local"]');
    expect(inputs.length).toBe(2);
  });

  it("shows Live button when a preset is active", async () => {
    renderWithQuery(() => <LogViewer traderId="test-id" />);
    fireEvent.click(screen.getByText("1h"));
    expect(screen.getByText("Live")).toBeInTheDocument();
  });
});
