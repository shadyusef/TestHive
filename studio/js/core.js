// Shared by every screen: the access key, state, API calls, dialogs, labels and small helpers.

// The access key arrives in the address; it is kept for this tab only and taken out of the address bar and history.
export const TOKEN = (() => { let t = new URLSearchParams(location.search).get('t') || '';
  try { if (t) sessionStorage.setItem('th-token', t); else t = sessionStorage.getItem('th-token') || ''; } catch {}
  if (location.search) history.replaceState(null, '', location.pathname + location.hash);
  return t; })();
export const store = { get(k) { try { return localStorage.getItem(k); } catch { return null; } }, set(k, v) { try { localStorage.setItem(k, v); } catch {} } };
export const STAGE_LABEL = { analysis: 'Analysis', design: 'Design', tools: 'Tools', automation: 'Automation', execution: 'Execution', reporting: 'Reporting' };
export const STATUS_LABEL = { approved: 'approved', awaiting_approval: 'waiting for you', in_progress: 'in progress', pending: 'not started' };
export const S = { view: 'home', module: null, tab: 'sources', dtab: 'cases', data: null, dirty: {}, open: new Set(), filters: {}, agents: 'live' };
export const $ = s => document.querySelector(s);
export const esc = v => String(v ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));

export async function api(path, opts = {}) {
  const r = await fetch(path, { ...opts, headers: { 'X-TestHive-Token': TOKEN, ...(opts.body && !(opts.body instanceof Blob) ? { 'Content-Type': 'application/json' } : {}), ...(opts.headers || {}) } });
  let body = {}; try { body = await r.json(); } catch {}
  return { status: r.status, ...body };
}
export function toast(text, kind = 'ok') {
  const d = document.createElement('div'); d.className = `msg ${kind} toast`; d.textContent = text; document.body.appendChild(d);
  setTimeout(() => d.remove(), kind === 'ok' ? 3500 : 9000);
}
export function me() { return store.get('th-name') || ''; }
export function showMe() { const n = me(); $('#whoname').textContent = n || 'Set your name'; $('#avatar').textContent = (n.trim()[0] || '?').toUpperCase(); }
export function askName(then) {
  const m = document.createElement('div'); m.className = 'modal';
  m.innerHTML = `<div class="card"><h3 style="margin-top:0">Who are you?</h3>
    <p class="muted small">Your name signs your answers, reviews and approvals (as in the approvals log). It stays in this browser.</p>
    <input id="nm" style="width:100%" placeholder="e.g. Sara (QA lead)" value="${esc(me())}">
    <p style="text-align:end;margin-bottom:0"><button class="primary" id="nmok">Continue</button></p></div>`;
  document.body.appendChild(m); const inp = m.querySelector('#nm'); inp.focus();
  const done = () => { const v = inp.value.trim(); if (!v) return inp.focus(); store.set('th-name', v); m.remove(); showMe(); then && then(); };
  m.querySelector('#nmok').onclick = done; inp.onkeydown = e => { if (e.key === 'Enter') done(); };
}
/* In-page confirmation (instead of the browser's confirm()): resolves to true, false, or the typed text when opts.input is set.
   opts: { ok: 'button text', danger: true, input: 'placeholder', match: 'text the input must equal' } */
export function ask(text, opts = {}) {
  return new Promise(resolve => {
    const m = document.createElement('div'); m.className = 'modal'; m.setAttribute('role', 'dialog'); m.setAttribute('aria-modal', 'true');
    m.innerHTML = `<div class="card"><p style="margin-top:0;white-space:pre-wrap" dir="auto">${esc(text)}</p>
      ${opts.input ? `<input id="ask-in" style="width:100%" placeholder="${esc(opts.input)}" aria-label="${esc(opts.input)}">` : ''}
      <p style="text-align:end;margin-bottom:0"><button id="ask-no">Cancel</button> <button id="ask-ok" class="${opts.danger ? 'danger' : 'primary'}">${esc(opts.ok || 'OK')}</button></p></div>`;
    document.body.appendChild(m);
    const inp = m.querySelector('#ask-in'), ok = m.querySelector('#ask-ok');
    const close = v => { m.remove(); document.removeEventListener('keydown', key); resolve(v); };
    const valid = () => !inp || (inp.value.trim() && (!opts.match || inp.value.trim().toUpperCase() === opts.match.toUpperCase()));
    const yes = () => { if (valid()) close(inp ? inp.value.trim() : true); else inp.focus(); };
    const key = e => { if (e.key === 'Escape') close(false); if (e.key === 'Enter' && document.activeElement?.tagName !== 'BUTTON') yes(); };
    if (inp) { ok.disabled = !valid(); inp.oninput = () => ok.disabled = !valid(); }
    ok.onclick = yes; m.querySelector('#ask-no').onclick = () => close(false);
    document.addEventListener('keydown', key); (inp || ok).focus();
  });
}
export function panel(title, html) {  // a wide read-only window: document text, requirement details
  const m = document.createElement('div'); m.className = 'modal'; m.setAttribute('role', 'dialog'); m.setAttribute('aria-modal', 'true');
  m.innerHTML = `<div class="card wide"><div class="bar"><h3 style="margin:0;flex:1" dir="auto">${esc(title)}</h3><button id="pn-x">Close</button></div>${html}</div>`;
  document.body.appendChild(m);
  const close = () => { m.remove(); document.removeEventListener('keydown', key); };
  const key = e => { if (e.key === 'Escape') close(); };
  m.querySelector('#pn-x').onclick = close; m.onclick = e => { if (e.target === m) close(); };
  document.addEventListener('keydown', key); m.querySelector('#pn-x').focus();
}
/* Requirement IDs become links that show the requirement, its questions and its cases. */
export const reqLinks = text => esc(text).replace(/REQ-[A-Z0-9]+-\d+/g, id => `<button class="req" data-req="${id}">${id}</button>`);
export const refs = cell => String(cell || '').split(/[;,]/).map(x => x.trim()).filter(Boolean);
export function setTheme(t) { if (t) document.documentElement.dataset.theme = t; else delete document.documentElement.dataset.theme; }
export const chip = (st, status) => `<span class="chip s-${status}" title="${esc(STAGE_LABEL[st])}: ${esc(STATUS_LABEL[status])}">${esc(STAGE_LABEL[st])} · ${esc(STATUS_LABEL[status])}</span>`;
export const pipeline = stages => `<div class="pipeline">${stages.map(s => chip(s.stage, s.status)).join('')}</div>`;
export const nextBox = (n, job) => `<div class="next"><b>Next:</b> ${esc(n.text)}
  ${job ? `<span class="chip s-in_progress">${esc(job)} is working…</span>` : n.run ? `<button class="primary" data-run="${esc(n.run)}" data-title="${esc(n.title)}" data-min="${esc(n.minutes)}">Run: ${esc(n.title)}</button>` : ''}
  ${n.command && !job ? `<span class="small muted">${n.run ? 'or in Claude Code:' : ''}</span> <code>${esc(n.command)}</code> <button class="small" data-copy="${esc(n.command)}">Copy</button>` : ''}</div>`;
export async function confirmLeave(go) {
  if (Object.keys(S.dirty).length && !await ask('You have unsaved changes. Leave without saving?', { ok: 'Leave', danger: true })) return false;
  S.dirty = {}; go(); return true;
}

/* The search and filter row above a table. fields: [name, label, options]; total: how many rows are shown. */
export function filterBar(key, fields, total) {
  const f = S.filters[key] = S.filters[key] || {};
  return `<div class="toolbar"><input type="search" class="search" placeholder="Search" aria-label="Search" data-f="${key}:q" value="${esc(f.q || '')}">${fields.map(([name, label, opts]) =>
    `<select data-f="${key}:${name}" aria-label="${esc(label)}"><option value="">${esc(label)}: all</option>${opts.map(o => `<option ${f[name] === o ? 'selected' : ''}>${esc(o)}</option>`).join('')}</select>`).join('')}
    <span class="grow"></span>${total === undefined ? '' : `<span class="total">${total} shown</span>`}</div>`;
}
export function bindFilters(rerender) {
  document.querySelectorAll('[data-f]').forEach(el => {
    const [key, name] = el.dataset.f.split(':');
    el.oninput = el.onchange = () => { S.filters[key][name] = el.value; rerender(); if (el.tagName === 'INPUT') { const again = document.querySelector(`[data-f="${key}:${name}"]`); again.focus(); again.setSelectionRange(el.value.length, el.value.length); } };
  });
}
export const matches = (row, f, cols) => (!f.q || cols.some(c => String(row[c] || '').toLowerCase().includes(f.q.toLowerCase())));

/* A summary strip: one row of figures split by thin rules. cells: { label, value, of, bar, sub } (sub is HTML, escape it first). */
export const strip = cells => `<div class="strip">${cells.map(c => `<div class="cell"><div class="l">${esc(c.label)}</div>
  <div class="val">${esc(c.value)}${c.of === undefined ? '' : `<small>/ ${esc(c.of)}</small>`}</div>${c.bar ? sbar(c.bar) : ''}${c.sub ? `<div class="sub">${c.sub}</div>` : ''}</div>`).join('')}</div>`;
/* A split bar with its legend. parts: [count, colour, label]. */
export function sbar(parts) {
  return `<div class="sbar" role="img" aria-label="${esc(parts.map(p => `${p[0]} ${p[2]}`).join(', '))}">${parts.filter(p => p[0]).map(p => `<i style="flex:${p[0]};background:${p[1]}"></i>`).join('')}</div>
    <div class="legend">${parts.map(p => `<span><i class="sw" style="background:${p[1]}"></i><b>${p[0]}</b> ${esc(p[2])}</span>`).join('')}</div>`;
}
/* Sub-tabs inside a tab. items: [key, label, extra HTML]; the chosen key is in S[stateKey]. */
export const subtabs = (stateKey, items) => `<div class="subtabs" role="tablist">${items.map(([k, l, x]) =>
  `<button role="tab" data-sub="${stateKey}:${k}" aria-selected="${S[stateKey] === k}" class="${S[stateKey] === k ? 'on' : ''}">${esc(l)}${x || ''}</button>`).join('')}</div>`;
