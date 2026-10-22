// A module's page: the header, the tabs, agent jobs, and saving (afterSave) for every tab.
import { S, $, esc, api, toast, ask, panel, STAGE_LABEL, confirmLeave } from './core.js';
import { home } from './home.js';
import { renderSide, setCrumbs } from './shell.js';
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
  render(); setHash(push); renderSide();
}
export const TABS = [['sources', 'Sources'], ['analysis', 'Analysis'], ['design', 'Design'], ['approvals', 'Approvals'], ['activity', 'Activity']];
let POLL = null;
export function jobCard(j) {
  if (!j) return '';
  const secs = Math.max(0, Math.round((Date.now() - Date.parse(j.started)) / 1000));
  return `<div class="jobcard" id="jobcard"><div class="bar"><span class="pulse" aria-hidden="true"></span><b class="grow">${esc(j.title)} is working… <span class="muted small">${Math.floor(secs / 60)} min ${secs % 60} s</span></b>
    <button class="danger" id="jobstop" data-id="${esc(j.id)}">Stop</button></div>
    <pre class="log">${esc((j.lines || []).join('\n')) || 'Starting…'}</pre>
    <p class="small muted">Saving on this module is paused until it finishes. The full log is kept in runs/agents/.</p></div>`;
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
    <div class="table-wrap"><table class="list"><thead><tr><th>Started (UTC)</th><th>What</th><th>Status</th><th>Took</th><th class="wide">Result</th><th><span class="sr">Log</span></th></tr></thead><tbody>
    ${js.map(j => { const took = j.ended ? Math.round((Date.parse(j.ended) - Date.parse(j.started)) / 60000) : null;
      return `<tr><td class="small">${esc(j.started.replace('T', ' ').slice(0, 16))}</td><td>${esc(j.title)}</td>
        <td><span class="pill ${j.status === 'done' ? 'ok' : j.status === 'running' ? 'Medium' : 'High'}">${esc(j.status)}</span></td>
        <td class="small">${took === null ? '' : took + ' min'}${j.cost_usd ? ` · $${esc(j.cost_usd)}` : ''}</td><td class="small" dir="auto">${esc(j.summary)}</td>
        <td class="rowacts"><button class="small" data-log="${esc(j.id)}">Log</button></td></tr>`; }).join('') || '<tr><td colspan="6" class="muted">Nothing run from Studio yet.</td></tr>'}
    </tbody></table></div><pre id="logview" class="log" hidden></pre>`;
  document.querySelectorAll('[data-log]').forEach(b => b.onclick = async () => {
    const r = await api('/api/job?id=' + encodeURIComponent(b.dataset.log));
    const v = $('#logview'); v.hidden = false; v.textContent = `${r.title} (${r.status})\nTask: ${r.task}\n\n${(r.lines || []).join('\n')}`;
  });
}
/* ---------- The module header: title, what to do next with its one action, and the stage track ---------- */
const PHASE = { tools: 3, automation: 4, execution: 5, reporting: 6 };  // stages built in later TestHive phases
const STAGE_TAB = { analysis: 'analysis', design: 'design' };
const day = iso => { const t = new Date(iso + 'T12:00:00'); return isNaN(t) ? iso : t.toLocaleDateString('en-GB', { day: 'numeric', month: 'short' }); };
function stageCell(s, now) {
  const v = s.status === 'approved' ? `Approved${s.by ? ' by ' + s.by : ''}${s.at ? ', ' + day(s.at) : ''}` : s.status === 'awaiting_approval' ? 'Waits for your approval'
    : s.status === 'in_progress' ? 'In progress' : PHASE[s.stage] ? `Comes in phase ${PHASE[s.stage]}` : 'Not started';
  const cls = s.status === 'approved' ? 'done' : s === now ? 'now' : 'later', tab = STAGE_TAB[s.stage];
  const inner = `<span class="k">${esc(STAGE_LABEL[s.stage])}</span><span class="v">${esc(v)}</span>`;
  return tab ? `<button class="stage ${cls}" data-goto="${tab}" ${s === now ? 'aria-current="step"' : ''}>${inner}</button>` : `<div class="stage ${cls}">${inner}</div>`;
}
function readyCell(r) {
  const done = r.items.filter(i => i.ok).length;
  return `<button class="ready" id="readybtn" aria-haspopup="dialog"><span class="k">Ready for automation</span>
    <span class="v">${r.ready ? 'Yes' : `${done} of ${r.items.length} approvals`}</span>
    <span class="pips" aria-hidden="true">${r.items.map(i => `<i class="${i.ok ? 'on' : ''}"></i>`).join('')}</span></button>`;
}
function showReadiness(r) {
  panel('Ready for automation', `<ul class="checks">${r.items.map(i => `<li class="${i.ok ? 'ok' : ''}"><b>${esc(i.label)}</b> <span class="muted small">${esc(i.detail)}</span></li>`).join('')}</ul>
    ${r.notes.length ? `<p class="small muted">${r.notes.map(esc).join(' · ')}</p>` : ''}`);
}
function headerActions(d) {
  const n = d.next, wait = d.stages.find(s => s.status === 'awaiting_approval');
  if (d.job) return '';
  if (n.run && S.agents !== 'review') return `<button class="primary" data-run="${esc(n.run)}" data-title="${esc(n.title)}" data-min="${esc(n.minutes)}">${esc(n.title)}</button>`;
  if (wait && S.tab !== 'approvals') return `<button class="primary" data-goto="approvals">Review and approve the ${esc(STAGE_LABEL[wait.stage].toLowerCase())}</button>`;
  return '';
}
function moduleHeader(d) {
  const now = d.stages.find(s => s.status !== 'approved'), n = d.next;
  return `<div class="titlerow"><div class="grow">
      <h1>${esc(d.module)}${d.meta.title ? ` <span dir="auto">${esc(d.meta.title)}</span>` : ''}</h1>
      <p class="finding" dir="auto">${d.job ? `<b>${esc(d.job.title)} is working.</b> ` : ''}${esc(n.text)}</p>
      ${n.command && !d.job ? `<p class="cmd small muted">${S.agents === 'review' ? 'Review mode: someone with Claude Code runs' : n.run ? 'Or in Claude Code:' : 'In Claude Code:'} <code>${esc(n.command)}</code> <button class="link" data-copy="${esc(n.command)}">Copy</button></p>` : ''}
    </div><div class="actions">${headerActions(d)}</div></div>
    <div class="track" aria-label="Stages">${d.stages.map(s => stageCell(s, now)).join('')}${readyCell(d.readiness)}</div>`;
}
function tabLabel(t, l, d) {
  const open = d.analysis.gaps.filter(g => g.Status === 'Open').length, cases = d.design.cases.filter(c => c.Status !== 'Removed').length;
  const extra = { sources: d.sources.files.length ? `<span class="c">${d.sources.files.length}</span>` : '',
    analysis: open ? `<span class="q">${open} open</span>` : '', design: cases ? `<span class="c">${cases}</span>` : '' }[t] || '';
  return `<button role="tab" data-tab="${t}" aria-selected="${S.tab === t}" class="${S.tab === t ? 'on' : ''}">${l}${extra}</button>`;
}
export function render() {
  const d = S.data;
  setCrumbs([['Modules', home], [d.module, () => { S.tab = 'sources'; openModule(d.module, true); }], [TABS.find(([t]) => t === S.tab)[1]]]);
  $('#main').innerHTML = `${moduleHeader(d)}${jobCard(d.job)}
    <div class="tabs" role="tablist" aria-label="${esc(d.module)}">${TABS.map(([t, l]) => tabLabel(t, l, d)).join('')}</div>
    <div id="tab" role="tabpanel"></div>`;
  const go = t => confirmLeave(() => { S.tab = t; S.dirty = {}; render(); setHash(false); });
  document.querySelectorAll('[data-tab]').forEach(b => b.onclick = () => go(b.dataset.tab));
  document.querySelectorAll('[data-goto]').forEach(b => b.onclick = () => go(b.dataset.goto));
  $('#readybtn').onclick = () => showReadiness(d.readiness);
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
