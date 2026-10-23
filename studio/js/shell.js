// The frame around every screen: the sidebar (project, modules and what each waits for) and the top bar (where you are).
import { S, $, esc, api, STAGE_LABEL, confirmLeave } from './core.js';
import { home, renderNewModule } from './home.js';
import { renderProjects } from './projects.js';
import { openModule } from './module.js';

/* One line per module: what it waits for now. */
export function waits(m) {
  if (m.job) return `${m.job} is working…`;
  const s = m.stages.find(x => x.status !== 'approved');
  if (!s) return 'Every stage approved';
  const label = STAGE_LABEL[s.stage];
  return { awaiting_approval: `${label} waits for your approval`, in_progress: `${label} in progress`, pending: `${label} not started` }[s.status];
}

/* The sidebar. Pass the overview and archive listing when the caller already has them. */
export async function renderSide(ov, arch) {
  [ov, arch] = await Promise.all([ov || api('/api/overview'), arch || api('/api/archive')]);
  if (ov.status !== 200) return;
  $('#newmod-side').hidden = $('#projbtn').hidden = false;
  S.agents = ov.agents;
  $('#project').textContent = ov.setup.setup_needed ? 'Studio' : ov.project;
  $('#mods').innerHTML = ov.modules.map(m => `<a class="nav ${S.view === 'module' && S.module === m.module ? 'on' : ''}" href="#/${esc(m.module)}" data-side="${esc(m.module)}"
      ${S.view === 'module' && S.module === m.module ? 'aria-current="page"' : ''}><span class="n">${esc(m.module)}${m.open_gaps && m.stages[0].status !== 'approved' ? ` <span class="count" title="Open questions">${m.open_gaps}</span>` : ''}</span>
      <span class="s">${esc(waits(m))}</span></a>`).join('') || '<p class="s none">No modules yet.</p>';
  const n = (arch.archived || []).length;
  $('#archbtn').hidden = !n; $('#archn').textContent = n;
  $('#mode').textContent = { recorded: 'Agents: recorded runs (demo)', review: 'Review mode' }[ov.agents] || '';
  $('#mode').title = ov.agents === 'review' ? `${ov.agents_missing.join(' and ')} not found on this PC: the Run buttons are off. Documents, answers, reviews, approvals and Excel all work.` : '';
  document.querySelectorAll('[data-side]').forEach(a => a.onclick = e => { e.preventDefault(); closeMenu(); confirmLeave(() => openModule(a.dataset.side)); });
}

/* The top bar path. parts: [label, onclick] pairs; the last one is where you are. */
export function setCrumbs(parts) {
  $('#crumbs').innerHTML = parts.map(([label, go], i) => i === parts.length - 1 ? `<b aria-current="page">${esc(label)}</b>`
    : `<button class="link ${i ? '' : 'hide-s'}" data-crumb="${i}">${esc(label)}</button><span class="sep ${i ? '' : 'hide-s'}" aria-hidden="true">/</span>`).join('');
  document.querySelectorAll('[data-crumb]').forEach(b => b.onclick = () => confirmLeave(parts[b.dataset.crumb][1]));
}

/* Phone and tablet: the sidebar opens over the page from the menu button. */
function closeMenu() { document.body.classList.remove('menu-open'); $('#menu').setAttribute('aria-expanded', 'false'); }
export function bindShell() {
  $('#menu').onclick = () => { const open = document.body.classList.toggle('menu-open'); $('#menu').setAttribute('aria-expanded', String(open)); };
  document.addEventListener('keydown', e => { if (e.key === 'Escape') closeMenu(); });
  document.addEventListener('click', e => { if (document.body.classList.contains('menu-open') && !e.target.closest('#side, #menu')) closeMenu(); });
  $('#brand').onclick = e => { e.preventDefault(); closeMenu(); confirmLeave(home); };
  $('#newmod-side').onclick = () => { closeMenu(); confirmLeave(renderNewModule); };
  $('#archbtn').onclick = () => { closeMenu(); confirmLeave(() => home({ archived: true })); };
  $('#switchbtn').onclick = () => { closeMenu(); confirmLeave(renderProjects); };
}
