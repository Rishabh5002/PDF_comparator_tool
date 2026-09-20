import React, { useState, useEffect } from 'react';
import Header from './components/Header';
import SetupView from './components/SetupView';
import ResultsView from './components/ResultsView';

export default function App() {
  const [theme, setTheme] = useState(() => {
    const saved = localStorage.getItem('formdiff_theme');
    if (saved) return saved;
    return window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches
      ? 'dark'
      : 'light';
  });

  const [view, setView] = useState('setup'); // 'setup' | 'results'
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');
  const [comparisonData, setComparisonData] = useState(null);

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('formdiff_theme', theme);
  }, [theme]);

  const toggleTheme = () => {
    setTheme((prev) => (prev === 'dark' ? 'light' : 'dark'));
  };

  const handleCompare = async ({ oldFile, newFile, oldPassword, newPassword, threshold }) => {
    setError('');
    setIsLoading(true);

    const formData = new FormData();
    formData.append('old_pdf', oldFile);
    formData.append('new_pdf', newFile);
    if (oldPassword) formData.append('old_password', oldPassword);
    if (newPassword) formData.append('new_password', newPassword);
    formData.append('threshold', threshold.toString());

    try {
      const response = await fetch('/api/compare', {
        method: 'POST',
        body: formData,
      });
      const data = await response.json();
      if (!response.ok || !data.ok) {
        throw new Error(data.error || data.detail || 'Comparison failed.');
      }
      setComparisonData(data);
      setView('results');
      window.scrollTo({ top: 0, behavior: 'smooth' });
    } catch (err) {
      setError(err.message || 'An error occurred while comparing PDFs.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleReset = () => {
    setView('setup');
    setComparisonData(null);
    setError('');
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  return (
    <>
      <Header
        theme={theme}
        onToggleTheme={toggleTheme}
        showNewComparison={view === 'results'}
        onNewComparison={handleReset}
      />

      <main className={`shell ${view === 'results' ? 'shell-wide' : ''}`}>
        {view === 'setup' && (
          <SetupView
            onCompare={handleCompare}
            isLoading={isLoading}
            error={error}
          />
        )}

        {view === 'results' && comparisonData && (
          <ResultsView
            payload={comparisonData.payload}
            reports={comparisonData.reports}
            onBack={handleReset}
            onReset={handleReset}
          />
        )}
      </main>

      <footer>
        <span>FormDiff • PDF Comparison & Difference Analysis</span>
        <span>Intelligent structural and text revision comparison</span>
      </footer>
    </>
  );
}
