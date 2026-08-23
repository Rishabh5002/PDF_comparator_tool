import React, { useState } from 'react';
import DetectedChanges from './DetectedChanges';
import QuestionAlignment from './QuestionAlignment';
import OverviewDetails from './OverviewDetails';

function countTypes(changes) {
  const counts = { ADDED: 0, REMOVED: 0, MODIFIED: 0, REORDERED: 0 };
  for (const d of changes || []) {
    const type = String(d.type || d.change_type || '').toUpperCase();
    if (type.includes('ADDED')) counts.ADDED++;
    else if (type.includes('REMOVED')) counts.REMOVED++;
    else if (type.includes('REORDER')) counts.REORDERED++;
    else counts.MODIFIED++;
  }
  return counts;
}

export default function ResultsView({
  payload,
  reports = {},
  onBack,
  onReset,
}) {
  const [activeTab, setActiveTab] = useState('tab-changes');

  const oldDoc = payload.old_document || {};
  const newDoc = payload.new_document || {};
  const comparison = payload.comparison || {};
  const changes = comparison.differences || comparison.changes || [];
  const questionPairs = payload.question_pairs || [];
  const stats = countTypes(changes);

  return (
    <section id="resultsView" className="results-page">
      <div className="results-header-bar">
        <div>
          <button type="button" className="back-link" id="backToUpload" onClick={onBack}>
            ← Back to upload
          </button>
          <h2>Comparison Results</h2>
          <p className="results-doc-subtitle" id="docSubtitle">
            Comparing "{oldDoc.filename || 'Original'}" ({oldDoc.pages || 1} pages) → "{newDoc.filename || 'Revised'}" ({newDoc.pages || 1} pages)
          </p>
        </div>
        <div className="results-quick-actions">
          <div className="downloads-compact">
            <span className="export-label">Export:</span>
            <div id="downloadLinks">
              {Object.entries(reports).map(([kind, url]) => (
                <a
                  key={kind}
                  className="download-btn"
                  href={url}
                  download={`comparison.${kind}`}
                >
                  <span className="fmt-pill">{kind.toUpperCase()}</span>
                </a>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* STATS OVERVIEW */}
      <div className="stats" id="stats">
        <div className="stat added">
          <div className="stat-header">
            <span className="stat-dot"></span>
            <span>Added</span>
          </div>
          <strong>{stats.ADDED}</strong>
        </div>
        <div className="stat removed">
          <div className="stat-header">
            <span className="stat-dot"></span>
            <span>Removed</span>
          </div>
          <strong>{stats.REMOVED}</strong>
        </div>
        <div className="stat changed">
          <div className="stat-header">
            <span className="stat-dot"></span>
            <span>Modified</span>
          </div>
          <strong>{stats.MODIFIED}</strong>
        </div>
        <div className="stat reordered">
          <div className="stat-header">
            <span className="stat-dot"></span>
            <span>Reordered</span>
          </div>
          <strong>{stats.REORDERED}</strong>
        </div>
      </div>

      {/* NAVIGATION TABS */}
      <div className="results-nav">
        <button
          type="button"
          className={`nav-tab ${activeTab === 'tab-changes' ? 'active' : ''}`}
          onClick={() => setActiveTab('tab-changes')}
        >
          <span>Detected Differences</span>
          <span className="tab-badge" id="changesTabBadge">
            {changes.length}
          </span>
        </button>
        <button
          type="button"
          className={`nav-tab ${activeTab === 'tab-questions' ? 'active' : ''}`}
          onClick={() => setActiveTab('tab-questions')}
        >
          <span>Question Alignment</span>
          <span className="tab-badge" id="questionsTabBadge">
            {questionPairs.length}
          </span>
        </button>
        <button
          type="button"
          className={`nav-tab ${activeTab === 'tab-overview' ? 'active' : ''}`}
          onClick={() => setActiveTab('tab-overview')}
        >
          <span>Overview & Details</span>
        </button>
      </div>

      {/* TAB CONTENTS */}
      {activeTab === 'tab-changes' && <DetectedChanges changes={changes} />}
      {activeTab === 'tab-questions' && (
        <QuestionAlignment questionPairs={questionPairs} />
      )}
      {activeTab === 'tab-overview' && <OverviewDetails payload={payload} />}

      <div className="results-footer-action">
        <button className="secondary" id="reset" onClick={onReset}>
          Compare another pair
        </button>
      </div>
    </section>
  );
}
