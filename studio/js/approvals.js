// Approvals tab: approve, reject or reopen a stage; the decisions log.
import { STAGE_LABEL, S, $, esc, api, toast, me, askName, ask, chip } from './core.js';
import { openModule } from './module.js';

/* ---------- Approvals ---------- */
export function renderApprovals() {
  const d = S.data, st = Object.fromEntries(d.stages.map(s => [s.stage, s]));
  const block = (name, chk) => { const s = st[name]; if (!chk) return '';
    return `<div class="card"><h3 style="margin-top:0">${STAGE_LABEL[name]} ${chip(name, s.status)} ${s.status === 'approved' ? `<span class="small muted">by ${esc(s.by)} ${esc(s.at)}</span>` : ''}</h3>
      ${s.status === 'approved' ? (chk.ok ? '' : `<div class="msg warn"><b>${chk.errors.length} items came up after the approval.</b> They are handled when this stage is reopened (for example when the requirements change):<ul class="plain">${chk.errors.slice(0, 25).map(e => `<li>${esc(e)}</li>`).join('')}</ul></div>`) :
        chk.ok ? `<div class="msg ok">Ready for approval: every rule passes.</div>` : `<div class="msg bad"><b>Not ready (${chk.errors.length}):</b><ul class="plain">${chk.errors.slice(0, 25).map(e => `<li>${esc(e)}</li>`).join('')}${chk.errors.length > 25 ? `<li>… ${chk.errors.length - 25} more</li>` : ''}</ul></div>`}
      ${chk.warnings.length ? `<details><summary class="small">${chk.warnings.length} warnings</summary><ul class="plain small">${chk.warnings.map(w => `<li>${esc(w)}</li>`).join('')}</ul></details>` : ''}
      <div class="bar" style="margin-top:10px"><input class="grow" id="c-${name}" placeholder="Comment (required to reject or reopen)">
        ${s.status === 'awaiting_approval' ? `<button class="primary" data-act="approve" data-st="${name}" ${chk.ok ? '' : 'disabled'}>Approve</button><button class="danger" data-act="reject" data-st="${name}">Reject</button>` : ''}
        ${s.status === 'approved' ? `<button data-act="reopen" data-st="${name}">Reopen (requirements changed)</button>` : ''}
        ${s.status === 'in_progress' || s.status === 'pending' ? `<span class="small muted">Approval becomes possible when the agent submits this stage.</span>` : ''}</div></div>`; };
  $('#tab').innerHTML = block('analysis', d.analysis.check) + block('design', d.design.check || (d.design.baseline ? null : { ok: false, errors: ['The analysis must be approved first.'], warnings: [] })) +
    `<h3>Decisions</h3><div class="table-wrap"><table><thead><tr><th>When (UTC)</th><th>Stage</th><th>Decision</th><th>By</th><th>Comment</th></tr></thead><tbody>
    ${d.approvals.map(a => `<tr><td class="small">${esc(a.When)}</td><td>${esc(a.Stage)}</td><td>${esc(a.Decision)}</td><td>${esc(a.By)}</td><td dir="auto">${esc(a.Comment)}</td></tr>`).join('') || '<tr><td colspan="5" class="muted">No decisions yet.</td></tr>'}
    </tbody></table></div>`;
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
