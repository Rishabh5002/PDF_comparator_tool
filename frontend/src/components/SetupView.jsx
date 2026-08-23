import React, { useState } from 'react';
import { ShieldIcon, UploadIcon, LockIcon } from './Icons';

export default function SetupView({
  onCompare,
  isLoading,
  error,
}) {
  const [oldFile, setOldFile] = useState(null);
  const [newFile, setNewFile] = useState(null);
  const [oldPassword, setOldPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [threshold, setThreshold] = useState(0.45);

  const [oldDrag, setOldDrag] = useState(false);
  const [newDrag, setNewDrag] = useState(false);

  const handleOldDrop = (e) => {
    e.preventDefault();
    setOldDrag(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      setOldFile(e.dataTransfer.files[0]);
    }
  };

  const handleNewDrop = (e) => {
    e.preventDefault();
    setNewDrag(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      setNewFile(e.dataTransfer.files[0]);
    }
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!oldFile || !newFile) {
      alert('Please select both Original and Revised PDF files.');
      return;
    }
    onCompare({
      oldFile,
      newFile,
      oldPassword,
      newPassword,
      threshold,
    });
  };

  return (
    <div id="setupView">
      <section className="hero">
        <div>
          <p className="eyebrow">PRIVATE • OFFLINE • LOCAL</p>
          <h1>
            Compare form revisions<br />
            <em>without sending them anywhere.</em>
          </h1>
          <p className="hero-copy">
            Upload two revisions of a form. FormDiff extracts the structure, matches logical questions, and reports additions, removals, modifications and reordering locally.
          </p>
        </div>
        <div className="hero-card">
          <div className="shield">
            <ShieldIcon />
          </div>
          <div>
            <strong>No cloud AI required</strong>
            <span>PDF content stays on this machine.</span>
          </div>
        </div>
      </section>

      <section className="workspace">
        <div className="step-head">
          <span>01</span>
          <div>
            <h2>Choose revisions</h2>
            <p>Original on the left, revised on the right.</p>
          </div>
        </div>
        <form id="compareForm" onSubmit={handleSubmit}>
          <div className="upload-grid">
            <label
              className={`dropzone ${oldDrag ? 'drag' : ''}`}
              id="oldDrop"
              onDragEnter={(e) => { e.preventDefault(); setOldDrag(true); }}
              onDragOver={(e) => { e.preventDefault(); setOldDrag(true); }}
              onDragLeave={(e) => { e.preventDefault(); setOldDrag(false); }}
              onDrop={handleOldDrop}
            >
              <input
                type="file"
                name="old_pdf"
                accept="application/pdf,.pdf"
                onChange={(e) => setOldFile(e.target.files[0] || null)}
              />
              <div className="upload-icon">
                <UploadIcon />
              </div>
              <span className="drop-title">Original revision</span>
              <span className="drop-sub">Drop PDF or click to browse</span>
              <strong className="filename">{oldFile ? oldFile.name : ''}</strong>
              <div className="password-row">
                <span className="input-icon">
                  <LockIcon />
                </span>
                <input
                  name="old_password"
                  type="password"
                  placeholder="Password (if protected)"
                  value={oldPassword}
                  onChange={(e) => setOldPassword(e.target.value)}
                  onClick={(e) => e.stopPropagation()}
                />
              </div>
            </label>

            <div className="versus">VS</div>

            <label
              className={`dropzone revised ${newDrag ? 'drag' : ''}`}
              id="newDrop"
              onDragEnter={(e) => { e.preventDefault(); setNewDrag(true); }}
              onDragOver={(e) => { e.preventDefault(); setNewDrag(true); }}
              onDragLeave={(e) => { e.preventDefault(); setNewDrag(false); }}
              onDrop={handleNewDrop}
            >
              <input
                type="file"
                name="new_pdf"
                accept="application/pdf,.pdf"
                onChange={(e) => setNewFile(e.target.files[0] || null)}
              />
              <div className="upload-icon">
                <UploadIcon />
              </div>
              <span className="drop-title">Revised revision</span>
              <span className="drop-sub">Drop PDF or click to browse</span>
              <strong className="filename">{newFile ? newFile.name : ''}</strong>
              <div className="password-row">
                <span className="input-icon">
                  <LockIcon />
                </span>
                <input
                  name="new_password"
                  type="password"
                  placeholder="Password (if protected)"
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                  onClick={(e) => e.stopPropagation()}
                />
              </div>
            </label>
          </div>

          <div className="controls">
            <div>
              <label htmlFor="threshold">Match confidence</label>
              <input
                id="threshold"
                name="threshold"
                type="range"
                min="0.25"
                max="0.75"
                step="0.01"
                value={threshold}
                onChange={(e) => setThreshold(parseFloat(e.target.value))}
              />
              <span id="thresholdValue">{threshold.toFixed(2)}</span>
            </div>
            <button className="primary" type="submit" disabled={isLoading}>
              <span>Compare revisions</span>
              <span>→</span>
            </button>
          </div>
        </form>
      </section>

      {isLoading && (
        <section id="loading" className="status-card">
          <div className="spinner"></div>
          <div>
            <strong>Comparing locally…</strong>
            <span>Extracting, matching and generating reports on this machine.</span>
          </div>
        </section>
      )}

      {error && (
        <section id="error" className="error-card">
          {error}
        </section>
      )}
    </div>
  );
}
