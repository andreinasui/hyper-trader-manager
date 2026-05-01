import { defineConfig, devices } from '@playwright/test';

/**
 * Playwright E2E Test Configuration
 *
 * Authentication is mocked by setting `auth_token` in localStorage
 * (see e2e/utils/auth-helpers.ts) and intercepting `/api/v1/auth/*`.
 * API responses are mocked via e2e/fixtures/api-handlers.ts for fast,
 * reliable tests with no real backend or external service dependencies.
 */
export default defineConfig({
  testDir: './e2e',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,

  // Test output
  reporter: process.env.CI ? 'github' : 'html',

  use: {
    baseURL: 'http://localhost:3000',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
  },

  // Test multiple browsers
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
    {
      name: 'firefox',
      use: { ...devices['Desktop Firefox'] },
    },
    {
      name: 'mobile',
      use: { ...devices['Pixel 7'] },
    },
    {
      name: 'tablet',
      // 820 x 1180 portrait, 2x DPR — iPad Air-ish form factor.
      // Reserved for manual smoke runs (`--project=tablet`); no specs target
      // it by default. Useful for verifying tablet container-query breakpoints
      // when the layout changes.
      use: {
        ...devices['Desktop Chrome'],
        viewport: { width: 820, height: 1180 },
        deviceScaleFactor: 2,
        isMobile: true,
        hasTouch: true,
      },
    },
    // WebKit requires system dependencies (libjpeg-turbo8) - disable for now
    // Uncomment when system dependencies are installed
    // {
    //   name: 'webkit',
    //   use: { ...devices['Desktop Safari'] },
    // },
  ],

  // Start dev server before tests
  webServer: {
    command: 'pnpm dev',
    url: 'http://localhost:3000',
    reuseExistingServer: !process.env.CI,
    timeout: 120000,
    env: {
      // Use relative API URL so requests go through the dev server proxy
      // This allows Playwright to intercept them at the browser level
      // DO NOT use http://localhost:8000 - it bypasses mocks!
      VITE_API_URL: '/api',
    },
  },
});
