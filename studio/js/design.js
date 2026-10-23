// Design tab (stage 2): the test cases and their review, coverage, the open questions they rely on, requests and new cases.
import { TOKEN, S, $, esc, api, toast, me, askName, reqLinks, filterBar, bindFilters, matches, strip, subtabs } from './core.js';
import { bindUploads, afterSave, updateSavebar } from './module.js';

const TAGS = ['smoke', 'sanity', 'regression', 'e2e'];
const REVIEWS = [['Accepted', 'Accept'], ['Change', 'Change'], ['Remove', 'Remove']];
const short = ids => ids.map(x => x.replace(/^TC-[A-Z0-9]+-/, '')).join(', ');
export const designApproved = () => S.data.stages[1].status === 'approved';

export function renderDesign() {
  const d = S.data.design;
  if (!d.baseline) return $('#tab').innerHTML = `<div class="empty"><h2>Test design starts after the analysis</h2>
    <p class="muted">When the analysis is approved, its requirements are frozen as a baseline and the manual tester designs the cases from it.</p></div>`;
  if (!d.cases.length) return $('#tab').innerHTML = `<div class="empty"><h2>No test cases yet</h2>
    <p class="muted">The manual tester designs them from analysis baseline ${esc(d.baseline)}. Run it from the button at the top, or in Claude Code: <code>/th-manual ${esc(S.module)}</code></p></div>`;
  const act = d.cases.filter(c => c.Status !== 'Removed'), covered = d.coverage.filter(r => r.Cases.length).length, frozen = designApproved();
  const pr = p => act.filter(c => c.Priority === p).length, rev = v => act.filter(c => c.Review === v).length;
  const gapsNeg = d.coverage.filter(r => r.Negative === 'NO' || r.Boundary === 'NO').length;
  const openAsks = d.requests.filter(q => q.Status === 'Open').length;
  S.dtab = S.dtab || 'cases';
  $('#tab').innerHTML = `${frozen ? `<div class="msg ok">The design is approved, so the cases are read-only (a frozen baseline). To change them, reopen the design in the Approvals tab and say why.</div>` : ''}
    ${strip([
      { label: 'Active cases', value: act.length, sub: `${d.cases.length - act.length} removed · from analysis ${esc(d.baseline)}` },
      { label: 'Requirements covered', value: covered, of: d.coverage.length, bar: [[covered, 'var(--accent)', 'covered'], [d.coverage.length - covered, 'var(--bad)', 'not covered']],
        sub: gapsNeg ? `${gapsNeg} miss a negative or boundary case` : 'Each has its negative and boundary cases' },
      { label: 'By priority', value: act.length, bar: [[pr('P0'), 'var(--text)', 'P0'], [pr('P1'), 'var(--accent)', 'P1'], [pr('P2'), 'var(--muted)', 'P2'], [pr('P3'), 'var(--control)', 'P3']] },
      { label: 'Your review', value: act.filter(c => c.Review).length, of: act.length,
        sub: `${rev('Accepted')} accepted · ${rev('Change')} to change · ${rev('Remove')} to remove${rev('Updated') ? ` · ${rev('Updated')} updated by the designer` : ''}` },
    ])}
    <div class="tabhead">${subtabs('dtab', [['cases', 'Cases', `<span class="c">${act.length}</span>`], ['coverage', 'Coverage', gapsNeg ? `<span class="q">${gapsNeg} gaps</span>` : ''],
        ['assumptions', 'Open questions', d.assumptions.length ? `<span class="c">${d.assumptions.length}</span>` : ''], ['requests', 'Requests and new cases', openAsks ? `<span class="q">${openAsks} open</span>` : '']])}
      <span class="small muted">Prefer Excel? <a href="/api/workbook?m=${encodeURIComponent(S.module)}&kind=design&t=${encodeURIComponent(TOKEN)}">Download the workbook</a>${frozen ? '' : ` · <label class="link accent">upload a filled one<input type="file" accept=".xlsx" hidden data-upload="design"></label>`}</span></div>
    <div id="dtab"></div>`;
  document.querySelectorAll('[data-sub^="dtab:"]').forEach(b => b.onclick = () => { S.dtab = b.dataset.sub.split(':')[1]; renderDesign(); updateSavebar(); });
  bindUploads();
  ({ cases: renderCases, coverage: renderCoverage, assumptions: renderAssumptions, requests: renderRequests })[S.dtab]();
}

/* The review switch of one case: Accept, Change or Remove; choosing the chosen one again clears it. */
function reviewSwitch(c, rev) {
  const updated = c.Review === 'Updated' && (!rev || rev === 'Updated');
  return `<div class="seg" role="group" aria-label="Review of ${esc(c.ID)}">${REVIEWS.map(([v, l]) =>
    `<button data-rev="${esc(c.ID)}" data-v="${v}" aria-pressed="${rev === v}" class="${rev === v ? 'on ' + v.toLowerCase() : ''}">${l}</button>`).join('')}</div>
    ${updated ? '<div class="meta edited">Updated by the designer: check it again</div>' : ''}`;
}
function renderCases() {
  const cases = S.data.design.cases, frozen = designApproved(), f = (S.filters.cases = S.filters.cases || { state: 'Active' });
  const shown = cases.filter(c => matches(c, f, ['ID', 'Title', 'Steps', 'Expected Result', 'Requirements']) && (!f.priority || c.Priority === f.priority) &&
    (!f.tag || c.Tags.split(/[;,]/).map(x => x.trim()).includes(f.tag)) && (!f.platform || c.Platform === f.platform) &&
    (!f.review || (f.review === 'Not reviewed' ? !c.Review : c.Review === f.review)) && (f.state !== 'Active' || c.Status !== 'Removed') && (f.state !== 'Removed' || c.Status === 'Removed'));
  $('#dtab').innerHTML = filterBar('cases', [['priority', 'Priority', ['P0', 'P1', 'P2', 'P3']], ['tag', 'Tag', TAGS], ['platform', 'Platform', ['Web', 'API', 'Android', 'iOS', 'Both']],
      ['review', 'Review', ['Not reviewed', 'Accepted', 'Change', 'Remove', 'Updated']], ['state', 'Cases', ['Active', 'Removed']]], shown.length) +
    `${frozen ? '' : '<p class="small muted">Review each case: Accept it, ask for a Change (say what) or Remove it. Click a title for its steps and expected result.</p>'}
    <div class="table-wrap"><table class="list cases"><thead><tr><th>ID</th><th>P</th><th class="wide">Title</th><th>Type · technique</th><th>Tags</th><th>Review</th></tr></thead><tbody>
    ${shown.map(c => { const dv = S.dirty[c.ID] || {}, rev = dv.Review ?? c.Review, com = dv['Review Comment'] ?? c['Review Comment'], locked = c.Status === 'Removed' || frozen;
      const needsNote = rev === 'Change' || rev === 'Remove' || com;
      return `<tr class="${S.dirty[c.ID] ? 'dirty' : ''} ${c.Status === 'Removed' ? 'removed' : ''}"><td class="id">${esc(c.ID)}</td><td class="p">${esc(c.Priority)}</td>
        <td class="main"><button class="link strong" data-open="${esc(c.ID)}" aria-expanded="${S.open.has(c.ID)}" dir="auto">${esc(c.Title)}</button>
          <div class="meta">${esc(c.Platform)} · ${reqLinks(c.Requirements)}${c.Origin !== 'Designed' ? ' · added by ' + (c.Origin === 'Human' ? 'a person' : 'request') : ''}</div></td>
        <td class="tech small">${esc(c.Type)}<div class="meta">${esc(c.Technique)} · risk ${esc(c.Risk)}</div></td>
        <td class="tags">${String(c.Tags).split(/[;,]/).map(t => t.trim()).filter(Boolean).map(t => `<span class="tag ${t === 'smoke' ? 'smoke' : ''}">${esc(t)}</span>`).join('')}</td>
        <td class="rev">${locked ? `<span class="small">${c.Status === 'Removed' ? 'Removed' : esc(c.Review) || '—'}</span>${c['Review Comment'] ? `<div class="meta" dir="auto">${esc(c['Review Comment'])}</div>` : ''}`
          : `${reviewSwitch(c, rev)}<input class="note" dir="auto" data-com="${esc(c.ID)}" value="${esc(com)}" aria-label="Comment on ${esc(c.ID)}" placeholder="${rev === 'Change' ? 'What should change? (required)' : 'Comment'}" ${needsNote ? '' : 'hidden'}>`}</td></tr>
        ${S.open.has(c.ID) ? `<tr class="detail"><td colspan="6"><dl>
          <dt>Preconditions</dt><dd dir="auto">${esc(c.Preconditions) || '—'}</dd><dt>Steps</dt><dd dir="auto">${esc(c.Steps).replace(/; (\d+\.)/g, '<br>$1')}</dd>
          <dt>Expected result</dt><dd dir="auto"><b>${esc(c['Expected Result'])}</b></dd><dt>Test data</dt><dd dir="auto">${esc(c['Test Data']) || '—'}</dd>
          <dt>Depends on open questions</dt><dd>${esc(c.Assumption) || '—'}</dd><dt>Status</dt><dd>${esc(c.Status)}</dd></dl></td></tr>` : ''}`; }).join('') || `<tr><td colspan="6" class="muted">No cases match.</td></tr>`}
    </tbody></table></div>`;
  bindFilters(renderCases);
  document.querySelectorAll('[data-open]').forEach(el => el.onclick = () => { S.open.has(el.dataset.open) ? S.open.delete(el.dataset.open) : S.open.add(el.dataset.open); renderCases(); });
  const mark = id => { const c = cases.find(x => x.ID === id), v = S.dirty[id] || {};
    if ((v.Review ?? c.Review) === c.Review && (v['Review Comment'] ?? c['Review Comment']) === c['Review Comment']) delete S.dirty[id];
    document.querySelector(`[data-com="${CSS.escape(id)}"]`)?.closest('tr').classList.toggle('dirty', !!S.dirty[id]); updateSavebar(); };
  document.querySelectorAll('[data-rev]').forEach(b => b.onclick = () => {
    const id = b.dataset.rev, c = cases.find(x => x.ID === id), cur = S.dirty[id]?.Review ?? c.Review, v = cur === b.dataset.v ? '' : b.dataset.v;
    S.dirty[id] = { ...(S.dirty[id] || {}), Review: v };
    b.parentElement.querySelectorAll('button').forEach(x => { const on = x.dataset.v === v; x.className = on ? 'on ' + v.toLowerCase() : ''; x.setAttribute('aria-pressed', on); });
    const t = document.querySelector(`[data-com="${CSS.escape(id)}"]`);
    t.hidden = !(v === 'Change' || v === 'Remove' || t.value); t.placeholder = v === 'Change' ? 'What should change? (required)' : 'Comment';
    if (v === 'Change') t.focus();
    mark(id);
  });
  document.querySelectorAll('[data-com]').forEach(t => t.oninput = () => { S.dirty[t.dataset.com] = { ...(S.dirty[t.dataset.com] || {}), 'Review Comment': t.value }; mark(t.dataset.com); });
}
function renderCoverage() {
  const cov = S.data.design.coverage;
  const missing = v => v === 'NO' ? '<span class="pill High">missing</span>' : esc(v);
  $('#dtab').innerHTML = `<p class="small muted">Each approved requirement and the active cases that test it. "Missing" means a negative or boundary case is required and not there yet.</p>
    <div class="table-wrap"><table class="list"><thead><tr><th>Requirement</th><th>P</th><th class="wide">Text</th><th>Cases</th><th>Negative</th><th>Boundary</th></tr></thead><tbody>
    ${cov.map(r => `<tr><td class="id">${reqLinks(r.ID)}</td><td class="p">${esc(r.Priority)}</td><td dir="auto">${esc(r.Text)}</td>
      <td class="small">${r.Cases.length ? `<b>${r.Cases.length}</b> <span class="muted">${esc(short(r.Cases))}</span>` : '<span class="pill High">none</span>'}</td>
      <td class="small">${missing(r.Negative)}</td><td class="small">${missing(r.Boundary)}</td></tr>`).join('')}
    </tbody></table></div>`;
}
function renderAssumptions() {
  const a = S.data.design.assumptions;
  $('#dtab').innerHTML = `<p class="small muted">Questions still open in the analysis that expected results depend on. They are answered when the analysis is reopened; the cases that rely on them are then updated.</p>
    <div class="table-wrap"><table class="list questions"><thead><tr><th>Question</th><th>Severity</th><th class="wide">Text</th><th>Cases relying on it</th></tr></thead><tbody>
    ${a.map(g => `<tr><td class="id">${esc(g.ID)}</td><td class="sev"><span class="pill ${esc(g.Severity)}">${esc(g.Severity)}</span></td><td class="qtext" dir="auto">${esc(g.Question)}</td>
      <td class="small">${g.Cases.length ? esc(short(g.Cases)) : '<span class="muted">none</span>'}</td></tr>`).join('') || '<tr><td colspan="4" class="muted">No open questions.</td></tr>'}
    </tbody></table></div>`;
}
function renderRequests() {
  const d = S.data.design, reqs = d.requirements || [];
  const list = `<div class="table-wrap"><table class="list"><thead><tr><th>Request</th><th class="wide">Text</th><th>By</th><th>Status</th><th class="wide">Answer</th></tr></thead><tbody>
    ${d.requests.map(q => `<tr><td class="id">${esc(q.ID)}</td><td dir="auto">${esc(q.Request)}</td><td class="small">${esc(q['Requested By'])}</td><td class="small">${esc(q.Status)}</td><td dir="auto" class="small">${esc(q.Response)}</td></tr>`).join('') || '<tr><td colspan="5" class="muted">No requests yet.</td></tr>'}
    </tbody></table></div>`;
  if (designApproved()) return $('#dtab').innerHTML = `<p class="small muted">The design is approved: new cases and requests wait until it is reopened.</p>${list}`;
  $('#dtab').innerHTML = `<section class="block"><div class="blockhead"><div class="grow"><h2>Ask TestHive for more cases</h2><p class="small muted">The manual tester answers at its next re-check.</p></div></div><div class="form">
      <label for="rq">What is missing?</label><textarea id="rq" dir="auto" rows="2" placeholder="The scenario or rule that has no case yet"></textarea>
      <label for="rqr">Requirement (optional)</label><input id="rqr" list="dreq"><span></span><span><button id="rqadd">Send request</button></span></div></section>
    <section class="block"><div class="blockhead"><div class="grow"><h2>Requests</h2></div></div>${list}</section>
    <details class="fold"><summary><b>Add a case yourself</b> <span class="small muted">the manual tester completes the type, technique and risk at its re-check</span></summary><div class="form">
      <label for="nc-title">Title</label><input id="nc-title" dir="auto">
      <label for="nc-req">Requirement(s)</label><input id="nc-req" list="dreq" placeholder="REQ-${esc(S.module)}-001; REQ-${esc(S.module)}-002">
      <label for="nc-plat">Platform</label><select id="nc-plat"><option></option>${['Web', 'API', 'Android', 'iOS', 'Both'].map(p => `<option>${p}</option>`).join('')}</select>
      <label for="nc-pre">Preconditions</label><input id="nc-pre" dir="auto">
      <label for="nc-steps">Steps</label><textarea id="nc-steps" dir="auto" rows="3" placeholder="1. ...; 2. ...; 3. ..."></textarea>
      <label for="nc-exp">Expected result</label><textarea id="nc-exp" dir="auto" rows="2" placeholder="Exactly what is seen"></textarea>
      <label for="nc-data">Test data</label><input id="nc-data" dir="auto">
      <label>Tags</label><span class="bar">${TAGS.map(t => `<label class="check"><input type="checkbox" value="${t}" class="nc-tag" ${t === 'regression' ? 'checked' : ''}> ${t}</label>`).join('')}</span>
      <span></span><span><button id="ncadd">Add case</button></span></div></details>
    <datalist id="dreq">${reqs.map(r => `<option value="${esc(r.ID)}">${esc(r.Text.slice(0, 80))}</option>`).join('')}</datalist>`;
  $('#rqadd').onclick = () => { const t = $('#rq').value.trim(); if (!t) return toast('Write the request first.', 'warn');
    saveReview([], [{ ID: '', Request: t, Requirement: $('#rqr').value.trim(), 'Requested By': me() }]); };
  $('#ncadd').onclick = () => {
    const c = { ID: '', Title: $('#nc-title').value, Requirements: $('#nc-req').value, Platform: $('#nc-plat').value, Preconditions: $('#nc-pre').value,
      Steps: $('#nc-steps').value, 'Expected Result': $('#nc-exp').value, 'Test Data': $('#nc-data').value,
      Tags: [...document.querySelectorAll('.nc-tag:checked')].map(x => x.value).join(';'), 'Review Comment': `Added by ${me()}` };
    if (!c.Title.trim() || !c.Steps.trim() || !c['Expected Result'].trim()) return toast('A new case needs a title, steps and an expected result.', 'warn');
    saveReview([c], []);
  };
}
export async function saveReview(extraCases = [], extraAsks = []) {
  if (!me()) return askName(() => saveReview(extraCases, extraAsks));
  const cases = Object.entries(S.dirty).map(([ID, v]) => { const c = S.data.design.cases.find(x => x.ID === ID);
    return { ID, Review: v.Review ?? c.Review, 'Review Comment': v['Review Comment'] ?? c['Review Comment'] }; });
  const missing = cases.filter(c => c.Review === 'Change' && !c['Review Comment'].trim());
  if (missing.length) return toast(`Say what should change for ${missing.map(c => c.ID).join(', ')}.`, 'warn');
  const r = await api('/api/review', { method: 'POST', body: JSON.stringify({ module: S.module, version: S.data.design.version, cases: cases.concat(extraCases), requests: extraAsks }) });
  return afterSave(r);
}
