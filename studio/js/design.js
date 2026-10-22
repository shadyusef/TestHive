// Design tab: test cases and their review, coverage, open questions, requests.
import { TOKEN, S, $, esc, api, toast, me, askName, reqLinks, chip, filterBar, bindFilters, matches } from './core.js';
import { bindUploads, afterSave, updateSavebar } from './module.js';

/* ---------- Design ---------- */
export const TAGS = ['smoke', 'sanity', 'regression', 'e2e'];
export function renderDesign() {
  const d = S.data.design;
  if (!d.baseline) return $('#tab').innerHTML = `<div class="card"><p>Test design starts when the analysis is approved (see the Approvals tab).</p></div>`;
  if (!d.cases.length) return $('#tab').innerHTML = `<div class="card"><p>No test cases yet. In Claude Code: <code>/th-manual ${esc(S.module)}</code></p></div>`;
  const act = d.cases.filter(c => c.Status !== 'Removed'), covered = d.coverage.filter(r => r.Cases.length).length;
  const reviewed = act.filter(c => c.Review).length, frozen = designApproved();
  $('#tab').innerHTML = `${frozen ? `<div class="msg ok">The design is approved, so the cases are read-only (a frozen baseline). To change them, reopen the design in the Approvals tab and say why.</div>` : ''}
    <div class="card"><div class="stats">
      <div class="stat"><b>${act.length}</b>active cases</div><div class="stat"><b>${covered}/${d.coverage.length}</b>requirements covered</div>
      ${['P0', 'P1', 'P2', 'P3'].map(p => `<div class="stat"><b>${act.filter(c => c.Priority === p).length}</b>${p}</div>`).join('')}
      <div class="stat"><b>${reviewed}</b>reviewed</div><div class="stat"><b>${d.requests.filter(q => q.Status === 'Open').length}</b>open requests</div></div>
      <p class="small muted">Designed from analysis baseline ${esc(d.baseline)}. ${frozen ? '' : 'Review each case: Accepted, Change (say what) or Remove. Prefer Excel? '}<a href="/api/workbook?m=${encodeURIComponent(S.module)}&kind=design&t=${encodeURIComponent(TOKEN)}">Download the workbook</a>${frozen ? '' : ` · <label class="crumb">upload a filled one<input type="file" accept=".xlsx" hidden data-upload="design"></label>`}</p></div>
    <div class="tabs">${[['cases', 'Cases'], ['coverage', 'Coverage'], ['assumptions', 'Open questions'], ['requests', 'Requests and new cases']].map(([k, l]) => `<button data-dtab="${k}" class="${S.dtab === k ? 'on' : ''}">${l}</button>`).join('')}</div><div id="dtab"></div>`;
  document.querySelectorAll('[data-dtab]').forEach(b => b.onclick = () => { S.dtab = b.dataset.dtab; renderDesign(); updateSavebar(); });
  bindUploads();
  ({ cases: renderCases, coverage: renderCoverage, assumptions: renderAssumptions, requests: renderRequests })[S.dtab]();
}
export function renderCases() {
  const cases = S.data.design.cases, f = (S.filters.cases = S.filters.cases || { state: 'Active' });
  const shown = cases.filter(c => matches(c, f, ['ID', 'Title', 'Steps', 'Expected Result', 'Requirements']) && (!f.priority || c.Priority === f.priority) &&
    (!f.tag || c.Tags.split(/[;,]/).map(x => x.trim()).includes(f.tag)) && (!f.platform || c.Platform === f.platform) &&
    (!f.review || (f.review === 'Not reviewed' ? !c.Review : c.Review === f.review)) && (f.state !== 'Active' || c.Status !== 'Removed') && (f.state !== 'Removed' || c.Status === 'Removed'));
  $('#dtab').innerHTML = filterBar('cases', [['priority', 'Priority', ['P0', 'P1', 'P2', 'P3']], ['tag', 'Tag', TAGS], ['platform', 'Platform', ['Web', 'API', 'Android', 'iOS', 'Both']],
      ['review', 'Review', ['Not reviewed', 'Accepted', 'Change', 'Remove', 'Updated']], ['state', 'Cases', ['Active', 'Removed']]]) +
    `<p class="small muted">${shown.length} shown. Click a title for steps and expected result.</p>
    <div class="table-wrap"><table><thead><tr><th>ID</th><th>P</th><th style="min-width:280px">Title</th><th>Type · technique</th><th>Tags</th><th>Review</th><th style="min-width:220px">Comment</th></tr></thead><tbody>
    ${shown.map(c => { const dv = S.dirty[c.ID] || {}; const rev = dv.Review ?? c.Review; const locked = c.Status === 'Removed' || designApproved();
      return `<tr class="${S.dirty[c.ID] ? 'dirty' : ''} ${locked ? 'removed' : ''}"><td class="id">${esc(c.ID)}</td><td>${esc(c.Priority)}</td>
        <td><span class="crumb" data-open="${esc(c.ID)}" dir="auto">${esc(c.Title)}</span><div class="small muted">${esc(c.Platform)} · ${reqLinks(c.Requirements)}${c.Origin !== 'Designed' ? ' · added by ' + (c.Origin === 'Human' ? 'a person' : 'request') : ''}</div></td>
        <td class="small">${esc(c.Type)}<br><span class="muted">${esc(c.Technique)} · risk ${esc(c.Risk)}</span></td><td class="small">${esc(c.Tags)}</td>
        <td>${locked ? (c.Status === 'Removed' ? 'Removed' : esc(c.Review) || '—') : `<select class="edit" aria-label="Review of ${esc(c.ID)}" data-rev="${esc(c.ID)}"><option value="">—</option>${['Accepted', 'Change', 'Remove'].map(o => `<option ${rev === o ? 'selected' : ''}>${o}</option>`).join('')}${c.Review === 'Updated' ? `<option ${rev === 'Updated' ? 'selected' : ''} value="Updated">Updated by designer</option>` : ''}</select>`}</td>
        <td>${locked ? `<span class="small muted">${esc(c['Review Comment'])}</span>` : `<textarea dir="auto" class="edit" rows="1" data-com="${esc(c.ID)}" placeholder="${rev === 'Change' ? 'What should change? (required)' : ''}">${esc(dv['Review Comment'] ?? c['Review Comment'])}</textarea>`}</td></tr>
        ${S.open.has(c.ID) ? `<tr class="detail"><td></td><td colspan="6"><dl>
          <dt>Preconditions</dt><dd dir="auto">${esc(c.Preconditions)}</dd><dt>Steps</dt><dd dir="auto">${esc(c.Steps).replace(/; (\d+\.)/g, '<br>$1')}</dd>
          <dt>Expected result</dt><dd dir="auto"><b>${esc(c['Expected Result'])}</b></dd><dt>Test data</dt><dd dir="auto">${esc(c['Test Data'])}</dd>
          <dt>Depends on open questions</dt><dd>${esc(c.Assumption) || '—'}</dd><dt>Status</dt><dd>${esc(c.Status)}</dd></dl></td></tr>` : ''}`; }).join('') || `<tr><td colspan="7" class="muted">No cases match.</td></tr>`}
    </tbody></table></div>`;
  bindFilters(renderCases);
  document.querySelectorAll('[data-open]').forEach(el => el.onclick = () => { S.open.has(el.dataset.open) ? S.open.delete(el.dataset.open) : S.open.add(el.dataset.open); renderCases(); });
  const mark = id => { const c = cases.find(x => x.ID === id), v = S.dirty[id] || {};
    const rev = v.Review ?? c.Review, com = v['Review Comment'] ?? c['Review Comment'];
    if (rev === c.Review && com === c['Review Comment']) delete S.dirty[id]; updateSavebar();
    document.querySelector(`[data-rev="${id}"]`)?.closest('tr').classList.toggle('dirty', !!S.dirty[id]); };
  document.querySelectorAll('[data-rev]').forEach(s => s.onchange = () => { S.dirty[s.dataset.rev] = { ...(S.dirty[s.dataset.rev] || {}), Review: s.value }; mark(s.dataset.rev);
    const t = document.querySelector(`[data-com="${s.dataset.rev}"]`); if (t) { t.placeholder = s.value === 'Change' ? 'What should change? (required)' : ''; if (s.value === 'Change') t.focus(); } });
  document.querySelectorAll('[data-com]').forEach(t => t.oninput = () => { S.dirty[t.dataset.com] = { ...(S.dirty[t.dataset.com] || {}), 'Review Comment': t.value }; mark(t.dataset.com); });
}
export function renderCoverage() {
  const cov = S.data.design.coverage;
  $('#dtab').innerHTML = `<p class="small muted">Each approved requirement and the active cases that test it. "NO" means a negative or boundary case is required and missing.</p>
    <div class="table-wrap"><table><thead><tr><th>Requirement</th><th>P</th><th style="min-width:320px">Text</th><th>Cases</th><th>Negative</th><th>Boundary</th></tr></thead><tbody>
    ${cov.map(r => `<tr><td class="id">${reqLinks(r.ID)}</td><td>${esc(r.Priority)}</td><td dir="auto">${esc(r.Text)}</td>
      <td class="small"><b>${r.Cases.length}</b> ${esc(r.Cases.map(x => x.replace(/^TC-[A-Z0-9]+-/, '')).join(', '))}</td>
      <td>${r.Negative === 'NO' ? '<span class="chip sev-High">missing</span>' : esc(r.Negative)}</td><td>${r.Boundary === 'NO' ? '<span class="chip sev-High">missing</span>' : esc(r.Boundary)}</td></tr>`).join('')}
    </tbody></table></div>`;
}
export function renderAssumptions() {
  const a = S.data.design.assumptions;
  $('#dtab').innerHTML = `<p class="small muted">Open questions the expected results depend on. Answer them in the Analysis tab; the analyst takes them into the next analysis round.</p>
    <div class="table-wrap"><table><thead><tr><th>Question</th><th>Severity</th><th style="min-width:360px">Text</th><th>Cases relying on it</th></tr></thead><tbody>
    ${a.map(g => `<tr><td class="id">${esc(g.ID)}</td><td><span class="chip sev-${esc(g.Severity)}">${esc(g.Severity)}</span></td><td dir="auto">${esc(g.Question)}</td>
      <td class="small">${g.Cases.length ? esc(g.Cases.map(x => x.replace(/^TC-[A-Z0-9]+-/, '')).join(', ')) : '<span class="muted">none</span>'}</td></tr>`).join('') || '<tr><td colspan="4" class="muted">No open questions.</td></tr>'}
    </tbody></table></div>`;
}
export function designApproved() { return S.data.stages[1].status === 'approved'; }
export function renderRequests() {
  const d = S.data.design, reqs = d.requirements || [];
  const list = `<div class="table-wrap"><table><thead><tr><th>Request</th><th style="min-width:300px">Text</th><th>By</th><th>Status</th><th style="min-width:240px">Answer</th></tr></thead><tbody>
    ${d.requests.map(q => `<tr><td class="id">${esc(q.ID)}</td><td dir="auto">${esc(q.Request)}</td><td>${esc(q['Requested By'])}</td><td>${esc(q.Status)}</td><td dir="auto" class="small">${esc(q.Response)}</td></tr>`).join('') || '<tr><td colspan="5" class="muted">No requests yet.</td></tr>'}
    </tbody></table></div>`;
  if (designApproved()) return $('#dtab').innerHTML = `<p class="small muted">The design is approved: new cases and requests wait until it is reopened.</p>${list}`;
  $('#dtab').innerHTML = `<div class="card"><h3 style="margin-top:0">Ask TestHive for more cases</h3><div class="form">
      <label>What is missing?</label><textarea id="rq" dir="auto" rows="2" placeholder="e.g. Add cases for pasting the code into the first box"></textarea>
      <label>Requirement (optional)</label><input id="rqr" list="dreq"><span></span><span><button id="rqadd">Send request</button></span></div></div>
    <div class="card"><h3 style="margin-top:0">Add a case yourself</h3><div class="form">
      <label>Title</label><input id="nc-title" dir="auto">
      <label>Requirement(s)</label><input id="nc-req" list="dreq" placeholder="REQ-${esc(S.module)}-001; REQ-${esc(S.module)}-002">
      <label>Platform</label><select id="nc-plat"><option></option>${['Web', 'API', 'Android', 'iOS', 'Both'].map(p => `<option>${p}</option>`).join('')}</select>
      <label>Preconditions</label><input id="nc-pre" dir="auto">
      <label>Steps</label><textarea id="nc-steps" dir="auto" rows="3" placeholder="1. ...; 2. ...; 3. ..."></textarea>
      <label>Expected result</label><textarea id="nc-exp" dir="auto" rows="2" placeholder="Exactly what is seen"></textarea>
      <label>Test data</label><input id="nc-data" dir="auto">
      <label>Tags</label><span>${TAGS.map(t => `<label style="margin-inline-end:10px"><input type="checkbox" value="${t}" class="nc-tag" ${t === 'regression' ? 'checked' : ''}> ${t}</label>`).join('')}</span>
      <span></span><span><button id="ncadd">Add case</button> <span class="small muted">The manual-tester completes the rest (type, technique, risk) at its re-check.</span></span></div>
      <datalist id="dreq">${reqs.map(r => `<option value="${esc(r.ID)}">${esc(r.Text.slice(0, 80))}</option>`).join('')}</datalist></div>${list}`;
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
