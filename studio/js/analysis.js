// Analysis tab: the questions to answer and the requirements.
import { TOKEN, S, $, esc, api, toast, me, askName, reqLinks, chip, filterBar, bindFilters, matches } from './core.js';
import { bindUploads, afterSave, updateSavebar } from './module.js';

/* ---------- Analysis ---------- */
export function renderAnalysis() {
  const a = S.data.analysis, gaps = a.gaps, f = (S.filters.gaps = S.filters.gaps || { status: 'Open' });
  const shown = gaps.filter(g => matches(g, f, ['ID', 'Question', 'Answer', 'Requirement']) && (!f.severity || g.Severity === f.severity) && (!f.status || g.Status === f.status));
  const cnt = (k, v) => gaps.filter(g => g[k] === v).length;
  const approved = S.data.stages[0].status === 'approved';
  $('#tab').innerHTML = `${approved ? `<div class="msg ok">The analysis is approved. Answers and questions you add now are kept for the next analysis round; to use them now, reopen the analysis in the Approvals tab.</div>` : ''}
    <div class="card"><div class="stats">
      <div class="stat"><b>${a.requirements.length}</b>requirements</div><div class="stat"><b>${gaps.length}</b>questions</div>
      <div class="stat"><b>${cnt('Status', 'Open')}</b>open</div><div class="stat"><b>${gaps.filter(g => g.Severity === 'High' && g.Status !== 'Closed').length}</b>High not closed</div>
      <div class="stat"><b>${cnt('Status', 'Answered')}</b>answered, waiting for the analyst</div></div>
      <p class="small muted">Answer in the yellow column; your name is added. Closed questions were settled by the analyst. Prefer Excel? <a href="/api/workbook?m=${encodeURIComponent(S.module)}&kind=analysis&t=${encodeURIComponent(TOKEN)}">Download the workbook</a> · <label class="crumb">upload a filled one<input type="file" accept=".xlsx" hidden data-upload="analysis"></label></p></div>
    ${filterBar('gaps', [['severity', 'Severity', ['High', 'Medium', 'Low']], ['status', 'Status', ['Open', 'Answered', 'Closed']]])}
    <div class="table-wrap"><table><thead><tr><th>ID</th><th>Severity</th><th style="min-width:300px">Question</th><th style="min-width:300px">Your answer</th><th>Status</th></tr></thead><tbody>
    ${shown.map(g => { const dv = S.dirty[g.ID] || {}; const closed = g.Status === 'Closed';
      return `<tr class="${S.dirty[g.ID] ? 'dirty' : ''}"><td class="id">${esc(g.ID)}</td><td><span class="chip sev-${esc(g.Severity)}">${esc(g.Severity)}</span><div class="small muted">${esc(g.Kind)}</div></td>
      <td dir="auto">${esc(g.Question)}${g.Requirement ? `<div class="small muted">About ${reqLinks(g.Requirement)}</div>` : ''}</td>
      <td>${closed ? `<div dir="auto">${esc(g.Answer)}</div><div class="small muted">${esc(g['Answered By'])}</div>` :
        `<textarea dir="auto" class="edit" data-gap="${esc(g.ID)}" rows="2">${esc(dv.Answer ?? g.Answer)}</textarea>${g['Answered By'] && !dv.Answer ? `<div class="small muted">${esc(g['Answered By'])}</div>` : ''}`}</td>
      <td>${closed ? 'Closed' : esc(dv.Status || g.Status)}</td></tr>`; }).join('') || `<tr><td colspan="5" class="muted">No questions match.</td></tr>`}
    </tbody></table></div>
    <div class="card" style="margin-top:14px"><h3 style="margin-top:0">Ask a question of your own</h3><div class="form">
      <label>Question</label><textarea id="nq" dir="auto" rows="2"></textarea>
      <label>About requirement(s)</label><input id="nqr" list="reqids" placeholder="e.g. REQ-${esc(S.module)}-003">
      <label>Kind</label><select id="nqk"><option>Missing</option><option>Ambiguous</option><option>Conflict</option><option>Untestable</option><option>To confirm</option></select>
      <label>Severity</label><select id="nqs"><option>Medium</option><option>High</option><option>Low</option></select>
      <span></span><span><button id="nqadd">Add question</button></span></div>
      <datalist id="reqids">${a.requirements.map(r => `<option value="${esc(r.ID)}">`).join('')}</datalist></div>
    <details class="card"><summary><b>Requirements (${a.requirements.length})</b> <span class="small muted">read-only; the analyst maintains them</span></summary>
      <div class="table-wrap" style="margin-top:10px"><table><thead><tr><th>ID</th><th>Priority</th><th>Type</th><th>Status</th><th>Requirement</th><th>Source</th></tr></thead><tbody>
      ${a.requirements.map(r => `<tr class="${r.Status === 'Removed' ? 'removed' : ''}"><td class="id">${reqLinks(r.ID)}</td><td>${esc(r.Priority)}</td><td>${esc(r.Type)}</td><td>${esc(r.Status)}</td><td dir="auto">${esc(r.Text)}</td><td class="small muted">${esc(r.Source)}</td></tr>`).join('')}
      </tbody></table></div></details>`;
  bindFilters(renderAnalysis); bindUploads();
  document.querySelectorAll('[data-gap]').forEach(t => t.oninput = () => {
    const g = gaps.find(x => x.ID === t.dataset.gap), v = t.value;
    if (v.trim() === (g.Answer || '').trim()) delete S.dirty[g.ID]; else S.dirty[g.ID] = { Answer: v, Status: v.trim() ? 'Answered' : 'Open' };
    t.closest('tr').classList.toggle('dirty', !!S.dirty[g.ID]); t.closest('tr').lastElementChild.textContent = S.dirty[g.ID]?.Status || g.Status; updateSavebar();
  });
  $('#nqadd').onclick = async () => {
    const q = $('#nq').value.trim(); if (!q) return toast('Write the question first.', 'warn');
    await saveAnswers([{ ID: '', Question: q, Requirement: $('#nqr').value.trim(), Kind: $('#nqk').value, Severity: $('#nqs').value }]);
  };
}
export async function saveAnswers(extra = []) {
  if (!me()) return askName(() => saveAnswers(extra));
  const rows = Object.entries(S.dirty).map(([ID, v]) => ({ ID, Answer: v.Answer.trim(), 'Answered By': v.Answer.trim() ? me() : '', Status: v.Status })).concat(extra);
  const r = await api('/api/answers', { method: 'POST', body: JSON.stringify({ module: S.module, version: S.data.analysis.version, rows }) });
  return afterSave(r);
}
