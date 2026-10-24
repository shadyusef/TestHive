// Automation tab (stage 4): the test of each approved case (placeholder, written, stable), running the tests by tag, and the last runs.
import { TOKEN, S, $, esc, api, toast, ask, strip, filterBar, bindFilters, matches } from './core.js';
import { openModule } from './module.js';

const STATE = { missing: ['No test yet', 'High'], stub: ['Placeholder', 'Medium'], 'written-no-check': ['Checks nothing', 'High'],
  written: ['Written', 'wait'], stable: ['Stable (3 runs)', 'ok'], 'by-hand': ['By hand', 'Low'] };
const KIND = { web: 'Web', api: 'API', contract: 'Contract', mobile: 'Mobile' };
const CONTRACT = { current: ['Up to date', 'ok'], stale: ['The spec changed: rebuild', 'High'], missing: ['Not built yet', 'High'] };
const TAGS = ['smoke', 'sanity', 'regression', 'e2e'];

export function renderAutomation() {
  const a = S.data.automation;
  if (!a) return $('#tab').innerHTML = `<div class="empty"><h2>Automation starts after the tools are chosen</h2>
    <p class="muted">When the tools are approved, TestHive sets up the test project with one placeholder test per approved case, and the engineers write them.</p></div>`;
  const cs = a.cases, n = st => cs.filter(c => c.state === st).length, ct = a.contract, kinds = [...new Set(cs.map(c => c.kind).filter(Boolean)), ...(ct ? ['contract'] : [])];
  const frozen = S.data.stages[3].status === 'approved', bugs = cs.filter(c => c.bug).length, f = (S.filters.auto = S.filters.auto || {});
  const shown = cs.filter(c => matches(c, f, ['ID', 'Title', 'spec']) && (!f.state || STATE[c.state][0] === f.state) && (!f.type || c.type === f.type) && (!f.tag || c.Tags.split(' ').includes(f.tag)));
  $('#tab').innerHTML = `${frozen ? '<div class="msg ok">The automation is approved: its tests are recorded in a baseline. Changes to the tests start with a reopen in Approvals.</div>' : ''}
    ${strip([
      { label: 'Cases to automate', value: cs.length, sub: Object.entries(a.tools).map(([t, tool]) => `${esc(t)}: ${esc(tool)}`).join(' · ') },
      { label: 'Tests written', value: n('written') + n('stable'), of: cs.length,
        bar: [[n('stable'), 'var(--accent)', 'stable'], [n('written'), 'var(--text)', 'written'], [n('stub') + n('missing') + n('written-no-check'), 'var(--control)', 'to write']] },
      { label: 'Proven stable', value: n('stable'), of: cs.length, sub: 'passed 3 runs in a row' },
      { label: 'Known bugs', value: bugs, sub: bugs ? 'tests expected to fail until the bug is fixed' : 'no test waits for a fix' },
    ])}
    ${kinds.length ? `<section class="block"><div class="blockhead"><div class="grow"><h2>Run the tests</h2>
      <p class="small muted">Against the environment in .env (TEST_ENV picks .env.&lt;name&gt;). Each run is kept in runs/ with its screenshots, videos and logs.</p></div></div>
      <div class="decide"><select id="rk" aria-label="Which tests">${kinds.map(k => `<option value="${k}">${KIND[k]} tests</option>`).join('')}</select>
        <select id="rt" aria-label="Tag"><option value="">every tag</option>${TAGS.map(t => `<option>${t}</option>`).join('')}</select>
        <button class="primary" id="rgo" ${S.agents === 'review' || S.data.job ? 'disabled' : ''}>Run</button></div></section>` : ''}
    ${ct ? contractBlock(ct) : ''}
    ${Object.entries(a.runs).map(([k, r]) => runBlock(k, r)).join('')}
    <section class="block"><div class="blockhead"><div class="grow"><h2>Tests</h2></div></div>
    ${filterBar('auto', [['state', 'State', Object.values(STATE).map(s => s[0])], ['type', 'Test type', [...new Set(cs.map(c => c.type))]], ['tag', 'Tag', TAGS]], shown.length)}
    <div class="table-wrap"><table class="list"><thead><tr><th>ID</th><th>P</th><th class="wide">Title</th><th>Tags</th><th class="status">State</th></tr></thead><tbody>
    ${shown.map(c => `<tr><td class="id">${esc(c.ID)}</td><td class="p">${esc(c.Priority)}</td>
      <td dir="auto">${esc(c.Title)}<div class="meta">${esc(c.type)} · ${esc(c.tool)}${c.spec ? ` · <code>${esc(c.spec)}</code>` : ''}${c.bug ? ` · expected to fail: ${esc(c.bug)}` : ''}</div></td>
      <td class="small">${esc(c.Tags)}</td><td class="status"><span class="pill ${STATE[c.state][1]}">${esc(STATE[c.state][0])}</span></td></tr>`).join('') ||
      '<tr><td colspan="5" class="muted">No test matches.</td></tr>'}
    </tbody></table></div></section>`;
  bindFilters(renderAutomation);
  if ($('#rgo')) $('#rgo').onclick = async () => {
    const kind = $('#rk').value, tag = kind === 'contract' ? '' : $('#rt').value;
    if (!await ask(`Run the ${KIND[kind]} tests of ${S.module}${tag ? ` tagged ${tag}` : ''} now? They run against the environment in .env.`, { ok: 'Run' })) return;
    const r = await api('/api/run', { method: 'POST', body: JSON.stringify({ module: S.module, action: 'run-tests', options: { kind, tag } }) });
    toast(r.message || r.error, r.ok ? 'ok' : 'bad'); if (r.ok) openModule(S.module, true);
  };
}

function contractBlock(ct) {
  return `<section class="block"><div class="blockhead"><div class="grow"><h2>Contract tests <span class="pill ${CONTRACT[ct.state][1]}">${CONTRACT[ct.state][0]}</span></h2>
    <p class="small muted">${ct.operations || 'No'} endpoints from ${ct.specs.map(f => `<code>${esc(f)}</code>`).join(', ')}: each must answer with a status and a body the spec lists.
      Built by TestHive from the spec (Set up the test project rebuilds them); no test data needed.</p></div></div>
    ${ct.state === 'current' && !ct.run ? '<p class="small">Not run yet: choose Contract tests above and Run.</p>' : ''}
    ${ct.failed.length ? `<ul class="plain">${ct.failed.map(f => `<li><b>${esc(f.endpoint)}</b> ${f.bug ? `expected to fail: ${esc(f.bug)}` :
      'answers differently from the spec: report a bug and list it in the contract-bugs file, or fix the spec'}</li>`).join('')}</ul>` : ct.run ? '<p class="small">Every endpoint answered as the spec says.</p>' : ''}</section>`;
}

function runBlock(kind, r) {
  const t = r.totals || {}, file = (run, name) => `/api/run-file?m=${encodeURIComponent(S.module)}&run=${encodeURIComponent(run)}&name=${encodeURIComponent(name)}&t=${encodeURIComponent(TOKEN)}`;
  return `<section class="block"><div class="blockhead"><div class="grow"><h2>Last ${KIND[kind] || esc(kind)} run <span class="muted small">${esc(r.run)} · ${esc(r.at.replace('T', ' ').slice(0, 16))} UTC${r.env ? ' · ' + esc(r.env) : ''}</span></h2>
    <p class="small muted">${t.total || 0} results: ${t.passed || 0} passed, ${r.problems.length} failed, ${r.placeholders} placeholders not written yet${kind === 'api' || kind === 'contract' ? ' (Newman counts each check)' : ''}</p></div></div>
    ${r.problems.length ? `<ul class="plain">${r.problems.slice(0, 20).map(p => `<li><b>${esc(p.id || p.suite || p.name)}</b> ${esc(p.status)}: <span class="small">${esc((p.message || '').slice(0, 200))}</span>
      ${(p.evidence || []).map(e => `<a class="small" href="${file(r.run, e)}" target="_blank" rel="noopener noreferrer">${esc(e.split('/').pop())}</a>`).join(' ')}</li>`).join('')}</ul>` : ''}</section>`;
}
