import React from 'react';

export default function OverviewDetails({ payload = {} }) {
  const oldDoc = payload.old_document || {};
  const newDoc = payload.new_document || {};
  const summary = payload.local_summary || {};
  const security = payload.security || {};
  const total = (payload.comparison?.differences || payload.comparison?.changes || []).length;

  const metaItems = [
    {
      title: 'Comparison Scope',
      value: 'Full Document',
      subtitle: 'Fields, questions, and page text compared',
    },
    {
      title: 'Detected Differences',
      value: `${total} differences`,
      subtitle: 'Classified into additions, removals, modifications & reordering',
    },
    {
      title: 'Document Protection',
      value: oldDoc.encrypted || newDoc.encrypted ? 'Password Protected' : 'Standard',
      subtitle: oldDoc.encrypted || newDoc.encrypted ? 'Authenticated decryption applied' : 'Standard unencrypted PDF files',
    },
    {
      title: 'Matching Method',
      value: 'Structural Alignment',
      subtitle: 'Multi-factor question and content mapping',
    },
  ];

  return (
    <div id="tab-overview" className="tab-content active">
      <div className="result-grid">
        <div className="panel overview-panel">
          <div className="panel-head">
            <div>
              <h3>Document Details & Summary</h3>
              <p className="panel-sub">File properties and structural change counts.</p>
            </div>
          </div>
          <div id="documents" className="details-padded">
            <div className="doc-info-group">
              <div className="doc-info-card">
                <span className="doc-info-label">ORIGINAL REVISION</span>
                <div className="doc-info-val">{oldDoc.filename || '—'}</div>
                <div className="doc-info-sub">
                  {oldDoc.pages || 0} pages · {oldDoc.questions || 0} questions{' '}
                  {oldDoc.encrypted ? '· Encrypted' : ''}
                </div>
              </div>
              <div className="doc-info-card">
                <span className="doc-info-label">REVISED REVISION</span>
                <div className="doc-info-val">{newDoc.filename || '—'}</div>
                <div className="doc-info-sub">
                  {newDoc.pages || 0} pages · {newDoc.questions || 0} questions{' '}
                  {newDoc.encrypted ? '· Encrypted' : ''}
                </div>
              </div>
              <div className="doc-info-card summary-card">
                <span className="doc-info-label">COMPARISON SUMMARY</span>
                <div className="doc-info-val">
                  {summary.summary || summary.text || `${total} differences detected.`}
                </div>
              </div>
            </div>
          </div>
        </div>

        <div className="panel security-panel overview-panel">
          <div className="panel-head">
            <div>
              <h3>Comparison Details</h3>
              <p className="panel-sub">Document properties and analysis specifications.</p>
            </div>
            <span className="good">Complete</span>
          </div>
          <div id="security" className="security-grid-padded">
            {metaItems.map((item, i) => (
              <div key={i} className="security-item">
                <div className="security-item-head">
                  <strong>{item.title}</strong>
                  <span className="security-val">{item.value}</span>
                </div>
                <span className="security-sub">{item.subtitle}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
