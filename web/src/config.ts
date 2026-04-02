import { z } from "zod";

const configSchema = z.object({
  VITE_API_URL: z.string().default("/api"),
});

export const config = configSchema.parse({
  VITE_API_URL: import.meta.env.VITE_API_URL,
});
