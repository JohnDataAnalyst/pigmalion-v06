import React, { useEffect, useState } from "react";
import axios from "axios";
import EmotionRadarChart from "./EmotionRadarChart";

const API_BASE = process.env.REACT_APP_API_BASE || "http://localhost:8000";

// Correspondance frontend → backend
const CATEGORY_MAPPING = {
  "arts_entertainment": "arts_&_culture",
  "business_entrepreneurship": "business_&_entrepreneurs",
  "pop_culture": "celebrity_&_pop_culture",
  "science_technology": "science_&_technology",
  "learning_educational": "learning_&_educational",
  "health_fitness": "fitness_&_health",
  "fashion_style": "fashion_&_style",
  "food_dining": "food_&_dining",
  "travel_adventure": "travel_&_adventure",
  "family": "relationships",
  "sports_gaming": "gaming",
  "news_social_concern": "news_&_social_concern"
};

export default function TrendsEmotion({ period, category }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!period || !category) return;

    const mappedCategory = CATEGORY_MAPPING[category] || category;

    setLoading(true);
    axios
      .get(`${API_BASE}/trends/emotion`, {
        params: { period, category: mappedCategory },
      })
      .then((response) => {
        const emotionList = response.data;

        const mappedData = {
          out_post_score_sentiments_anger: 0,
          out_post_score_sentiments_disgust: 0,
          out_post_score_sentiments_fear: 0,
          out_post_score_sentiments_joy: 0,
          out_post_score_sentiments_sadness: 0,
          out_post_score_sentiments_surprise: 0,
        };

        emotionList.forEach(({ label, score }) => {
          if (label === "anger") mappedData.out_post_score_sentiments_anger = score;
          else if (label === "disgust") mappedData.out_post_score_sentiments_disgust = score;
          else if (label === "fear") mappedData.out_post_score_sentiments_fear = score;
          else if (label === "joy") mappedData.out_post_score_sentiments_joy = score;
          else if (label === "surprise") mappedData.out_post_score_sentiments_surprise = score;
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
