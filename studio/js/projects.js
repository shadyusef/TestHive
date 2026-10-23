// Choosing the project folder: one Studio program serves any TestHive project (a clone of your team's project repository).
import { S, $, esc, api, toast } from './core.js';
import { renderSide, setCrumbs } from './shell.js';
import { home } from './home.js';
import { updateSavebar } from './module.js';

const base = p => p.split(/[\\/]/).filter(Boolean).pop() || p;

export async function renderProjects() {
  S.view = 'projects'; S.module = null; S.dirty = {}; updateSavebar();
  if (location.hash !== '#/') history.replaceState(null, '', '#/');
  const r = await api('/api/projects');
  if (r.status !== 200) return $('#main').innerHTML = `<div class="msg bad">${esc(r.error || 'Studio could not load. Open the address printed in the Studio window.')}</div>`;
  if (!r.current) { $('#project').textContent = 'No project open'; $('#mods').innerHTML = '<p class="s none">Open a project to see its modules.</p>'; $('#newmod-side').hidden = $('#projbtn').hidden = true; }
  setCrumbs(r.current ? [['Modules', home], ['Switch project']] : [['Open a project']]);
  $('#main').innerHTML = `<div class="formpage picker">
    <h1>${r.current ? 'Switch project' : 'Open a project'}</h1>
    <p class="finding">Studio works on one TestHive project folder at a time: your copy of the team's project repository on this PC.</p>
    ${r.current ? `<p class="small muted">Open now: <code>${esc(r.current)}</code></p>` : ''}
    ${r.recent.length ? `<section class="block"><div class="blockhead"><div class="grow"><h2>Recent projects</h2></div></div><div class="modlist">
      ${r.recent.map(p => `<div class="module-card proj" data-path="${esc(p)}"><div class="mc-name"><button class="link strong">${esc(base(p))}</button><span class="muted">${esc(p)}</span></div>
        <div class="mc-act">${p === r.current ? '<span class="small muted">open now</span>' : '<button class="small">Open</button>'}</div></div>`).join('')}</div></section>` : ''}
    <section class="block"><div class="blockhead"><div class="grow"><h2>Open a folder</h2>
      <p class="small muted">Paste the folder's full path, for example C:\\Projects\\my-project. In File Explorer: hold Shift, right-click the folder, Copy as path.</p>
      <p class="small muted">Open only a copy of your team's own project repository: the Run buttons start that folder's scripts and agents on this PC.</p></div></div>
      <div class="decide"><input id="pp" class="grow" placeholder="Folder path" aria-label="Project folder path" spellcheck="false" autocomplete="off"><button class="primary" id="ppgo">Open</button></div></section>
    <details class="fold"><summary><b>No project folder yet?</b> <span class="small muted">get your team's copy, or start a new one</span></summary>
      <p>Your team keeps each project in a git repository. Copy it to this PC once, then open its folder here:</p>
      <pre class="log">git clone &lt;your team's project repository&gt;</pre>
      <p class="small muted">A new project starts from the TestHive template repository the same way; the person who sets it up shares it with the team.</p></details></div>`;
  const open = async path => {
    const x = await api('/api/open-project', { method: 'POST', body: JSON.stringify({ path }) });
    toast(x.message || x.error, x.ok ? 'ok' : 'bad');
    if (x.ok) { S.data = null; home(); }
  };
  $('#ppgo').onclick = () => { const p = $('#pp').value.trim(); if (!p) return $('#pp').focus(); open(p); };
  $('#pp').onkeydown = e => { if (e.key === 'Enter') $('#ppgo').click(); };
  document.querySelectorAll('.proj').forEach(el => el.onclick = () => { if (el.dataset.path !== r.current) open(el.dataset.path); });
  if (r.current) renderSide();
}
