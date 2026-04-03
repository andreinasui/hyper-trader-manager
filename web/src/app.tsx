import { type ParentProps, Suspense, onMount, createSignal, Show } from "solid-js";
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
    <div class="min-h-screen flex items-center justify-center bg-background">
      <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
    </div>
  );
}

function AuthGuard(props: ParentProps) {
  const [initialized, setInitialized] = createSignal(false);

  onMount(async () => {
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

export default function App() {
  return (
    <MetaProvider>
      <QueryClientProvider client={queryClient}>
        <AuthGuard>
          <Router root={(props) => <Suspense>{props.children}</Suspense>}>
            <FileRoutes />
          </Router>
        </AuthGuard>
      </QueryClientProvider>
    </MetaProvider>
  );
}
