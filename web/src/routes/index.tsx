import { useNavigate } from "@solidjs/router";
import { LoginForm } from "~/components/auth/LoginForm";
import { authStore } from "~/stores/auth";

export default function LoginPage() {
  const navigate = useNavigate();

  // Redirect to setup if not initialized
  if (!authStore.isInitialized()) {
    navigate("/setup", { replace: true });
    return null;
  }

  // Redirect to traders if already authenticated
  if (authStore.authenticated()) {
    navigate("/traders", { replace: true });
    return null;
  }

  return (
    <div class="min-h-screen bg-surface-base flex items-center justify-center p-4">
      <div class="w-full max-w-md bg-surface-raised border border-border-default rounded-md overflow-hidden">
        {/* Header strip */}
        <div class="px-8 pt-8 pb-6 border-b border-border-default">
          <div class="w-10 h-10 rounded-md bg-primary flex items-center justify-center mb-5">
            <span class="text-white text-sm font-semibold">HT</span>
          </div>
          <h1 class="text-xl font-semibold text-text-base">Welcome back</h1>
          <p class="text-sm text-text-subtle mt-1">Sign in to your account</p>
        </div>

        {/* Form area */}
        <div class="px-8 py-6">
          <LoginForm />
        </div>
      </div>
    </div>
  );
}
