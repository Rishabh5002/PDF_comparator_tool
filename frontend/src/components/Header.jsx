import React from 'react';
import { MoonIcon, SunIcon } from './Icons';

export default function Header({ theme, onToggleTheme, showNewComparison, onNewComparison }) {
  return (
    <header className="topbar">
      <div className="brand">
        <div className="brand-mark">FD</div>
        <div>
          <strong>FormDiff</strong>
          <span>Offline PDF Comparison</span>
        </div>
      </div>
      <div className="topbar-actions">
        <button
          id="themeToggle"
          className="theme-toggle-btn"
          type="button"
          onClick={onToggleTheme}
          title={theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'}
          aria-label="Toggle theme"
        >
          <span className="theme-icon" id="themeIcon">
            {theme === 'dark' ? <SunIcon /> : <MoonIcon />}
          </span>
          <span className="theme-label" id="themeLabel">
            {theme === 'dark' ? 'Light' : 'Dark'}
          </span>
        </button>

        {showNewComparison && (
          <button
            id="navBackBtn"
            className="nav-back-btn"
            type="button"
            onClick={onNewComparison}
          >
            New Comparison
          </button>
        )}

        <div className="secure-pill">
          <span className="dot"></span> Local processing
        </div>
      </div>
    </header>
  );
}
