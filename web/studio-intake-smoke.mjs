// TestHive Studio intake click-through: home, readiness, Sources (upload through the file picker), masking panel, Project page.
// Run by demo/phase2c/run.sh --check (after its API walkthrough) when the web tools are installed.
// Usage: node web/studio-intake-smoke.mjs <studio-url> <out-dir> <file-to-upload>
import { chromium } from '@playwright/test';
import fs from 'node:fs';

const [url, out, file] = process.argv.slice(2);
if (!url || !out || !file) { console.log('Usage: node web/studio-intake-smoke.mjs <studio-url> <out-dir> <file-to-upload>'); process.exit(1); }
fs.mkdirSync(out, { recursive: true });
const channel = process.env.TH_BROWSER_CHANNEL || (process.platform === 'win32' ? 'msedge' : 'chromium');
let browser;
try { browser = await chromium.launch(channel === 'chromium' ? {} : { channel }); }
catch (e) { console.log(`UI smoke test skipped: could not start the browser (${channel}).`); process.exit(0); }
const page = await browser.newPage({ viewport: { width: 1366, height: 860 }, colorScheme: 'light' });
await page.addInitScript(() => { try { localStorage.setItem('th-name', 'Sara (QA lead)'); } catch {} });
const errors = [];
page.on('pageerror', e => errors.push(e.message));
const shot = async name => page.screenshot({ path: `${out}/${name}.png` });
const check = async (text, fn) => { try { await fn(); console.log('  ok    ' + text); } catch (e) { errors.push(`${text}: ${e.message.split('\n')[0]}`); console.log('  WRONG ' + text); } };

await page.goto(url);
if (process.argv.includes('--welcome')) {  // before setup: the first-opening screen only
  await check('first opening shows the project setup form (and no name pop-up)', async () => {
    await page.getByRole('heading', { name: 'Welcome to TestHive' }).waitFor();
    if (await page.locator('.modal').count()) throw new Error('name pop-up shown over the setup form'); });
  await shot('0-welcome'); await browser.close();
  if (errors.length) { console.log('UI SMOKE FAIL\n- ' + errors.join('\n- ')); process.exit(1); }
  process.exit(0);
}
await check('home lists the module and the New module button', async () => { await page.getByRole('button', { name: 'New module', exact: true }).waitFor(); await page.locator('.module-card').first().waitFor(); await page.locator('#mods [data-side]').first().waitFor(); });
await shot('1-home');
await page.locator('.module-card').first().click();
await check('the module opens on its readiness card and Sources tab', async () => { await page.getByRole('button', { name: /^Ready for automation/ }).waitFor(); await page.getByText('Requirement documents').waitFor(); });
await page.locator('#files').setInputFiles(file);
await check('a file chosen in the file picker is uploaded and shown as not read yet', async () => { await page.getByText('not read yet').first().waitFor(); });
await shot('2-sources-uploaded');
await page.getByRole('button', { name: /Read the documents/ }).click();
await check('Read the documents reads it', async () => { await page.getByText(/INGESTED \d+ sources/).waitFor({ timeout: 60000 }); });
await page.getByText('Personal data', { exact: true }).click();
await page.getByRole('button', { name: 'Check the documents' }).click();
await check('the personal-data check lists what masking would hide', async () => { await page.getByText(/Names TestHive is not sure about/).waitFor(); });
await shot('3-masking');
const doc = file.split(/[\\/]/).pop(), row = () => page.locator('tbody tr').filter({ hasText: doc }).filter({ has: page.locator('[data-rm]') });
const dlg = page.getByRole('dialog');
await check('Remove asks in the page and takes the document out of the list', async () => {
  await row().getByRole('button', { name: 'Remove' }).click(); await dlg.getByRole('button', { name: 'Remove' }).click();
  await row().waitFor({ state: 'detached' }); });
await check('Earlier versions shows it as removed, and Restore brings it back', async () => {
  await page.getByText('Earlier versions and removed documents').click(); await page.getByText('removed', { exact: true }).first().waitFor();
  await shot('3b-versions'); await page.locator('[data-restore]').first().click(); await dlg.getByRole('button', { name: 'Restore' }).click(); await row().waitFor(); });
const mod = (await page.locator('#main h1').first().textContent()).trim().split(/\s/)[0];
await check('Archive needs the module code typed, then moves the module to Archived modules', async () => {
  await page.getByText('Archive this module').click(); await page.getByRole('button', { name: /^Archive / }).click();
  if (!(await dlg.getByRole('button', { name: 'Continue' }).isDisabled())) throw new Error('Continue enabled before the code is typed');
  await dlg.locator('input').fill(mod); await dlg.getByRole('button', { name: 'Continue' }).click();
  await dlg.locator('input').fill('Smoke test: archive and restore'); await dlg.getByRole('button', { name: `Archive ${mod}` }).click();
  await page.getByText(/^Archived modules \(1\)/).waitFor(); });
await check('Restore from the start page brings the module back', async () => {
  await page.getByText(/^Archived modules/).click(); await shot('3c-archived'); await page.locator('[data-unarch]').click();
  await dlg.getByRole('button', { name: 'Restore' }).click(); await page.locator('.module-card').first().waitFor();
  if (await page.getByText(/^Archived modules/).count()) throw new Error('still listed as archived'); });
await page.getByRole('button', { name: 'Project' }).click();
await check('the Project page shows the saved facts', async () => { await page.getByRole('heading', { name: 'Project details' }).waitFor();
  if ((await page.locator('#p-project').inputValue()) !== 'Nakhla Rewards') throw new Error('project name not shown'); });
await shot('4-project');
await page.getByRole('button', { name: 'Cancel' }).click();
await page.getByRole('button', { name: 'New module', exact: true }).click();
await check('the New module form opens', async () => { await page.getByRole('heading', { name: 'New module' }).waitFor(); });
await shot('5-new-module');
await browser.close();
if (errors.length) { console.log('UI SMOKE FAIL\n- ' + errors.join('\n- ')); process.exit(1); }
console.log(`UI SMOKE PASS (screenshots in ${out})`);
