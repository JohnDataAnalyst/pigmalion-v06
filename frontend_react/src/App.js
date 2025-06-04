import React, { useState } from "react";
import "./App.css";

function App() {
  const [url, setUrl] = useState("");
  const [data, setData] = useState(null);
  const [error, setError] = useState("");
  const [isLoading, setIsLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!url.trim()) {
      setError("⚠ Veuillez saisir une URL Bluesky.");
      return;
    }
    setError("");
    setData(null);
    setIsLoading(true);
    try {
      const resp = await fetch(
        `http://localhost:8000/analyze?url=${encodeURIComponent(url.trim())}`
      );
      if (!resp.ok) {
        const err = await resp.json();
        throw new Error(err.detail || "Erreur inconnue");
      }
      const json = await resp.json();
      setData(json);
    } catch (e) {
      setError(e.message);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="container">
      <h1>Analyse d’un post Bluesky</h1>
      <form onSubmit={handleSubmit} className="form">
        <input
          type="text"
          placeholder="https://bsky.app/profile/.../post/..."
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          disabled={isLoading}
          className="input-url"
        />
        <button type="submit" disabled={isLoading} className="btn-submit">
          {isLoading ? "Analyse…" : "Analyser"}
        </button>
      </form>

      {error && <div className="error">{error}</div>}

      {data && (
        <div className="result">
          <h2>Résultats de l’analyse :</h2>
          <table>
            <tbody>
              {Object.entries(data).map(([key, value]) => (
                <tr key={key}>
                  <td className="cell-key">{key}</td>
                  <td className="cell-value">
                    {typeof value === "object"
                      ? JSON.stringify(value, null, 2)
                      : value}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

export default App;
