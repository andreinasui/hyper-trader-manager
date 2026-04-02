import { type Component } from "solid-js";
import { Navigate } from "@solidjs/router";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "~/components/ui/card";
import { BootstrapForm } from "~/components/auth/BootstrapForm";
import { authStore } from "~/stores/auth";

const SetupPage: Component = () => {
  // Redirect to login if already initialized
  if (authStore.isInitialized()) {
    return <Navigate href="/" />;
  }

  return (
    <div class="min-h-screen flex items-center justify-center bg-background p-4">
      <Card class="w-full max-w-md">
        <CardHeader class="text-center">
          <CardTitle class="text-2xl">Welcome to Hyper Trader</CardTitle>
          <CardDescription>Create your admin account to get started</CardDescription>
        </CardHeader>
        <CardContent>
          <BootstrapForm />
        </CardContent>
      </Card>
    </div>
  );
};

export default SetupPage;
