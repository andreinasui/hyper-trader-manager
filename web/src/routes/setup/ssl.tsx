import { type Component, createSignal, Show } from "solid-js";
import { useNavigate } from "@solidjs/router";
import { Lock } from "lucide-solid";
import { api } from "~/lib/api";

const SSLSetupPage: Component = () => {
  const navigate = useNavigate();
  const [mode, setMode] = createSignal<"domain" | "ip">("domain");
  const [domain, setDomain] = createSignal("");
  const [error, setError] = createSignal<string | null>(null);
  const [loading, setLoading] = createSignal(false);

  async function handleSubmit(e: Event) {
    e.preventDefault();
    setError(null);
    setLoading(true);

    try {
      await api.configureSSL(mode(), mode() === "domain" ? domain() : undefined);
      navigate("/");
    } catch (err) {
      setError(err instanceof Error ? err.message : "SSL configuration failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div class="min-h-screen bg-[#08090a] flex items-center justify-center p-4">
      <div class="w-full max-w-md bg-[#111214] border border-[#222426] rounded-md overflow-hidden">
        {/* Header strip */}
        <div class="px-8 pt-8 pb-6 border-b border-[#222426]">
          <div class="w-10 h-10 rounded-md bg-[#5e6ad2] flex items-center justify-center mb-5">
            <Lock size={18} stroke-width={1.5} class="text-white" />
          </div>
          <h1 class="text-xl font-semibold text-zinc-50">SSL Configuration</h1>
          <p class="text-sm text-zinc-500 mt-1">Configure SSL for secure connections</p>
        </div>

        {/* Form area */}
        <div class="px-8 py-6">
          <form onSubmit={handleSubmit} class="space-y-6">
            <Show when={error()}>
              <div class="bg-red-950/30 border border-red-900 rounded-md px-4 py-3 text-sm text-red-400">
                {error()}
              </div>
            </Show>

            <div class="space-y-3">
              <label class="text-sm font-medium text-zinc-300 block">SSL Mode</label>
              <div class="grid grid-cols-2 gap-3">
                <button
                  type="button"
                  onClick={() => setMode("domain")}
                  class={`border rounded-md px-4 py-2.5 text-sm cursor-pointer transition-all ${
                    mode() === "domain"
                      ? "border-[#5e6ad2] bg-[#5e6ad2]/10 text-zinc-100"
                      : "border-[#222426] text-zinc-400 hover:border-zinc-600"
                  }`}
                >
                  Domain (Let's Encrypt)
                </button>
                <button
                  type="button"
                  onClick={() => setMode("ip")}
                  class={`border rounded-md px-4 py-2.5 text-sm cursor-pointer transition-all ${
                    mode() === "ip"
                      ? "border-[#5e6ad2] bg-[#5e6ad2]/10 text-zinc-100"
                      : "border-[#222426] text-zinc-400 hover:border-zinc-600"
                  }`}
                >
                  IP Only (Self-signed)
                </button>
              </div>
            </div>

            <Show when={mode() === "domain"}>
              <div class="space-y-2">
                <label for="domain" class="text-sm font-medium text-zinc-300 block">
                  Domain Name
                </label>
                <input
                  id="domain"
                  type="text"
                  value={domain()}
                  onInput={(e) => setDomain(e.currentTarget.value)}
                  placeholder="example.com"
                  required
                  class="bg-[#08090a] border border-[#222426] rounded-md px-3 py-2.5 text-sm text-zinc-100 placeholder:text-zinc-600 focus:outline-none focus:border-[#5e6ad2] transition-colors w-full"
                />
              </div>
            </Show>

            <button
              type="submit"
              disabled={loading()}
              class="w-full bg-[#5e6ad2] hover:bg-[#6b76d9] text-white rounded-md px-4 py-2.5 text-sm font-medium transition-all disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {loading() ? "Configuring..." : "Configure SSL"}
            </button>
          </form>
        </div>
      </div>
    </div>
  );
};

export default SSLSetupPage;
