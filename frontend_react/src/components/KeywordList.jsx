import React, { useEffect, useState } from "react";

export default function KeywordList({ category, period }) {
  const [keywords, setKeywords] = useState([]);

  useEffect(() => {
    if (!category || !period) return;

    const fetchKeywords = async () => {
      try {
        const response = await fetch(
          `http://localhost:8000/api/keywords?period=${period}&category=${category}`
        );
        const data = await response.json();
        setKeywords(data);
      } catch (error) {
        console.error("Erreur lors de la récupération des mots-clés :", error);
        setKeywords([]);
      }
    };

    fetchKeywords();
  }, [category, period]);

  return (
    <div className="keyword-grid">
      {keywords.length === 0 ? (
        <div>Aucun mot-clé trouvé.</div>
      ) : (
        keywords.map((item, idx) => (
          <div key={idx}>
            <span className="rank">{idx + 1}.</span> {item.keyword} ({item.occurrence || 0})
          </div>
        ))
      )}
    </div>
  );
}
