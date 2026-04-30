import { type Component } from "solid-js";
import { BootstrapForm } from "~/components/auth/BootstrapForm";

const SetupPage: Component = () => {
  return (
    <div class="min-h-screen bg-surface-base flex items-center justify-center p-4">
      <div class="w-full max-w-md bg-surface-raised border border-border-default rounded-md overflow-hidden">
        {/* Header strip */}
        <div class="px-8 pt-8 pb-6 border-b border-border-default">
          <div class="w-10 h-10 rounded-md bg-primary flex items-center justify-center mb-5">
            <span class="text-white text-sm font-semibold">HT</span>
          </div>
          <h1 class="text-xl font-semibold text-text-base">Create your account</h1>
          <p class="text-sm text-text-subtle mt-1">Set up the admin account to get started</p>
        </div>

        {/* Form area */}
        <div class="px-8 py-6">
          <BootstrapForm />
        </div>
      </div>
    </div>
  );
};

export default SetupPage;
