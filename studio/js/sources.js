// Sources tab: requirement documents, earlier versions, the built product, personal data, archive.
import { TOKEN, S, $, esc, api, toast, me, askName, ask, panel } from './core.js';
import { openModule } from './module.js';
import { home } from './home.js';

/* ---------- Sources ---------- */
export const fileUrl = (name, version) => `/api/source-file?m=${encodeURIComponent(S.module)}&name=${encodeURIComponent(name)}${version ? '&version=' + encodeURIComponent(version) : ''}&t=${encodeURIComponent(TOKEN)}`;
export function renderSources() {
  const d = S.data, src = d.sources, mt = d.meta, analysisDone = d.stages[0].status === 'approved';
  const changed = analysisDone ? src.changed_after_approval : [];
  const unread = src.files.filter(f => !f.read).length;
  $('#tab').innerHTML = `${changed.length ? `<div class="msg warn"><b>${changed.length} document(s) changed after the analysis was approved:</b> ${esc(changed.map(c => `${c.name} (${c.action})`).join(', '))}.
      Reopen the analysis so the analyst reads them; after the new approval TestHive shows which test cases are affected.
      <div class="bar"><input class="grow" id="ro-c" placeholder="What changed (required)" aria-label="What changed"><button id="ro">Reopen analysis</button></div></div>` : ''}
    <section class="block"><div class="blockhead"><div class="grow"><h2>Requirement documents</h2>
        <p class="small muted">${src.read_at ? 'Last read ' + esc(src.read_at) + '. ' : ''}Reading turns every document into text the analyst works from (free, no AI).</p></div>
      <label class="check"><input type="checkbox" id="rd-mask" ${mt.mask ? 'checked' : ''}> Mask personal data</label>
      <button class="${unread ? 'primary' : ''}" id="read" ${src.files.length ? '' : 'disabled'}>Read the documents${unread ? ` (${unread} new)` : ''}</button></div>
      <pre id="readout" class="log" hidden></pre>
      <div class="table-wrap"><table class="list"><thead><tr><th class="wide">Document</th><th>Type</th><th>Changed</th><th>Read by TestHive</th><th><span class="sr">Actions</span></th></tr></thead><tbody>
      ${src.files.map(f => `<tr><td dir="auto"><button class="link strong" data-doc="${esc(f.name)}" title="See what TestHive read">${esc(f.name)}</button></td><td class="small">${esc(f.type)}</td><td class="small muted">${esc(f.modified)}</td>
        <td class="small">${f.read ? `<span class="okmark">${f.type === 'image' ? 'image, read directly' : esc(f.words) + ' words'}${f.masked === 'yes' ? ' · masked' : ''}</span>` : '<span class="pill Medium">not read yet</span>'}</td>
        <td class="rowacts"><button class="small" data-doc="${esc(f.name)}">Text</button><a class="btnlike small" href="${fileUrl(f.name)}" target="_blank" rel="noopener noreferrer">Original</a><button class="small danger" data-rm="${esc(f.name)}">Remove</button></td></tr>`).join('')
        || '<tr><td colspan="5" class="muted">No documents yet: add them below.</td></tr>'}
      </tbody></table></div>
      <div id="drop" class="drop"><b>Drop files here</b> or <label class="link accent" role="button" tabindex="0">choose files<input type="file" id="files" multiple hidden accept=".pdf,.docx,.xlsx,.xlsm,.csv,.txt,.md,.json,.yaml,.yml,.png,.jpg,.jpeg,.gif,.bmp,.webp"></label>
        <div class="small">PDF, Word (.docx), Excel, CSV, text, OpenAPI / Swagger (.json, .yaml), design images · up to 25 MB each · a file with the same name replaces the old one, which is kept</div></div></section>
    <section class="block"><div class="blockhead"><div class="grow"><h2>Module details and built product</h2>
      <p class="small muted">Saved as you type. If the product is already built, give its address or APK: the analyst explores it too.</p></div></div>
      <div class="form">
      <label for="u-title">Module title</label><input id="u-title" dir="auto" value="${esc(mt.title)}" placeholder="What this part of the product does">
      <label for="u-url">Web address <span class="muted">optional</span></label><span><input id="u-url" class="full" value="${esc(mt.url)}" placeholder="https://test.example.com/page">
        ${!mt.url && d.project_url ? `<button class="link accent small" id="u-useproj">Use the project's address (${esc(d.project_url)})</button>` : ''}</span>
      <span></span><label class="check"><input type="checkbox" id="u-test" ${mt.test_env ? 'checked' : ''}> Test environment (the analyst may submit forms with test data)</label>
      <label>Android app <span class="muted">optional</span></label><span>${src.apk ? `<code>${esc(src.apk)}</code> · ` : ''}<label class="link accent" role="button" tabindex="0">${src.apk ? 'replace' : 'upload an APK'}<input type="file" id="apk" accept=".apk" hidden></label></span>
      <span></span><div>${S.agents === 'review' ? '' : d.web_tools ? '<button id="u-explore" data-run="explore-web" data-title="Explore the built product" data-min="1-5">Explore the built product</button>'
          : '<p class="msg warn">Explore needs the web tools on this PC. Someone at a terminal installs them once: setup --install --web (see docs/TEAM-GUIDE.md).</p>'}
        ${d.exploration ? `<p class="small" dir="auto">Explored <span class="mono">${esc(d.exploration.url)}</span> on ${esc(d.exploration.at)}: ${d.exploration.pages} page(s)${d.exploration.failed ? `, ${d.exploration.failed} could not be opened` : ''} · <button class="link accent" id="u-report">Open the report</button></p>`
          : '<p class="small muted">Explore opens the address in a hidden browser and records each screen (free, no AI); the analyst reads them with the documents.</p>'}</div></div></section>
    <details class="fold" id="vercard"><summary><b>Earlier versions and removed documents</b> <span class="small muted">${src.old_versions} kept · who changed what</span></summary><div id="verbody"></div></details>
    <details class="fold" id="maskcard"><summary><b>Personal data</b> <span class="small muted">check what masking hides before the AI reads anything</span></summary><div id="maskbody"><button id="mprev">Check the documents</button></div></details>
    <details class="fold danger-zone"><summary><b>Archive this module</b> <span class="small muted">moves it and all its files out of the project; it can be restored from the start page</span></summary>
      <p class="small muted">Use it for a module added by mistake or no longer tested. Nothing is deleted: everything goes to archive/${esc(d.module)}-&lt;time&gt;/ and the decision is logged with your name.</p>
      <button class="danger" id="arch">Archive ${esc(d.module)}…</button></details>`;
  const upload = async (files, kind) => {
    for (const f of files) {
      const r = await api(`/api/source?m=${encodeURIComponent(d.module)}&kind=${kind}&name=${encodeURIComponent(f.name)}&by=${encodeURIComponent(me())}`, { method: 'POST', body: f, headers: { 'Content-Type': 'application/octet-stream' } });
      toast(r.message || r.error, r.ok ? 'ok' : 'bad');
    }
    openModule(d.module, true);
  };
  $('#files').onchange = e => upload([...e.target.files], 'source');
  $('#apk').onchange = e => upload([...e.target.files], 'apk');
  const drop = $('#drop');
  drop.ondragover = e => { e.preventDefault(); drop.classList.add('over'); };
  drop.ondragleave = () => drop.classList.remove('over');
  drop.ondrop = e => { e.preventDefault(); drop.classList.remove('over'); upload([...e.dataTransfer.files], 'source'); };
  document.querySelectorAll('[data-doc]').forEach(b => b.onclick = () => showText(b.dataset.doc));
  document.querySelectorAll('[data-rm]').forEach(b => b.onclick = async () => {
    if (!me()) return askName();
    if (!await ask(`Remove ${b.dataset.rm}?\n\nIt moves to the earlier versions (nothing is deleted) and the analyst no longer reads it.${analysisDone ? ' The analysis is approved: removing a document is a change that needs a reopen.' : ''}`, { ok: 'Remove', danger: true })) return;
    const r = await api('/api/source-remove', { method: 'POST', body: JSON.stringify({ module: d.module, name: b.dataset.rm, by: me() }) });
    toast(r.message || r.error, r.ok ? 'ok' : 'bad'); openModule(d.module, true);
  });
  $('#vercard').ontoggle = () => { if ($('#vercard').open) renderVersions(); };
  $('#read').onclick = async () => {
    $('#read').disabled = true; $('#read').textContent = 'Reading…';
    const r = await api('/api/ingest', { method: 'POST', body: JSON.stringify({ module: d.module, mask: $('#rd-mask').checked }) });
    toast(r.ok ? 'Documents read.' : 'Some documents could not be read.', r.ok ? 'ok' : 'bad');
    await openModule(d.module, true); const o = $('#readout'); o.textContent = r.message || r.error; o.hidden = false;
  };
  const saveMeta = () => api('/api/module-meta', { method: 'POST', body: JSON.stringify({ module: d.module, url: $('#u-url').value.trim(), test_env: $('#u-test').checked,
      title: $('#u-title').value, mask: $('#rd-mask').checked }) });
  const autosave = async () => {  // every field saves on change: nothing typed here is lost by switching tab
    const r = await saveMeta(); if (!r.ok) return toast(r.message || r.error, 'bad');
    const urlNow = $('#u-url').value.trim(), refresh = !!urlNow !== !!mt.url;  // Next and the Run button depend on having an address
    Object.assign(mt, { url: urlNow, test_env: $('#u-test').checked, title: $('#u-title').value, mask: $('#rd-mask').checked });
    toast('Saved.');
    if (refresh) setTimeout(() => { if (!document.querySelector('.modal')) openModule(d.module, true); }, 400);  // not under an Explore confirmation
  };
  ['#u-title', '#u-url', '#u-test', '#rd-mask'].forEach(id => $(id).onchange = autosave);
  if ($('#u-useproj')) $('#u-useproj').onclick = () => { $('#u-url').value = d.project_url; autosave(); };
  if ($('#u-report')) $('#u-report').onclick = async () => {
    const r = await api('/api/exploration?m=' + encodeURIComponent(d.module));
    if (r.status !== 200) return toast(r.error || 'No report yet.', 'warn');
    panel('What Explore found', `<p class="small muted">Observed behaviour, not confirmed requirements. Screenshots are in ${esc(r.folder)}/.</p><pre class="log">${esc(r.text)}</pre>`);
  };
  if ($('#u-explore')) $('#u-explore').onclick = async e => {  // saves a typed address first, then the usual Run confirmation
    const b = e.currentTarget; if (b.dataset.saved) { delete b.dataset.saved; return; }
    e.stopPropagation();
    if (!$('#u-url').value.trim()) { toast('Type the web address of the built product first.', 'warn'); return $('#u-url').focus(); }
    if ($('#u-url').value.trim() !== mt.url || $('#u-test').checked !== !!mt.test_env) {
      const r = await saveMeta(); if (!r.ok) return toast(r.message || r.error, 'bad');
      mt.url = $('#u-url').value.trim(); mt.test_env = $('#u-test').checked;
    }
    b.dataset.saved = '1'; b.click();
  };
  if ($('#ro')) $('#ro').onclick = async () => {
    if (!me()) return askName(); const c = $('#ro-c').value.trim(); if (!c) return toast('Say what changed.', 'warn');
    if (!await ask('Reopen the analysis? Later stages go back to in progress and need a new approval.', { ok: 'Reopen' })) return;
    const r = await api('/api/stage', { method: 'POST', body: JSON.stringify({ module: d.module, stage: 'analysis', action: 'reopen', by: me(), comment: c }) });
    toast(r.message || r.error, r.ok ? 'ok' : 'bad'); openModule(d.module, true);
  };
  $('#arch').onclick = () => archiveModule(d.module);
  $('#mprev').onclick = renderMask;
}
export async function showText(name) {
  const r = await api(`/api/source-text?m=${encodeURIComponent(S.module)}&name=${encodeURIComponent(name)}`);
  panel(name, `<p class="small muted">${r.text ? `What TestHive read${r.masked ? ' (masked)' : ''}: this is what the analyst works from. ` : esc(r.note || r.error || '')}
      <a href="${fileUrl(name)}" target="_blank" rel="noopener noreferrer">Open the original</a></p>
    ${r.text ? `<pre dir="auto" class="doctext">${esc(r.text)}</pre>` : ''}`);
}
export async function renderVersions() {
  const r = await api('/api/source-versions?m=' + encodeURIComponent(S.module));
  $('#verbody').innerHTML = `${r.versions.length ? `<div class="table-wrap"><table><thead><tr><th>Kept since</th><th>Document</th><th>Size</th><th></th></tr></thead><tbody>
      ${r.versions.map(v => `<tr><td class="small">${esc(v.kept)}</td><td dir="auto">${esc(v.name)} ${v.current ? '' : '<span class="pill Medium">removed</span>'}</td><td class="small">${Math.ceil(v.size / 1024)} KB</td>
        <td class="rowacts"><a class="btnlike small" href="${fileUrl(v.name, v.version)}" target="_blank" rel="noopener noreferrer">Open</a>
          <button class="small" data-restore="${esc(v.version)}" data-name="${esc(v.name)}" data-current="${v.current ? 1 : ''}">Restore</button></td></tr>`).join('')}</tbody></table></div>`
    : '<p class="muted">No earlier versions: nothing was replaced or removed yet.</p>'}
    ${r.history.length ? `<h4>Changes</h4><div class="table-wrap"><table><thead><tr><th>When (UTC)</th><th>What</th><th>Document</th><th>By</th></tr></thead><tbody>
      ${r.history.map(h => `<tr><td class="small">${esc(h.When.replace('T', ' ').slice(0, 16))}</td><td>${esc(h.Action)}</td><td dir="auto">${esc(h.Document)}</td><td>${esc(h.By)}</td></tr>`).join('')}</tbody></table></div>` : ''}`;
  document.querySelectorAll('[data-restore]').forEach(b => b.onclick = async () => {
    if (!me()) return askName();
    if (!await ask(`Restore ${b.dataset.name} as it was on ${b.closest('tr').firstElementChild.textContent}?${b.dataset.current ? '\n\nThe current version is kept as an earlier version.' : ''}`, { ok: 'Restore' })) return;
    const x = await api('/api/source-restore', { method: 'POST', body: JSON.stringify({ module: S.module, version: b.dataset.restore, name: b.dataset.name, by: me() }) });
    toast(x.message || x.error, x.ok ? 'ok' : 'bad'); openModule(S.module, true);
  });
}
export async function archiveModule(mod) {
  if (!me()) return askName();
  const typed = await ask(`Archive ${mod}?\n\nThe module, its documents, questions, test cases, baselines and agent logs move to the archive folder and leave Studio. You can restore it from the start page.\n\nType ${mod} to confirm.`,
    { input: `Type ${mod}`, match: mod, ok: 'Continue', danger: true });
  if (!typed) return;
  const why = await ask(`Why is ${mod} archived? (kept in the approvals log)`, { input: 'Reason, e.g. added by mistake', ok: `Archive ${mod}`, danger: true });
  if (!why) return;
  const r = await api('/api/module-archive', { method: 'POST', body: JSON.stringify({ module: mod, confirm: typed, comment: why, by: me() }) });
  toast(r.message || r.error, r.ok ? 'ok' : 'bad'); if (r.ok) home();
}
export async function renderMask() {
  $('#maskbody').innerHTML = '<p class="muted">Checking…</p>';
  const m = await api('/api/mask-preview?m=' + encodeURIComponent(S.module));
  if (m.status !== 200) return $('#maskbody').innerHTML = `<div class="msg bad">${esc(m.error)}</div>`;
  const counts = esc(Object.entries(m.counts).map(([k, v]) => `${v} ${k.toLowerCase()}`).join(', ') || 'nothing');
  $('#maskbody').innerHTML = `<p class="small muted">This stays on your PC: the agents cannot open Studio. Ticked names are added to the names to hide (.mask-terms); unticked values are left as they are (.mask-allow). Then read the documents again with "Mask personal data" on.</p>
    <h4>Names TestHive is not sure about (${m.names.length})</h4>
    ${m.names.length ? `<div class="table-wrap"><table><thead><tr><th>Hide</th><th>Name</th><th>Why</th><th>In</th></tr></thead><tbody>${m.names.map((n, i) =>
      `<tr><td><input type="checkbox" class="mk-name" data-i="${i}"></td><td dir="auto">${esc(n.name)}</td><td class="small muted">${esc(n.why)}</td><td class="small">${esc(n.file)}</td></tr>`).join('')}</tbody></table></div>` : '<p class="muted">None.</p>'}
    <h4>Values masking would hide (${counts})</h4>
    ${m.values.length ? `<div class="table-wrap"><table><thead><tr><th>Hide</th><th>Kind</th><th class="wide">In context</th><th>In</th></tr></thead><tbody>${m.values.map((v, i) =>
      `<tr><td><input type="checkbox" class="mk-val" data-i="${i}" checked></td><td>${esc(v.kind)}</td><td dir="auto" class="small">${esc(v.context)}</td><td class="small">${esc(v.file)}</td></tr>`).join('')}</tbody></table></div>` : '<p class="muted">None.</p>'}
    ${m.skipped.length ? `<div class="msg warn small">${m.skipped.map(esc).join('<br>')}</div>` : ''}
    <p><button class="primary" id="mk-save">Save choices</button></p>`;
  $('#mk-save').onclick = async () => {
    const terms = [...document.querySelectorAll('.mk-name:checked')].map(x => m.names[x.dataset.i].name);
    const allow = [...new Set([...document.querySelectorAll('.mk-val:not(:checked)')].map(x => m.values[x.dataset.i].value))];
    const r = await api('/api/mask-lists', { method: 'POST', body: JSON.stringify({ module: S.module, terms, allow }) });
    toast(r.message || r.error, r.ok ? 'ok' : 'bad');
  };
}
