import React, { useEffect, useState } from "react";
import axios from "axios";
import EmotionRadarChart from "./EmotionRadarChart";

const API_BASE = process.env.REACT_APP_API_BASE || "http://localhost:8000";

export default function TrendsEmotion({ period, category }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!period || !category) return;

    setLoading(true);
    axios
      .get(`${API_BASE}/trends/emotion`, {
        params: { period, category },
      })
      .then((response) => {
        const emotionList = response.data;

        const mappedData = {};
        emotionList.forEach(({ label, score }) => {
          mappedData[`out_post_score_sentiments_${label}`] = score;
        });

        setData(mappedData);
      })
      .catch((err) => {
        console.error("Erreur de récupération des émotions :", err);
        setData(null);
      })
      .finally(() => setLoading(false));
  }, [period, category]);

  return (
    <div className="box_trends_emotion">
      {loading && <p>Chargement...</p>}
      {!loading && data ? (
        <EmotionRadarChart data={data} />
      ) : (
        !loading && <p>Aucune donnée disponible pour cette période et catégorie.</p>
      )}
    </div>
  );
}
