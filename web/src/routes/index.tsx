import { type Component } from "solid-js";
import { useNavigate } from "@solidjs/router";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "~/components/ui/card";
import { LoginForm } from "~/components/auth/LoginForm";
import { authStore } from "~/stores/auth";

export default function LoginPage() {
  const navigate = useNavigate();

  // Redirect to setup if not initialized
  if (!authStore.isInitialized()) {
    navigate("/setup", { replace: true });
    return null;
  }

  // Redirect to dashboard if already authenticated
  if (authStore.authenticated()) {
    navigate("/dashboard", { replace: true });
    return null;
  }

  return (
    <div class="min-h-screen flex items-center justify-center bg-background p-4">
      <Card class="w-full max-w-md">
        <CardHeader class="text-center">
          <CardTitle class="text-2xl">Hyper Trader Manager</CardTitle>
          <CardDescription>Sign in to your account</CardDescription>
        </CardHeader>
        <CardContent>
          <LoginForm />
        </CardContent>
      </Card>
    </div>
  );
}
