# backend/main.py
import os
from datetime import date, timedelta
import psycopg2
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from analyse.analyse_post_unitaire import analyser_post

# ──────── configuration .env ──────────────────────────────────────────
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), ".env10"))

PG_DSN = os.getenv("PG_DSN") or (
    f"dbname={os.getenv('DB_NAME')} "
    f"user={os.getenv('DB_USER')} "
    f"password={os.getenv('DB_PASSWORD')} "
    f"host={os.getenv('DB_HOST')} "
    f"port={os.getenv('DB_PORT')}"
)
ALLOWED_CATEGORIES = {
    "news_social_concern","arts_entertainment","sports_gaming","pop_culture",
    "learning_educational","science_technology","business_entrepreneurship",
    "food_dining","travel_adventure","fashion_style","health_fitness","family"
}

# ──────── FastAPI + CORS ──────────────────────────────────────────────
app = FastAPI(title="API Pigmalion – Analyse Bluesky")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:8501"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

# ──────── helpers SQL ─────────────────────────────────────────────────
def get_connection():
    return psycopg2.connect(PG_DSN)

def count_posts(period: str, category: str):
    """
    Retourne le nombre de posts pour la période / catégorie demandée
    d’après la table trends_results (colonne post_occurrence).
    """
    today = date.today()
    if period == "today":
        start = today
    elif period == "week":
        start = today - timedelta(days=6)         # 7 derniers jours
    else:                                         # "all"
        start = None

    where = ["categorie = %s"]
    params = [category]
    if start:
        where.append("post_date >= %s")
        params.append(start)

    sql = f"""
        SELECT COALESCE(SUM(post_occurrence),0)
        FROM trends_results
        WHERE {' AND '.join(where)}
    """

    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(sql, params)
        return cur.fetchone()[0]

def top_keywords(period: str, category: str, limit: int = 20):
    """Retourne les mots-clés les plus fréquents."""
    today = date.today()
    if period == "today":
        start = today
    elif period == "week":
        start = today - timedelta(days=6)
    else:  # "all"
        start = None

    where = ["categorie = %s"]
    params = [category]
    if start:
        where.append("post_date >= %s")
        params.append(start)

    sql = f"""
        SELECT keyword, SUM(occurrence) AS occ
        FROM keywords_results
        WHERE {' AND '.join(where)}
        GROUP BY keyword
        ORDER BY occ DESC
        LIMIT %s
    """

    params.append(limit)

    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(sql, params)
        return cur.fetchall()

# ──────── endpoints ───────────────────────────────────────────────────
@app.get("/health")
async def health_check():
    return {"status": "ok", "version": "0.2"}

@app.get("/analyze")
async def analyze(url: str):
    result = analyser_post(url)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result

@app.get("/trends/count")
async def trends_count(
    period: str = Query(..., pattern="^(today|week|all)$"),
    category: str = Query(...),
):
    """
    Ex : /trends/count?period=today&category=health_fitness
    Renvoie {"period":"today","category":"health_fitness","posts":123}
    """
    if category not in ALLOWED_CATEGORIES:
        raise HTTPException(status_code=400, detail="Catégorie inconnue")

    try:
        n = count_posts(period, category)
        return {"period": period, "category": category, "posts": n}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/trends/keywords")
async def trends_keywords(
    period: str = Query(..., pattern="^(today|week|all)$"),
    category: str = Query(...),
    limit: int = 20,
):
    """Renvoie la liste des mots-clés les plus fréquents."""
    if category not in ALLOWED_CATEGORIES:
        raise HTTPException(status_code=400, detail="Catégorie inconnue")
    try:
        rows = top_keywords(period, category, limit)
        return [
            {"rank": i + 1, "keyword": kw, "occurrence": occ}
            for i, (kw, occ) in enumerate(rows)
        ]
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
