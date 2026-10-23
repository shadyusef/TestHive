// TestHive Studio project picker: Studio started outside any project shows "Open a project"; a wrong folder is refused,
// the project folder opens, and Switch project lists it as the recent one. Run by demo/phase2b/run.sh --check.
// Usage: node web/studio-projects-smoke.mjs <studio-url> <project-folder> <out-dir>
import { chromium } from '@playwright/test';
import fs from 'node:fs';

const [url, folder, out] = process.argv.slice(2);
if (!url || !folder || !out) { console.log('Usage: node web/studio-projects-smoke.mjs <studio-url> <project-folder> <out-dir>'); process.exit(1); }
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
const check = async (text, fn) => { try { await fn(); console.log('  ok    ' + text); } catch (e) { errors.push(`${text}: ${e.message.split('\n')[0]}`); console.log('  WRONG ' + text); await shot(`wrong-${errors.length}`).catch(() => {}); } };

await page.goto(url);
await check('with no project open, Studio asks for the project folder', async () => {
  await page.locator('#main h1', { hasText: 'Open a project' }).waitFor(); await page.getByText('No project open').waitFor(); });
await shot('p1-open-a-project');
await check('a folder that is not a TestHive project is refused', async () => {
  await page.getByLabel('Project folder path').fill(out); await page.getByRole('button', { name: 'Open', exact: true }).click();
  await page.getByText(/not a TestHive project/).waitFor(); });
await check('the project folder opens and shows its modules', async () => {
  await page.getByLabel('Project folder path').fill(folder); await page.getByLabel('Project folder path').press('Enter');
  await page.locator('.module-card').first().waitFor(); await page.locator('#main h1', { hasText: 'Modules' }).waitFor(); });
await shot('p2-opened');
await check('Switch project lists it as the project open now', async () => {
  await page.getByRole('button', { name: 'Switch project' }).click();
  await page.locator('#main h1', { hasText: 'Switch project' }).waitFor(); await page.locator('.proj').getByText('open now').waitFor(); });
await shot('p3-switch-project');
await page.setViewportSize({ width: 390, height: 844 }); await page.reload(); await page.locator('#main h1', { hasText: 'Modules' }).waitFor();
await page.getByRole('button', { name: /menu/i }).click().catch(() => page.locator('#menu').click()); await page.getByRole('button', { name: 'Switch project' }).click();
await page.locator('#main h1', { hasText: 'Switch project' }).waitFor(); await page.waitForTimeout(400);
await check('the picker fits a phone without sideways scrolling', async () => {
  if (await page.evaluate(() => document.documentElement.scrollWidth > innerWidth + 1)) throw new Error('page scrolls sideways'); });
await shot('p4-phone');
await browser.close();
if (errors.length) { console.log('PROJECT PICKER CHECK FAILED:\n  ' + errors.join('\n  ')); process.exit(1); }
console.log('PROJECT PICKER CHECK PASS');
