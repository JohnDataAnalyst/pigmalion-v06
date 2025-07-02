# backend/main.py
import os
from datetime import date, timedelta
import psycopg2
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from .analyse.analyse_post_unitaire import analyser_post 
from .api_keywords import router as keywords_router          # <- corrigé

# ───── config .env ───────────────────────────────────────────
load_dotenv(os.path.join(os.path.dirname(__file__), ".env10"))
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

# ───── FastAPI + CORS ───────────────────────────────────────
app = FastAPI(title="API Pigmalion – Analyse Bluesky")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000","http://localhost:8501","*"],
    allow_methods=["GET","POST"],
    allow_headers=["*"],
)
app.include_router(keywords_router)                          # router OK

# ───── helpers SQL ──────────────────────────────────────────
def get_connection(): return psycopg2.connect(PG_DSN)

def count_posts(period:str, category:str)->int:
    today=date.today()
    start = today if period=="today" else today-timedelta(days=6) if period=="week" else None
    where, params = ["categorie=%s"], [category]
    if start: where.append("post_date>=%s"); params.append(start)
    sql=f"SELECT COALESCE(SUM(post_occurrence),0) FROM trends_results WHERE {' AND '.join(where)}"
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(sql, params); return cur.fetchone()[0]

# ───── endpoints ────────────────────────────────────────────
@app.get("/health")
def health(): return {"status":"ok","version":"0.2"}

@app.get("/analyze")
def analyze(url:str):
    r=analyser_post(url)
    if "error" in r: raise HTTPException(status_code=400, detail=r["error"])
    return r

@app.get("/trends/count")
def trends_count(
    period:   str = Query(..., pattern="^(today|week|all)$"),
    category: str = Query(...)
):
    if category not in ALLOWED_CATEGORIES:
        raise HTTPException(status_code=400, detail="Catégorie inconnue")
    try: return {"period":period,"category":category,"posts":count_posts(period,category)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
