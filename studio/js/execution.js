// Execution tab (stage 5): the test cycle. Its runs on one environment, the result of every case (from the runs, or recorded by
// hand), bugs and their fixes, retests, and flaky tests to quarantine. The rules are execute.py's (the same as scripts/cycle.sh).
import { S, $, esc, api, toast, ask, me, askName, strip, filterBar, bindFilters, matches, targetSelects, wireTargets, targetOptions } from './core.js';
import { openModule } from './module.js';

const RESULT = { passed: ['Passed', 'ok'], 'known-bug': ['Known bug', 'Medium'], failed: ['Failed', 'High'], blocked: ['Blocked', 'Medium'], 'not-run': ['Not run', 'Low'] };
const KIND = { web: 'Web', api: 'API', mobile: 'Mobile', manual: 'By hand', contract: 'Contract' };
const TAGS = ['smoke', 'sanity', 'regression', 'e2e'];

async function send(action, body) {
  if (!me()) { askName(); return false; }
  const r = await api('/api/execution', { method: 'POST', body: JSON.stringify({ module: S.module, action, by: me(), ...body }) });
  toast(r.message || r.error, r.ok ? 'ok' : 'bad');
  if (r.ok) openModule(S.module, true);
  return r.ok;
}

async function run(action, options = {}) {
  const r = await api('/api/run', { method: 'POST', body: JSON.stringify({ module: S.module, action, options }) });
  toast(r.message || r.error, r.ok ? 'ok' : 'bad'); if (r.ok) openModule(S.module, true);
}

export function renderExecution() {
  const x = S.data.execution, off = S.agents === 'review' || !!S.data.job;
  if (!x) return $('#tab').innerHTML = `<div class="empty"><h2>Execution starts after the automation is approved</h2>
    <p class="muted">Then a test cycle runs every case on one environment: the automated tests from their runs, the others by hand.</p></div>`;
  if (!x.cycle) return startForm(x);
  const cs = x.cases, n = r => cs.filter(c => c.result === r).length, c = x.cycle, f = (S.filters.exec = S.filters.exec || {});
  const kinds = [...new Set(cs.map(c => c.kind).filter(k => k !== 'manual')), ...(x.contract ? ['contract'] : [])];
  const retest = ['web', 'api'].filter(k => cs.some(c => c.kind === k && c.retest));
  const bugs = [...new Set(cs.map(c => c.bug).filter(Boolean))].sort();
  const shown = cs.filter(r => matches(r, f, ['ID', 'Title', 'bug']) && (!f.result || RESULT[r.result][0] === f.result) && (!f.kind || KIND[r.kind] === f.kind)
    && (!f.flag || (f.flag === 'Flaky' ? r.flaky : f.flag === 'Quarantined' ? r.quarantine : r.retest)));
  const todo = shown.filter(r => r.kind === 'manual' && (r.result === 'not-run' || r.retest));
  $('#tab').innerHTML = `${S.data.stages[4].status === 'approved' ? '<div class="msg ok">The execution is approved: its results are recorded in a baseline. A new round starts with a reopen in Approvals and a new cycle.</div>' : ''}
    ${strip([
      { label: `Cycle ${c.id}`, value: c.name, sub: `on ${esc(c.env || 'the default .env')} · since ${esc(c.started_at.replace('T', ' ').slice(0, 16))} UTC · ${x.runs.length} runs` },
      { label: 'Results', value: cs.length - n('not-run'), of: cs.length,
        bar: [[n('passed'), 'var(--accent)', 'passed'], [n('known-bug') + n('failed'), 'var(--bad, #b00020)', 'failed'], [n('blocked'), 'var(--text)', 'blocked'], [n('not-run'), 'var(--control)', 'not run']] },
      { label: 'Failed', value: n('failed') + n('known-bug'), sub: `${bugs.length} bugs, ${Object.keys(x.fixed).length} fixed` },
      { label: 'Flaky', value: cs.filter(r => r.flaky).length, sub: `${cs.filter(r => r.quarantine).length} quarantined` },
    ])}
    ${x.other_env_runs ? `<div class="msg warn">${x.other_env_runs} runs since the cycle started were on another environment: they do not count in this cycle.</div>` : ''}
    <section class="block"><div class="blockhead"><div class="grow"><h2>Run the cycle's tests</h2>
      <p class="small muted">On ${esc(c.env || 'the default .env')}, the cycle's environment. Each run is kept in runs/ with its evidence; failed web tests keep their video, screenshot and trace, API tests each request and response.</p></div></div>
      ${kinds.length ? `<div class="decide"><select id="xk" aria-label="Which tests">${kinds.map(k => `<option value="${k}">${KIND[k]} tests</option>`).join('')}</select>
        <select id="xt" aria-label="Suite"><option value="">every tag</option>${TAGS.map(t => `<option>${t}</option>`).join('')}</select>
        ${targetSelects('xtg', 'xdv')}
        <button class="primary" id="xgo" ${off ? 'disabled' : ''}>Run</button>
        ${retest.map(k => `<button data-retest="${k}" ${off ? 'disabled' : ''}>Retest the ${KIND[k]} failures</button>`).join('')}</div>` : '<p class="small muted">No automated tests: every case is run by hand.</p>'}</section>
    ${bugs.length ? `<section class="block"><div class="blockhead"><div class="grow"><h2>Bugs in this cycle</h2>
      <p class="small muted">When the developers fix one, mark it fixed: its cases must then be retested.</p></div></div>
      <ul class="plain">${bugs.map(b => `<li><b>${esc(b)}</b> ${x.fixed[b] ? `<span class="pill ok">fixed ${esc(x.fixed[b].slice(0, 10))}</span>` : `<button class="small" data-fixed="${esc(b)}">Mark fixed</button>`}
        <span class="small muted">${cs.filter(r => r.bug === b).map(r => esc(r.ID)).join(', ')}</span></li>`).join('')}</ul></section>` : ''}
    ${x.contract && x.contract.failed.length ? `<section class="block"><h2>Contract tests</h2><ul class="plain">${x.contract.failed.map(e => `<li><b>${esc(e.endpoint)}</b> ${e.bug ? 'expected to fail: ' + esc(e.bug) : 'answers differently from the spec: list it in the contract-bugs file with its bug ID'}</li>`).join('')}</ul></section>` : ''}
    <section class="block"><div class="blockhead"><div class="grow"><h2>Cases</h2></div>
      ${todo.length ? `<button id="xall" ${S.data.stages[4].status === 'approved' ? 'disabled' : ''}>Mark the ${todo.length} shown cases run by hand as Passed</button>` : ''}</div>
    ${filterBar('exec', [['result', 'Result', Object.values(RESULT).map(r => r[0])], ['kind', 'Run', [...new Set(cs.map(r => KIND[r.kind]))]], ['flag', 'Show', ['Flaky', 'Quarantined', 'To retest']]], shown.length)}
    <div class="table-wrap"><table class="list"><thead><tr><th>ID</th><th>P</th><th class="wide">Title</th><th>Run</th><th class="status">Result</th><th>Record</th></tr></thead><tbody>
    ${shown.map(row).join('') || '<tr><td colspan="6" class="muted">No case matches.</td></tr>'}
    </tbody></table></div></section>`;
  bindFilters(renderExecution); wireTargets('xk', 'xtg', 'xdv');
  if ($('#xgo')) $('#xgo').onclick = async () => {
    const k = $('#xk').value, tag = k === 'contract' ? '' : $('#xt').value;
    if (await ask(`Run the ${KIND[k]} tests${tag ? ` tagged ${tag}` : ''} of ${S.module} on ${c.env || 'the default .env'}?`, { ok: 'Run' })) run(`cycle-${k}`, { tag, ...targetOptions('xtg', 'xdv') });
  };
  document.querySelectorAll('[data-retest]').forEach(b => b.onclick = () => run(`retest-${b.dataset.retest}`, b.dataset.retest === 'web' && $('#xk').value === 'web' ? { target: targetOptions('xtg', 'xdv').target } : {}));
  document.querySelectorAll('[data-fixed]').forEach(b => b.onclick = async () => {
    if (await ask(`Mark ${b.dataset.fixed} as fixed? Its cases must be retested before the cycle can be approved.`, { ok: 'Mark fixed' })) send('fixed', { bug: b.dataset.fixed });
  });
  if ($('#xall')) $('#xall').onclick = async () => {
    if (await ask(`Record ${todo.length} cases run by hand as Passed, signed ${me() || '(your name)'}? Only do this if you ran them and they passed.`, { ok: 'Record' })) send('result', { ids: todo.map(r => r.ID), result: 'Passed' });
  };
  document.querySelectorAll('[data-save]').forEach(b => b.onclick = () => {
    const id = b.dataset.save, v = k => ($(`#${k}-${id}`) || {}).value || '';
    send('result', { ids: [id], result: v('xr'), bug: v('xb').trim(), note: v('xn').trim() });
  });
  document.querySelectorAll('[data-link]').forEach(b => b.onclick = () => send('bug', { id: b.dataset.link, bug: ($(`#xb-${b.dataset.link}`) || {}).value.trim() }));
  document.querySelectorAll('[data-quar]').forEach(b => b.onclick = () => {
    const reason = ($(`#xq-${b.dataset.quar}`) || {}).value.trim();
    if (!reason) return toast('Say why it is quarantined.', 'warn');
    send('quarantine', { id: b.dataset.quar, reason });
  });
  document.querySelectorAll('[data-unquar]').forEach(b => b.onclick = () => send('unquarantine', { id: b.dataset.unquar }));
}

function row(r) {
  const id = esc(r.ID), flags = [r.flaky ? `<span class="pill High">flaky ${esc(r.history.join(''))}</span>` : '', r.quarantine ? `<span class="pill Low" title="${esc(r.quarantine.reason)}">quarantined</span>` : '',
    r.retest ? '<span class="pill Medium">retest</span>' : ''].join(' ');
  let rec = '';
  if (r.kind === 'manual') rec = `<select id="xr-${id}" aria-label="Result of ${id}">${['Passed', 'Failed', 'Blocked'].map(o => `<option ${RESULT[r.result][0] === o ? 'selected' : ''}>${o}</option>`).join('')}</select>
    <input id="xb-${id}" placeholder="BUG-…" value="${esc(r.bug)}" aria-label="Bug of ${id}" size="9"><input id="xn-${id}" placeholder="Note" value="${esc(r.note)}" aria-label="Note on ${id}" size="12">
    <button class="small" data-save="${id}">Save</button>`;
  else if (r.result === 'failed' && !r.bug) rec = `<input id="xb-${id}" placeholder="BUG-…" aria-label="Bug of ${id}" size="9"><button class="small" data-link="${id}">Link bug</button>`;
  if (r.flaky && !r.quarantine) rec += ` <input id="xq-${id}" placeholder="Why quarantine" aria-label="Quarantine reason for ${id}" size="14"><button class="small" data-quar="${id}">Quarantine</button>`;
  if (r.quarantine) rec += ` <button class="small" data-unquar="${id}">Release</button>`;
  return `<tr><td class="id">${id}</td><td class="p">${esc(r.Priority)}</td><td dir="auto">${esc(r.Title)}<div class="meta">${esc(r.Type)}${r.history.length ? ' · runs ' + esc(r.history.join('')) : ''}${r.note ? ' · ' + esc(r.note) : ''}</div></td>
    <td class="small">${KIND[r.kind]}</td><td class="status"><span class="pill ${RESULT[r.result][1]}">${RESULT[r.result][0]}</span>${r.bug ? `<div class="small">${esc(r.bug)}</div>` : ''} ${flags}</td>
    <td class="small">${rec}</td></tr>`;
}

function startForm(x) {
  $('#tab').innerHTML = `<section class="block"><div class="blockhead"><div class="grow"><h2>Start a test cycle</h2>
    <p class="small muted">A cycle is one round of testing on one environment, for example "1.4 UAT". Runs on that environment from now on count in it; cases run by hand are recorded here.</p></div></div>
    <div class="decide"><input id="cn" class="grow" placeholder="Cycle name" aria-label="Cycle name" maxlength="120">
      <select id="ce" aria-label="Environment"><option value="">the default .env</option>${x.envs.map(e => `<option value="${esc(e)}">.env.${esc(e)}</option>`).join('')}</select>
      <button class="primary" id="cgo">Start the cycle</button></div></section>`;
  $('#cgo').onclick = () => {
    const name = $('#cn').value.trim();
    if (!name) return toast('Give the cycle a name.', 'warn');
    send('start', { name, env: $('#ce').value });
  };
}
