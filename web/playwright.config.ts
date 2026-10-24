import { defineConfig, devices } from '@playwright/test';

// A BrowserStack target (run-web.sh --target bs-...): the browser runs at BrowserStack, the tests here. The keys come from .env
// through run-web.sh and go only to BrowserStack's address (or a local stand-in on 127.0.0.1, as scripts/lib/targets.py allows).
function browserstack() {
  const ws = process.env.TH_BS_WS, caps = process.env.TH_BS_CAPS;
  if (!ws || !caps) return undefined;
  if (ws !== 'wss://cdp.browserstack.com/playwright' && !/^ws:\/\/127\.0\.0\.1:\d+\/?[\w/-]*$/.test(ws)) throw new Error('TH_BS_WS may only be BrowserStack or 127.0.0.1');
  const version: string = require('@playwright/test/package.json').version;  // BrowserStack matches its browsers to this
  const full = { ...JSON.parse(caps), 'browserstack.username': process.env.BROWSERSTACK_USERNAME || '', 'browserstack.accessKey': process.env.BROWSERSTACK_ACCESS_KEY || '',
    'client.playwrightVersion': version };
  return { wsEndpoint: `${ws}?caps=${encodeURIComponent(JSON.stringify(full))}` };
}
const remote = browserstack();

// Run through scripts/run-web.sh <module>: it loads .env and sets MODULE.
export default defineConfig({
  testDir: './tests',
  forbidOnly: !!process.env.CI,
  retries: 0, // a flaky test is a defect: stability is proven by scripts/stable.sh, not hidden by retries
  reporter: [['list'], ['junit', { outputFile: `../reports/web-${process.env.MODULE || 'all'}.xml` }]],
  use: {
    baseURL: process.env.BASE_URL,
    testIdAttribute: process.env.TEST_ID_ATTRIBUTE || 'data-qa', // getByTestId() finds data-qa="..." (the agents' locator rule)
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure', // the evidence of a failed test: its video, screenshot and trace (each step) are kept with the run
    ...(remote ? { connectOptions: remote } : {}),
  },
  // Windows uses the installed Microsoft Edge (no browser download); elsewhere Playwright's Chromium. TH_BROWSER_CHANNEL overrides.
  projects: [{ name: 'browser', use: remote  // at BrowserStack the browser type follows its caps; here the installed Edge (Windows) or Chrome, TH_BROWSER_CHANNEL overrides
    ? { ...devices['Desktop Chrome'], browserName: /webkit/.test(process.env.TH_BS_CAPS || '') ? 'webkit' : /firefox/.test(process.env.TH_BS_CAPS || '') ? 'firefox' : 'chromium' }
    : { ...devices['Desktop Chrome'], channel: process.env.TH_BROWSER_CHANNEL || (process.platform === 'win32' ? 'msedge' : undefined) } }],
});
