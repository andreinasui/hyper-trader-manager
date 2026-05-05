import { type Component, createSignal, Show, Switch, Match, onCleanup, onMount } from "solid-js";
import { Loader2, AlertCircle, CheckCircle2, XCircle, RefreshCw } from "lucide-solid";
import { api } from "~/lib/api";

const POLL_INTERVAL_MS = 2000;
const TIMEOUT_MS = 5 * 60 * 1000;
// If we land on the overlay and the backend is already idle but reports a
// recent finished_at, treat that as a completion signal. This handles the
// case where the API container was restarted by the helper (wiping any
// in-memory "seenUpdating" state) and the new API reports idle on first poll.
const RECENT_FINISH_WINDOW_MS = 10 * 60 * 1000;

type Phase = "INITIATING" | "POLLING" | "DONE" | "FAILED" | "ROLLED_BACK" | "TIMEOUT";

interface Step {
  label: string;
}

const STEPS: Step[] = [
  { label: "Starting update" },
  { label: "Pulling new images" },
  { label: "Restarting services" },
  { label: "Verifying health" },
];

export const UpdateProgressOverlay: Component = () => {
  const [phase, setPhase] = createSignal<Phase>("INITIATING");
  const [errorMessage, setErrorMessage] = createSignal<string | null>(null);
  const [consecutiveFailures, setConsecutiveFailures] = createSignal(0);
  const [seenUpdating, setSeenUpdating] = createSignal(false);

  let intervalId: ReturnType<typeof setInterval> | undefined;
  const startTime = Date.now();

  onMount(() => {
    setPhase("POLLING");

    intervalId = setInterval(async () => {
      if (Date.now() - startTime > TIMEOUT_MS) {
        clearInterval(intervalId);
        setPhase("TIMEOUT");
        return;
      }

      try {
        const status = await api.updates.getStatus();
        setConsecutiveFailures(0);

        if (status.status === "updating") {
          setSeenUpdating(true);
        } else if (status.status === "idle") {
          // Two paths to "DONE":
          //  1) We previously observed an "updating" poll on this overlay.
          //  2) The backend reports a recent finished_at — meaning the helper
          //     just completed (likely while the API container was restarting,
          //     so we never got to observe "updating" ourselves).
          const finishedAt = status.finished_at
            ? Date.parse(status.finished_at)
            : NaN;
          const finishedRecently =
            Number.isFinite(finishedAt) &&
            Date.now() - finishedAt < RECENT_FINISH_WINDOW_MS;

          if (seenUpdating() || finishedRecently) {
            clearInterval(intervalId);
            setPhase("DONE");
            setTimeout(() => {
              window.location.href = "/";
            }, 2000);
          }
        } else if (status.status === "failed") {
          clearInterval(intervalId);
          setErrorMessage(status.error_message);
          setPhase("FAILED");
        } else if (status.status === "rolled_back") {
          clearInterval(intervalId);
          setPhase("ROLLED_BACK");
        }
      } catch {
        setConsecutiveFailures((f) => f + 1);
      }
    }, POLL_INTERVAL_MS);
  });

  onCleanup(() => clearInterval(intervalId));

  const isReconnecting = () => consecutiveFailures() >= 3;

  return (
    <div class="fixed inset-0 z-50 bg-surface-base flex items-center justify-center p-4">
      <div class="w-full max-w-md bg-surface-raised border border-border-default rounded-md overflow-hidden">
        {/* Header */}
        <div class="px-8 pt-8 pb-6 border-b border-border-default">
          <div class="w-10 h-10 rounded-md bg-primary flex items-center justify-center mb-5">
            <RefreshCw size={18} stroke-width={1.5} class="text-white" />
          </div>
          <h1 class="text-xl font-semibold text-text-base">System Update</h1>
          <p class="text-sm text-text-subtle mt-1">Updating to the latest version</p>
        </div>

        {/* Body */}
        <div class="px-8 py-6">
          <Switch>
            {/* INITIATING / POLLING */}
            <Match when={phase() === "INITIATING" || phase() === "POLLING"}>
              <div class="relative">
                {/* Reconnecting overlay */}
                <Show when={isReconnecting()}>
                  <div
                    role="alert"
                    aria-label="reconnecting"
                    class="absolute inset-0 z-10 flex items-center justify-center rounded-md bg-surface-raised/80 backdrop-blur-sm"
                  >
                    <div class="flex items-center gap-2 text-sm text-text-subtle">
                      <Loader2 class="h-4 w-4 animate-spin" />
                      <span>Reconnecting…</span>
                    </div>
                  </div>
                </Show>

                <div class="flex flex-col items-center text-center py-4 gap-4" role="status">
                  <Loader2 class="h-9 w-9 animate-spin text-primary" />
                  <div>
                    <p class="text-sm font-medium text-text-base">Applying update…</p>
                    <p class="text-sm text-text-subtle mt-1">
                      Services are restarting. This may take a few minutes.
                    </p>
                  </div>
                  <div
                    role="alert"
                    class="w-full p-3 bg-amber-950 border border-amber-800 rounded-md flex gap-2 text-xs text-amber-200"
                  >
                    <span aria-hidden="true">⚠</span>
                    <span>Do not close or refresh this page</span>
                  </div>
                </div>

                {/* Progress steps */}
                <div class="mt-4 space-y-2">
                  {STEPS.map((step) => (
                    <div class="flex items-center gap-3 text-sm text-text-subtle">
                      <Loader2 class="h-4 w-4 animate-spin text-primary flex-shrink-0" />
                      <span>{step.label}</span>
                    </div>
                  ))}
                </div>
              </div>
            </Match>

            {/* DONE */}
            <Match when={phase() === "DONE"}>
              <div class="flex flex-col items-center text-center py-8 gap-4" role="status">
                <CheckCircle2 class="h-9 w-9 text-success" />
                <div>
                  <p class="text-sm font-medium text-text-base">Update complete!</p>
                  <p class="text-sm text-text-subtle mt-1">
                    Redirecting you to the dashboard…
                  </p>
                </div>

                <div class="mt-4 space-y-2 w-full">
                  {STEPS.map((step) => (
                    <div class="flex items-center gap-3 text-sm text-text-subtle">
                      <CheckCircle2 class="h-4 w-4 text-success flex-shrink-0" />
                      <span>{step.label}</span>
                    </div>
                  ))}
                </div>
              </div>
            </Match>

            {/* FAILED */}
            <Match when={phase() === "FAILED"}>
              <div class="flex flex-col items-center text-center py-8 gap-4">
                <XCircle class="h-9 w-9 text-error" />
                <div>
                  <p class="text-sm font-medium text-text-base">Update failed</p>
                  <Show when={errorMessage()}>
                    <p class="text-sm text-text-subtle mt-1 font-mono break-all">
                      {errorMessage()}
                    </p>
                  </Show>
                  <p class="text-sm text-text-subtle mt-2">
                    The previous version has been restored.
                  </p>
                </div>
                <a href="/" class="text-sm text-primary underline underline-offset-2">
                  Go home
                </a>
              </div>
            </Match>

            {/* ROLLED_BACK */}
            <Match when={phase() === "ROLLED_BACK"}>
              <div class="flex flex-col items-center text-center py-8 gap-4">
                <AlertCircle class="h-9 w-9 text-warning" />
                <div>
                  <p class="text-sm font-medium text-text-base">Update rolled back</p>
                  <p class="text-sm text-text-subtle mt-1">
                    The update was rolled back to the previous version.
                  </p>
                </div>
                <a href="/" class="text-sm text-primary underline underline-offset-2">
                  Go home
                </a>
              </div>
            </Match>

            {/* TIMEOUT */}
            <Match when={phase() === "TIMEOUT"}>
              <div class="flex flex-col items-center text-center py-8 gap-4">
                <AlertCircle class="h-9 w-9 text-error" />
                <div>
                  <p class="text-sm font-medium text-text-base">Update timed out</p>
                  <p class="text-sm text-text-subtle mt-1">
                    The update did not complete within 5 minutes. Please check the system
                    status.
                  </p>
                </div>
                <button
                  onClick={() => window.location.reload()}
                  class="text-sm text-primary underline underline-offset-2"
                >
                  Try again
                </button>
              </div>
            </Match>
          </Switch>
        </div>
      </div>
    </div>
  );
};
