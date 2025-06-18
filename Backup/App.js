// src/App.js
import React, { useState } from 'react';
import logoPigmalion from './assets/logo-pigmalion.png';
import ToxicityChart from './components/charts/ToxicityChart';
import './styles/App.css';

function App() {
  /* -------------------- états -------------------- */
  const [url, setUrl] = useState('');
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);

  /* -------------------- appel API -------------------- */
  const handleAnalyze = async () => {
    if (!url) return;
    setLoading(true);
    setError(null);
    setData(null);

    try {
      const resp = await fetch(
        `http://localhost:8000/analyze?url=${encodeURIComponent(url)}`
      );

      if (!resp.ok) {
        const detail = await resp.json().catch(() => null);
        throw new Error(detail || 'Erreur inconnue');
      }

      const json = await resp.json();

      /* --- nettoyage du contenu texte pour l’affichage --- */
      if (json?.out_post_clean_contenu) {
        json.out_post_clean_contenu = json.out_post_clean_contenu
          .replace(/\s*\n\s*/g, ' ')  // tous les retours à la ligne → espace
          .replace(/\s{2,}/g, ' ')    // espaces multiples → un seul
          .trim();
      }

      setData(json);
    } catch (err) {
      setError(err.message || 'Échec de la requête');
    } finally {
      setLoading(false);
    }
  };

  /* -------------------- données graph. toxicité -------------------- */
  const toxiciteData = data
    ? [
        { label: 'Toxic',   score: data.out_post_score_toxicite_toxic },
        { label: 'Obscene', score: data.out_post_score_toxicite_obscene },
        { label: 'Insult',  score: data.out_post_score_toxicite_insult },
        { label: 'Severe',  score: data.out_post_score_toxicite_toxicsevere },
        { label: 'Hate',    score: data.out_post_score_toxicite_hate },
        { label: 'Threat',  score: data.out_post_score_toxicite_threat },
      ]
    : [];

  /* -------------------- rendu -------------------- */
  return (
    <div className="App">
      {/* Logo */}
      <header className="HEADER">
        <img src={logoPigmalion} alt="Logo Pigmalion" className="App-logo" />
      </header>

      {/* Sous-headers */}
      <div className="HEADER_SUB_LEFT">
        <div className="title-small">
          Track <span className="highlight red">your</span> post
        </div>
      </div>
      <div className="HEADER_SUB_RIGHT">
        <span className="highlight green">dds</span>
      </div>

      {/* Corps principal */}
      <div className="App-body">
        <div className="left-column">
          {/* Saisie URL */}
          <div className="BLOCL1_URL">
            <div className="App-inputbar">
              <input
                className="url-input"
                placeholder="Entrez l’URL du post Bluesky"
                value={url}
                onChange={(e) => setUrl(e.target.value)}
              />
              <button
                className="btn-analyze"
                onClick={handleAnalyze}
                disabled={loading}
              >
                {loading ? '…' : 'Analyser'}
              </button>
            </div>
            {error && <div className="error-message">{error}</div>}
          </div>

          {/* Texte du post */}
          <div className="BLOCL2_TEXT">
            <div className="App-postcontent">
              {loading && <div className="loading-spinner"></div>}
              {!loading && data?.out_post_clean_contenu && (
                <div className="post-text">{data.out_post_clean_contenu}</div>
              )}
              {!loading && !data?.out_post_clean_contenu && (
                <div className="post-placeholder">Aucun texte à afficher</div>
              )}
            </div>
          </div>

          {/* Graphique de toxicité */}
          <div className="BLOCL5_SINGLE_TOXICITE">
            <div className="chart-title">Score de toxicité</div>
            <div className="chart-container">
              {data ? (
                <ToxicityChart data={toxiciteData} />
              ) : (
                <div className="chart-placeholder">Pas de données disponibles</div>
              )}
            </div>
          </div>
        </div>

        {/* colonne de droite (à remplir plus tard) */}
        <div className="right-column" />
      </div>
    </div>
  );
}

export default App;
