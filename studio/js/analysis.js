// Analysis tab (stage 1): the questions to answer, your own questions, and the requirements the analyst wrote.
import { TOKEN, S, $, esc, api, toast, me, askName, reqLinks, filterBar, bindFilters, matches, strip, subtabs } from './core.js';
import { bindUploads, afterSave, updateSavebar } from './module.js';

const SEV = ['High', 'Medium', 'Low'];
export const analysisApproved = () => S.data.stages[0].status === 'approved';

export function renderAnalysis() {
  const a = S.data.analysis, gaps = a.gaps, locked = analysisApproved();
  const n = st => gaps.filter(g => g.Status === st).length;
  const high = gaps.filter(g => g.Severity === 'High' && g.Status !== 'Closed').length;
  const reqs = a.requirements.filter(r => r.Status !== 'Removed');
  S.atab = S.atab || 'questions';
  if (!reqs.length && !gaps.length) return $('#tab').innerHTML = `<div class="empty"><h2>No analysis yet</h2>
    <p class="muted">The analyst reads the documents in Sources and writes the requirements and the questions it could not answer from them. Run it from the button at the top.</p></div>`;
  $('#tab').innerHTML = `${locked ? `<div class="msg ok">The analysis is approved, so its questions and answers are read-only (a frozen baseline). To change them, reopen the analysis in the Approvals tab and say why.</div>` : ''}
    ${strip([
      { label: 'Requirements', value: reqs.length, sub: `${reqs.filter(r => r.Priority === 'P0').length} P0 · from ${new Set(reqs.flatMap(r => String(r.Source).match(/[\w.-]+\.[a-z]{2,5}/gi) || [])).size} documents` },
      { label: 'Questions', value: gaps.length, bar: [[n('Closed'), 'var(--text)', 'closed'], [n('Answered'), 'var(--accent)', 'answered'], [n('Open'), 'var(--warn)', 'open']] },
      { label: 'High not closed', value: high, sub: locked ? 'Kept open in the approved baseline' : high ? 'They block the approval' : 'None block the approval' },
      { label: 'Waiting for the analyst', value: n('Answered'), sub: n('Answered') ? 'Answered: run the re-check' : 'Nothing to re-check' },
    ])}
    <div class="tabhead">${subtabs('atab', [['questions', 'Questions', n('Open') ? `<span class="q">${n('Open')} open</span>` : ''], ['requirements', 'Requirements', `<span class="c">${reqs.length}</span>`]])}
      <span class="small muted">Prefer Excel? <a href="/api/workbook?m=${encodeURIComponent(S.module)}&kind=analysis&t=${encodeURIComponent(TOKEN)}">Download the workbook</a>${locked ? '' : ` · <label class="link accent" role="button" tabindex="0">upload a filled one<input type="file" accept=".xlsx" hidden data-upload="analysis"></label>`}</span></div>
    <div id="atab"></div>`;
  document.querySelectorAll('[data-sub^="atab:"]').forEach(b => b.onclick = () => { S.atab = b.dataset.sub.split(':')[1]; renderAnalysis(); });
  bindUploads();
  (S.atab === 'requirements' ? renderRequirements : renderQuestions)();
}

function renderQuestions() {
  const a = S.data.analysis, gaps = a.gaps, locked = analysisApproved(), f = (S.filters.gaps = S.filters.gaps || { status: locked ? '' : 'Open' });
  const shown = gaps.filter(g => matches(g, f, ['ID', 'Question', 'Answer', 'Requirement']) && (!f.severity || g.Severity === f.severity) && (!f.status || g.Status === f.status));
  $('#atab').innerHTML = `${filterBar('gaps', [['severity', 'Severity', SEV], ['status', 'Status', ['Open', 'Answered', 'Closed']]], shown.length)}
    ${locked ? '' : '<p class="small muted">Write your answer under each question; your name is added when you save. Closed questions were settled by the analyst.</p>'}
    <div class="table-wrap"><table class="list questions"><thead><tr><th>ID</th><th>Severity</th><th class="wide">Question</th><th class="wide">Your answer</th><th>Status</th></tr></thead><tbody>
    ${shown.map(g => { const dv = S.dirty[g.ID] || {}, ro = locked || g.Status === 'Closed';
      return `<tr class="${S.dirty[g.ID] ? 'dirty' : ''}"><td class="id">${esc(g.ID)}</td><td class="sev"><span class="pill ${esc(g.Severity)}">${esc(g.Severity)}</span><div class="meta">${esc(g.Kind)}</div></td>
      <td class="qtext" dir="auto">${esc(g.Question)}${g.Requirement ? `<div class="meta">About ${reqLinks(g.Requirement)}</div>` : ''}</td>
      <td class="ansc">${ro ? `<div dir="auto">${esc(g.Answer) || '<span class="muted">No answer</span>'}</div>${g['Answered By'] ? `<div class="meta">${esc(g['Answered By'])}</div>` : ''}` :
        `<textarea dir="auto" class="ans" data-gap="${esc(g.ID)}" rows="2" aria-label="Answer to ${esc(g.ID)}" placeholder="Your answer">${esc(dv.Answer ?? g.Answer)}</textarea>${g['Answered By'] && !dv.Answer ? `<div class="meta">${esc(g['Answered By'])}</div>` : ''}`}</td>
      <td class="status">${esc(dv.Status || g.Status)}</td></tr>`; }).join('') || `<tr><td colspan="5" class="muted">No questions match.</td></tr>`}
    </tbody></table></div>
    ${locked ? '' : `<details class="fold"><summary><b>Ask a question of your own</b> <span class="muted small">the analyst answers it from the documents or asks the product owner</span></summary><div class="form">
      <label for="nq">Question</label><textarea id="nq" dir="auto" rows="2"></textarea>
      <label for="nqr">About requirement(s)</label><input id="nqr" list="reqids" placeholder="e.g. REQ-${esc(S.module)}-003">
      <label for="nqk">Kind</label><select id="nqk"><option>Missing</option><option>Ambiguous</option><option>Conflict</option><option>Untestable</option><option>To confirm</option></select>
      <label for="nqs">Severity</label><select id="nqs"><option>Medium</option><option>High</option><option>Low</option></select>
      <span></span><span><button id="nqadd">Add question</button></span></div>
      <datalist id="reqids">${a.requirements.map(r => `<option value="${esc(r.ID)}">`).join('')}</datalist></details>`}`;
  bindFilters(renderQuestions);
  document.querySelectorAll('[data-gap]').forEach(t => t.oninput = () => {
    const g = gaps.find(x => x.ID === t.dataset.gap), v = t.value;
    if (v.trim() === (g.Answer || '').trim()) delete S.dirty[g.ID]; else S.dirty[g.ID] = { Answer: v, Status: v.trim() ? 'Answered' : 'Open' };
    t.closest('tr').classList.toggle('dirty', !!S.dirty[g.ID]); t.closest('tr').lastElementChild.textContent = S.dirty[g.ID]?.Status || g.Status; updateSavebar();
  });
  if ($('#nqadd')) $('#nqadd').onclick = async () => {
    const q = $('#nq').value.trim(); if (!q) return toast('Write the question first.', 'warn');
    await saveAnswers([{ ID: '', Question: q, Requirement: $('#nqr').value.trim(), Kind: $('#nqk').value, Severity: $('#nqs').value }]);
  };
}

function renderRequirements() {
  const reqs = S.data.analysis.requirements, f = (S.filters.reqs = S.filters.reqs || {});
  const shown = reqs.filter(r => matches(r, f, ['ID', 'Text', 'Source', 'Notes']) && (!f.priority || r.Priority === f.priority) && (!f.type || r.Type === f.type));
  $('#atab').innerHTML = `${filterBar('reqs', [['priority', 'Priority', ['P0', 'P1', 'P2', 'P3']], ['type', 'Type', [...new Set(reqs.map(r => r.Type))].filter(Boolean).sort()]], shown.length)}
    <p class="small muted">Read-only: the analyst maintains them from the documents and your answers. Click an ID to see its questions and test cases.</p>
    <div class="table-wrap"><table class="list"><thead><tr><th>ID</th><th>Priority</th><th>Type</th><th class="wide">Requirement</th><th>Source</th><th>Status</th></tr></thead><tbody>
    ${shown.map(r => `<tr class="${r.Status === 'Removed' ? 'removed' : ''}"><td class="id">${reqLinks(r.ID)}</td><td>${esc(r.Priority)}</td><td class="small">${esc(r.Type)}</td>
      <td dir="auto">${esc(r.Text)}</td><td class="small muted">${esc(r.Source)}${r.Section ? `<div>${esc(r.Section)}</div>` : ''}</td><td class="small">${esc(r.Status)}</td></tr>`).join('') || '<tr><td colspan="6" class="muted">No requirements match.</td></tr>'}
    </tbody></table></div>`;
  bindFilters(renderRequirements);
}

export async function saveAnswers(extra = []) {
  if (!me()) return askName(() => saveAnswers(extra));
  const rows = Object.entries(S.dirty).map(([ID, v]) => ({ ID, Answer: v.Answer.trim(), 'Answered By': v.Answer.trim() ? me() : '', Status: v.Status })).concat(extra);
  const r = await api('/api/answers', { method: 'POST', body: JSON.stringify({ module: S.module, version: S.data.analysis.version, rows }) });
  return afterSave(r);
}
