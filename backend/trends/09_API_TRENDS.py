# 09_API_TRENDS.py

from fastapi import APIRouter, Query, HTTPException
from datetime import date, timedelta
import psycopg2
import os
from dotenv import load_dotenv

# ───── CONFIG .env ─────
load_dotenv()
PG_DSN = os.getenv("PG_DSN")

# ────── CATEGORIES AUTORISÉES ──────
ALLOWED_CATEGORIES = {
    "news_social_concern", "arts_entertainment", "sports_gaming", "pop_culture",
    "learning_educational", "science_technology", "business_entrepreneurship",
    "food_dining", "travel_adventure", "fashion_style", "health_fitness", "family"
}

router = APIRouter()

# ────── Connexion DB ──────
def get_connection():
    return psycopg2.connect(PG_DSN)

# ────── Helper : dates ──────
def get_start_date(period: str) -> date | None:
    today = date.today()
    if period == "today":
        return today
    elif period == "week":
        return today - timedelta(days=6)
    return None  # all time

# ────── ENDPOINT : émotions agrégées ──────
@router.get("/trends/emotions")
def get_emotions(
    period: str = Query(..., pattern="^(today|week|all)$"),
    category: str = Query(...)
):
    if category != "all" and category not in ALLOWED_CATEGORIES:
        raise HTTPException(status_code=400, detail="Catégorie inconnue")

    start_date = get_start_date(period)
    conditions = []
    params = []

    if category != "all":
        conditions.append("categorie = %s")
        params.append(category)

    if start_date:
        conditions.append("post_date >= %s")
        params.append(start_date)

    where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""
    sql = f"""
        SELECT
            ROUND(AVG(mean_anger)::numeric, 4),
            ROUND(AVG(mean_disgust)::numeric, 4),
            ROUND(AVG(mean_fear)::numeric, 4),
            ROUND(AVG(mean_joy)::numeric, 4),
            ROUND(AVG(mean_surprise)::numeric, 4)
        FROM trends_results
        {where_clause}
    """

    try:
        with get_connection() as conn, conn.cursor() as cur:
            cur.execute(sql, params)
            row = cur.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="Aucune donnée")
            return {
                "period": period,
                "category": category,
                "emotions": {
                    "anger": row[0],
                    "disgust": row[1],
                    "fear": row[2],
                    "joy": row[3],
                    "surprise": row[4],
                }
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))