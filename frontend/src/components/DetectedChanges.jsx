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

export default function DetectedChanges({ changes = [] }) {
  const [filter, setFilter] = useState('all');
  const [search, setSearch] = useState('');

  const filteredChanges = useMemo(() => {
    const q = search.trim().toLowerCase();
    return changes.filter((d) => {
      const type = String(d.type || d.change_type || '').toLowerCase();
      if (filter === 'added' && !type.includes('added')) return false;
      if (filter === 'removed' && !type.includes('removed')) return false;
      if (filter === 'changed' && (type.includes('added') || type.includes('removed'))) return false;
      if (!q) return true;

      const oldText = formatDiffText(d.old_value ?? d.old_text ?? d.old_question ?? '');
      const newText = formatDiffText(d.new_value ?? d.new_text ?? d.new_question ?? '');
      const hay = [
        type,
        d.message,
        d.description,
        d.question_number,
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
              const typeDisplay = rawType.replaceAll('_', ' ');
              const tagClass = rawType.toLowerCase().includes('added')
                ? 'added'
                : rawType.toLowerCase().includes('removed')
                ? 'removed'
                : 'changed';
              const oldVal = formatDiffText(d.old_value ?? d.old_text ?? d.old_question);
              const newVal = formatDiffText(d.new_value ?? d.new_text ?? d.new_question);
              const qNum =
                d.question_number != null
                  ? `Question #${d.question_number}`
                  : d.question != null
                  ? `Question #${d.question}`
                  : '';
              const hasBoth = Boolean(oldVal && newVal);
              const hasAny = Boolean(oldVal || newVal);

              return (
                <div key={index} className="change-card-large">
                  <div className="change-card-header">
                    <div className="change-card-tags">
                      <span className={`tag ${tagClass}`}>{typeDisplay}</span>
                      {qNum && <span className="change-q-num">{qNum}</span>}
                    </div>
                    {d.confidence != null && (
                      <span className="change-q-num">
                        Confidence: {(Number(d.confidence) * 100).toFixed(0)}%
                      </span>
                    )}
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
