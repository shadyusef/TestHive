// Approvals tab: approve, reject or reopen each stage (the same rules as stage.sh), and every decision made so far.
import { STAGE_LABEL, STATUS_LABEL, S, $, esc, api, toast, me, askName, ask } from './core.js';
import { openModule } from './module.js';

const PILL = { approved: 'ok', awaiting_approval: 'wait', in_progress: 'Medium', pending: 'Low' };
const list = (items, max = 25) => `<ul class="plain">${items.slice(0, max).map(e => `<li>${esc(e)}</li>`).join('')}${items.length > max ? `<li>… ${items.length - max} more</li>` : ''}</ul>`;

function block(name, s, chk) {
  if (!chk) return '';
  const state = s.status === 'approved' ? (chk.ok ? '' : `<div class="msg warn"><b>${chk.errors.length} items came up after the approval.</b> They are handled when this stage is reopened (for example when the requirements change):${list(chk.errors)}</div>`)
    : chk.ok ? '<div class="msg ok">Ready for approval: every rule passes.</div>' : `<div class="msg bad"><b>Not ready (${chk.errors.length}):</b>${list(chk.errors)}</div>`;
  return `<section class="block"><div class="blockhead"><div class="grow"><h2>${STAGE_LABEL[name]} <span class="pill ${PILL[s.status]}">${esc(STATUS_LABEL[s.status])}</span></h2>
      ${s.status === 'approved' ? `<p class="small muted">Approved by ${esc(s.by)} on ${esc(s.at)}</p>` : ''}</div></div>
    ${state}
    ${chk.warnings.length ? `<details class="fold"><summary><b>${chk.warnings.length} warnings</b> <span class="small muted">worth a look; they do not block the approval</span></summary>${list(chk.warnings, 200)}</details>` : ''}
    ${s.status === 'in_progress' || s.status === 'pending' ? '<p class="small muted">Approval becomes possible when the agent submits this stage.</p>' :
      `<div class="decide"><input class="grow" id="c-${name}" placeholder="Comment (required to reject or reopen)" aria-label="Comment on the ${STAGE_LABEL[name].toLowerCase()}">
      ${s.status === 'awaiting_approval' ? `<button class="primary" data-act="approve" data-st="${name}" ${chk.ok ? '' : 'disabled'}>Approve</button><button class="danger" data-act="reject" data-st="${name}">Reject</button>` : ''}
      ${s.status === 'approved' ? `<button data-act="reopen" data-st="${name}">Reopen (requirements changed)</button>` : ''}</div>`}</section>`;
}

export function renderApprovals() {
  const d = S.data, st = Object.fromEntries(d.stages.map(s => [s.stage, s]));
  $('#tab').innerHTML = block('analysis', st.analysis, d.analysis.check) +
    block('design', st.design, d.design.check || (d.design.baseline ? null : { ok: false, errors: ['The analysis must be approved first.'], warnings: [] })) +
    `<section class="block"><div class="blockhead"><div class="grow"><h2>Decisions</h2><p class="small muted">Also kept in workflow/APPROVALS.md, with the name of whoever decided.</p></div></div>
    <div class="table-wrap"><table class="list"><thead><tr><th>When (UTC)</th><th>Stage</th><th>Decision</th><th>By</th><th class="wide">Comment</th></tr></thead><tbody>
    ${d.approvals.map(a => `<tr><td class="small">${esc(a.When)}</td><td>${esc(a.Stage)}</td><td>${esc(a.Decision)}</td><td class="small">${esc(a.By)}</td><td dir="auto">${esc(a.Comment)}</td></tr>`).join('') || '<tr><td colspan="5" class="muted">No decisions yet.</td></tr>'}
    </tbody></table></div></section>`;
  document.querySelectorAll('[data-act]').forEach(b => b.onclick = async () => {
    if (!me()) return askName();
    const act = b.dataset.act, stg = b.dataset.st, comment = $('#c-' + stg).value.trim();
    if (act !== 'approve' && !comment) return toast('Write a comment: say why.', 'warn');
    const what = { approve: `Approve the ${stg} of ${S.module} as ${me()}? This freezes a baseline.`, reject: `Send the ${stg} back to the agent?`,
      reopen: `Reopen the ${stg}? Later stages go back to in progress and need a new approval.` }[act];
    if (!await ask(what, { ok: { approve: 'Approve', reject: 'Send back', reopen: 'Reopen' }[act], danger: act !== 'approve' })) return;
    const r = await api('/api/stage', { method: 'POST', body: JSON.stringify({ module: S.module, stage: stg, action: act, by: me(), comment }) });
    toast(r.message || r.error || 'Done', r.ok ? 'ok' : 'bad'); openModule(S.module, true);
  });
}
