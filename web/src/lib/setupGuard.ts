export type GuardDecision =
  | { type: "allow" }
  | { type: "redirect-route"; to: string }
  | { type: "redirect-https"; url: string };

/**
 * Determines what should happen on the current page based on SSL/auth state.
 * Order: SSL config → secure context → bootstrap → allow.
 *
 * @param currentPath path being evaluated (e.g. window.location.pathname)
 * @param isSecureContext whether window.isSecureContext is true
 * @param authState object containing sslConfigured and isInitialized booleans
 */
export function evaluateSetupGuard(
  currentPath: string,
  isSecureContext: boolean,
  authState: { sslConfigured: boolean | null; isInitialized: boolean },
): GuardDecision {
  // The SSL setup page is reachable only while SSL is not yet configured —
  // it has to work over plain HTTP pre-config. Once configured, redirect away.
  if (currentPath === "/setup/ssl") {
    if (authState.sslConfigured === true) {
      // SSL already configured. Force HTTPS if we're on HTTP, else go home.
      if (!isSecureContext) {
        const url = `https://${window.location.host}/`;
        return { type: "redirect-https", url };
      }
      return { type: "redirect-route", to: "/" };
    }
    return { type: "allow" };
  }

  // 1. SSL must be configured first.
  if (authState.sslConfigured === false) {
    return { type: "redirect-route", to: "/setup/ssl" };
  }

  // 2. After SSL is configured, the page MUST be loaded over HTTPS (secure context).
  //    If not, force a reload over HTTPS using the configured domain when available.
  //    `sslConfigured === null` means we haven't checked yet — let the page render
  //    (AuthGuard waits for the check to complete before mounting routes).
  if (authState.sslConfigured === true && !isSecureContext) {
    // We don't know the domain client-side reliably — use current host.
    const url = `https://${window.location.host}${currentPath}${window.location.search}`;
    return { type: "redirect-https", url };
  }

  // 3. System bootstrap (admin user creation).
  if (!authState.isInitialized && currentPath !== "/setup") {
    return { type: "redirect-route", to: "/setup" };
  }

  return { type: "allow" };
}
