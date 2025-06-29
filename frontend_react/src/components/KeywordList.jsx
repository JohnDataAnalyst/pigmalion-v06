import { useEffect, useState } from "react";
import axios from "axios";
import "./RightColumn.css";           // on réutilise la feuille existante

export default function KeywordList({ period, category }) {
  const [keywords, setKeywords] = useState([]);

  useEffect(() => {
    const fetchKeywords = async () => {
      try {
        const res = await axios.get(
          `${process.env.REACT_APP_API_URL || ""}/api/keywords`,
          { params: { period, category } }
        );
        setKeywords(res.data);
      } catch (err) {
        console.error(err);
        setKeywords([]);
      }
    };
    fetchKeywords();
  }, [period, category]);

  // 2 colonnes, 10 lignes chacune
  const left = keywords.slice(0, 10);
  const right = keywords.slice(10, 20);

  return (
    <div className="keyword-grid">
      <div>
        {left.map((k) => (
          <div key={k.rank}>
            <span className="rank">{k.rank}</span>&nbsp;{k.keyword}
          </div>
        ))}
      </div>
      <div>
        {right.map((k) => (
          <div key={k.rank}>
            <span className="rank">{k.rank}</span>&nbsp;{k.keyword}
          </div>
        ))}
      </div>
    </div>
  );
}
