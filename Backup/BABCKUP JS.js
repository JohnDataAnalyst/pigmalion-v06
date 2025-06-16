import React, { useState } from 'react';
import './App.css';
import logoPigmalion from './assets/logo-pigmalion.png';
import ToxicityChart from './components/Toxicitychart';

function App() {
  const [url, setUrl] = useState('');
  const [loading, setLoading] = useState(false);
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);

  const handleAnalyze = async () => {
    if (!url.trim()) return;
    setLoading(true);
    setError(null);
    setData(null);
    try {
      const response = await fetch(`http://localhost:8000/analyze?url=${encodeURIComponent(url)}`);
      if (!response.ok) {
        const { detail } = await response.json();
        throw new Error(detail || 'Erreur inconnue');
      }
      const json = await response.json();
      setData(json);
    } catch (err) {
      setError(err.message || 'Échec de la requête');
    } finally {
      setLoading(false);
    }
  };

  const toxiciteData = data
    ? [
        { label: 'Toxic', score: data.out_post_score_toxicite_toxic },
        { label: 'Obscene', score: data.out_post_score_toxicite_obscene },
        { label: 'Insult', score: data.out_post_score_toxicite_insult },
        { label: 'Severe', score: data.out_post_score_toxicite_toxicsevere },
        { label: 'Hate', score: data.out_post_score_toxicite_hate },
        { label: 'Threat', score: data.out_post_score_toxicite_threat }
      ]
    : [];

  return (
    <div className="App">
      <header className="HEADER">
        <img src={logoPigmalion} alt="Logo Pigmalion" className="App-logo" />
      </header>

      <div className="HEADER_SUB_LEFT">
        <div className="header-title">Track <span className="highlight red">your</span> post</div>
        <div className="arrow">↓</div>
      </div>

      <div className="HEADER_SUB_RIGHT">
        <div className="header-title">Tren<span className="highlight green">ds</span></div>
        <div className="arrow">↓</div>
      </div>

      <div className="App-body">
        <div className="left-column">
          <div className="BLOCL1_URL">
            <div className="App-inputbar">
              <input type="text" placeholder="https://bsky.app/profile/…/post/…" value={url} onChange={e => setUrl(e.target.value)} className="url-input" />
              <button className="btn-analyze" onClick={handleAnalyze} disabled={loading}>
                {loading ? 'Chargement…' : 'Analyser'}
              </button>
            </div>
          </div>

          <div className="BLOCL2_TEXT">
            <section className="App-postcontent">
              {error && <div className="error-message">{error}</div>}
              {data ? (
                <div className="post-text">{data.out_post_text || 'Le post est vide.'}</div>
              ) : (
                <div className="post-placeholder">Ici s’affichera le texte du post</div>
              )}
            </section>
          </div>

          <div className="BLOCL3_DATA_POST">
            <div className="metric-card"><div className="metric-value">{data ? data.out_post_comment : '--'}</div><div className="metric-label">Comments</div></div>
            <div className="metric-card"><div className="metric-value">{data ? data.out_post_repost : '--'}</div><div className="metric-label">Reposts</div></div>
            <div className="metric-card"><div className="metric-value">{data ? data.out_post_like : '--'}</div><div className="metric-label">Likes</div></div>
          </div>

          <div className="BLOCL4_DATA_COMPTE">
            {data ? (
              <div className="info-card">
                <h4 className="info-card-title">{data.out_compte_name}</h4>
                <div className="info-grid">
                  <div className="info-label">Créé le</div><div className="info-value">{data.out_compte_creationdate}</div>
                  <div className="info-label">Abonnements</div><div className="info-value">{data.out_compte_following}</div>
                  <div className="info-label">Abonnés</div><div className="info-value">{data.out_compte_followers}</div>
                </div>
              </div>
            ) : (
              <p>Informations du compte…</p>
            )}
          </div>

          <div className="BLOCL5_SINGLE_TOXICITE">
            <ToxicityChart data={toxiciteData} />
          </div>
          <div className="BLOCL6_SINGLE_SENTIMENTS" />
          <div className="BLOCL7_SINGLE_BOT_DETECTION" />
        </div>

        <div className="right-column">
          <div className="BLOCR1_TRENDS_FILTRE_DATE" />
          <div className="BLOCR2_TRENDS_NOMBRE_POST" />
          <div className="BLOCR3_TRENDS_LISTE_KEYWORDS" />
          <div className="BLOCR4_TRENDS_SENTIMENTS" />
          <div className="BLOCR5_FILTRE_TRENDS_CATEGORIES" />
          <div className="BLOCR6_TRENDS_TOXICITE" />
          <div className="BLOCR7_TRENDS_BOT_DETECTION" />
        </div>
      </div>
    </div>
  );
}

export default App;
