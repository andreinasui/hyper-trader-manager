import { defineConfig } from "@solidjs/start/config";
import { fileURLToPath } from "node:url";
import { dirname, resolve } from "node:path";
import tailwindcss from "@tailwindcss/vite";
import packageJson from "./package.json";

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

const apiTarget = process.env.API_URL || "http://localhost:8000";

export default defineConfig({
  // SSR disabled: this is an auth-gated dashboard with no SEO needs, and SSR
  // caused hydration races where the AuthGuard <Show> gate delayed Router
  // mount, so the first client navigate() after Router-mount was dropped
  // (URL updated, route component never committed → blank until refresh).
  ssr: false,
  server: {
    preset: "node-server",
    routeRules: {
      "/api/**": {
        proxy: { to: `${apiTarget}/api/**` }
      }
    }
  },
  vite: {
    plugins: [tailwindcss()],
    define: {
      __APP_VERSION__: JSON.stringify(packageJson.version),
    },
    resolve: {
      alias: {
        "~": resolve(__dirname, "src")
      }
    }
  }
});
