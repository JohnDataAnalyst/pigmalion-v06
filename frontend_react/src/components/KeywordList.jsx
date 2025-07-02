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
        setKeywords(data || []);
      } catch (error) {
        console.error("Erreur lors de la récupération des mots-clés :", error);
        setKeywords([]);
      }
    };

    fetchKeywords();
  }, [category, period]);

  if (keywords.length === 0) return <p className="no-keywords">Aucun mot-clé trouvé.</p>;

  const left = keywords.slice(0, 10);
  const right = keywords.slice(10, 20);

  return (
    <div
      style={{
        display: "flex",
        justifyContent: "center", // <== centrage horizontal
        width: "100%",
      }}
    >
      <div
        style={{
          display: "flex",
          gap: "2rem",
          fontSize: "0.85rem",
          lineHeight: "1.4",
          maxHeight: "320px",
          overflowY: "auto",
          paddingRight: "0.5rem",
        }}
      >
        <div style={{ minWidth: "130px" }}>
          {left.map((item, idx) => (
            <div
              key={idx}
              style={{
                whiteSpace: "nowrap",
                overflow: "hidden",
                textOverflow: "ellipsis",
              }}
            >
              <strong>{idx + 1}.</strong> {item.keyword} ({item.occurrence})
            </div>
          ))}
        </div>
        <div style={{ minWidth: "130px" }}>
          {right.map((item, idx) => (
            <div
              key={idx + 10}
              style={{
                whiteSpace: "nowrap",
                overflow: "hidden",
                textOverflow: "ellipsis",
              }}
            >
              <strong>{idx + 11}.</strong> {item.keyword} ({item.occurrence})
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}