import React, { useState, useMemo } from 'react';

function pairStatus(pair) {
  if (!pair.matched) return pair.side === 'old' ? 'removed' : 'added';
  return pair.changed ? 'changed' : 'unchanged';
}

function statusLabel(status) {
  return (
    {
      changed: 'Changed',
      unchanged: 'Unchanged',
      removed: 'Removed',
      added: 'Added',
    }[status] || status
  );
}

function fmtList(value) {
  if (!Array.isArray(value)) return value || '—';
  if (!value.length) return '—';
  return (
    <ul>
      {value.slice(0, 30).map((v, i) => (
        <li key={i}>{String(v)}</li>
      ))}
      {value.length > 30 && <li className="muted">+ {value.length - 30} more</li>}
    </ul>
  );
}

function QuestionMeta({ q }) {
  return (
    <div className="meta-grid">
      <div>
        <span>Field type</span>
        <b>{q.field_type || 'Unknown'}</b>
      </div>
      <div>
        <span>Page</span>
        <b>{q.page ?? '—'}</b>
      </div>
      <div className="wide">
        <span>Options</span>
        <div className="option-list">{fmtList(q.options)}</div>
      </div>
      <div className="wide">
        <span>Child questions</span>
        <div className="option-list">{fmtList(q.child_questions)}</div>
      </div>
    </div>
  );
}

function SignalItem({ label, value }) {
  return (
    <div>
      <span>{label}</span>
      <b>{Number(value || 0).toFixed(2)}</b>
    </div>
  );
}

export default function QuestionAlignment({ questionPairs = [] }) {
  const [filter, setFilter] = useState('all');
  const [search, setSearch] = useState('');

  const matchedCount = questionPairs.filter((x) => x.matched).length;
  const unmatchedCount = questionPairs.filter((x) => !x.matched).length;

  const filteredPairs = useMemo(() => {
    const q = search.trim().toLowerCase();
    return questionPairs.filter((pair) => {
      const status = pairStatus(pair);
      if (filter !== 'all') {
        if (filter === 'unmatched') {
          if (status !== 'added' && status !== 'removed') return false;
        } else if (status !== filter) {
          return false;
        }
      }
      if (!q) return true;
      const hay = [
        pair.old?.text,
        pair.new?.text,
        pair.old?.number,
        pair.new?.number,
        pair.status_label,
      ]
        .join(' ')
        .toLowerCase();
      return hay.includes(q);
    });
  }, [questionPairs, filter, search]);

  return (
    <div id="tab-questions" className="tab-content active">
      <div className="panel comparison-panel">
        <div className="panel-head">
          <div>
            <h3>Question-by-Question Comparison</h3>
            <p className="panel-sub">
              Matched questions are aligned side-by-side. Expand a row to inspect fields, options, and changes.
            </p>
          </div>
          <span id="matchCount">
            {matchedCount} matched · {unmatchedCount} unmatched
          </span>
        </div>

        <div className="comparison-toolbar">
          <div className="filter-tabs" id="filterTabs">
            <button
              type="button"
              className={`filter ${filter === 'all' ? 'active' : ''}`}
              onClick={() => setFilter('all')}
            >
              All
            </button>
            <button
              type="button"
              className={`filter ${filter === 'changed' ? 'active' : ''}`}
              onClick={() => setFilter('changed')}
            >
              Changed
            </button>
            <button
              type="button"
              className={`filter ${filter === 'unchanged' ? 'active' : ''}`}
              onClick={() => setFilter('unchanged')}
            >
              Unchanged
            </button>
            <button
              type="button"
              className={`filter ${filter === 'unmatched' ? 'active' : ''}`}
              onClick={() => setFilter('unmatched')}
            >
              Added / removed
            </button>
          </div>
          <input
            id="questionSearch"
            className="search"
            type="search"
            placeholder="Search questions…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>

        <div id="questionPairs" className="question-pairs">
          {filteredPairs.length === 0 ? (
            <div className="empty-state">No questions match the current filter.</div>
          ) : (
            filteredPairs.map((pair, idx) => {
              const status = pairStatus(pair);
              const old = pair.old || {};
              const neu = pair.new || {};
              const signal = pair.signals || {};
              const title = pair.matched
                ? `Q${old.number} → Q${neu.number}`
                : pair.side === 'old'
                ? `Q${old.number} → Removed`
                : `Added → Q${neu.number}`;

              return (
                <details key={idx} className={`pair-row ${status}`}>
                  <summary>
                    <div className="pair-main">
                      <span className="pair-number">{title}</span>
                      <span className={`pair-status ${status}`}>{statusLabel(status)}</span>
                    </div>
                    <div className="pair-preview">
                      <span>{old.text || '—'}</span>
                      <b>→</b>
                      <span>{neu.text || '—'}</span>
                    </div>
                    <div className="pair-score">
                      {pair.matched ? 'Matched' : 'Unpaired'}
                    </div>
                  </summary>
                  <div className="pair-body">
                    <div className="side old-side">
                      <div className="side-title">
                        <span>ORIGINAL</span>
                        {old.number != null && <b>Q{old.number}</b>}
                      </div>
                      <h4>{old.text || 'Question not present'}</h4>
                      <QuestionMeta q={old} />
                    </div>
                    <div className="arrow-column">→</div>
                    <div className="side new-side">
                      <div className="side-title">
                        <span>REVISED</span>
                        {neu.number != null && <b>Q{neu.number}</b>}
                      </div>
                      <h4>{neu.text || 'Question not present'}</h4>
                      <QuestionMeta q={neu} />
                    </div>
                    {pair.matched && (
                      <div className="signals">
                        <strong>Match factors</strong>
                        <div className="signal-grid">
                          <SignalItem label="Text" value={signal.text_similarity} />
                          <SignalItem label="Semantic vector" value={signal.local_vector_similarity} />
                          <SignalItem label="Options" value={signal.option_similarity} />
                          <SignalItem label="Field" value={signal.field_similarity} />
                          <SignalItem label="Position" value={signal.position_similarity} />
                          <SignalItem label="Neighbour" value={signal.neighbor_context} />
                        </div>
                      </div>
                    )}
                  </div>
                </details>
              );
            })
          )}
        </div>
      </div>
    </div>
  );
}
