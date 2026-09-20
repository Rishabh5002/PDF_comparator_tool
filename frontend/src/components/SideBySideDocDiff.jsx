import React, { useState, useMemo, useRef, useEffect } from 'react';

function renderChunks(chunks, defaultText) {
  if (!chunks || !chunks.length) {
    return defaultText;
  }
  return chunks.map((chunk, idx) => {
    if (chunk.type === 'del') {
      return (
        <mark key={idx} className="diff-word-del" title="Removed text">
          {chunk.text}
        </mark>
      );
    }
    if (chunk.type === 'add') {
      return (
        <mark key={idx} className="diff-word-add" title="Added text">
          {chunk.text}
        </mark>
      );
    }
    return <span key={idx}>{chunk.text}</span>;
  });
}

export default function SideBySideDocDiff({
  diffRows = [],
  oldDoc = {},
  newDoc = {},
}) {
  const [search, setSearch] = useState('');
  const [wrapLines, setWrapLines] = useState(true);
  const [activeRowIdx, setActiveRowIdx] = useState(null);
  const [viewportRatio, setViewportRatio] = useState({ top: 0, height: 100 });
  const rowRefs = useRef({});
  const editorBodyRef = useRef(null);

  // Statistics
  const stats = useMemo(() => {
    let added = 0;
    let deleted = 0;
    let modified = 0;
    let unchanged = 0;
    for (const r of diffRows) {
      if (r.status === 'added') added++;
      else if (r.status === 'deleted') deleted++;
      else if (r.status === 'modified') modified++;
      else unchanged++;
    }
    return { added, deleted, modified, unchanged, total: diffRows.length };
  }, [diffRows]);

  // Filtered rows (always showing all lines sequence, filtered only by search if active)
  const filteredRows = useMemo(() => {
    const q = search.trim().toLowerCase();
    return diffRows.map((r, originalIndex) => ({ ...r, originalIndex })).filter((r) => {
      if (!q) return true;
      const t1 = r.old?.text?.toLowerCase() || '';
      const t2 = r.new?.text?.toLowerCase() || '';
      return t1.includes(q) || t2.includes(q);
    });
  }, [diffRows, search]);

  const scrollToRow = (index) => {
    setActiveRowIdx(index);
    const el = rowRefs.current[index];
    if (el) {
      el.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
  };

  const handleScroll = () => {
    if (!editorBodyRef.current) return;
    const { scrollTop, scrollHeight, clientHeight } = editorBodyRef.current;
    if (scrollHeight <= clientHeight) {
      setViewportRatio({ top: 0, height: 100 });
    } else {
      const top = (scrollTop / scrollHeight) * 100;
      const height = (clientHeight / scrollHeight) * 100;
      setViewportRatio({ top, height });
    }
  };

  useEffect(() => {
    handleScroll();
  }, [diffRows]);

  const handleRulerClick = (e) => {
    const ruler = e.currentTarget;
    const rect = ruler.getBoundingClientRect();
    const clickY = e.clientY - rect.top;
    const ratio = clickY / rect.height;
    if (editorBodyRef.current) {
      const { scrollHeight, clientHeight } = editorBodyRef.current;
      editorBodyRef.current.scrollTo({
        top: ratio * scrollHeight - clientHeight / 2,
        behavior: 'smooth',
      });
    }
  };

  return (
    <div className="diff-wide-container" id="sideBySideDiffSection">
      {/* Clean Uncluttered Header */}
      <div className="diff-clean-header">
        <div className="diff-header-left">
          <h3>Document Side-by-Side Comparison</h3>
          <span className="diff-line-count-badge">{diffRows.length} lines</span>

          <div className="diff-stat-chips">
            <span className="diff-chip chip-added">+{stats.added} added</span>
            <span className="diff-chip chip-deleted">-{stats.deleted} removed</span>
            <span className="diff-chip chip-modified">~{stats.modified} modified</span>
            <span className="diff-chip chip-unchanged">{stats.unchanged} unchanged</span>
          </div>
        </div>

        {/* Tools */}
        <div className="diff-header-right">
          <label className="diff-toggle-wrap">
            <input
              type="checkbox"
              checked={wrapLines}
              onChange={(e) => setWrapLines(e.target.checked)}
            />
            <span>Wrap lines</span>
          </label>

          <input
            type="search"
            className="diff-search-input"
            placeholder="Search text…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
      </div>

      {/* Pane Titles Header */}
      <div className="diff-panes-bar">
        <div className="pane-title-col left-pane-title">
          <span className="pane-badge original-badge">ORIGINAL</span>
          <span className="pane-filename" title={oldDoc.filename}>
            {oldDoc.filename || 'Original Document'}
          </span>
          <span className="pane-pages">({oldDoc.pages || 1} pages)</span>
        </div>
        <div className="pane-title-col right-pane-title">
          <span className="pane-badge revised-badge">REVISED</span>
          <span className="pane-filename" title={newDoc.filename}>
            {newDoc.filename || 'Revised Document'}
          </span>
          <span className="pane-pages">({newDoc.pages || 1} pages)</span>
        </div>
      </div>

      {/* Diff Table and Scrollbar Ruler Wrapper */}
      <div className="diff-viewport-wrapper">
        <div
          ref={editorBodyRef}
          onScroll={handleScroll}
          className={`diff-scroll-body ${wrapLines ? 'wrap-lines' : ''}`}
        >
          {filteredRows.length === 0 ? (
            <div className="diff-empty-state">
              <p>No document lines match the search query.</p>
            </div>
          ) : (
            <table className="diff-table">
              <colgroup>
                <col style={{ width: '40px' }} />
                <col style={{ width: '28px' }} />
                <col style={{ width: '20px' }} />
                <col style={{ width: 'calc(50% - 88px)' }} />
                <col style={{ width: '40px' }} />
                <col style={{ width: '28px' }} />
                <col style={{ width: '20px' }} />
                <col style={{ width: 'calc(50% - 88px)' }} />
              </colgroup>
              <tbody>
                {filteredRows.map((row) => {
                  const status = row.status; // 'unchanged' | 'modified' | 'added' | 'deleted'
                  const oldLine = row.old;
                  const newLine = row.new;
                  const rowIdx = row.originalIndex;
                  const isCurrentActive = activeRowIdx === rowIdx;

                  return (
                    <tr
                      key={rowIdx}
                      ref={(el) => (rowRefs.current[rowIdx] = el)}
                      className={`diff-row status-${status} ${isCurrentActive ? 'active-diff-row' : ''}`}
                    >
                      {/* LEFT (ORIGINAL) */}
                      {oldLine ? (
                        <>
                          <td className="diff-gutter line-col">{oldLine.line_no}</td>
                          <td className="diff-gutter page-col" title={`Page ${oldLine.page}`}>
                            P{oldLine.page}
                          </td>
                          <td className={`diff-symbol symbol-${status}`}>
                            {status === 'deleted' ? '-' : status === 'modified' ? '~' : ' '}
                          </td>
                          <td className={`diff-text left-text cell-${status}`}>
                            {status === 'modified' && row.word_diff
                              ? renderChunks(row.word_diff.old_chunks, oldLine.text)
                              : oldLine.text}
                          </td>
                        </>
                      ) : (
                        <>
                          <td className="diff-gutter line-col empty-gutter"></td>
                          <td className="diff-gutter page-col empty-gutter"></td>
                          <td className="diff-symbol empty-gutter"></td>
                          <td className="diff-text diff-empty-spacer" title="Added in revised document">
                            <span className="spacer-hatch"></span>
                          </td>
                        </>
                      )}

                      {/* RIGHT (REVISED) */}
                      {newLine ? (
                        <>
                          <td className="diff-gutter line-col">{newLine.line_no}</td>
                          <td className="diff-gutter page-col" title={`Page ${newLine.page}`}>
                            P{newLine.page}
                          </td>
                          <td className={`diff-symbol symbol-${status}`}>
                            {status === 'added' ? '+' : status === 'modified' ? '~' : ' '}
                          </td>
                          <td className={`diff-text right-text cell-${status}`}>
                            {status === 'modified' && row.word_diff
                              ? renderChunks(row.word_diff.new_chunks, newLine.text)
                              : newLine.text}
                          </td>
                        </>
                      ) : (
                        <>
                          <td className="diff-gutter line-col empty-gutter"></td>
                          <td className="diff-gutter page-col empty-gutter"></td>
                          <td className="diff-symbol empty-gutter"></td>
                          <td className="diff-text diff-empty-spacer" title="Removed from original document">
                            <span className="spacer-hatch"></span>
                          </td>
                        </>
                      )}
                    </tr>
                  );
                })}
              </tbody>
            </table>
          )}
        </div>

        {/* Scrollbar Overview Ruler with Red/Green/Yellow Marks */}
        <div
          className="diff-overview-ruler"
          onClick={handleRulerClick}
        >
          {/* Viewport Slider Indicator */}
          <div
            className="ruler-viewport-indicator"
            style={{
              top: `${viewportRatio.top}%`,
              height: `${Math.max(4, viewportRatio.height)}%`,
            }}
          />

          {/* Marks for each change */}
          {diffRows.map((r, i) => {
            if (r.status === 'unchanged') return null;
            const topPercent = (i / Math.max(1, diffRows.length)) * 100;
            return (
              <div
                key={i}
                className={`ruler-mark mark-${r.status}`}
                style={{ top: `${topPercent}%` }}
                onClick={(e) => {
                  e.stopPropagation();
                  scrollToRow(i);
                }}
              />
            );
          })}
        </div>
      </div>

      {/* Clean Footer Info */}
      <div className="diff-clean-footer">
        <span>Displaying full document text sequence ({diffRows.length} lines)</span>
        <span className="footer-legend">
          <span className="legend-item"><span className="legend-dot dot-del"></span> Red = Removed</span>
          <span className="legend-item"><span className="legend-dot dot-add"></span> Green = Added</span>
          <span className="legend-item"><span className="legend-dot dot-mod"></span> Amber = Modified</span>
          <span className="legend-item">Right bar indicates change positions along the scrollbar</span>
        </span>
      </div>
    </div>
  );
}
