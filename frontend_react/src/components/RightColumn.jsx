import React, { useState, useEffect } from "react";
import axios from "axios";
import KeywordList from "./KeywordList";
import TrendsEmotion from "./TrendsEmotion";
import "./RightColumn.css";

const CATEGORIES = [
  "news_social_concern", "arts_entertainment", "sports_gaming", "pop_culture",
  "learning_educational", "science_technology", "business_entrepreneurship",
  "food_dining", "travel_adventure", "fashion_style", "health_fitness", "family"
];

const API_BASE = process.env.REACT_APP_API_BASE || "http://localhost:8000";

export default function RightColumn({ dateFilter, setDateFilter }) {
  const [category, setCategory] = useState("all");
  const [count, setCount] = useState("--");

  useEffect(() => {
    async function fetchCount() {
      try {
        const { data } = await axios.get(`${API_BASE}/trends/count`, {
          params: { period: dateFilter, category }
        });
        if (data && typeof data.posts === "number") {
          setCount(data.posts.toLocaleString());
        } else {
          setCount("--");
        }
      } catch (err) {
        console.error("Erreur /trends/count :", err);
        setCount("--");
      }
    }
    fetchCount();
  }, [dateFilter, category]);

  return (
    <div className="right-column">
      <div className="BLOCR1_TRENDS_FILTRE_DATE card">
        <div className="filter-group">
          {["today", "week", "all"].map(p => (
            <button key={p}
              className={`filter-btn ${dateFilter === p ? "active" : ""}`}
              onClick={() => setDateFilter(p)}
            >
              {p === "today" ? "Today" : p === "week" ? "This week" : "All time"}
            </button>
          ))}
        </div>
      </div>

      <div className="BLOCR2_TRENDS_NOMBRE_POST card center">
        <h3 style={{ marginBottom: "0.25rem" }}>
          {count !== "--" ? `${count} posts` : "--"}
        </h3>
      </div>

      <div className="BLOCR5_FILTRE_TRENDS_CATEGORIES card">
        <div className="cat-grid">
          {CATEGORIES.map(cat => (
            <button key={cat}
              className={`cat-btn ${category === cat ? "active" : ""}`}
              onClick={() => setCategory(prev => (prev === cat ? "all" : cat))}
              title={cat.replace("_", " ")}
            >
              {cat.replace(/_/g, " ")}
            </button>
          ))}
        </div>
      </div>

      <div className="BLOCR3_TRENDS_LISTE_KEYWORDS card">
        <h3 className="section-title">Top&nbsp;20 keywords</h3>
        <KeywordList period={dateFilter} category={category} />
      </div>

      <div className="BLOCR4_TRENDS_EMOTIONS card">
        <h3 className="section-title">Sentiment trends</h3>
        <TrendsEmotion period={dateFilter} category={category} />
      </div>

      <div className="BLOCR6_TRENDS_TOXICITE card" />
      <div className="BLOCR7_TRENDS_BOT_DETECTION card" />
    </div>
  );
}
