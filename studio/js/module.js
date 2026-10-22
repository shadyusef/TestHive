// A module's page: the header, the tabs, agent jobs, and saving (afterSave) for every tab.
import { S, $, esc, api, toast, ask, chip, pipeline, nextBox, confirmLeave } from './core.js';
import { home } from './home.js';
import { renderSources } from './sources.js';
import { renderAnalysis } from './analysis.js';
import { renderDesign } from './design.js';
import { renderApprovals } from './approvals.js';

/* ---------- Page address: #/MODULE/tab, so a refresh or a bookmark opens the same place ---------- */
export function setHash(push) {
  const h = S.view === 'module' ? `#/${S.module}/${S.tab}` : '#/';
  if ((location.hash || '#/') !== h) history[push ? 'pushState' : 'replaceState'](null, '', h);
}
export function route() {
  const [, mod, tab] = location.hash.match(/^#\/([A-Z][A-Z0-9]*)(?:\/([a-z]+))?/) || [];
  if (!mod) return home();
  if (TABS.some(([t]) => t === tab)) S.tab = tab;
  openModule(mod, TABS.some(([t]) => t === tab));
}

export async function openModule(mod, keepTab) {
  const d = await api('/api/module?m=' + encodeURIComponent(mod));
  if (d.status !== 200) { toast(d.error === 'unknown module' ? `There is no module ${mod} (it may be archived).` : d.error || 'Could not load the module', 'bad'); return home(); }
  const push = !(S.view === 'module' && S.module === mod);
  S.view = 'module'; S.module = mod; S.data = d; S.dirty = {}; S.agents = d.agents;
  if (!keepTab) { S.tab = d.stages[0].status === 'pending' ? 'sources' : 'analysis'; S.open.clear(); }
  render(); setHash(push);
}
export const TABS = [['sources', 'Sources'], ['analysis', 'Analysis (questions)'], ['design', 'Design (test cases)'], ['approvals', 'Approvals'], ['activity', 'Activity']];
let POLL = null;
export function jobCard(j) {
  if (!j) return '';
  const secs = Math.max(0, Math.round((Date.now() - Date.parse(j.started)) / 1000));
  return `<div class="card" id="jobcard" style="border-color:var(--accent)"><div class="bar" style="margin:0"><b style="flex:1">${esc(j.title)} is working… <span class="muted small">${Math.floor(secs / 60)} min ${secs % 60} s</span></b>
    <button class="danger" id="jobstop" data-id="${esc(j.id)}">Stop</button></div>
    <pre class="small" style="white-space:pre-wrap;max-height:260px;overflow:auto;background:var(--raised);padding:8px;border-radius:6px;margin:8px 0 0">${esc((j.lines || []).join('\n')) || 'Starting…'}</pre>
    <p class="small muted" style="margin:6px 0 0">Saving on this module is paused until it finishes. The full log is kept in runs/agents/.</p></div>`;
}
export function watchJob() {
  clearInterval(POLL);
  if (!S.data?.job) return;
  POLL = setInterval(async () => {
    if (S.view !== 'module') return clearInterval(POLL);
    const r = await api('/api/jobs?m=' + encodeURIComponent(S.module));
    if (r.job) { const c = $('#jobcard'); if (c) c.outerHTML = jobCard(r.job); bindStop(); return; }
    clearInterval(POLL);
    if (r.last) toast(`${r.last.title}: ${r.last.status}. ${r.last.summary || ''}`.slice(0, 400), r.last.status === 'done' ? 'ok' : 'bad');
    openModule(S.module, true);
  }, 2000);
}
export function bindStop() {
  const b = $('#jobstop'); if (!b) return;
  b.onclick = async () => {
    if (!await ask('Stop the agent now? Files it already wrote stay as they are; you can run it again later.', { ok: 'Stop', danger: true })) return;
    const r = await api('/api/stop', { method: 'POST', body: JSON.stringify({ module: S.module, id: b.dataset.id }) });
    toast(r.message || r.error, r.ok ? 'ok' : 'bad'); openModule(S.module, true);
  };
}
export function renderActivity() {
  const js = S.data.jobs;
  $('#tab').innerHTML = `<p class="small muted">Every agent run and exploration started from Studio, newest first. Runs started in Claude Code directly are not listed.</p>
    <div class="table-wrap"><table><thead><tr><th>Started (UTC)</th><th>What</th><th>Status</th><th>Took</th><th style="min-width:320px">Result</th><th></th></tr></thead><tbody>
    ${js.map(j => { const took = j.ended ? Math.round((Date.parse(j.ended) - Date.parse(j.started)) / 60000) : null;
      return `<tr><td class="small">${esc(j.started.replace('T', ' ').slice(0, 16))}</td><td>${esc(j.title)}</td>
        <td><span class="chip ${j.status === 'done' ? 's-approved' : j.status === 'running' ? 's-in_progress' : 'sev-High'}">${esc(j.status)}</span></td>
        <td class="small">${took === null ? '' : took + ' min'}${j.cost_usd ? ` · $${esc(j.cost_usd)}` : ''}</td><td class="small" dir="auto">${esc(j.summary)}</td>
        <td><button class="small" data-log="${esc(j.id)}">Log</button></td></tr>`; }).join('') || '<tr><td colspan="6" class="muted">Nothing run from Studio yet.</td></tr>'}
    </tbody></table></div><pre id="logview" class="small" style="white-space:pre-wrap;display:none;background:var(--raised);padding:8px;border-radius:6px;margin-top:10px"></pre>`;
  document.querySelectorAll('[data-log]').forEach(b => b.onclick = async () => {
    const r = await api('/api/job?id=' + encodeURIComponent(b.dataset.log));
    const v = $('#logview'); v.style.display = 'block'; v.textContent = `${r.title} (${r.status})\nTask: ${r.task}\n\n${(r.lines || []).join('\n')}`;
  });
}
export function readinessCard(r) {
  return `<details class="card" ${r.ready ? 'open' : ''}><summary><b>Ready for automation:</b> ${r.ready ? '<span class="chip s-approved">yes</span>' : `<span class="chip s-pending">not yet</span> <span class="small muted">${r.items.filter(i => i.ok).length} of ${r.items.length} approvals</span>`}</summary>
    <ul class="plain" style="margin-top:8px">${r.items.map(i => `<li>${i.ok ? '✓' : '○'} <b>${esc(i.label)}</b> <span class="muted small">${esc(i.detail)}</span></li>`).join('')}</ul>
    ${r.notes.length ? `<p class="small muted" style="margin-bottom:0">${r.notes.map(esc).join(' · ')}</p>` : ''}</details>`;
}
export function render() {
  const d = S.data;
  $('#main').innerHTML = `<p class="small"><span class="crumb" id="back">All modules</span> › ${esc(d.module)}</p>
    <div class="card"><h2 style="margin:0">${esc(d.module)} ${d.meta.title ? `<span class="muted" style="font-weight:400;font-size:15px">${esc(d.meta.title)}</span>` : ''}</h2>${pipeline(d.stages)}${nextBox(d.next, d.job && d.job.title)}</div>
    ${jobCard(d.job)}
    ${readinessCard(d.readiness)}
    <div class="tabs">${TABS.map(([t, l]) => `<button data-tab="${t}" class="${S.tab === t ? 'on' : ''}">${l}</button>`).join('')}</div>
    <div id="tab"></div>`;
  $('#back').onclick = () => confirmLeave(home);
  document.querySelectorAll('[data-tab]').forEach(b => b.onclick = () => confirmLeave(() => { S.tab = b.dataset.tab; S.dirty = {}; render(); setHash(false); }));
  ({ sources: renderSources, analysis: renderAnalysis, design: renderDesign, approvals: renderApprovals, activity: renderActivity })[S.tab]();
  updateSavebar(); bindStop(); watchJob();
}

/* ---------- saving ---------- */
export function bindUploads() {
  document.querySelectorAll('[data-upload]').forEach(inp => inp.onchange = async () => {
    const kind = inp.dataset.upload, file = inp.files[0]; if (!file) return;
    const ver = S.data[kind].version;
    const r = await api(`/api/upload?m=${encodeURIComponent(S.module)}&kind=${kind}&version=${ver}`, { method: 'POST', body: file, headers: { 'Content-Type': 'application/octet-stream' } });
    toast(r.message || r.error, r.ok ? 'ok' : 'bad'); if (r.ok) openModule(S.module, true);
  });
}
export async function afterSave(r) {
  if (r.status === 409) { toast(r.error, 'warn'); return openModule(S.module, true); }
  if (!r.ok) return toast('Not saved, nothing changed:\n' + (r.errors || [r.error]).join('\n'), 'bad');
  toast(r.message); S.dirty = {}; openModule(S.module, true);
}
export function updateSavebar() {
  const n = Object.keys(S.dirty).length, bar = $('#savebar');
  bar.classList.toggle('show', n > 0 && S.view === 'module');
  $('#savetext').textContent = `${n} unsaved ${S.tab === 'analysis' ? 'answer' : 'review'}${n === 1 ? '' : 's'}`;
}
