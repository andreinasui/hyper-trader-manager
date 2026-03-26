import { z } from 'zod';

const envSchema = z.object({
  VITE_API_URL: z.string().default('/api'),
});

// Parse environment variables
// Note: import.meta.env contains string values
export const config = envSchema.parse(import.meta.env);
