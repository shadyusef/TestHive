// TestHive web exploration: visits a site and records what it does, for the business analyst.
// Run through scripts/explore-web.sh (it sets the output folder). Usage:
//   node web/explore.mjs <start-url> <out-dir> [--max-pages N] [--submit-valid]
// Per page: screenshot, title, headings, visible text, form fields with their HTML rules, buttons, links.
// Per form: submits it empty and with invalid values and records the messages shown (fields marked numeric get digits:
// '1' when valid, 'x' when invalid). With --submit-valid it also
// submits plausible valid values (this can create data: use a test environment only).
// Browser: Microsoft Edge on Windows (no download), Playwright's Chromium elsewhere; TH_BROWSER_CHANNEL=msedge|chrome|chromium overrides.
import { chromium } from '@playwright/test';
import fs from 'node:fs';
import path from 'node:path';

const args = process.argv.slice(2);
const start = args[0], out = args[1];
if (!start || !out) { console.log('Usage: node web/explore.mjs <start-url> <out-dir> [--max-pages N] [--submit-valid]'); process.exit(1); }
const maxPages = Number(args[args.indexOf('--max-pages') + 1]) || 10;
const submitValid = args.includes('--submit-valid');
fs.mkdirSync(out, { recursive: true });

const INVALID = { email: 'not-an-email', tel: '12', number: '-1', url: 'nota url', password: '1', text: 'a', date: '1900-01-01' };
const VALID = { email: 'qa.explorer@example.com', tel: '0551234567', number: '5', url: 'https://example.com', password: 'Passw0rd!2024', text: 'Test User', date: '1990-05-15' };

const channel = process.env.TH_BROWSER_CHANNEL || (process.platform === 'win32' ? 'msedge' : 'chromium');
let browser;
try { browser = await chromium.launch(channel === 'chromium' ? {} : { channel }); }
catch (e) { console.log(`Could not start the browser (${channel}). Install Microsoft Edge, or set TH_BROWSER_CHANNEL=chromium after: cd web && npx playwright install chromium\n${e.message.split('\n')[0]}`); process.exit(1); }
const page = await browser.newPage({ viewport: { width: 1280, height: 900 } });

const origin = u => { try { const x = new URL(u); return x.protocol === 'file:' ? path.dirname(x.pathname) : x.origin; } catch { return ''; } };
const home = origin(start);
const queue = [start], seen = new Set(), report = [];

async function snapshotForms() {
  return page.evaluate(() => {
    const label = el => {
      if (el.id) { const l = document.querySelector(`label[for="${el.id}"]`); if (l) return l.innerText.trim(); }
      const p = el.closest('label'); if (p) return p.innerText.trim();
      return el.getAttribute('aria-label') || el.getAttribute('placeholder') || el.name || el.id || '';
    };
    return [...document.forms].map((f, fi) => ({
      index: fi, novalidate: f.noValidate,
      action: f.getAttribute('action') || '', method: f.getAttribute('method') || 'get',
      fields: [...f.elements].filter(e => ['INPUT', 'SELECT', 'TEXTAREA'].includes(e.tagName) && e.type !== 'hidden' && e.type !== 'submit' && e.type !== 'button')
        .map(e => ({ tag: e.tagName.toLowerCase(), type: e.type, inputmode: e.getAttribute('inputmode'), name: e.name || e.id, label: label(e), required: e.required,
          minlength: e.getAttribute('minlength'), maxlength: e.getAttribute('maxlength'), pattern: e.getAttribute('pattern'),
          min: e.getAttribute('min'), max: e.getAttribute('max'), placeholder: e.getAttribute('placeholder'),
          options: e.tagName === 'SELECT' ? [...e.options].map(o => o.text) : undefined })),
      buttons: [...f.querySelectorAll('button, input[type=submit]')].map(b => (b.innerText || b.value || '').trim()),
    }));
  });
}

async function visibleMessages() {
  return page.evaluate(() => {
    const out = new Set();
    // browser validation bubbles are only shown when the form does not switch them off with novalidate
    for (const e of document.querySelectorAll('input, select, textarea'))
      if (e.validationMessage && !(e.form && e.form.noValidate)) out.add(`(browser) ${e.name || e.id}: ${e.validationMessage}`);
    for (const e of document.querySelectorAll('[role=alert], .error, .errors, .invalid-feedback, .message, .success, [aria-live]'))
      if (e.offsetParent !== null && e.innerText.trim()) out.add(e.innerText.trim());
    return [...out];
  });
}

async function tryForm(url, fi, mode) {
  await page.goto(url, { waitUntil: 'load' });
  const form = page.locator('form').nth(fi);
  const fields = await form.locator('input:not([type=hidden]):not([type=submit]):not([type=button]), textarea, select').all();
  for (const f of fields) {
    const type = (await f.getAttribute('type')) || 'text';
    const tag = await f.evaluate(e => e.tagName);
    if (mode === 'empty') continue;
    if (tag === 'SELECT') { if (mode === 'valid') await f.selectOption({ index: 1 }).catch(() => {}); continue; }
    if (type === 'checkbox' || type === 'radio') { if (mode === 'valid') await f.check().catch(() => {}); continue; }
    const numeric = (await f.getAttribute('inputmode')) === 'numeric';  // e.g. one-digit OTP boxes
    const value = numeric ? (mode === 'valid' ? '1' : 'x') : (mode === 'valid' ? VALID : INVALID)[type] ?? (mode === 'valid' ? VALID.text : INVALID.text);
    await f.fill(value).catch(() => {});
  }
  const before = page.url();
  const submit = form.locator('button[type=submit], input[type=submit], button:not([type])').first();
  if (await submit.count()) await submit.click({ timeout: 3000 }).catch(() => {}); else await form.evaluate(f => f.requestSubmit());
  await page.waitForTimeout(800);
  return { mode, navigated_to: page.url() !== before ? page.url() : null, messages: await visibleMessages() };
}

while (queue.length && seen.size < maxPages) {
  const url = queue.shift();
  if (seen.has(url)) continue;
  seen.add(url);
  try { await page.goto(url, { waitUntil: 'load', timeout: 30000 }); }
  catch (e) { report.push({ url, error: e.message.split('\n')[0] }); continue; }
  const n = String(seen.size).padStart(2, '0');
  const info = await page.evaluate(() => ({
    title: document.title,
    headings: [...document.querySelectorAll('h1, h2, h3')].map(h => h.innerText.trim()).filter(Boolean),
    text: document.body.innerText.replace(/\n{3,}/g, '\n\n').slice(0, 4000),
    links: [...document.querySelectorAll('a[href]')].map(a => a.href),
    lang: document.documentElement.lang, dir: document.documentElement.dir,
  }));
  await page.screenshot({ path: path.join(out, `${n}-page.png`), fullPage: true });
  const forms = await snapshotForms();
  for (const f of forms) {
    f.tries = [];
    for (const mode of ['empty', 'invalid'].concat(submitValid ? ['valid'] : [])) {
      const r = await tryForm(url, f.index, mode);
      await page.screenshot({ path: path.join(out, `${n}-form${f.index}-${mode}.png`), fullPage: true });
      f.tries.push(r);
      if (r.navigated_to && origin(r.navigated_to) === home && !seen.has(r.navigated_to)) queue.push(r.navigated_to);
    }
  }
  for (const l of info.links) if (origin(l) === home && !seen.has(l) && !l.includes('#')) queue.push(l);
  report.push({ n, url, ...info, links: undefined, forms });
}
await browser.close();

fs.writeFileSync(path.join(out, 'exploration.json'), JSON.stringify(report, null, 2));
const md = [`# Web exploration: ${start}`, `Explored ${new Date().toISOString().slice(0, 16)} with ${channel}. Pages: ${report.length}. Everything below is OBSERVED behaviour, not confirmed requirements.`,
  `Values tried per form: empty; invalid (e.g. "${INVALID.email}", "${INVALID.tel}", "${INVALID.password}", numeric boxes "x"); valid (e.g. "${VALID.text}", "${VALID.tel}", numeric boxes "1", first option, boxes ticked). A real valid code or password is not known to the explorer.`, ''];
for (const p of report) {
  if (p.error) { md.push(`## ${p.url}\nCould not open: ${p.error}\n`); continue; }
  md.push(`## Page ${p.n}: ${p.title || p.url}`, `- URL: ${p.url}`, `- Language: ${p.lang || '?'}, direction: ${p.dir || 'ltr'}`, `- Screenshot: ${p.n}-page.png`);
  if (p.headings.length) md.push(`- Headings: ${p.headings.join(' / ')}`);
  for (const f of p.forms) {
    md.push('', `### Form ${f.index} (${f.method.toUpperCase()} ${f.action || 'same page'}${f.novalidate ? ', browser validation off, so browser messages are not shown' : ''}) buttons: ${f.buttons.join(', ')}`, '| Field | Label | Type | Required | Rules |', '|---|---|---|---|---|');
    for (const x of f.fields) {
      const rules = ['minlength', 'maxlength', 'pattern', 'min', 'max'].filter(k => x[k]).map(k => `${k}=${x[k]}`).concat(x.options ? [`options: ${x.options.join(', ')}`] : []);
      md.push(`| ${x.name} | ${x.label} | ${x.type}${x.inputmode ? ' (' + x.inputmode + ')' : ''} | ${x.required ? 'yes' : 'no'} | ${rules.join('; ')} |`);
    }
    for (const t of f.tries) md.push(`- Submitted **${t.mode}**: ${t.messages.length ? t.messages.map(m => `"${m}"`).join('; ') : 'no message shown'}${t.navigated_to ? ` -> went to ${t.navigated_to}` : ''} (screenshot ${p.n}-form${f.index}-${t.mode}.png)`);
  }
  md.push('', '<details><summary>Visible text</summary>', '', '```', p.text, '```', '</details>', '');
}
fs.writeFileSync(path.join(out, 'exploration.md'), md.join('\n'));
console.log(`EXPLORED ${report.length} pages -> ${out.replace(/\\/g, '/')}/exploration.md (and screenshots)`);
