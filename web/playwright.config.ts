import { defineConfig, devices } from '@playwright/test';

// Run through scripts/run-web.sh <module>: it loads .env and sets MODULE.
export default defineConfig({
  testDir: './tests',
  forbidOnly: !!process.env.CI,
  retries: 0, // a flaky test is a defect: stability is proven by scripts/stable.sh, not hidden by retries
  reporter: [['list'], ['junit', { outputFile: `../reports/web-${process.env.MODULE || 'all'}.xml` }]],
  use: {
    baseURL: process.env.BASE_URL,
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
  },
  projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'] } }],
});
