// src/App.js
import React, { useState } from 'react';
import './App.css';
import logoPigmalion from './assets/logo-pigmalion.png';

function App() {
  const [url, setUrl] = useState('');
  const [loading, setLoading] = useState(false);
  const [postData, setPostData] = useState(null);
  const [error, setError] = useState(null);

  const handleAnalyze = async () => {
    if (!url.trim()) return;
    setLoading(true);
    setError(null);
    setPostData(null);

    try {
      const response = await fetch(
        `http://localhost:8000/analyze?url=${encodeURIComponent(url)}`
      );
      if (!response.ok) {
        const { detail } = await response.json();
        throw new Error(detail || 'Erreur inconnue');
      }
      const data = await response.json();
      setPostData(data);
    } catch (err) {
      setError(err.message || 'Échec de la requête');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="App">
      {/* 1. En-tête / Logo */}
      <header className="App-header">
        <img src={logoPigmalion} alt="Logo Pigmalion" className="App-logo" />
      </header>

      {/* 2+3. “Track your post” + Barre d’entrée alignées sous deux colonnes */}
      <div className="App-top-row">
        <div className="left-column">
          <div className="track-your-post">
            <span className="title-small">
              Track&nbsp;<span className="highlight">your</span>&nbsp;post
            </span>
            <div className="arrow-down">&#x2193;</div>
          </div>

          <div className="App-inputbar">
            <input
              type="text"
              placeholder="https://bsky.app/profile/…/post/…"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              className="url-input"
            />
            <button
              className="btn-analyze"
              onClick={handleAnalyze}
              disabled={loading}
            >
              {loading ? 'Chargement…' : 'Analyser'}
            </button>
          </div>
        </div>

        <div className="right-column">
          <div className="trends">
            <span className="title-small">
              Tren<span className="highlight">d</span>s
            </span>
            <div className="arrow-down arrow-green">&#x2193;</div>
          </div>
          {/* Vous pouvez ajouter d’autres éléments sous “Trends” ici */}
        </div>
      </div>

      {/* 4. Zone d’affichage du contenu du post */}
      <section className="App-postcontent">
        {error && <div className="error-message">{error}</div>}
        {postData ? (
          <div className="post-text">
            {postData.out_post_text || 'Le post est vide.'}
          </div>
        ) : (
          <div className="post-placeholder">
            Ici s’affichera le texte du post
          </div>
        )}
      </section>

      {/* 5. Ligne de métriques (Comments, Reposts, Likes) */}
      <section className="App-metrics">
        <div className="metric-card">
          <div className="metric-value">
            {postData ? postData.out_post_comment : '--'}
          </div>
          <div className="metric-label">Comments</div>
        </div>
        <div className="metric-card">
          <div className="metric-value">
            {postData ? postData.out_post_repost : '--'}
          </div>
          <div className="metric-label">Reposts</div>
        </div>
        <div className="metric-card">
          <div className="metric-value">
            {postData ? postData.out_post_like : '--'}
          </div>
          <div className="metric-label">Likes</div>
        </div>
      </section>
    </div>
  );
}

export default App;
