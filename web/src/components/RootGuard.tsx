import { type ParentProps, createEffect, createSignal, onMount, Show } from "solid-js";
import { useLocation, useNavigate } from "@solidjs/router";
import { authStore } from "~/stores/auth";
import { evaluateSetupGuard } from "~/lib/setupGuard";

function LoadingScreen() {
  return (
    <div class="min-h-screen flex items-center justify-center bg-surface-base">
      <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
    </div>
  );
}

/**
 * Router-root guard that performs SSL/setup/auth checks once on mount, then
 * reactively re-evaluates the setup guard whenever the relevant signals or
 * the current pathname change. It does NOT block the Router from mounting —
 * it only renders a LoadingScreen until the first checks resolve. This avoids
 * the previous bug where `navigate()` calls fired immediately after the
 * Router's first client-mount were dropped, leaving the URL updated but the
 * destination route un-rendered until a manual refresh.
 */
export function RootGuard(props: ParentProps) {
  const navigate = useNavigate();
  const location = useLocation();
  const [checked, setChecked] = createSignal(false);

  onMount(async () => {
    await authStore.checkSSL();
    await authStore.checkSetup();
    await authStore.checkAuth();
    setChecked(true);
  });

  // Reactive guard — re-runs whenever any input changes (incl. pathname).
  createEffect(() => {
    if (!checked()) return;

    const path = location.pathname;
    const ssl = authStore.sslConfigured();
    const init = authStore.isInitialized();
    const authed = authStore.authenticated();

    const decision = evaluateSetupGuard(path, window.isSecureContext, {
      sslConfigured: ssl,
      isInitialized: init,
    });

    if (decision.type === "redirect-route") {
      if (decision.to !== path) {
        navigate(decision.to, { replace: true });
      }
      return;
    }

    if (decision.type === "redirect-https") {
      window.location.replace(decision.url);
      return;
    }

    // decision === allow
    // Auth-aware redirects on top of the base setup guard.
    if (authed && (path === "/" || path === "/setup" || path === "/setup/ssl")) {
      navigate("/traders", { replace: true });
    }
  });

  return <Show when={checked()} fallback={<LoadingScreen />}>{props.children}</Show>;
}
