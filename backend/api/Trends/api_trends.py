# backend/api/Trends/api_trends.py

from fastapi import APIRouter, Query, HTTPException
from datetime import date, timedelta
from enum import Enum
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

# Enum des catégories
class CategoryEnum(str, Enum):
    all = "all"
    news_social_concern = "news_social_concern"
    arts_entertainment = "arts_entertainment"
    sports_gaming = "sports_gaming"
    pop_culture = "pop_culture"
    learning_educational = "learning_educational"
    science_technology = "science_technology"
    business_entrepreneurship = "business_entrepreneurship"
    food_dining = "food_dining"
    travel_adventure = "travel_adventure"
    fashion_style = "fashion_style"
    health_fitness = "health_fitness"
    family = "family"

CATEGORY_MAPPING = {
    "arts_entertainment":        "arts_&_culture",
    "business_entrepreneurship": "business_&_entrepreneurs",
    "pop_culture":               "celebrity_&_pop_culture",
    "science_technology":        "science_&_technology",
    "youth_student_life":        "youth_&_student_life",
    "learning_educational":      "learning_&_educational",
    "health_fitness":            "fitness_&_health",
    "fashion_style":             "fashion_&_style",
    "food_dining":               "food_&_dining",
    "travel_adventure":          "travel_&_adventure",
    "family":                    "relationships",
    "sports_gaming":             "gaming",
    "news_social_concern":       "news_&_social_concern"
}

def get_connection():
    return psycopg2.connect(PG_DSN)

@router.get("/trends/count")
def get_post_count(
    period: str = Query("today", pattern="^(today|week|all)$"),
    category: CategoryEnum = Query("all")
):
    today = date.today()
    start = None
    end = None

    if period == "today":
        start = today
        end = today + timedelta(days=1)
    elif period == "week":
        start = today - timedelta(days=6)
        end = today + timedelta(days=1)

    where = []
    params = []

    if start and end:
        where.append("post_brut_date >= %s AND post_brut_date < %s")
        params.extend([start, end])

    if category != CategoryEnum.all:
        mapped = CATEGORY_MAPPING.get(category.value, category.value)
        where.append("categorie = %s")
        params.append(mapped)

    where_clause = " AND ".join(where) if where else "1=1"

    query = f"""
        SELECT COUNT(*) FROM post_brut
        WHERE {where_clause}
    """

    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(query, params)
        count = cur.fetchone()[0]

    return {"posts": count}

@router.get("/trends/stats")
def get_toxicity_stats(
    categorie: str = Query("all"),
    start_date: str = Query(None),
    end_date: str = Query(None)
):
    where = []
    params = []

    if categorie != "all":
        mapped = CATEGORY_MAPPING.get(categorie, categorie)
        where.append("categorie = %s")
        params.append(mapped)

    if start_date and end_date:
        where.append("post_date BETWEEN %s AND %s")
        params.extend([start_date, end_date])

    where_clause = " AND ".join(where) if where else "1=1"

    sql = f"""
        SELECT
            ROUND(AVG(mean_toxic)::NUMERIC, 4)       AS toxic,
            ROUND(AVG(mean_severe)::NUMERIC, 4)      AS severe,
            ROUND(AVG(mean_insult)::NUMERIC, 4)      AS insult,
            ROUND(AVG(mean_obscene)::NUMERIC, 4)     AS obscene,
            ROUND(AVG(mean_threat)::NUMERIC, 4)      AS threat,
            ROUND(AVG(mean_identityhate)::NUMERIC,4) AS identityhate
        FROM trends_results
        WHERE {where_clause}
    """

    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(sql, params)
        result = cur.fetchone()

    labels = ["toxic", "severe", "insult", "obscene", "threat", "identityhate"]
    return {label: float(score or 0.0) for label, score in zip(labels, result)}

@router.get("/trends/emotion")
def get_emotion_stats(
    period: str = Query("week", pattern="^(today|week|all)$"),
    category: str = Query("all")
):
    today = date.today()
    start = None

    if period == "today":
        start = today
    elif period == "week":
        start = today - timedelta(days=6)

    where = []
    params = []

    if category != "all":
        mapped = CATEGORY_MAPPING.get(category, category)
        where.append("categorie = %s")
        params.append(mapped)

    if start:
        where.append("post_date >= %s")
        params.append(start)

    where_clause = " AND ".join(where) if where else "1=1"

    sql = f"""
        SELECT
            ROUND(AVG(mean_anger)::NUMERIC, 4)    AS anger,
            ROUND(AVG(mean_disgust)::NUMERIC, 4)  AS disgust,
            ROUND(AVG(mean_fear)::NUMERIC, 4)     AS fear,
            ROUND(AVG(mean_joy)::NUMERIC, 4)      AS joy,
            ROUND(AVG(mean_surprise)::NUMERIC, 4) AS surprise
        FROM trends_results
        WHERE {where_clause}
    """

    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(sql, params)
        result = cur.fetchone()

    labels = ["anger", "disgust", "fear", "joy", "surprise"]
    return [{"label": label, "score": float(score or 0.0)} for label, score in zip(labels, result)]