// TestHive Studio interface smoke test: clicks through the screens like a person and saves a screenshot of each.
// Run by demo/phase2b/run.sh --check when the web tools are installed. Usage: node web/studio-smoke.mjs <studio-url> <out-dir>
// Browser: Microsoft Edge on Windows (no download), Playwright's Chromium elsewhere; TH_BROWSER_CHANNEL overrides.
import { chromium } from '@playwright/test';
import fs from 'node:fs';

const [url, out] = process.argv.slice(2);
if (!url || !out) { console.log('Usage: node web/studio-smoke.mjs <studio-url> <out-dir>'); process.exit(1); }
fs.mkdirSync(out, { recursive: true });
const channel = process.env.TH_BROWSER_CHANNEL || (process.platform === 'win32' ? 'msedge' : 'chromium');
let browser;
try { browser = await chromium.launch(channel === 'chromium' ? {} : { channel }); }
catch (e) { console.log(`UI smoke test skipped: could not start the browser (${channel}).`); process.exit(0); }
const page = await browser.newPage({ viewport: { width: 1366, height: 860 }, colorScheme: 'light' });
await page.addInitScript(() => { try { localStorage.setItem('th-name', 'Sara (QA lead)'); } catch {} });
const errors = [];
page.on('pageerror', e => errors.push(e.message));
const shot = async name => page.screenshot({ path: `${out}/${name}.png`, fullPage: false });
const check = async (text, fn) => { try { await fn(); console.log('  ok    ' + text); } catch (e) { errors.push(`${text}: ${e.message.split('\n')[0]}`); console.log('  WRONG ' + text); } };

await page.goto(url);
await check('home shows the module with its stages', async () => { await page.getByText('Design · waiting for you').waitFor(); });
await shot('1-home');
await page.locator('.module-card').first().click();
await check('Analysis tab lists the open questions', async () => { await page.getByRole('columnheader', { name: 'Your answer' }).waitFor(); });
const box = page.locator('textarea[data-gap]').first();
await box.fill('Arabic and English; the accepted version is stored with the account.');
await check('typing an answer shows the save bar', async () => { await page.getByText('1 unsaved answer').waitFor(); });
await shot('2-analysis-answer');
await page.getByRole('button', { name: 'Save', exact: true }).click();
await check('the answer is saved', async () => { await page.getByText(/Saved: 1 answer/).waitFor(); });
await page.getByRole('tab', { name: /^Design/ }).click();
await check('Design tab lists the cases', async () => { await page.getByText('requirements covered').waitFor(); await page.locator('select[data-rev]').first().waitFor(); });
await page.locator('[data-open]').first().click();
await shot('3-design-cases');
await page.getByRole('button', { name: 'Coverage' }).click();
await check('Coverage shows every requirement', async () => { await page.getByRole('columnheader', { name: 'Boundary' }).waitFor(); });
await shot('4-design-coverage');
await page.getByRole('tab', { name: 'Approvals' }).click();
await check('Approvals shows the design ready with Approve enabled', async () => {
  await page.getByText('Ready for approval: every rule passes.').waitFor();
  if (await page.getByRole('button', { name: 'Approve', exact: true }).isDisabled()) throw new Error('Approve is disabled');
});
await shot('5-approvals');
await browser.close();
if (errors.length) { console.log('UI SMOKE FAIL\n- ' + errors.join('\n- ')); process.exit(1); }
console.log(`UI SMOKE PASS (screenshots in ${out})`);
