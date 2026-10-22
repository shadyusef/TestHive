// TestHive Studio, loaded by studio/index.html as a module. Plain JS, no libraries, no build step.
// All data comes from the JSON API (scripts/lib/studio.py); every save goes through the same rules as the Excel imports and stage.sh.
// The screens are in studio/js/: core (shared), home, module (header, tabs, saving), sources, analysis, design, approvals.
import { TOKEN, store, S, $, esc, api, toast, showMe, askName, ask, panel, refs, setTheme, confirmLeave } from './js/core.js';
import { setHash, route, openModule, render } from './js/module.js';
import { renderSetup } from './js/home.js';
import { bindShell } from './js/shell.js';
import { saveAnswers } from './js/analysis.js';
import { saveReview } from './js/design.js';

document.addEventListener('click', e => {
  const el = e.target.closest('[data-req]'); if (!el || !S.data) return;
  e.stopPropagation();
  const id = el.dataset.req, a = S.data.analysis, d = S.data.design;
  const r = a.requirements.find(x => x.ID === id) || (d.requirements || []).find(x => x.ID === id);
  if (!r) return toast(`${id} is not in the requirements of ${S.module}.`, 'warn');
  const qs = a.gaps.filter(g => refs(g.Requirement).includes(id)), cs = d.cases.filter(c => refs(c.Requirements).includes(id) && c.Status !== 'Removed');
  panel(`${id} · ${r.Priority} · ${r.Type}`, `<p dir="auto" style="font-size:15px">${esc(r.Text)}</p>
    <p class="small muted">Status ${esc(r.Status)} · from ${esc(r.Source)}${r.Section ? ', ' + esc(r.Section) : ''}${r.Notes ? ' · ' + esc(r.Notes) : ''}</p>
    <h4>Questions (${qs.length})</h4>${qs.length ? `<ul class="plain">${qs.map(g => `<li dir="auto"><b>${esc(g.ID)}</b> ${esc(g.Status)}: ${esc(g.Question)}${g.Answer ? ` <span class="muted">→ ${esc(g.Answer)}</span>` : ''}</li>`).join('')}</ul>` : '<p class="muted">None.</p>'}
    <h4>Test cases (${cs.length})</h4>${cs.length ? `<ul class="plain">${cs.map(c => `<li dir="auto"><b>${esc(c.ID)}</b> ${esc(c.Priority)} ${esc(c.Title)}</li>`).join('')}</ul>` : '<p class="muted">None yet.</p>'}`);
});
$('#theme').onclick = () => { const cur = document.documentElement.dataset.theme || (matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light');
  const t = cur === 'dark' ? 'light' : 'dark'; setTheme(t); store.set('th-theme', t); };
$('#who').onclick = () => askName();
setTheme(store.get('th-theme'));
document.addEventListener('click', async e => {
  const b = e.target.closest('[data-run]'); if (!b) return;
  e.stopPropagation();
  const mod = b.closest('[data-mod]')?.dataset.mod || S.module;
  const script = b.dataset.run === 'explore-web';
  const how = script ? `Opens the built product in a hidden browser and records what it shows (free, no AI). It usually takes ${b.dataset.min} minutes.`
    : S.agents === 'recorded' ? 'Replays a recorded run of the agent (demo: free, a few seconds).'
    : `Claude Code works in the background on this PC and uses your Claude plan. It usually takes ${b.dataset.min} minutes.`;
  if (!await ask(`${b.dataset.title} for ${mod}?\n\n${how} You can keep using Studio; saving on ${mod} pauses until it finishes, and you can stop it at any time.`, { ok: 'Run' })) return;
  const r = await api('/api/run', { method: 'POST', body: JSON.stringify({ module: mod, action: b.dataset.run }) });
  toast(r.message || r.error, r.ok ? 'ok' : 'bad');
  if (r.ok) { S.module = mod; S.tab = S.view === 'module' ? S.tab : 'activity'; openModule(mod, true); }
});
document.addEventListener('click', e => { const c = e.target.closest('[data-copy]'); if (c) { navigator.clipboard?.writeText(c.dataset.copy).then(() => toast('Copied. Paste it in Claude Code.')).catch(() => toast('Select the text and copy it.', 'warn')); } });
window.addEventListener('popstate', async () => {  // back / forward
  if (Object.keys(S.dirty).length && !await ask('You have unsaved changes. Leave without saving?', { ok: 'Leave', danger: true })) return setHash(true);
  S.dirty = {}; route();
});
$('#projbtn').onclick = async () => confirmLeave(async () => { const p = await api('/api/project'); if (p.status === 200) renderSetup(p, p.setup_needed); });
window.addEventListener('beforeunload', e => { if (Object.keys(S.dirty).length) { e.preventDefault(); e.returnValue = ''; } });
$('#save').onclick = () => S.tab === 'analysis' ? saveAnswers() : saveReview();
$('#discard').onclick = () => { S.dirty = {}; render(); };

showMe(); bindShell();
if (!TOKEN) $('#main').innerHTML = '<div class="msg bad">Open Studio with the address printed in its window (it contains an access key).</div>';
else route();
