import React, { useState, useMemo } from 'react';

function formatDiffText(val) {
  if (val == null) return '';
  if (typeof val === 'object') {
    try {
      return JSON.stringify(val, null, 2);
    } catch {
      return String(val);
    }
  }
  return String(val);
}

export function getDifferenceCategory(d) {
  if (d.category) {
    if (d.category === 'removed') return 'removed';
    if (d.category === 'added') return 'added';
    return 'modified';
  }
  const type = String(d.type || d.change_type || '').toUpperCase();
  // Pure removal of an entire section or document element
  if (type === 'QUESTION_REMOVED' || type === 'SECTION_REMOVED' || type === 'CONTENT_REMOVED' || type === 'REMOVED') {
    return 'removed';
  }
  // Pure addition of an entire section or document element
  if (type === 'QUESTION_ADDED' || type === 'SECTION_ADDED' || type === 'CONTENT_ADDED' || type === 'ADDED') {
    return 'added';
  }
  // If only old value exists and it's not a partial option modification
  if (d.old_value != null && d.new_value == null && !type.includes('OPTION')) {
    return 'removed';
  }
  // If only new value exists and it's not a partial option modification
  if (d.new_value != null && d.old_value == null && !type.includes('OPTION')) {
    return 'added';
  }
  // Everything else (e.g. OPTIONS_REMOVED, OPTIONS_ADDED, TEXT_CHANGED, etc.) is a modification
  return 'modified';
}

export default function DetectedChanges({ changes = [] }) {
  const [filter, setFilter] = useState('all');
  const [search, setSearch] = useState('');

  const filteredChanges = useMemo(() => {
    const q = search.trim().toLowerCase();
    return changes.filter((d) => {
      const cat = getDifferenceCategory(d);
      if (filter === 'added' && cat !== 'added') return false;
      if (filter === 'removed' && cat !== 'removed') return false;
      if (filter === 'changed' && cat !== 'modified') return false;
      if (!q) return true;

      const oldText = formatDiffText(d.old_value ?? d.old_text ?? d.old_question ?? '');
      const newText = formatDiffText(d.new_value ?? d.new_text ?? d.new_question ?? '');
      const secNum = d.section_number ?? d.question_number ?? d.question ?? '';
      const hay = [
        d.type,
        d.change_type,
        d.message,
        d.description,
        secNum,
        oldText,
        newText,
      ].join(' ').toLowerCase();
      return hay.includes(q);
    });
  }, [changes, filter, search]);

  return (
    <div id="tab-changes" className="tab-content active">
      <div className="panel changes-panel-large">
        <div className="panel-head">
          <div>
            <h3>Detected Differences</h3>
            <p className="panel-sub">
              Complete structural and text changes found between the original and revised documents.
            </p>
          </div>
          <span id="changeCount">
            {filteredChanges.length} of {changes.length} shown
          </span>
        </div>

        <div className="changes-toolbar">
          <div className="filter-tabs" id="changeFilterTabs">
            <button
              type="button"
              className={`filter ${filter === 'all' ? 'active' : ''}`}
              onClick={() => setFilter('all')}
            >
              All Differences
            </button>
            <button
              type="button"
              className={`filter ${filter === 'added' ? 'active' : ''}`}
              onClick={() => setFilter('added')}
            >
              Added
            </button>
            <button
              type="button"
              className={`filter ${filter === 'removed' ? 'active' : ''}`}
              onClick={() => setFilter('removed')}
            >
              Removed
            </button>
            <button
              type="button"
              className={`filter ${filter === 'changed' ? 'active' : ''}`}
              onClick={() => setFilter('changed')}
            >
              Modified
            </button>
          </div>
          <input
            id="changeSearch"
            className="search"
            type="search"
            placeholder="Search differences…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>

        <div id="changes" className="changes-list-large">
          {filteredChanges.length === 0 ? (
            <div className="change-empty">
              <strong>No differences match the filter.</strong>
              <p>Try switching filter tabs or clearing the search query.</p>
            </div>
          ) : (
            filteredChanges.map((d, index) => {
              const rawType = String(d.type || d.change_type || 'CHANGE');
              const typeDisplay = rawType
                .replaceAll('QUESTION_', 'SECTION_')
                .replaceAll('_', ' ');
              const cat = getDifferenceCategory(d);
              const tagClass = cat === 'added' ? 'added' : cat === 'removed' ? 'removed' : 'changed';
              const oldVal = formatDiffText(d.old_value ?? d.old_text ?? d.old_question);
              const newVal = formatDiffText(d.new_value ?? d.new_text ?? d.new_question);
              const secNum =
                d.section_number != null
                  ? `Section #${d.section_number}`
                  : d.question_number != null
                  ? `Section #${d.question_number}`
                  : d.question != null
                  ? `Section #${d.question}`
                  : '';
              const hasBoth = Boolean(oldVal && newVal);
              const hasAny = Boolean(oldVal || newVal);

              return (
                <div key={index} className="change-card-large">
                  <div className="change-card-header">
                    <div className="change-card-tags">
                      <span className={`tag ${tagClass}`}>{typeDisplay}</span>
                      {secNum && <span className="change-q-num">{secNum}</span>}
                    </div>
                  </div>
                  <div className="change-card-title">
                    {d.message || d.description || typeDisplay}
                  </div>
                  {hasAny && (
                    <div className={`change-diff-grid ${hasBoth ? '' : 'single-col'}`}>
                      {oldVal && (
                        <div className="diff-box old-box">
                          <div className="diff-box-head">
                            <span>Original Content</span>
                          </div>
                          <pre>{oldVal}</pre>
                        </div>
                      )}
                      {newVal && (
                        <div className="diff-box new-box">
                          <div className="diff-box-head">
                            <span>Revised Content</span>
                          </div>
                          <pre>{newVal}</pre>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              );
            })
          )}
        </div>
      </div>
    </div>
  );
}
