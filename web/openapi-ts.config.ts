import { defineConfig } from "@hey-api/openapi-ts";

export default defineConfig({
  client: "@hey-api/client-fetch",
  input: "./openapi.json",
  output: {
    path: "./src/lib/api/generated",
  },
  postProcess: ["prettier", "eslint"],
  plugins: [
    "@hey-api/schemas",
    "@hey-api/sdk",
    {
      name: "@hey-api/typescript",
      enums: "javascript",
    },
  ],
});
