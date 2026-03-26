import { z } from 'zod';

const envSchema = z.object({
  VITE_API_URL: z.string().default('/api'),
  VITE_PRIVY_APP_ID: z.string().min(1).optional(), // Optional for now as it might be empty in dev
  MODE: z.enum(['development', 'production', 'test']).default('development'),
});

const _env = envSchema.safeParse(import.meta.env);

if (!_env.success) {
  console.error('❌ Invalid environment variables:', _env.error.format());
  // In production we might want to throw, but in dev we can just log
  if (import.meta.env.PROD) {
    throw new Error('Invalid environment variables');
  }
}

export const config = _env.success ? _env.data : envSchema.parse(import.meta.env);
