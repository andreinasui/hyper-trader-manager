import { type Component, Show } from "solid-js";
import { Navigate } from "@solidjs/router";
import { BootstrapForm } from "~/components/auth/BootstrapForm";
import { authStore } from "~/stores/auth";

const SetupPage: Component = () => {
  return (
    <Show 
      when={!authStore.isInitialized()} 
      fallback={<Navigate href="/" />}
    >
      <div class="min-h-screen bg-[#08090a] flex items-center justify-center p-4">
        <div class="w-full max-w-md bg-[#111214] border border-[#222426] rounded-md overflow-hidden">
          {/* Header strip */}
          <div class="px-8 pt-8 pb-6 border-b border-[#222426]">
            <div class="w-10 h-10 rounded-md bg-[#5e6ad2] flex items-center justify-center mb-5">
              <span class="text-white text-sm font-semibold">HT</span>
            </div>
            <h1 class="text-xl font-semibold text-zinc-50">Create your account</h1>
            <p class="text-sm text-zinc-500 mt-1">Set up the admin account to get started</p>
          </div>

          {/* Form area */}
          <div class="px-8 py-6">
            <BootstrapForm />
          </div>
        </div>
      </div>
    </Show>
  );
};

export default SetupPage;
