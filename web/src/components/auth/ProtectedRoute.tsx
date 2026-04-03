import { type ParentProps, onMount, Show } from "solid-js";
import { useNavigate } from "@solidjs/router";
import { authStore } from "~/stores/auth";

export function ProtectedRoute(props: ParentProps) {
  const navigate = useNavigate();

  onMount(() => {
    if (!authStore.authenticated()) {
      navigate("/", { replace: true });
    }
  });

  return (
    <Show when={authStore.authenticated()}>
      {props.children}
    </Show>
  );
}
