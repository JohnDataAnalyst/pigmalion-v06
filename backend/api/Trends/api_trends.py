# backend/api/Trends/api_trends.py
from fastapi import APIRouter, Query, HTTPException
from datetime import date, timedelta
import psycopg2
import os
from dotenv import load_dotenv

router = APIRouter()

# Chargement de la configuration .env
load_dotenv(os.path.join(os.path.dirname(__file__), "../../.env10"))
PG_DSN = os.getenv("PG_DSN") or (
    f"dbname={os.getenv('DB_NAME')} "
    f"user={os.getenv('DB_USER')} "
    f"password={os.getenv('DB_PASSWORD')} "
    f"host={os.getenv('DB_HOST')} "
    f"port={os.getenv('DB_PORT')}"
)

ALLOWED_CATEGORIES = {
    "news_social_concern", "arts_entertainment", "sports_gaming", "pop_culture",
    "learning_educational", "science_technology", "business_entrepreneurship",
    "food_dining", "travel_adventure", "fashion_style", "health_fitness", "family", "all"
}


def get_connection():
    return psycopg2.connect(PG_DSN)


@router.get("/trends/emotion")
def trends_emotion(
    period: str = Query(..., pattern="^(today|week|all)$"),
    category: str = Query(...)
):
    if category not in ALLOWED_CATEGORIES:
        raise HTTPException(status_code=400, detail="Catégorie inconnue")

    today = date.today()
    start = today if period == "today" else today - timedelta(days=6) if period == "week" else None

    where, params = ["1=1"], []
    if category != "all":
        where.append("categorie = %s")
        params.append(category)
    if start:
        where.append("post_date >= %s")
        params.append(start)

    sql = f"""
        SELECT
            ROUND(AVG(mean_anger), 4) AS anger,
            ROUND(AVG(mean_disgust), 4) AS disgust,
            ROUND(AVG(mean_fear), 4) AS fear,
            ROUND(AVG(mean_joy), 4) AS joy,
            ROUND(AVG(mean_surprise), 4) AS surprise
        FROM trends_results
        WHERE {' AND '.join(where)}
    """

    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(sql, params)
        result = cur.fetchone()

    labels = ["anger", "disgust", "fear", "joy", "surprise"]
    return [{"label": label, "score": score or 0.0} for label, score in zip(labels, result)]
