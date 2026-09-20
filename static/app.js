const form = document.getElementById('compareForm');
const loading = document.getElementById('loading');
const errorBox = document.getElementById('error');
const setupView = document.getElementById('setupView');
const resultsView = document.getElementById('resultsView');
const navBackBtn = document.getElementById('navBackBtn');
const backToUpload = document.getElementById('backToUpload');
const resetBtn = document.getElementById('reset');
const threshold = document.getElementById('threshold');
const themeToggle = document.getElementById('themeToggle');

let currentPairs = [];
let currentChanges = [];
let currentFilter = 'all';
let currentChangeFilter = 'all';
let currentSearch = '';
let currentChangeSearch = '';

// ==========================================
// Theme Management (Dark / Light Mode, Emojiless)
// ==========================================
const MOON_SVG = `<svg class="icon-moon" width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"></path></svg>`;
const SUN_SVG = `<svg class="icon-sun" width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="5"></circle><line x1="12" y1="1" x2="12" y2="3"></line><line x1="12" y1="21" x2="12" y2="23"></line><line x1="4.22" y1="4.22" x2="5.64" y2="5.64"></line><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"></line><line x1="1" y1="12" x2="3" y2="12"></line><line x1="21" y1="12" x2="23" y2="12"></line><line x1="4.22" y1="19.78" x2="5.64" y2="18.36"></line><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"></line></svg>`;

function updateThemeUI() {
  const currentTheme = document.documentElement.getAttribute('data-theme') || 'light';
  if (themeToggle) {
    const icon = document.getElementById('themeIcon');
    const label = document.getElementById('themeLabel');
    if (currentTheme === 'dark') {
      if (icon) icon.innerHTML = SUN_SVG;
      if (label) label.textContent = 'Light';
      themeToggle.setAttribute('title', 'Switch to light mode');
    } else {
      if (icon) icon.innerHTML = MOON_SVG;
      if (label) label.textContent = 'Dark';
      themeToggle.setAttribute('title', 'Switch to dark mode');
    }
  }
}

if (themeToggle) {
  themeToggle.addEventListener('click', () => {
    const currentTheme = document.documentElement.getAttribute('data-theme') || 'light';
    const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
    document.documentElement.setAttribute('data-theme', newTheme);
    localStorage.setItem('formdiff_theme', newTheme);
    updateThemeUI();
  });
}
updateThemeUI();

// Drag & Drop Upload
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
  errorBox.classList.add('hidden');
  loading.classList.remove('hidden');
  try {
    const response = await fetch('/api/compare', { method:'POST', body:new FormData(form) });
    const data = await response.json();
    if (!response.ok || !data.ok) throw new Error(data.error || 'Comparison failed.');
    render(data.payload, data.reports);
  } catch (err) {
    errorBox.textContent = err.message;
    errorBox.classList.remove('hidden');
  } finally {
    loading.classList.add('hidden');
  }
});

function pairStatus(pair) {
  if (!pair.matched) return pair.side === 'old' ? 'removed' : 'added';
  return pair.changed ? 'changed' : 'unchanged';
}
function statusLabel(status) {
  return ({changed:'Changed', unchanged:'Unchanged', removed:'Removed', added:'Added'})[status] || status;
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
    root.innerHTML = '<div class="empty-state">No sections match the current filter.</div>';
    return;
  }
  root.innerHTML = filtered.map((pair, idx) => {
    const status = pairStatus(pair);
    const old = pair.old || {};
    const neu = pair.new || {};
    const signal = pair.signals || {};
    const title = pair.matched ? `Sec ${esc(old.number)} → Sec ${esc(neu.number)}` : (pair.side === 'old' ? `Sec ${esc(old.number)} → Removed` : `Added → Sec ${esc(neu.number)}`);
    return `<details class="pair-row ${status}" data-index="${idx}">
      <summary>
        <div class="pair-main"><span class="pair-number">${title}</span><span class="pair-status ${status}">${statusLabel(status)}</span></div>
        <div class="pair-preview"><span>${esc(old.text || '—')}</span><b>→</b><span>${esc(neu.text || '—')}</span></div>
        <div class="pair-score">${pair.matched ? 'Matched' : 'Unpaired'}</div>
      </summary>
      <div class="pair-body">
        <div class="side old-side"><div class="side-title"><span>ORIGINAL</span>${old.number != null ? `<b>Sec ${esc(old.number)}</b>` : ''}</div><h4>${esc(old.text || 'Section not present in original')}</h4>${renderQuestionMeta(old)}</div>
        <div class="arrow-column">→</div>
        <div class="side new-side"><div class="side-title"><span>REVISED</span>${neu.number != null ? `<b>Sec ${esc(neu.number)}</b>` : ''}</div><h4>${esc(neu.text || 'Section not present in revised')}</h4>${renderQuestionMeta(neu)}</div>
        ${pair.matched ? `<div class="signals"><strong>Match factors</strong><div class="signal-grid">${signalItem('Text', signal.text_similarity)}${signalItem('Semantic vector', signal.local_vector_similarity)}${signalItem('Options', signal.option_similarity)}${signalItem('Field', signal.field_similarity)}${signalItem('Position', signal.position_similarity)}${signalItem('Neighbour', signal.neighbor_context)}</div></div>` : ''}
      </div>
    </details>`;
  }).join('');
}

function signalItem(label, value) { return `<div><span>${esc(label)}</span><b>${Number(value || 0).toFixed(2)}</b></div>`; }
function renderQuestionMeta(q) {
  return `<div class="meta-grid"><div><span>Field / Type</span><b>${esc(q.field_type || 'Text / Section')}</b></div><div><span>Page</span><b>${q.page ?? '—'}</b></div><div class="wide"><span>Options / Elements</span><div class="option-list">${fmtList(q.options)}</div></div><div class="wide"><span>Sub-items / Child content</span><div class="option-list">${fmtList(q.child_questions)}</div></div></div>`;
}

function formatDiffText(val) {
  if (val == null) return '';
  if (typeof val === 'object') {
    try { return JSON.stringify(val, null, 2); } catch (e) { return String(val); }
  }
  return String(val);
}

function getDifferenceCategory(d) {
  if (d.category) return d.category;
  const type = String(d.type || d.change_type || '').toUpperCase();
  if (type === 'QUESTION_REMOVED' || type === 'SECTION_REMOVED' || type === 'CONTENT_REMOVED' || type === 'REMOVED') return 'removed';
  if (type === 'QUESTION_ADDED' || type === 'SECTION_ADDED' || type === 'CONTENT_ADDED' || type === 'ADDED') return 'added';
  if (d.old_value != null && d.new_value == null && !type.includes('OPTION')) return 'removed';
  if (d.new_value != null && d.old_value == null && !type.includes('OPTION')) return 'added';
  return 'modified';
}

function renderChanges() {
  const root = document.getElementById('changes');
  const q = currentChangeSearch.trim().toLowerCase();
  const filtered = currentChanges.filter(d => {
    const cat = getDifferenceCategory(d);
    if (currentChangeFilter === 'added' && cat !== 'added') return false;
    if (currentChangeFilter === 'removed' && cat !== 'removed') return false;
    if (currentChangeFilter === 'changed' && cat !== 'modified') return false;
    if (!q) return true;
    const oldText = formatDiffText(d.old_value ?? d.old_text ?? d.old_question ?? '');
    const newText = formatDiffText(d.new_value ?? d.new_text ?? d.new_question ?? '');
    const secNum = d.section_number ?? d.question_number ?? d.question ?? '';
    const hay = [d.type, d.change_type, d.message, d.description, secNum, oldText, newText].join(' ').toLowerCase();
    return hay.includes(q);
  });

  document.getElementById('changeCount').textContent = `${filtered.length} of ${currentChanges.length} shown`;

  if (!filtered.length) {
    root.innerHTML = '<div class="change-empty"><strong>No differences match the filter.</strong><p>Try switching filter tabs or clearing the search query.</p></div>';
    return;
  }

  root.innerHTML = filtered.map(d => {
    const rawType = String(d.type || d.change_type || 'CHANGE');
    const typeDisplay = rawType.replaceAll('QUESTION_', 'SECTION_').replaceAll('_', ' ');
    const cat = getDifferenceCategory(d);
    const tagClass = cat === 'added' ? 'added' : cat === 'removed' ? 'removed' : 'changed';
    const oldVal = formatDiffText(d.old_value ?? d.old_text ?? d.old_question);
    const newVal = formatDiffText(d.new_value ?? d.new_text ?? d.new_question);
    const secNum = d.section_number != null ? `Section #${esc(d.section_number)}` : (d.question_number != null ? `Section #${esc(d.question_number)}` : (d.question != null ? `Section #${esc(d.question)}` : ''));
    const hasBoth = Boolean(oldVal && newVal);
    const hasAny = Boolean(oldVal || newVal);

    return `<div class="change-card-large">
      <div class="change-card-header">
        <div class="change-card-tags">
          <span class="tag ${tagClass}">${esc(typeDisplay)}</span>
          ${qNum ? `<span class="change-q-num">${qNum}</span>` : ''}
        </div>
      </div>
      <div class="change-card-title">${esc(d.message || d.description || typeDisplay)}</div>
      ${hasAny ? `<div class="change-diff-grid ${hasBoth ? '' : 'single-col'}">
        ${oldVal ? `<div class="diff-box old-box">
          <div class="diff-box-head"><span>Original Content</span></div>
          <pre>${esc(oldVal)}</pre>
        </div>` : ''}
        ${newVal ? `<div class="diff-box new-box">
          <div class="diff-box-head"><span>Revised Content</span></div>
          <pre>${esc(newVal)}</pre>
        </div>` : ''}
      </div>` : ''}
    </div>`;
  }).join('');
}

function render(payload, reports) {
  const comparison = payload.comparison || {};
  currentChanges = comparison.differences || comparison.changes || [];
  const c = countTypes(currentChanges);
  const summary = payload.local_summary || {};
  const total = currentChanges.length;

  document.getElementById('stats').innerHTML = [
    ['Added', c.ADDED, 'added'],
    ['Removed', c.REMOVED, 'removed'],
    ['Modified', c.MODIFIED, 'changed'],
    ['Reordered', c.REORDERED, 'reordered']
  ].map(x => `<div class="stat ${x[2]}"><div class="stat-header"><span class="stat-dot"></span><span>${x[0]}</span></div><strong>${x[1]}</strong></div>`).join('');
  
  const oldDoc = payload.old_document || {}, newDoc = payload.new_document || {};
  document.getElementById('docSubtitle').textContent = `Comparing "${oldDoc.filename || 'Original'}" (${oldDoc.pages || 1} pages) → "${newDoc.filename || 'Revised'}" (${newDoc.pages || 1} pages)`;
  
  // Padded Document Details Cards (Emojiless)
  document.getElementById('documents').innerHTML = `
    <div class="doc-info-group">
      <div class="doc-info-card">
        <span class="doc-info-label">ORIGINAL REVISION</span>
        <div class="doc-info-val">${esc(oldDoc.filename || '—')}</div>
        <div class="doc-info-sub">${oldDoc.pages || 0} pages · ${oldDoc.questions || 0} questions ${oldDoc.encrypted ? '· Encrypted' : ''}</div>
      </div>
      <div class="doc-info-card">
        <span class="doc-info-label">REVISED REVISION</span>
        <div class="doc-info-val">${esc(newDoc.filename || '—')}</div>
        <div class="doc-info-sub">${newDoc.pages || 0} pages · ${newDoc.questions || 0} questions ${newDoc.encrypted ? '· Encrypted' : ''}</div>
      </div>
      <div class="doc-info-card summary-card">
        <span class="doc-info-label">COMPARISON SUMMARY</span>
        <div class="doc-info-val">${esc(summary.summary || summary.text || `${total} differences detected.`)}</div>
      </div>
    </div>
  `;
  
  // Padded Comparison Details Grid
  document.getElementById('security').innerHTML = [
    ['Comparison Scope', 'Full Document', 'Fields, questions, and page text compared'],
    ['Detected Differences', `${total} differences`, 'Classified into additions, removals, modifications & reordering'],
    ['Document Protection', (oldDoc.encrypted || newDoc.encrypted) ? 'Protected' : 'Standard', (oldDoc.encrypted || newDoc.encrypted) ? 'Authenticated decryption applied' : 'Standard unencrypted PDF files'],
    ['Matching Method', 'Structural Alignment', 'Multi-factor question and content mapping']
  ].map(x => `
    <div class="security-item">
      <div class="security-item-head">
        <strong>${esc(x[0])}</strong>
        <span class="security-val">${esc(x[1])}</span>
      </div>
      <span class="security-sub">${esc(x[2])}</span>
    </div>
  `).join('');
  
  // Emojiless Export Buttons
  document.getElementById('downloadLinks').innerHTML = Object.entries(reports).map(([kind, url]) => 
    `<a class="download-btn" href="${esc(url)}"><span class="fmt-pill">${esc(kind.toUpperCase())}</span></a>`
  ).join('');

  currentPairs = payload.question_pairs || [];
  document.getElementById('matchCount').textContent = `${currentPairs.filter(x => x.matched).length} matched · ${currentPairs.filter(x => !x.matched).length} unmatched`;
  
  document.getElementById('changesTabBadge').textContent = String(total);
  document.getElementById('questionsTabBadge').textContent = String(currentPairs.length);

  renderChanges();
  renderPairs();

  // Switch to dedicated results page
  setupView.classList.add('hidden');
  resultsView.classList.remove('hidden');
  navBackBtn.classList.remove('hidden');
  window.scrollTo({top:0, behavior:'smooth'});
}

function switchToUpload() {
  resultsView.classList.add('hidden');
  navBackBtn.classList.add('hidden');
  errorBox.classList.add('hidden');
  setupView.classList.remove('hidden');
  form.reset();
  document.querySelectorAll('.filename').forEach(x => x.textContent = '');
  if (threshold) threshold.value = '0.45';
  currentPairs = [];
  currentChanges = [];
  currentFilter = 'all';
  currentChangeFilter = 'all';
  currentSearch = '';
  currentChangeSearch = '';
  document.querySelectorAll('.filter').forEach(x => x.classList.toggle('active', (x.dataset.filter === 'all' || x.dataset.changeFilter === 'all')));
  if (document.getElementById('questionSearch')) document.getElementById('questionSearch').value = '';
  if (document.getElementById('changeSearch')) document.getElementById('changeSearch').value = '';
  window.scrollTo({top:0, behavior:'smooth'});
}

// Navigation Tabs
document.querySelectorAll('.nav-tab').forEach(tab => {
  tab.addEventListener('click', () => {
    document.querySelectorAll('.nav-tab').forEach(t => t.classList.remove('active'));
    document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
    tab.classList.add('active');
    const targetId = tab.dataset.tab;
    const targetEl = document.getElementById(targetId);
    if (targetEl) targetEl.classList.add('active');
  });
});

// Question filters & search
document.querySelectorAll('#filterTabs .filter').forEach(btn => btn.addEventListener('click', () => {
  document.querySelectorAll('#filterTabs .filter').forEach(x => x.classList.remove('active'));
  btn.classList.add('active');
  currentFilter = btn.dataset.filter;
  renderPairs();
}));
if (document.getElementById('questionSearch')) {
  document.getElementById('questionSearch').addEventListener('input', e => {
    currentSearch = e.target.value;
    renderPairs();
  });
}

// Change filters & search
document.querySelectorAll('#changeFilterTabs .filter').forEach(btn => btn.addEventListener('click', () => {
  document.querySelectorAll('#changeFilterTabs .filter').forEach(x => x.classList.remove('active'));
  btn.classList.add('active');
  currentChangeFilter = btn.dataset.changeFilter;
  renderChanges();
}));
if (document.getElementById('changeSearch')) {
  document.getElementById('changeSearch').addEventListener('input', e => {
    currentChangeSearch = e.target.value;
    renderChanges();
  });
}

// Reset & Back
if (navBackBtn) navBackBtn.addEventListener('click', switchToUpload);
if (backToUpload) backToUpload.addEventListener('click', switchToUpload);
if (resetBtn) resetBtn.addEventListener('click', switchToUpload);
