// Reports tab (stage 6): the bug register (report a bug, change its status), the HTML report of the approved test cycle with
// TestHive's Go / No-go suggestion, and the decision a named person signs. The rules are report.py's (scripts/bug.sh, report.sh).
import { TOKEN, S, $, esc, api, toast, ask, me, askName } from './core.js';
import { openModule } from './module.js';

const SEV = { Blocker: 'High', Major: 'Medium', Minor: 'Low' };
const STAT = { Open: 'High', Fixed: 'wait', Verified: 'ok', "Won't fix": 'Low' };

async function post(path, body) {
  if (!me()) { askName(); return false; }
  const r = await api(path, { method: 'POST', body: JSON.stringify({ module: S.module, by: me(), ...body }) });
  toast(r.message || r.error, r.ok ? 'ok' : 'bad'); if (r.ok) openModule(S.module, true);
  return r.ok;
}

export function renderReports() {
  const d = S.data, b = d.bugs, r = d.reporting, pre = S.bugPrefill || {}, off = S.agents === 'review' || !!d.job, signed = d.stages[5].status === 'approved';
  const rep = r && r.report, dec = r && r.decision;
  $('#tab').innerHTML = `${signed ? '<div class="msg ok">Signed off: the report and the decision are recorded in a baseline. A new release starts with a new test cycle.</div>' : ''}
    <section class="block"><div class="blockhead"><div class="grow"><h2>Test report</h2>
      <p class="small muted">${r ? 'One page from the approved test cycle: results, bugs, requirements covered, trends and cost. It opens offline and prints to PDF.' : 'The report is built once the test cycle (execution) is approved.'}</p></div>
      ${r ? `<button id="rbuild" ${off ? 'disabled' : ''}>${rep ? 'Build it again' : 'Build the report'}</button>${rep ? ` <a class="btnlike" href="/api/report-file?m=${encodeURIComponent(S.module)}&t=${encodeURIComponent(TOKEN)}" target="_blank" rel="noopener noreferrer">Open the report</a>` : ''}` : ''}</div>
      ${rep ? `<div class="msg ${rep.suggestion === 'Go' ? 'ok' : rep.suggestion === 'No-go' ? 'bad' : 'warn'}"><b>TestHive suggests: ${esc(rep.suggestion)}</b> <span class="small muted">built ${esc(rep.built_at.replace('T', ' ').slice(0, 16))} UTC from execution ${esc(rep.execution)}; the reasons are in the report.</span></div>` : ''}
      ${r && r.check.errors.length ? `<ul class="plain small">${r.check.errors.map(e => `<li>${esc(e)}</li>`).join('')}</ul>` : ''}
    </section>
    ${rep ? `<section class="block"><div class="blockhead"><div class="grow"><h2>Go or No-go</h2>
      <p class="small muted">${dec ? `Decided <b>${esc(dec.decision)}</b> by ${esc(dec.by)} on ${esc(dec.at.slice(0, 10))}: ${esc(dec.reason)}` : 'A named person decides, with the reason. Go is refused while a Blocker bug is open.'}</p></div></div>
      ${signed ? '' : `<div class="decide"><select id="dgo" aria-label="Decision"><option>Go</option><option>No-go</option></select>
        <input id="dwhy" class="grow" placeholder="Reason (required)" aria-label="Reason for the decision" maxlength="300"><button class="primary" id="dsave" ${off ? 'disabled' : ''}>Record the decision</button></div>`}</section>` : ''}
    <section class="block"><div class="blockhead"><div class="grow"><h2>Bugs <span class="muted small">${b.rows.length} in reports/bugs.csv</span></h2>
      <p class="small muted">Real app bugs. Marking one Fixed asks for a retest of its cases in the open test cycle.</p></div></div>
      ${b.problems.length ? `<div class="msg bad"><b>The register breaks its rules:</b><ul class="plain">${b.problems.map(p => `<li>${esc(p)}</li>`).join('')}</ul></div>` : ''}
      <div class="table-wrap"><table class="list"><thead><tr><th>ID</th><th>Severity</th><th class="wide">Bug</th><th>Cases</th><th>Found in</th><th class="status">Status</th></tr></thead><tbody>
      ${b.rows.map(x => `<tr><td class="id">${esc(x.ID)}</td><td><span class="pill ${SEV[x.Severity] || ''}">${esc(x.Severity)}</span></td>
        <td dir="auto">${esc(x.Title)}<div class="meta">${[x.Steps, x.Expected && 'expected: ' + x.Expected, x.Actual && 'actual: ' + x.Actual, x.Evidence].filter(Boolean).map(esc).join(' · ')}</div></td>
        <td class="small">${esc(x.Cases)}</td><td class="small">${esc([x.Cycle, x.Env, x.Target].filter(Boolean).join(' · '))}</td>
        <td class="status"><select data-bug="${esc(x.ID)}" aria-label="Status of ${esc(x.ID)}" ${signed ? 'disabled' : ''}>${b.status.map(s => `<option ${s === x.Status ? 'selected' : ''}>${esc(s)}</option>`).join('')}</select></td></tr>`).join('') ||
        '<tr><td colspan="6" class="muted">No bugs reported.</td></tr>'}</tbody></table></div></section>
    <section class="block"><div class="blockhead"><div class="grow"><h2>Report a bug</h2><p class="small muted">${pre.cases ? `From the failed case ${esc(pre.cases)}.` : 'The case IDs it affects, and what happened.'}</p></div></div>
      <div class="form">
        <label for="bt">Title</label><input id="bt" maxlength="300" value="${esc(pre.title || '')}">
        <label for="bs">Severity</label><select id="bs">${b.severity.map(s => `<option>${esc(s)}</option>`).join('')}</select>
        <label for="bc">Cases</label><input id="bc" placeholder="TC-${esc(S.module)}-001, ..." value="${esc(pre.cases || '')}">
        <label for="bst">Steps</label><input id="bst" maxlength="300" value="${esc(pre.steps || '')}">
        <label for="bex">Expected</label><input id="bex" maxlength="300" value="${esc(pre.expected || '')}">
        <label for="bac">Actual</label><input id="bac" maxlength="300">
        <label for="bev">Evidence</label><input id="bev" placeholder="R-…/evidence/…" value="${esc(pre.evidence || '')}">
        <span></span><div><button class="primary" id="badd" ${signed ? 'disabled' : ''}>Report the bug</button></div></div></section>`;
  if ($('#rbuild')) $('#rbuild').onclick = async () => {
    const x = await api('/api/run', { method: 'POST', body: JSON.stringify({ module: S.module, action: 'report' }) });
    toast(x.message || x.error, x.ok ? 'ok' : 'bad'); if (x.ok) openModule(S.module, true);
  };
  if ($('#dsave')) $('#dsave').onclick = async () => {
    const decision = $('#dgo').value, reason = $('#dwhy').value.trim();
    if (!reason) return toast('Say why: the reason is part of the decision.', 'warn');
    if (await ask(`Record ${decision} for ${S.module}, signed ${me() || '(your name)'}?`, { ok: 'Record', danger: decision === 'Go' && rep.suggestion === 'No-go' })) post('/api/report-decision', { decision, reason });
  };
  document.querySelectorAll('[data-bug]').forEach(s => s.onchange = async () => {
    if (await ask(`Mark ${s.dataset.bug} as ${s.value}?${s.value === 'Fixed' ? ' Its cases are then retested in the open test cycle.' : ''}`, { ok: 'Save' })) post('/api/bugs', { action: 'status', id: s.dataset.bug, status: s.value });
    else openModule(S.module, true);
  });
  $('#badd').onclick = async () => {
    const v = id => $('#' + id).value.trim(), body = { action: 'add', title: v('bt'), severity: v('bs'), cases: v('bc'), steps: v('bst'), expected: v('bex'), actual: v('bac'), evidence: v('bev') };
    if (!body.title || !body.cases) return toast('A bug needs a title and the cases it affects.', 'warn');
    if (await post('/api/bugs', body)) S.bugPrefill = null;
  };
}
