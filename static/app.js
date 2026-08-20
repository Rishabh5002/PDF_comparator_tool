const form = document.getElementById('compareForm');
const loading = document.getElementById('loading');
const errorBox = document.getElementById('error');
const results = document.getElementById('results');
const threshold = document.getElementById('threshold');
const thresholdValue = document.getElementById('thresholdValue');
let currentPairs = [];
let currentFilter = 'all';
let currentSearch = '';

threshold.addEventListener('input', () => thresholdValue.textContent = Number(threshold.value).toFixed(2));

for (const zone of document.querySelectorAll('.dropzone')) {
  const input = zone.querySelector('input[type=file]');
  const name = zone.querySelector('.filename');
  input.addEventListener('change', () => name.textContent = input.files[0]?.name || '');
  ['dragenter','dragover'].forEach(e => zone.addEventListener(e, ev => { ev.preventDefault(); zone.classList.add('drag'); }));
  ['dragleave','drop'].forEach(e => zone.addEventListener(e, ev => { ev.preventDefault(); zone.classList.remove('drag'); }));
  zone.addEventListener('drop', ev => { if (ev.dataTransfer.files.length) { input.files = ev.dataTransfer.files; name.textContent = input.files[0].name; } });
}

function esc(value) { return String(value ?? '').replace(/[&<>'"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[c])); }
function fmtList(value) {
  if (!Array.isArray(value)) return esc(value || '—');
  if (!value.length) return '—';
  return `<ul>${value.slice(0, 30).map(v => `<li>${esc(v)}</li>`).join('')}${value.length > 30 ? `<li class="muted">+ ${value.length - 30} more</li>` : ''}</ul>`;
}
function countTypes(changes) {
  const counts = {ADDED:0, REMOVED:0, MODIFIED:0, REORDERED:0};
  for (const d of changes || []) {
    const type = String(d.type || d.change_type || '').toUpperCase();
    if (type.includes('ADDED')) counts.ADDED++;
    else if (type.includes('REMOVED')) counts.REMOVED++;
    else if (type.includes('REORDER')) counts.REORDERED++;
    else counts.MODIFIED++;
  }
  return counts;
}

form.addEventListener('submit', async e => {
  e.preventDefault();
  errorBox.classList.add('hidden'); results.classList.add('hidden'); loading.classList.remove('hidden');
  try {
    const response = await fetch('/api/compare', { method:'POST', body:new FormData(form) });
    const data = await response.json();
    if (!response.ok || !data.ok) throw new Error(data.error || 'Comparison failed.');
    render(data.payload, data.reports);
  } catch (err) {
    errorBox.textContent = err.message; errorBox.classList.remove('hidden');
  } finally { loading.classList.add('hidden'); }
});

function pairStatus(pair) {
  if (!pair.matched) return pair.side === 'old' ? 'removed' : 'added';
  return pair.changed ? 'changed' : 'unchanged';
}
function statusLabel(status) {
  return ({changed:'Changed', unchanged:'Unchanged', removed:'Removed', added:'Added'})[status] || status;
}
function confidenceLabel(score) {
  if (score >= 0.80) return 'High';
  if (score >= 0.55) return 'Medium';
  return 'Low';
}
function renderPairs() {
  const root = document.getElementById('questionPairs');
  const q = currentSearch.trim().toLowerCase();
  const filtered = currentPairs.filter(pair => {
    const status = pairStatus(pair);
    if (currentFilter !== 'all' && status !== currentFilter) return false;
    if (!q) return true;
    const hay = [pair.old?.text, pair.new?.text, pair.old?.number, pair.new?.number, pair.status_label].join(' ').toLowerCase();
    return hay.includes(q);
  });
  if (!filtered.length) {
    root.innerHTML = '<div class="empty-state">No questions match the current filter.</div>';
    return;
  }
  root.innerHTML = filtered.map((pair, idx) => {
    const status = pairStatus(pair);
    const old = pair.old || {};
    const neu = pair.new || {};
    const score = Number(pair.score || 0);
    const signal = pair.signals || {};
    const confidence = pair.matched ? confidenceLabel(score) : '—';
    const title = pair.matched ? `Q${esc(old.number)} → Q${esc(neu.number)}` : (pair.side === 'old' ? `Q${esc(old.number)} → Removed` : `Added → Q${esc(neu.number)}`);
    return `<details class="pair-row ${status}" data-index="${idx}">
      <summary>
        <div class="pair-main"><span class="pair-number">${title}</span><span class="pair-status ${status}">${statusLabel(status)}</span></div>
        <div class="pair-preview"><span>${esc(old.text || '—')}</span><b>→</b><span>${esc(neu.text || '—')}</span></div>
        <div class="pair-score">${confidence}${pair.matched ? ` · ${score.toFixed(2)}` : ''}</div>
      </summary>
      <div class="pair-body">
        <div class="side old-side"><div class="side-title"><span>ORIGINAL</span>${old.number != null ? `<b>Q${esc(old.number)}</b>` : ''}</div><h4>${esc(old.text || 'Question not present')}</h4>${renderQuestionMeta(old)}</div>
        <div class="arrow-column">→</div>
        <div class="side new-side"><div class="side-title"><span>REVISED</span>${neu.number != null ? `<b>Q${esc(neu.number)}</b>` : ''}</div><h4>${esc(neu.text || 'Question not present')}</h4>${renderQuestionMeta(neu)}</div>
        ${pair.matched ? `<div class="signals"><strong>Why this matched</strong><div class="signal-grid">${signalItem('Text', signal.text_similarity)}${signalItem('Local vector', signal.local_vector_similarity)}${signalItem('Options', signal.option_similarity)}${signalItem('Field', signal.field_similarity)}${signalItem('Position', signal.position_similarity)}${signalItem('Neighbour', signal.neighbor_context)}</div></div>` : ''}
      </div>
    </details>`;
  }).join('');
}
function signalItem(label, value) { return `<div><span>${esc(label)}</span><b>${Number(value || 0).toFixed(2)}</b></div>`; }
function renderQuestionMeta(q) {
  return `<div class="meta-grid"><div><span>Field type</span><b>${esc(q.field_type || 'Unknown')}</b></div><div><span>Page</span><b>${q.page ?? '—'}</b></div><div class="wide"><span>Options</span><div class="option-list">${fmtList(q.options)}</div></div><div class="wide"><span>Child questions</span><div class="option-list">${fmtList(q.child_questions)}</div></div></div>`;
}

function render(payload, reports) {
  const comparison = payload.comparison || {};
  const changes = comparison.differences || comparison.changes || [];
  const c = countTypes(changes);
  const summary = payload.local_summary || {};
  const total = changes.length;
  document.getElementById('stats').innerHTML = [['Added',c.ADDED],['Removed',c.REMOVED],['Modified',c.MODIFIED],['Reordered',c.REORDERED]].map(x => `<div class="stat"><span>${x[0]}</span><strong>${x[1]}</strong></div>`).join('');
  document.getElementById('changeCount').textContent = `${total} detected`;
  document.getElementById('changes').innerHTML = changes.length ? changes.map(d => {
    const type = String(d.type || d.change_type || 'CHANGE').replaceAll('_',' ');
    const oldText = d.old_value ?? d.old_text ?? d.old_question ?? '';
    const newText = d.new_value ?? d.new_text ?? d.new_question ?? '';
    return `<div class="change"><span class="tag">${esc(type)}</span><div><strong>${esc(d.message || d.description || '')}</strong><p>${oldText ? `Original: ${esc(JSON.stringify(oldText))}<br>` : ''}${newText ? `Revised: ${esc(JSON.stringify(newText))}` : ''}</p></div></div>`;
  }).join('') : '<div class="change"><div></div><div><strong>No differences detected.</strong><p>The two revisions are structurally equivalent under the current matching threshold.</p></div></div>';
  const oldDoc = payload.old_document || {}, newDoc = payload.new_document || {};
  document.getElementById('documents').innerHTML = `<dl><dt>Original revision</dt><dd>${esc(oldDoc.filename)} · ${oldDoc.pages} pages · ${oldDoc.questions} questions</dd><dt>Revised revision</dt><dd>${esc(newDoc.filename)} · ${newDoc.pages} pages · ${newDoc.questions} questions</dd><dt>Local summary</dt><dd>${esc(summary.summary || summary.text || `${total} differences detected.`)}</dd></dl>`;
  const s = payload.security || {};
  document.getElementById('security').innerHTML = [['Processing','Local / offline'],['Cloud AI','Not required'],['PDF logging',s.pdf_content_logged ? 'Enabled' : 'Disabled'],['Password bypass',s.password_bypass_attempted ? 'Attempted' : 'Not attempted']].map(x => `<div class="security-item"><strong>${esc(x[0])}</strong><span>${esc(x[1])}</span></div>`).join('');
  document.getElementById('downloadLinks').innerHTML = Object.entries(reports).map(([kind,url]) => `<a href="${esc(url)}">Download ${esc(kind.toUpperCase())}</a>`).join('');

  currentPairs = payload.question_pairs || [];
  document.getElementById('matchCount').textContent = `${currentPairs.filter(x => x.matched).length} matched · ${currentPairs.filter(x => !x.matched).length} unmatched`;
  renderPairs();
  results.classList.remove('hidden'); results.scrollIntoView({behavior:'smooth',block:'start'});
}

document.querySelectorAll('.filter').forEach(btn => btn.addEventListener('click', () => {
  document.querySelectorAll('.filter').forEach(x => x.classList.remove('active')); btn.classList.add('active'); currentFilter = btn.dataset.filter; renderPairs();
}));
document.getElementById('questionSearch').addEventListener('input', e => { currentSearch = e.target.value; renderPairs(); });
document.getElementById('reset').addEventListener('click', () => { results.classList.add('hidden'); errorBox.classList.add('hidden'); form.reset(); document.querySelectorAll('.filename').forEach(x => x.textContent=''); threshold.value='0.45'; thresholdValue.textContent='0.45'; currentPairs=[]; currentFilter='all'; currentSearch=''; document.querySelectorAll('.filter').forEach(x => x.classList.toggle('active', x.dataset.filter==='all')); document.getElementById('questionSearch').value=''; window.scrollTo({top:0,behavior:'smooth'}); });
