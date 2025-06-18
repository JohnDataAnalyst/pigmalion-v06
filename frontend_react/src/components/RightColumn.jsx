import React, { useState, useEffect } from "react";
import axios from "axios";
import "./RightColumn.css";          //  ← pense à ajouter un peu de CSS

const CATEGORIES = [
  "news_social_concern","arts_entertainment","sports_gaming","pop_culture",
  "learning_educational","science_technology","business_entrepreneurship",
  "food_dining","travel_adventure","fashion_style","health_fitness","family"
];

export default function RightColumn({ dateFilter, setDateFilter }) {
  const [category, setCategory] = useState(CATEGORIES[0]);
  const [count, setCount]       = useState("--");

  // appel API à chaque changement de filtre
  useEffect(() => {
    async function fetchCount() {
      try {
        const { data } = await axios.get("http://localhost:8000/trends/count", {
          params: { period: dateFilter, category }
        });
        setCount(data.posts.toLocaleString());
      } catch (err) {
        setCount("--");
      }
    }
    fetchCount();
  }, [dateFilter, category]);

  return (
    <div className="right-column">

      {/* filtre Today / Week / All time */}
      <div className="BLOCR1_TRENDS_FILTRE_DATE card">
        <div className="filter-group">
          {["today","week","all"].map(p => (
            <button key={p}
              className={`filter-btn ${dateFilter===p?"active":""}`}
              onClick={()=>setDateFilter(p)}
            >
              {p==="today"?"Today":p==="week"?"This week":"All time"}
            </button>
          ))}
        </div>
      </div>

      {/* bloc compteur de posts */}
      <div className="BLOCR2_TRENDS_NOMBRE_POST card center">
        <h3 style={{marginBottom:"0.25rem"}}>{count}</h3>
        <small>posts</small>
      </div>

      {/* grille 12 filtres catégories (3 × 4) */}
      <div className="BLOCR5_FILTRE_TRENDS_CATEGORIES card">
        <div className="cat-grid">
          {CATEGORIES.map(cat => (
            <button key={cat}
              className={`cat-btn ${category===cat?"active":""}`}
              onClick={()=>setCategory(cat)}
              title={cat.replace("_"," ")}
            >
              {cat.replace(/_/g," ")}
            </button>
          ))}
        </div>
      </div>

      {/* espaces réservés */}
      <div className="BLOCR3_TRENDS_LISTE_KEYWORDS card" />
      <div className="BLOCR4_TRENDS_SENTIMENTS   card" />
      <div className="BLOCR6_TRENDS_TOXICITE     card" />
      <div className="BLOCR7_TRENDS_BOT_DETECTION card" />
    </div>
  );
}
