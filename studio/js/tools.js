// Tools tab (stage 3, functional tests): the decision matrix per test type, the human's choice with a reason, weights and team skills.
import { S, $, esc, api, toast, me, askName, strip } from './core.js';
import { afterSave, updateSavebar } from './module.js';

export const toolsApproved = () => S.data.stages[2].status === 'approved';
const key = t => 'tool:' + t;  // S.dirty key of one test type's choice

export function renderTools() {
  const t = S.data.tools, a = t.advice;
  if (!a) return $('#tab').innerHTML = `<div class="empty"><h2>Tool advice starts after the test cases</h2>
    <p class="muted">When the design is approved, TestHive groups its functional cases into test types and recommends a tool for each.</p></div>`;
  const frozen = toolsApproved(), mine = Object.fromEntries(t.choices.map(c => [c['Test Type'], c]));
  const pick = x => S.dirty[key(x.type)] || { tool: mine[x.type]?.Chosen || '', reason: mine[x.type]?.Reason || '' };
  const chosen = a.types.filter(x => pick(x).tool).length, cases = a.types.reduce((n, x) => n + x.cases, 0);
  $('#tab').innerHTML = `${frozen ? '<div class="msg ok">The tool choice is approved (a frozen baseline). To change it, reopen the tools stage in the Approvals tab and say why.</div>' : ''}
    ${strip([
      { label: 'Test types', value: a.types.length, sub: `from design baseline ${esc(a.design_baseline)}` },
      { label: 'Cases to automate', value: cases, sub: `functional cases marked Yes or Candidate · ${a.manual} stay manual` },
      { label: 'Tools chosen', value: chosen, of: a.types.length, sub: chosen === a.types.length ? 'every test type has its tool' : 'choose one per test type' },
      { label: 'Not covered yet', value: a.other, sub: 'accessibility, security and performance cases: tool advice comes later' },
    ])}
    <p class="small muted">Scores are TestHive's starting judgement on each criterion (1 to 5), weighted by your settings below. The best total is recommended; choose another with a reason.</p>
    ${a.types.map(x => typeBlock(x, pick(x), mine[x.type], frozen, t.criteria)).join('') || `<div class="empty"><h2>Nothing to choose</h2>
      <p class="muted">Design ${esc(a.design_baseline)} has no functional cases marked for automation.${frozen ? '' : ' Submit the stage as it is, or reopen the design to mark cases for automation.'}</p>
      ${frozen ? '' : '<button class="primary" id="toolsave">Submit with nothing to choose</button>'}</div>`}
    ${a.types.length && !frozen ? '<div class="decide"><span class="grow small muted">Saving every choice submits the tools stage; a named person approves it in the Approvals tab.</span><button class="primary" id="toolsave">Save the choices</button></div>' : ''}
    ${settingsFold(t, frozen)}`;
  document.querySelectorAll('[data-pick]').forEach(r => r.onchange = () => { const tt = r.dataset.pick;
    S.dirty[key(tt)] = { ...pick(a.types.find(x => x.type === tt)), tool: r.value }; renderTools(); updateSavebar(); });
  document.querySelectorAll('[data-why]').forEach(i => i.oninput = () => { const tt = i.dataset.why;
    S.dirty[key(tt)] = { ...pick(a.types.find(x => x.type === tt)), reason: i.value }; updateSavebar(); });
  document.querySelectorAll('[data-w],[data-skill]').forEach(i => i.onchange = () => { S.dirty.settings = 1; updateSavebar(); });
  if ($('#toolsave')) $('#toolsave').onclick = saveTools;
}

function typeBlock(x, p, saved, frozen, criteria) {
  const off = p.tool && p.tool !== x.recommended;
  return `<section class="block"><div class="blockhead"><div class="grow"><h2>${esc(x.type)} <span class="muted small">${x.cases} cases · ${x.smoke} smoke · ${x.high} P0/P1</span></h2>
      <p class="small muted">Recommended: <b>${esc(x.recommended)}</b>${saved ? ` · chosen ${esc(saved.Chosen)} by ${esc(saved['Chosen By'])}${saved['Design Baseline'] !== S.data.tools.advice.design_baseline ? ` <span class="pill High">cases changed since</span>` : ''}` : ''}</p></div></div>
    <div class="table-wrap"><table class="list tools"><thead><tr><th><span class="sr">Choose</span></th><th class="wide">Tool</th><th class="num">Score</th>
      ${criteria.map(([k, l]) => `<th class="num" title="${esc(l)}">${esc(l.split(' (')[0])}</th>`).join('')}</tr></thead><tbody>
    ${x.options.map(o => `<tr class="${o.tool === p.tool ? 'dirty' : ''}"><td class="id"><input type="radio" name="pick-${esc(x.type)}" data-pick="${esc(x.type)}" value="${esc(o.tool)}"
        aria-label="Choose ${esc(o.tool)} for ${esc(x.type)}" ${o.tool === p.tool ? 'checked' : ''} ${frozen ? 'disabled' : ''}></td>
      <td class="strong">${esc(o.tool)}${o.tool === x.recommended ? ' <span class="pill ok">recommended</span>' : ''}${o.ready ? '' : ' <span class="pill Low">no TestHive setup yet</span>'}
        <div class="meta">${esc(o.langs.join(', '))}</div><div class="small">${esc(o.note)}</div></td>
      <td class="num strong">${o.score}%</td>${criteria.map(([k]) => `<td class="num">${o.scores[k]}</td>`).join('')}</tr>`).join('')}
    </tbody></table></div>
    ${off || p.reason ? `<label class="small" for="why-${esc(x.type)}">Why ${esc(p.tool)} instead of ${esc(x.recommended)}?${off ? ' <span class="req">required</span>' : ''}</label>
      <input id="why-${esc(x.type)}" data-why="${esc(x.type)}" value="${esc(p.reason)}" ${frozen ? 'disabled' : ''} placeholder="For example: the team writes Java" dir="auto">` : ''}</section>`;
}

function settingsFold(t, frozen) {
  return `<details class="fold"><summary><b>Weights and team skills</b> <span class="small muted">shared by every module of this project; they change the scores</span></summary>
    <p class="small muted">How much each criterion counts, from 0 (ignore it) to 5.</p>
    <div class="wgrid">${t.criteria.map(([k, l]) => `<label class="small">${esc(l)} <input type="number" min="0" max="5" step="1" data-w="${k}" value="${t.settings.weights[k]}" ${frozen ? 'disabled' : ''}></label>`).join('')}</div>
    <p class="small muted">Languages your team writes tests in (none ticked: skills count as neutral). Tools without code always fit.</p>
    <div class="wgrid">${t.langs.map(l => `<label class="small"><input type="checkbox" data-skill="${esc(l)}" ${t.settings.skills.includes(l) ? 'checked' : ''} ${frozen ? 'disabled' : ''}> ${esc(l)}</label>`).join('')}</div>
    ${frozen ? '' : '<p class="small muted">Saved with the choices; the scores and the recommendation update after saving.</p>'}</details>`;
}

export async function saveTools() {
  if (!me()) return askName(saveTools);
  const a = S.data.tools.advice, mine = Object.fromEntries(S.data.tools.choices.map(c => [c['Test Type'], c]));
  const picks = a.types.map(x => S.dirty[key(x.type)] ? { type: x.type, ...S.dirty[key(x.type)] } : null).filter(Boolean);
  const missing = picks.filter(p => p.tool && p.tool !== a.types.find(x => x.type === p.type).recommended && !p.reason.trim());
  if (missing.length) return toast(`Say why for ${missing.map(p => p.type).join(', ')}: the tool is not the recommended one.`, 'warn');
  if (!picks.length && !S.dirty.settings && a.types.some(x => !mine[x.type])) return toast('Choose a tool for each test type first.', 'warn');
  const settings = S.dirty.settings ? { weights: Object.fromEntries([...document.querySelectorAll('[data-w]')].map(i => [i.dataset.w, Number(i.value)])),
    skills: [...document.querySelectorAll('[data-skill]:checked')].map(i => i.dataset.skill) } : null;
  const r = await api('/api/tools', { method: 'POST', body: JSON.stringify({ module: S.module, version: S.data.tools.version, by: me(), picks, settings }) });
  return afterSave(r);
}
