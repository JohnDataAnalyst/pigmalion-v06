import React, { useState } from 'react';
import './App.css';
import logoPigmalion from './assets/logo-pigmalion.png';

import LeftColumn from './components/LeftColumn';
import RightColumn from './components/RightColumn';

const API_BASE = process.env.REACT_APP_API_BASE || 'http://localhost:8000';

export default function App() {
  /* ─── états globaux ───────────────────────────────────────── */
  const [url, setUrl]           = useState('');
  const [loading, setLoading]   = useState(false);
  const [data, setData]         = useState(null);
  const [error, setError]       = useState(null);
  const [dateFilter, setDateFilter] = useState('all');    // today | week | all

  /* ─── appel API pour analyser un post ─────────────────────── */
  const handleAnalyze = async () => {
    if (!url.trim()) return;
    setLoading(true);
    setError(null);
    setData(null);
    try {
      const r = await fetch(`${API_BASE}/analyze?url=${encodeURIComponent(url)}`);
      if (!r.ok) {
        const { detail } = await r.json().catch(() => ({}));
        throw new Error(detail || `Erreur ${r.status}`);
      }
      setData(await r.json());
    } catch (err) {
      setError(err.message || 'Échec de la requête');
    } finally {
      setLoading(false);
    }
  };

  /* ─── rendu général ───────────────────────────────────────── */
  return (
    <div className="App">
      {/* logo */}
      <header className="HEADER">
        <img src={logoPigmalion} alt="Logo Pigmalion" className="App-logo" />
      </header>

      {/* sous-headers */}
      <div className="HEADER_SUB_LEFT">
        <div className="header-title">
          Track <span className="highlight red">your</span> post
        </div>
        <div className="arrow">↓</div>
      </div>
      <div className="HEADER_SUB_RIGHT">
        <div className="header-title">
          Tren<span className="highlight green">ds</span>
        </div>
        <div className="arrow">↓</div>
      </div>

      {/* deux colonnes */}
      <div className="App-body">
        <LeftColumn
          url={url}
          setUrl={setUrl}
          loading={loading}
          error={error}
          data={data}
          onAnalyze={handleAnalyze}
        />

        <RightColumn
          dateFilter={dateFilter}
          setDateFilter={setDateFilter}
        />
      </div>
    </div>
  );
}
