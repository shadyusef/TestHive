// TestHive Studio Run-button click-through: press Run under Next, confirm, watch the live job panel, see the result.
// Run by demo/phase2d/run.sh --check (recorded agents) when the web tools are installed.
// Usage: node web/studio-run-smoke.mjs <studio-url> <out-dir>
import { chromium } from '@playwright/test';
import fs from 'node:fs';

const [url, out] = process.argv.slice(2);
if (!url || !out) { console.log('Usage: node web/studio-run-smoke.mjs <studio-url> <out-dir>'); process.exit(1); }
fs.mkdirSync(out, { recursive: true });
const channel = process.env.TH_BROWSER_CHANNEL || (process.platform === 'win32' ? 'msedge' : 'chromium');
let browser;
try { browser = await chromium.launch(channel === 'chromium' ? {} : { channel }); }
catch (e) { console.log(`UI smoke test skipped: could not start the browser (${channel}).`); process.exit(0); }
const page = await browser.newPage({ viewport: { width: 1366, height: 860 }, colorScheme: 'light' });
await page.addInitScript(() => { try { localStorage.setItem('th-name', 'Sara (QA lead)'); } catch {} });
const errors = [];
page.on('pageerror', e => errors.push(e.message));
page.on('dialog', d => { errors.push(`a browser pop-up appeared: ${d.message().slice(0, 60)}`); d.dismiss(); });  // Studio asks in the page
const shot = async name => page.screenshot({ path: `${out}/${name}.png` });
const check = async (text, fn) => { try { await fn(); console.log('  ok    ' + text); } catch (e) { errors.push(`${text}: ${e.message.split('\n')[0]}`); console.log('  WRONG ' + text); } };

await page.goto(url);
await page.locator('.module-card').first().click();
await check('Next shows a Run button for the analyst', async () => { await page.getByRole('button', { name: /^Run: Business analyst/ }).waitFor(); });
await shot('1-run-button');
await check('the module has its own address, and a refresh stays on it', async () => {
  await page.waitForURL(/#\/SIGNUP\//); await page.reload(); await page.getByRole('button', { name: /^Run: Business analyst/ }).waitFor(); });
await check('Sources: a document shows the text TestHive read from it', async () => {
  await page.getByRole('tab', { name: 'Sources' }).click(); await page.getByRole('button', { name: 'Text' }).first().click();
  await page.getByRole('dialog').locator('pre').waitFor(); await shot('1b-document-text'); await page.getByRole('dialog').getByRole('button', { name: 'Close' }).click(); });
await page.getByRole('button', { name: /^Run: Business analyst/ }).click();
await check('Run asks in the page and says the run is recorded', async () => {
  const dlg = page.getByRole('dialog'); await dlg.getByText(/recorded run/).waitFor(); await dlg.getByRole('button', { name: 'Run' }).click(); });
await check('the job panel shows the agent at work, with its steps and a Stop button', async () => {
  await page.getByText(/is working…/).first().waitFor(); await page.getByRole('button', { name: 'Stop' }).waitFor(); });
await page.locator('#jobcard pre').filter({ hasText: '$ bash scripts' }).waitFor({ timeout: 15000 }).catch(() => {});
await shot('2-job-running');
await check('when the agent finishes, its questions appear and Next moves on', async () => {
  await page.getByRole('button', { name: 'Stop' }).waitFor({ state: 'detached', timeout: 60000 });
  await page.getByText(/questions are open/).first().waitFor({ timeout: 15000 }); });
await check('a requirement ID opens the requirement, its questions and its cases', async () => {
  await page.getByRole('tab', { name: /^Analysis/ }).click();
  await page.locator('[data-req]').first().click(); await page.getByRole('dialog').getByText(/^Questions \(/).waitFor();
  await shot('2b-requirement'); await page.keyboard.press('Escape'); });
await page.getByRole('tab', { name: 'Activity' }).click();
await page.getByRole('button', { name: 'Log' }).first().click();
await check('Activity lists the run and shows its log', async () => { await page.getByText('Task: Module SIGNUP').waitFor(); });
await shot('3-activity');
await browser.close();
if (errors.length) { console.log('UI SMOKE FAIL\n- ' + errors.join('\n- ')); process.exit(1); }
console.log(`UI SMOKE PASS (screenshots in ${out})`);
