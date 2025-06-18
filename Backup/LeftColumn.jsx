import React from 'react';
import ToxicityChart from './Toxicitychart';
import EmotionRadarChart from './EmotionRadarChart';

/* helpers ---------------------------------------------------- */
const buildToxicData = d => d ? [
  { label: 'Toxic',   score: d.out_post_score_toxicite_toxic },
  { label: 'Obscene', score: d.out_post_score_toxicite_obscene },
  { label: 'Insult',  score: d.out_post_score_toxicite_insult },
  { label: 'Severe',  score: d.out_post_score_toxicite_toxicsevere },
  { label: 'Hate',    score: d.out_post_score_toxicite_hate },
  { label: 'Threat',  score: d.out_post_score_toxicite_threat }
] : [];

export default function LeftColumn({
  url, setUrl, loading, error, data, onAnalyze
}) {
  const toxiciteData = buildToxicData(data);

  return (
    <div className="left-column">
      {/* saisie URL */}
      <div className="BLOCL1_URL card">
        <div className="App-inputbar">
          <input
            type="text"
            className="url-input"
            placeholder="https://bsky.app/profile/…/post/…"
            value={url}
            onChange={e => setUrl(e.target.value)}
          />
          <button
            className="btn-analyze"
            onClick={onAnalyze}
            disabled={loading}
          >
            {loading ? 'Chargement…' : 'Analyser'}
          </button>
        </div>
      </div>

      {/* texte du post */}
      <div className="BLOCL2_TEXT card">
        <section className="App-postcontent">
          {error && <div className="error-message">{error}</div>}
          {data ? (
            <div className="post-text">
              {data.out_post_text || 'Le post est vide.'}
            </div>
          ) : (
            <div className="post-placeholder">
              Ici s’affichera le texte du post
            </div>
          )}
        </section>
      </div>

      {/* métriques post */}
      <div className="BLOCL3_DATA_POST card">
        {['comment','repost','like'].map((k,i)=>(
          <div className="metric-card" key={i}>
            <div className="metric-value">
              {data ? data['out_post_'+k] : '--'}
            </div>
            <div className="metric-label">
              {k==='comment'?'Comments':k==='repost'?'Reposts':'Likes'}
            </div>
          </div>
        ))}
      </div>

      {/* info compte */}
      <div className="BLOCL4_DATA_COMPTE card">
        {data ? (
          <>
            <h4 className="info-card-title">{data.out_compte_name}</h4>
            <div className="info-metrics">
              <div className="metric-card">
                <div className="metric-value">{data.out_compte_creationdate}</div>
                <div className="metric-label">Créé le</div>
              </div>
              <div className="metric-card">
                <div className="metric-value">{data.out_compte_following}</div>
                <div className="metric-label">Abonnements</div>
              </div>
              <div className="metric-card">
                <div className="metric-value">{data.out_compte_followers}</div>
                <div className="metric-label">Abonnés</div>
              </div>
            </div>
          </>
        ) : (
          <p>Informations du compte…</p>
        )}
      </div>

      {/* toxicité */}
      <div className="BLOCL5_SINGLE_TOXICITE card">
        <ToxicityChart data={toxiciteData} />
      </div>

      {/* radar émotions */}
      <div className="BLOCL6_SINGLE_SENTIMENTS card">
        {data ? (
          <EmotionRadarChart data={data} />
        ) : (
          <p className="chart-placeholder">
            Le radar des émotions s’affichera ici
          </p>
        )}
      </div>

      {/* (placeholder) bot */}
      <div className="BLOCL7_SINGLE_BOT_DETECTION card" />
    </div>
  );
}
