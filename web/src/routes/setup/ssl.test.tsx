import { render, screen, fireEvent } from "@solidjs/testing-library";
import { vi, describe, it, expect, beforeEach, afterEach } from "vitest";
import SSLSetupPage from "./ssl";

vi.mock("~/lib/api", () => ({
  api: {
    configureSSL: vi.fn(),
  },
}));

async function flushMicrotasks() {
  // Flush promise chains inside async handlers (e.g. handleSubmit's await)
  await vi.advanceTimersByTimeAsync(0);
}

async function fillAndSubmitForm() {
  fireEvent.input(screen.getByLabelText("Domain Name"), {
    target: { value: "example.com" },
  });
  fireEvent.input(screen.getByLabelText("Email Address"), {
    target: { value: "admin@example.com" },
  });
  const form = screen.getByRole("button", { name: /configure ssl/i }).closest("form")!;
  fireEvent.submit(form);
  await flushMicrotasks();
}

describe("SSLSetupPage", () => {
  let originalLocationDescriptor: PropertyDescriptor | undefined;

  beforeEach(async () => {
    vi.useFakeTimers();
    const { api } = await import("~/lib/api");
    vi.mocked(api.configureSSL).mockResolvedValue({
      success: true,
      message: "ok",
      redirect_url: "https://example.com/",
    });
    // Default: fetch keeps failing (server still down)
    vi.stubGlobal(
      "fetch",
      vi.fn().mockRejectedValue(new TypeError("Failed to fetch"))
    );
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.unstubAllGlobals();
    vi.clearAllMocks();
    // Restore window.location if it was replaced
    if (originalLocationDescriptor) {
      Object.defineProperty(window, "location", originalLocationDescriptor);
      originalLocationDescriptor = undefined;
    }
  });

  it("renders the form initially", () => {
    render(() => <SSLSetupPage />);
    expect(screen.getByLabelText("Domain Name")).toBeInTheDocument();
    expect(screen.getByLabelText("Email Address")).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Configure SSL" })
    ).toBeInTheDocument();
  });

  it("shows waiting state after successful form submission", async () => {
    render(() => <SSLSetupPage />);
    await fillAndSubmitForm();

    expect(screen.getByText("Configuring SSL…")).toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: /configure ssl/i })
    ).not.toBeInTheDocument();
    expect(
      screen.getByText(/do not close or refresh this page/i)
    ).toBeInTheDocument();
  });

  it("redirects to https url when poll returns ok response", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({ type: "basic", ok: true } as Response)
    );

    let capturedHref = "";
    originalLocationDescriptor = Object.getOwnPropertyDescriptor(window, "location");
    Object.defineProperty(window, "location", {
      writable: true,
      value: {
        ...window.location,
        get href() { return capturedHref; },
        set href(v: string) { capturedHref = v; },
      },
    });

    render(() => <SSLSetupPage />);
    await fillAndSubmitForm();

    await vi.advanceTimersByTimeAsync(1500);

    expect(capturedHref).toBe("https://example.com/");
  });

  it("redirects to https url when poll returns opaqueredirect", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({ type: "opaqueredirect" } as Response)
    );

    // Capture location.href changes
    let capturedHref = "";
    originalLocationDescriptor = Object.getOwnPropertyDescriptor(window, "location");
    Object.defineProperty(window, "location", {
      writable: true,
      value: {
        ...window.location,
        get href() { return capturedHref; },
        set href(v: string) { capturedHref = v; },
      },
    });

    render(() => <SSLSetupPage />);
    await fillAndSubmitForm();

    // Fire first poll interval
    await vi.advanceTimersByTimeAsync(1500);

    expect(capturedHref).toBe("https://example.com/");
    // No manual restore here — afterEach handles it
  });

  it("shows error state after 90-second timeout", async () => {
    render(() => <SSLSetupPage />);
    await fillAndSubmitForm();

    // Advance past the 90-second timeout
    await vi.advanceTimersByTimeAsync(90_000);

    expect(screen.getByText(/could not connect to server/i)).toBeInTheDocument();
    expect(
      screen.getByRole("link", { name: /open.*manually/i })
    ).toHaveAttribute("href", "https://example.com/");
    // Waiting spinner should be gone
    expect(screen.queryByText("Configuring SSL…")).not.toBeInTheDocument();
  });
});
