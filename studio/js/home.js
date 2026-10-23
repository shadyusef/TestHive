// The start page (every module and what it waits for, archived modules), project setup and a new module.
import { store, S, $, esc, api, toast, me, showMe, askName, ask, STAGE_LABEL } from './core.js';
import { renderSide, setCrumbs, waits } from './shell.js';
import { setHash, openModule, updateSavebar } from './module.js';
import { renderProjects } from './projects.js';

/* The two stages TestHive has today, as a small track: done, now, or still to come. */
const miniTrack = stages => `<span class="minitrack" aria-hidden="true">${stages.slice(0, 2).map(s =>
  `<i class="${s.status === 'approved' ? 'done' : s.status === 'pending' ? '' : 'now'}" title="${esc(STAGE_LABEL[s.stage])}"></i>`).join('')}</span>`;

export async function home(opts = {}) {
  S.view = 'home'; S.module = null; S.dirty = {}; updateSavebar(); setHash(true);
  const [d, arch] = await Promise.all([api('/api/overview'), api('/api/archive')]);
  if (d.no_project) return renderProjects();
  if (d.status !== 200) return $('#main').innerHTML = `<div class="msg bad">${esc(d.error || 'Studio could not load. Open the address printed in the Studio window.')}</div>`;
  renderSide(d, arch); setCrumbs([['Modules']]);
  if (d.setup.setup_needed) return renderSetup(d.setup, true);
  const waiting = d.modules.filter(m => m.stages.some(s => s.status === 'awaiting_approval')).length;
  const archived = arch.archived || [];
  $('#main').innerHTML = `${d.setup.incomplete ? `<div class="msg warn">Some project details are missing (app name, platforms). <button class="link accent" id="fix">Complete them</button></div>` : ''}
    <div class="titlerow"><div class="grow"><h1>Modules</h1>
      <p class="finding">${d.modules.length ? `<b>${d.modules.length} module${d.modules.length === 1 ? '' : 's'}</b> in ${esc(d.project)}${waiting ? `; ${waiting} wait${waiting === 1 ? 's' : ''} for your approval` : ''}.` : 'A module is one part of the product, tested on its own: sign-up, login, checkout…'}</p></div>
      <div class="actions"><button class="primary" id="newmod">New module</button></div></div>
    ${d.modules.length ? `<div class="modlist">${d.modules.map(m => `<div class="module-card" data-mod="${esc(m.module)}">
        <div class="mc-name"><button class="link strong" data-open-mod="${esc(m.module)}">${esc(m.module)}</button>${m.title ? `<span class="muted" dir="auto">${esc(m.title)}</span>` : ''}</div>
        <div class="mc-state">${miniTrack(m.stages)}<span>${esc(waits(m))}</span></div>
        <div class="mc-counts small muted"><span><b>${m.open_gaps}</b> open questions</span><span><b>${m.cases}</b> active cases</span></div>
        <div class="mc-next small muted" dir="auto">${esc(m.next.text)}</div>
        <div class="mc-act">${m.job ? `<span class="small"><span class="pulse"></span> ${esc(m.job)} is working…</span>`
          : m.next.run && S.agents !== 'review' ? `<button class="primary small" data-run="${esc(m.next.run)}" data-title="${esc(m.next.title)}" data-min="${esc(m.next.minutes)}">${esc(m.next.title)}</button>` : `<button class="small" data-open-mod="${esc(m.module)}">Open</button>`}</div>
      </div>`).join('')}</div>`
    : `<div class="empty"><h2>Start with your first module</h2><p class="muted">Add it, then give TestHive its requirement documents or the address of the built product. The analyst turns them into requirements and questions; the manual tester then designs the test cases.</p></div>`}
    ${archived.length ? `<details class="fold" id="archived" ${opts.archived ? 'open' : ''}><summary><b>Archived modules (${archived.length})</b> <span class="small muted">kept in the archive folder; restore puts everything back</span></summary>
      <div class="table-wrap"><table class="list"><thead><tr><th>Module</th><th>Archived (UTC)</th><th>By</th><th class="wide">Why</th><th>Kept</th><th><span class="sr">Actions</span></th></tr></thead><tbody>
      ${archived.map(a => `<tr><td class="id">${esc(a.module)}</td><td class="small">${esc(a.archived_at.replace('T', ' ').slice(0, 16))}</td><td class="small">${esc(a.by)}</td><td dir="auto">${esc(a.why)}</td>
        <td class="small muted">${a.files} files or folders, ${a.rows} register rows</td><td class="rowacts"><button class="small" data-unarch="${esc(a.name)}">Restore</button></td></tr>`).join('')}
      </tbody></table></div></details>` : ''}`;
  $('#newmod').onclick = renderNewModule;
  if (opts.archived) $('#archived')?.scrollIntoView();
  document.querySelectorAll('[data-unarch]').forEach(b => b.onclick = async e => {
    e.stopPropagation(); if (!me()) return askName();
    if (!await ask(`Restore ${b.dataset.unarch.replace(/-\d{8}-\d{6}$/, '')} from the archive? Its files and register rows go back where they were.`, { ok: 'Restore' })) return;
    const r = await api('/api/module-restore', { method: 'POST', body: JSON.stringify({ archive: b.dataset.unarch, by: me() }) });
    toast(r.message || r.error, r.ok ? 'ok' : 'bad'); home();
  });
  if (!me() && !document.querySelector('.modal')) askName();  // first opening asks the name in the setup form instead
  if ($('#fix')) $('#fix').onclick = () => renderSetup(d.setup, false);
  document.querySelectorAll('.module-card').forEach(el => el.onclick = e => { if (!e.target.closest('[data-copy],[data-run]')) openModule(el.dataset.mod); });
}

/* ---------- Project setup (first opening) ---------- */
export function renderSetup(p, first) {
  setCrumbs(first ? [['Welcome']] : [['Modules', home], ['Project']]);
  S.view = 'setup'; updateSavebar();
  const plat = ['Web', 'API', 'Android', 'iOS'];
  $('#main').innerHTML = `<div class="formpage">
    <h1>${first ? 'Welcome to TestHive' : 'Project details'}</h1>
    <p class="finding">${first ? 'Tell TestHive about the product you are testing. You can change this later (Project, in the sidebar).' : 'These facts are shared with the agents (CONTEXT.md).'}</p>
    <div class="form">
      <label for="p-project">Project name</label><input id="p-project" dir="auto" value="${esc(p.project)}" placeholder="Nakhla Rewards">
      <label for="p-app">App name</label><input id="p-app" dir="auto" value="${esc(p.app)}" placeholder="Nakhla">
      <label>Platforms</label><span class="bar">${plat.map(x => `<label class="check"><input type="checkbox" class="p-plat" value="${x}" ${p.platforms.includes(x) ? 'checked' : ''}> ${x}</label>`).join('')}</span>
      <label for="p-env">Environment name</label><input id="p-env" value="${esc(p.test_env)}" placeholder="staging">
      <label for="p-web">Web address</label><input id="p-web" value="${esc(p.base_url)}" placeholder="https://staging.example.com">
      <label for="p-api">API address</label><input id="p-api" value="${esc(p.api_url)}" placeholder="https://api.staging.example.com">
      <label for="p-appid">Android package</label><input id="p-appid" value="${esc(p.app_id)}" placeholder="com.company.app (optional)">
      <label for="p-me">Your name</label><input id="p-me" value="${esc(me())}" placeholder="Sara (QA lead)">
      <span></span><span class="small muted">Passwords and tokens are never typed here: add them to the .env file yourself when a test needs them.</span>
      <span></span><span class="bar"><button class="primary" id="p-save">${first ? 'Create project' : 'Save'}</button>${first ? '' : '<button id="p-cancel">Cancel</button>'}</span>
    </div></div>`;
  if ($('#p-cancel')) $('#p-cancel').onclick = home;
  $('#p-save').onclick = async () => {
    const name = $('#p-me').value.trim(); if (!name) return toast('Enter your name: it signs your decisions.', 'warn');
    store.set('th-name', name); showMe();
    const r = await api('/api/project', { method: 'POST', body: JSON.stringify({ project: $('#p-project').value, app: $('#p-app').value,
      platforms: [...document.querySelectorAll('.p-plat:checked')].map(x => x.value), test_env: $('#p-env').value.trim(), base_url: $('#p-web').value.trim(),
      api_url: $('#p-api').value.trim(), app_id: $('#p-appid').value.trim() }) });
    toast(r.message || r.error, r.ok ? 'ok' : 'bad'); if (r.ok) home();
  };
}

/* ---------- New module ---------- */
export function renderNewModule() {
  S.view = 'newmodule'; updateSavebar();
  setCrumbs([['Modules', home], ['New module']]); renderSide();
  $('#main').innerHTML = `<div class="formpage">
    <h1>New module</h1><p class="finding">One part of the product, tested on its own. Next you add its documents (and an APK if you have one).</p>
    <div class="form">
      <label for="m-code">Module code</label><input id="m-code" class="upper" placeholder="SIGNUP">
      <label for="m-title">Title</label><input id="m-title" dir="auto" placeholder="Sign-up and mobile verification">
      <label for="m-url">Built product (optional)</label><input id="m-url" placeholder="https://staging.example.com/signup">
      <span></span><label class="check"><input type="checkbox" id="m-test"> This address is a test environment (the analyst may submit forms with test data)</label>
      <span></span><label class="check"><input type="checkbox" id="m-mask"> The documents contain personal data: mask it before the AI reads them</label>
      <span></span><span class="bar"><button class="primary" id="m-save">Add module</button><button id="m-cancel">Cancel</button></span>
    </div></div>`;
  $('#m-cancel').onclick = home;
  $('#m-save').onclick = async () => {
    const r = await api('/api/module-new', { method: 'POST', body: JSON.stringify({ module: $('#m-code').value.trim().toUpperCase(), title: $('#m-title').value,
      url: $('#m-url').value.trim(), test_env: $('#m-test').checked, mask: $('#m-mask').checked }) });
    toast(r.message || r.error, r.ok ? 'ok' : 'bad'); if (r.ok) { S.tab = 'sources'; openModule(r.module, true); }
  };
}
