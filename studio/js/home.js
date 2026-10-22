// The start page (modules, archived modules), project setup and a new module.
import { store, S, $, esc, api, toast, me, askName, ask, pipeline, nextBox } from './core.js';
import { setHash, openModule, updateSavebar } from './module.js';

export async function home() {
  S.view = 'home'; S.module = null; S.dirty = {}; updateSavebar(); setHash(true);
  const [d, arch] = await Promise.all([api('/api/overview'), api('/api/archive')]);
  if (d.status !== 200) return $('#main').innerHTML = `<div class="msg bad">${esc(d.error || 'Studio could not load. Open the address printed in the Studio window.')}</div>`;
  S.agents = d.agents;
  $('#project').textContent = d.setup.setup_needed ? '' : d.project;
  if (d.setup.setup_needed) return renderSetup(d.setup, true);
  $('#main').innerHTML = `${d.setup.incomplete ? `<div class="msg warn">Some project details are missing (app name, platforms). <span class="crumb" id="fix">Complete them</span></div>` : ''}
    <div class="bar"><h2 style="margin:0;flex:1">Modules</h2><button class="primary" id="newmod">New module</button></div>
    ${d.modules.length ? `<div class="cards">${d.modules.map(m => `<div class="card module-card" data-mod="${esc(m.module)}">
      <h2>${esc(m.module)}</h2>${pipeline(m.stages)}
      <p class="small muted">${m.open_gaps} open questions · ${m.cases} active test cases</p>${nextBox(m.next, m.job)}</div>`).join('')}</div>`
    : `<div class="card"><h2 style="margin-top:0">Start with your first module</h2><p>A module is one part of the product, tested on its own: sign-up, login, checkout… Add it, then give TestHive its requirement documents or the address of the built product.</p></div>`}
    ${(arch.archived || []).length ? `<details class="card" style="margin-top:14px"><summary><b>Archived modules (${arch.archived.length})</b> <span class="small muted">kept in the archive folder; restore puts everything back</span></summary>
      <div class="table-wrap" style="margin-top:10px"><table><thead><tr><th>Module</th><th>Archived (UTC)</th><th>By</th><th>Why</th><th>Kept</th><th></th></tr></thead><tbody>
      ${arch.archived.map(a => `<tr><td><b>${esc(a.module)}</b></td><td class="small">${esc(a.archived_at.replace('T', ' ').slice(0, 16))}</td><td>${esc(a.by)}</td><td dir="auto">${esc(a.why)}</td>
        <td class="small">${a.files} files or folders, ${a.rows} register rows</td><td><button class="small" data-unarch="${esc(a.name)}">Restore</button></td></tr>`).join('')}
      </tbody></table></div></details>` : ''}`;
  $('#newmod').onclick = renderNewModule;
  document.querySelectorAll('[data-unarch]').forEach(b => b.onclick = async e => {
    e.stopPropagation(); if (!me()) return askName();
    if (!await ask(`Restore ${b.dataset.unarch.replace(/-\d{8}-\d{6}$/, '')} from the archive? Its files and register rows go back where they were.`, { ok: 'Restore' })) return;
    const r = await api('/api/module-restore', { method: 'POST', body: JSON.stringify({ archive: b.dataset.unarch, by: me() }) });
    toast(r.message || r.error, r.ok ? 'ok' : 'bad'); home();
  });
  if (!me() && !document.querySelector('.modal')) askName();  // first opening asks the name in the setup form instead
  if ($('#fix')) $('#fix').onclick = () => renderSetup(d.setup, false);
  document.querySelectorAll('[data-mod]').forEach(el => el.onclick = e => { if (!e.target.closest('[data-copy],[data-run]')) openModule(el.dataset.mod); });
}

/* ---------- Project setup (first opening) ---------- */
export function renderSetup(p, first) {
  S.view = 'setup'; updateSavebar();
  const plat = ['Web', 'API', 'Android', 'iOS'];
  $('#main').innerHTML = `<div class="card" style="max-width:760px">
    <h2 style="margin-top:0">${first ? 'Welcome to TestHive' : 'Project details'}</h2>
    <p class="muted">${first ? 'Tell TestHive about the product you are testing. You can change this later (Project, top right).' : 'These facts are shared with the agents (CONTEXT.md).'}</p>
    <div class="form">
      <label>Project name</label><input id="p-project" dir="auto" value="${esc(p.project)}" placeholder="Nakhla Rewards">
      <label>App name</label><input id="p-app" dir="auto" value="${esc(p.app)}" placeholder="Nakhla">
      <label>Platforms</label><span>${plat.map(x => `<label style="margin-inline-end:14px"><input type="checkbox" class="p-plat" value="${x}" ${p.platforms.includes(x) ? 'checked' : ''}> ${x}</label>`).join('')}</span>
      <label>Environment name</label><input id="p-env" value="${esc(p.test_env)}" placeholder="staging">
      <label>Web address</label><input id="p-web" value="${esc(p.base_url)}" placeholder="https://staging.example.com">
      <label>API address</label><input id="p-api" value="${esc(p.api_url)}" placeholder="https://api.staging.example.com">
      <label>Android package</label><input id="p-appid" value="${esc(p.app_id)}" placeholder="com.company.app (optional)">
      <label>Your name</label><input id="p-me" value="${esc(me())}" placeholder="Sara (QA lead)">
      <span></span><span class="small muted">Passwords and tokens are never typed here: add them to the .env file yourself when a test needs them.</span>
      <span></span><span><button class="primary" id="p-save">${first ? 'Create project' : 'Save'}</button> ${first ? '' : '<button id="p-cancel">Cancel</button>'}</span>
    </div></div>`;
  if ($('#p-cancel')) $('#p-cancel').onclick = home;
  $('#p-save').onclick = async () => {
    const name = $('#p-me').value.trim(); if (!name) return toast('Enter your name: it signs your decisions.', 'warn');
    store.set('th-name', name); $('#who').textContent = name;
    const r = await api('/api/project', { method: 'POST', body: JSON.stringify({ project: $('#p-project').value, app: $('#p-app').value,
      platforms: [...document.querySelectorAll('.p-plat:checked')].map(x => x.value), test_env: $('#p-env').value.trim(), base_url: $('#p-web').value.trim(),
      api_url: $('#p-api').value.trim(), app_id: $('#p-appid').value.trim() }) });
    toast(r.message || r.error, r.ok ? 'ok' : 'bad'); if (r.ok) home();
  };
}

/* ---------- New module ---------- */
export function renderNewModule() {
  S.view = 'newmodule'; updateSavebar();
  $('#main').innerHTML = `<p class="small"><span class="crumb" id="back">All modules</span> › New module</p><div class="card" style="max-width:760px">
    <h2 style="margin-top:0">New module</h2><div class="form">
      <label>Module code</label><input id="m-code" placeholder="SIGNUP" style="text-transform:uppercase">
      <label>Title</label><input id="m-title" dir="auto" placeholder="Sign-up and mobile verification">
      <label>Built product (optional)</label><input id="m-url" placeholder="https://staging.example.com/signup">
      <span></span><label><input type="checkbox" id="m-test" aria-label="This address is a test environment"> This address is a test environment (the analyst may submit forms with test data)</label>
      <span></span><label><input type="checkbox" id="m-mask" aria-label="Mask personal data"> The documents contain personal data: mask it before the AI reads them</label>
      <span></span><span><button class="primary" id="m-save">Add module</button> <span class="small muted">Next: add the documents (and an APK if you have one).</span></span>
    </div></div>`;
  $('#back').onclick = home;
  $('#m-save').onclick = async () => {
    const r = await api('/api/module-new', { method: 'POST', body: JSON.stringify({ module: $('#m-code').value.trim().toUpperCase(), title: $('#m-title').value,
      url: $('#m-url').value.trim(), test_env: $('#m-test').checked, mask: $('#m-mask').checked }) });
    toast(r.message || r.error, r.ok ? 'ok' : 'bad'); if (r.ok) { S.tab = 'sources'; openModule(r.module, true); }
  };
}
