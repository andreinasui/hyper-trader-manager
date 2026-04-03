import { defineConfig } from "@solidjs/start/config";
import { fileURLToPath } from "node:url";
import { dirname, resolve } from "node:path";
import tailwindcss from "@tailwindcss/vite";

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

const apiTarget = process.env.API_URL || "http://localhost:8000";

export default defineConfig({
  ssr: true,
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
    resolve: {
      alias: {
        "~": resolve(__dirname, "src")
      }
    }
  }
});
