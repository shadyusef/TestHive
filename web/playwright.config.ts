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
  // Windows uses the installed Microsoft Edge (no browser download); elsewhere Playwright's Chromium. TH_BROWSER_CHANNEL overrides.
  projects: [{ name: 'browser', use: { ...devices['Desktop Chrome'], channel: process.env.TH_BROWSER_CHANNEL || (process.platform === 'win32' ? 'msedge' : undefined) } }],
});
