import { type ParentProps, Suspense, onMount, createSignal, Show, ErrorBoundary } from "solid-js";
import { Router } from "@solidjs/router";
import { FileRoutes } from "@solidjs/start/router";
import { QueryClient, QueryClientProvider } from "@tanstack/solid-query";
import { MetaProvider } from "@solidjs/meta";
import { authStore } from "~/stores/auth";
import "./styles.css";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 1000 * 60,
      retry: 1,
    },
  },
});

function LoadingScreen() {
  return (
    <div class="min-h-screen flex items-center justify-center bg-surface-base">
      <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
    </div>
  );
}

function AuthGuard(props: ParentProps) {
  const [initialized, setInitialized] = createSignal(false);

  onMount(async () => {
    await authStore.checkSSL();
    await authStore.checkSetup();
    await authStore.checkAuth();
    setInitialized(true);
  });

  return (
    <Show when={initialized()} fallback={<LoadingScreen />}>
      {props.children}
    </Show>
  );
}

function ErrorFallback(props: { error: Error }) {
  return (
    <div class="min-h-screen flex items-center justify-center bg-surface-base p-4">
      <div class="max-w-md text-center">
        <h1 class="text-2xl font-bold text-error mb-4">Something went wrong</h1>
        <pre class="text-sm text-text-subtle bg-surface-raised p-4 rounded overflow-auto">
          {props.error.message}
        </pre>
      </div>
    </div>
  );
}

export default function App() {
  return (
    <ErrorBoundary fallback={(err) => <ErrorFallback error={err} />}>
      <MetaProvider>
        <QueryClientProvider client={queryClient}>
          <AuthGuard>
            <Router root={(props) => <Suspense fallback={<LoadingScreen />}>{props.children}</Suspense>}>
              <FileRoutes />
            </Router>
          </AuthGuard>
        </QueryClientProvider>
      </MetaProvider>
    </ErrorBoundary>
  );
}
