// src/components/TrendsEmotion.jsx
import React, { useEffect, useState } from "react";
import {
  Radar, RadarChart, PolarGrid,
  PolarAngleAxis, PolarRadiusAxis, ResponsiveContainer
} from "recharts";
import axios from "axios";

const API_BASE = process.env.REACT_APP_API_BASE || "http://localhost:8000";

export default function TrendsEmotion({ period, category }) {
  const [data, setData] = useState([]);

  useEffect(() => {
    axios.get(`${API_BASE}/trends/emotion`, {
      params: { period, category }
    })
    .then((res) => setData(res.data))
    .catch(() => setData([]));
  }, [period, category]);

  return (
    <div className="BLOCR4_TRENDS_EMOTIONS card">
      <h3 className="section-title">Emotions moyennes</h3>
      {data.length > 0 ? (
        <div style={{ width: "100%", height: 250 }}>
          <ResponsiveContainer width="100%" height="100%">
            <RadarChart data={data} cx="50%" cy="50%" outerRadius="90%">
              <PolarGrid />
              <PolarAngleAxis dataKey="label" />
              <PolarRadiusAxis angle={30} domain={[0, 1]} />
              <Radar
                name="Sentiment"
                dataKey="score"
                stroke="#0f172a"
                fill="#3b82f6"
                fillOpacity={0.6}
              />
            </RadarChart>
          </ResponsiveContainer>
        </div>
      ) : (
        <p>Chargement des émotions…</p>
      )}
    </div>
  );
}
