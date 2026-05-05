// web/src/routes/updates/progress.test.tsx
import { render, screen } from "@solidjs/testing-library";
import { vi, describe, it, expect, beforeEach, afterEach } from "vitest";
import UpdateProgress from "./progress";

vi.mock("~/lib/api", () => ({
  api: {
    updates: {
      getStatus: vi.fn(),
    },
  },
}));

describe("UpdateProgress", () => {
  let originalLocationDescriptor: PropertyDescriptor | undefined;

  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.clearAllMocks();
    if (originalLocationDescriptor) {
      Object.defineProperty(window, "location", originalLocationDescriptor);
      originalLocationDescriptor = undefined;
    }
  });

  it("shows polling/updating content while polling", async () => {
    const { api } = await import("~/lib/api");
    vi.mocked(api.updates.getStatus).mockResolvedValue({
      status: "updating",
      current_version: null,
      latest_version: null,
      update_available: false,
      last_checked: null,
      error_message: null,
      finished_at: null,
      configured: true,
      service_status: null,
    });

    render(() => <UpdateProgress />);

    // Should show the spinner and the "do not close" warning immediately
    expect(screen.getByText(/applying update/i)).toBeInTheDocument();
    expect(screen.getByText(/do not close or refresh this page/i)).toBeInTheDocument();
  });

  it("transitions to DONE when status goes idle after seeing updating", async () => {
    const { api } = await import("~/lib/api");

    // First call: updating; second call: idle
    vi.mocked(api.updates.getStatus)
      .mockResolvedValueOnce({
        status: "updating",
        current_version: null,
        latest_version: null,
        update_available: false,
        last_checked: null,
        error_message: null,
        finished_at: null,
        configured: true,
        service_status: null,
      })
      .mockResolvedValueOnce({
        status: "idle",
        current_version: "1.1.0",
        latest_version: "1.1.0",
        update_available: false,
        last_checked: null,
        error_message: null,
        finished_at: null,
        configured: true,
        service_status: null,
      });

    render(() => <UpdateProgress />);

    // First poll: see "updating"
    await vi.advanceTimersByTimeAsync(2000);
    // Second poll: see "idle" → DONE
    await vi.advanceTimersByTimeAsync(2000);

    expect(screen.getByText(/update complete/i)).toBeInTheDocument();
  });

  it("transitions to DONE when first poll is idle with recent finished_at", async () => {
    const { api } = await import("~/lib/api");

    // Simulate the case where the helper completed the update while the API
    // container was restarting — the page mounts and the very first poll
    // returns idle (no prior "updating" observation), but with a recent
    // finished_at indicating completion.
    vi.mocked(api.updates.getStatus).mockResolvedValue({
      status: "idle",
      current_version: "1.1.0",
      latest_version: "1.1.0",
      update_available: false,
      last_checked: null,
      error_message: null,
      finished_at: new Date().toISOString(),
      configured: true,
      service_status: null,
    });

    render(() => <UpdateProgress />);

    await vi.advanceTimersByTimeAsync(2000);

    expect(screen.getByText(/update complete/i)).toBeInTheDocument();
  });

  it("does not transition to DONE on idle with stale finished_at and no prior updating", async () => {
    const { api } = await import("~/lib/api");

    // finished_at is older than the recent-finish window — should not be
    // treated as a completion signal (e.g., user navigated to the page
    // manually long after a previous update).
    const stale = new Date(Date.now() - 60 * 60 * 1000).toISOString();
    vi.mocked(api.updates.getStatus).mockResolvedValue({
      status: "idle",
      current_version: "1.1.0",
      latest_version: "1.1.0",
      update_available: false,
      last_checked: null,
      error_message: null,
      finished_at: stale,
      configured: true,
      service_status: null,
    });

    render(() => <UpdateProgress />);

    await vi.advanceTimersByTimeAsync(2000);

    expect(screen.getByText(/applying update/i)).toBeInTheDocument();
  });

  it("transitions to FAILED when status is failed", async () => {
    const { api } = await import("~/lib/api");

    vi.mocked(api.updates.getStatus).mockResolvedValue({
      status: "failed",
      current_version: null,
      latest_version: null,
      update_available: false,
      last_checked: null,
      error_message: "Docker pull failed",
      finished_at: null,
      configured: true,
      service_status: null,
    });

    render(() => <UpdateProgress />);

    await vi.advanceTimersByTimeAsync(2000);

    expect(screen.getByText(/update failed/i)).toBeInTheDocument();
    expect(screen.getByText("Docker pull failed")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /go home/i })).toHaveAttribute("href", "/");
  });

  it("shows ROLLED_BACK message when status is rolled_back", async () => {
    const { api } = await import("~/lib/api");

    vi.mocked(api.updates.getStatus).mockResolvedValue({
      status: "rolled_back",
      current_version: null,
      latest_version: null,
      update_available: false,
      last_checked: null,
      error_message: null,
      finished_at: null,
      configured: true,
      service_status: null,
    });

    render(() => <UpdateProgress />);

    await vi.advanceTimersByTimeAsync(2000);

    expect(screen.getByText(/update was rolled back/i)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /go home/i })).toHaveAttribute("href", "/");
  });

  it("shows reconnecting overlay after 3 consecutive failures", async () => {
    const { api } = await import("~/lib/api");

    vi.mocked(api.updates.getStatus).mockRejectedValue(new TypeError("Network error"));

    render(() => <UpdateProgress />);

    // 3 consecutive failures need 3 poll intervals
    await vi.advanceTimersByTimeAsync(2000);
    await vi.advanceTimersByTimeAsync(2000);
    await vi.advanceTimersByTimeAsync(2000);

    expect(screen.getByRole("alert", { name: /reconnecting/i })).toBeInTheDocument();
  });
});
