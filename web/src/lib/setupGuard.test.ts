import { describe, it, expect } from "vitest";
import { evaluateSetupGuard } from "./setupGuard";

describe("evaluateSetupGuard", () => {
  it("should allow /setup/ssl when SSL is not yet configured", () => {
    const decision = evaluateSetupGuard("/setup/ssl", false, {
      sslConfigured: false,
      isInitialized: false,
    });
    expect(decision).toEqual({ type: "allow" });

    // Also allowed when sslConfigured is null (status unknown / still loading)
    const decision2 = evaluateSetupGuard("/setup/ssl", false, {
      sslConfigured: null,
      isInitialized: false,
    });
    expect(decision2).toEqual({ type: "allow" });
  });

  it("should redirect away from /setup/ssl when SSL is already configured", () => {
    // Already on HTTPS → in-app redirect to home
    const decision = evaluateSetupGuard("/setup/ssl", true, {
      sslConfigured: true,
      isInitialized: true,
    });
    expect(decision).toEqual({ type: "redirect-route", to: "/" });

    // Still on HTTP somehow → force HTTPS upgrade
    const originalLocation = window.location;
    delete (window as any).location;
    window.location = { ...originalLocation, host: "example.com" } as Location;
    try {
      const decision2 = evaluateSetupGuard("/setup/ssl", false, {
        sslConfigured: true,
        isInitialized: false,
      });
      expect(decision2).toEqual({ type: "redirect-https", url: "https://example.com/" });
    } finally {
      window.location = originalLocation;
    }
  });

  it("should redirect to /setup/ssl when SSL is not configured", () => {
    const decision = evaluateSetupGuard("/", false, {
      sslConfigured: false,
      isInitialized: false,
    });
    expect(decision).toEqual({ type: "redirect-route", to: "/setup/ssl" });

    const decision2 = evaluateSetupGuard("/setup", false, {
      sslConfigured: false,
      isInitialized: false,
    });
    expect(decision2).toEqual({ type: "redirect-route", to: "/setup/ssl" });
  });

  it("should redirect to HTTPS when SSL is configured but context is not secure", () => {
    const decision = evaluateSetupGuard("/", false, {
      sslConfigured: true,
      isInitialized: false,
    });
    expect(decision.type).toBe("redirect-https");
    if (decision.type === "redirect-https") {
      expect(decision.url).toContain("https://");
      expect(decision.url).toContain("/");
    }

    const decision2 = evaluateSetupGuard("/traders", false, {
      sslConfigured: true,
      isInitialized: true,
    });
    expect(decision2.type).toBe("redirect-https");
    if (decision2.type === "redirect-https") {
      expect(decision2.url).toContain("https://");
      expect(decision2.url).toContain("/traders");
    }
  });

  it("should redirect to /setup when SSL is configured, secure, but not initialized", () => {
    const decision = evaluateSetupGuard("/", true, {
      sslConfigured: true,
      isInitialized: false,
    });
    expect(decision).toEqual({ type: "redirect-route", to: "/setup" });

    const decision2 = evaluateSetupGuard("/traders", true, {
      sslConfigured: true,
      isInitialized: false,
    });
    expect(decision2).toEqual({ type: "redirect-route", to: "/setup" });
  });

  it("should allow /setup when SSL is configured, secure, but not initialized", () => {
    const decision = evaluateSetupGuard("/setup", true, {
      sslConfigured: true,
      isInitialized: false,
    });
    expect(decision).toEqual({ type: "allow" });
  });

  it("should allow access when SSL is configured, secure, and initialized", () => {
    const decision = evaluateSetupGuard("/", true, {
      sslConfigured: true,
      isInitialized: true,
    });
    expect(decision).toEqual({ type: "allow" });

    const decision2 = evaluateSetupGuard("/traders", true, {
      sslConfigured: true,
      isInitialized: true,
    });
    expect(decision2).toEqual({ type: "allow" });
  });

  it("should allow access when SSL status is null (not yet checked)", () => {
    const decision = evaluateSetupGuard("/", true, {
      sslConfigured: null,
      isInitialized: true,
    });
    expect(decision).toEqual({ type: "allow" });
  });

  it("should preserve query parameters in HTTPS redirect", () => {
    // Mock window.location for this test
    const originalLocation = window.location;
    delete (window as any).location;
    window.location = {
      ...originalLocation,
      host: "example.com:8080",
      search: "?foo=bar",
    } as Location;

    const decision = evaluateSetupGuard("/traders", false, {
      sslConfigured: true,
      isInitialized: true,
    });

    expect(decision.type).toBe("redirect-https");
    if (decision.type === "redirect-https") {
      expect(decision.url).toBe("https://example.com:8080/traders?foo=bar");
    }

    // Restore original location
    window.location = originalLocation;
  });
});
