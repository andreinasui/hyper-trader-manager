import { type Component, type ParentProps, Suspense, onMount, createSignal, Show } from "solid-js";
import { Navigate, useLocation } from "@solidjs/router";
import { authStore } from "~/stores/auth";

// Loading screen component
function LoadingScreen() {
  return (
    <div class="min-h-screen flex items-center justify-center bg-background">
      <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
    </div>
  );
}

// The root component that wraps all routes
const App: Component<ParentProps> = (props) => {
  const [initialized, setInitialized] = createSignal(false);
  const location = useLocation();

  onMount(async () => {
    await authStore.checkSetup();
    await authStore.checkAuth();
    setInitialized(true);
  });

  // Check if current route requires auth
  const isProtectedRoute = () => {
    const path = location.pathname;
    return path.startsWith("/dashboard") ||
           path.startsWith("/settings") ||
           path.startsWith("/traders");
  };

  return (
    <Suspense fallback={<LoadingScreen />}>
      <Show when={initialized()} fallback={<LoadingScreen />}>
        <Show
          when={!isProtectedRoute() || authStore.authenticated()}
          fallback={<Navigate href="/" />}
        >
          {props.children}
        </Show>
      </Show>
    </Suspense>
  );
};

export default App;
