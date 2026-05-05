import { render, screen, fireEvent } from "@solidjs/testing-library";
import { describe, expect, it, vi, beforeEach, afterEach } from "vitest";
import { QueryClient, QueryClientProvider } from "@tanstack/solid-query";
import { MemoryRouter, Route, Router } from "@solidjs/router";
import { UpdateBanner } from "./UpdateBanner";

vi.mock("~/lib/api", () => ({
  api: {
    updates: {
      getStatus: vi.fn(),
      apply: vi.fn(),
      acknowledge: vi.fn(),
    },
  },
}));

vi.mock("~/components/UpdateProgressOverlay", () => ({
  UpdateProgressOverlay: () => <div data-testid="update-progress-overlay" />,
}));

function makeClient() {
  return new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: 0 } },
  });
}

function renderBanner(client: QueryClient) {
  return render(() => (
    <QueryClientProvider client={client}>
      <MemoryRouter>
        <Route path="/" component={() => <UpdateBanner />} />
      </MemoryRouter>
    </QueryClientProvider>
  ));
}

describe("UpdateBanner", () => {
  let client: QueryClient;

  beforeEach(() => {
    client = makeClient();
  });

  afterEach(() => {
    vi.clearAllMocks();
    client.clear();
  });

  it("renders nothing when update_available is false", async () => {
    const { api } = await import("~/lib/api");
    vi.mocked(api.updates.getStatus).mockResolvedValue({
      configured: true,
      update_available: false,
      status: "idle",
      current_version: "1.0.0",
      latest_version: "1.0.0",
      last_checked: null,
      error_message: null,
      finished_at: null,
      service_status: null,
    });

    const { container } = renderBanner(client);
    // Wait for query to settle
    await vi.waitFor(() => {
      expect(api.updates.getStatus).toHaveBeenCalled();
    });
    // No banner content
    expect(container.textContent).toBe("");
  });

  it("shows 'Update available' text when update_available is true", async () => {
    const { api } = await import("~/lib/api");
    vi.mocked(api.updates.getStatus).mockResolvedValue({
      configured: true,
      update_available: true,
      status: "idle",
      current_version: "1.0.0",
      latest_version: "1.1.0",
      last_checked: null,
      error_message: null,
      finished_at: null,
      service_status: null,
    });

    renderBanner(client);
    expect(await screen.findByText(/update available/i)).toBeInTheDocument();
  });

  it("shows 'Update failed' when status is 'failed' with error_message", async () => {
    const { api } = await import("~/lib/api");
    vi.mocked(api.updates.getStatus).mockResolvedValue({
      configured: true,
      update_available: false,
      status: "failed",
      current_version: "1.0.0",
      latest_version: "1.1.0",
      last_checked: null,
      error_message: "Pull failed",
      finished_at: null,
      service_status: null,
    });

    renderBanner(client);
    expect(await screen.findByText(/update failed: Pull failed/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /acknowledge/i })).toBeInTheDocument();
  });

  it("shows 'Update rolled back' when status is 'rolled_back'", async () => {
    const { api } = await import("~/lib/api");
    vi.mocked(api.updates.getStatus).mockResolvedValue({
      configured: true,
      update_available: false,
      status: "rolled_back",
      current_version: "1.0.0",
      latest_version: "1.1.0",
      last_checked: null,
      error_message: null,
      finished_at: null,
      service_status: null,
    });

    renderBanner(client);
    expect(await screen.findByText(/update rolled back/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /acknowledge/i })).toBeInTheDocument();
  });

  it("calls api.updates.apply when 'Update now' is clicked", async () => {
    const { api } = await import("~/lib/api");
    vi.mocked(api.updates.getStatus).mockResolvedValue({
      configured: true,
      update_available: true,
      status: "idle",
      current_version: "1.0.0",
      latest_version: "1.1.0",
      last_checked: null,
      error_message: null,
      finished_at: null,
      service_status: null,
    });
    vi.mocked(api.updates.apply).mockResolvedValue({ status: "updating", message: "ok" });

    renderBanner(client);
    const btn = await screen.findByRole("button", { name: /update now/i });
    fireEvent.click(btn);
    await vi.waitFor(() => {
      expect(api.updates.apply).toHaveBeenCalledOnce();
    });
  });

  it("shows progress overlay when status is 'updating'", async () => {
    const { api } = await import("~/lib/api");
    vi.mocked(api.updates.getStatus).mockResolvedValue({
      configured: true,
      update_available: false,
      status: "updating",
      current_version: null,
      latest_version: null,
      last_checked: null,
      error_message: null,
      finished_at: null,
      service_status: null,
    });

    renderBanner(client);
    expect(await screen.findByTestId("update-progress-overlay")).toBeInTheDocument();
  });

  it("hides the banner when Dismiss is clicked", async () => {
    const { api } = await import("~/lib/api");
    vi.mocked(api.updates.getStatus).mockResolvedValue({
      configured: true,
      update_available: true,
      status: "idle",
      current_version: "1.0.0",
      latest_version: "1.1.0",
      last_checked: null,
      error_message: null,
      finished_at: null,
      service_status: null,
    });

    renderBanner(client);
    // Banner is visible
    expect(await screen.findByText(/update available/i)).toBeInTheDocument();

    // Click Dismiss
    fireEvent.click(screen.getByRole("button", { name: /dismiss/i }));

    // Banner should be gone
    await vi.waitFor(() => {
      expect(screen.queryByText(/update available/i)).not.toBeInTheDocument();
    });
  });

  it("shows progress overlay when 'Update now' succeeds", async () => {
    const { api } = await import("~/lib/api");
    vi.mocked(api.updates.getStatus).mockResolvedValue({
      configured: true,
      update_available: true,
      status: "idle",
      current_version: "1.0.0",
      latest_version: "1.1.0",
      last_checked: null,
      error_message: null,
      finished_at: null,
      service_status: null,
    });
    vi.mocked(api.updates.apply).mockResolvedValue({ status: "updating", message: "ok" });

    renderBanner(client);
    const btn = await screen.findByRole("button", { name: /update now/i });
    fireEvent.click(btn);
    expect(await screen.findByTestId("update-progress-overlay")).toBeInTheDocument();
  });
});
