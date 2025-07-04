import React, { useState, useEffect } from "react";
import axios from "axios";
import TimeFilter from "./TimeFilter";
import CategoryFilter from "./CategoryFilter";

const API_BASE = process.env.REACT_APP_API_BASE || "http://localhost:8000";

export default function TrendsToxicite() {
  const [category, setCategory] = useState("news_social_concern");
  const [period, setPeriod] = useState("week");
  const [start_date, setStartDate] = useState(null);
  const [end_date, setEndDate] = useState(null);
  const [stats7j, setStats7j] = useState(null);
  const [statsAll, setStatsAll] = useState(null);

  // Génération des dates selon période sélectionnée
  useEffect(() => {
    const today = new Date();
    if (period === "today") {
      const d = today.toISOString().split("T")[0];
      setStartDate(d);
      setEndDate(d);
    } else if (period === "week") {
      const d1 = new Date(today);
      d1.setDate(d1.getDate() - 6);
      setStartDate(d1.toISOString().split("T")[0]);
      setEndDate(today.toISOString().split("T")[0]);
    } else {
      setStartDate(null);
      setEndDate(null);
    }
  }, [period]);

  // Appels API
  useEffect(() => {
    if (!category) return;

    axios
      .get(`${API_BASE}/api/trends/stats`, {
        params: { categorie: category, start_date, end_date },
      })
      .then((res) => setStats7j(res.data))
      .catch(() => setStats7j(null));

    axios
      .get(`${API_BASE}/api/trends/stats`, {
        params: { categorie: category },
      })
      .then((res) => setStatsAll(res.data))
      .catch(() => setStatsAll(null));
  }, [category, start_date, end_date]);

  // Affichage brut
  return (
    <>
      <h3>TEST TRENDS TOXICITÉ</h3>
      <CategoryFilter value={category} onChange={setCategory} />
      <TimeFilter value={period} onChange={setPeriod} />

      <pre>
        --- Données sur 7 jours ---
        {stats7j ? JSON.stringify(stats7j, null, 2) : "Aucune donnée."}

        --- Données globales ---
        {statsAll ? JSON.stringify(statsAll, null, 2) : "Aucune donnée."}
      </pre>
    </>
  );
}
