from fastapi import APIRouter, Query, HTTPException
from typing import List
import psycopg2
import os
from dotenv import load_dotenv

# ─── Chargement de la config ─────────────────────────────────────
BASE_DIR = os.path.dirname(__file__)
load_dotenv(dotenv_path=os.path.join(BASE_DIR, ".env10"))

PG_DSN = os.getenv("PG_DSN") or (
    f"dbname={os.getenv('DB_NAME')} "
    f"user={os.getenv('DB_USER')} "
    f"password={os.getenv('DB_PASSWORD')} "
    f"host={os.getenv('DB_HOST')} "
    f"port={os.getenv('DB_PORT')}"
)

# ─── Définition du routeur ───────────────────────────────────────
router = APIRouter(prefix="/api", tags=["keywords"])

def get_connection():
    return psycopg2.connect(PG_DSN)

# ─────────────────────────────────────────────────────────────────
# 🔹 TOP 20 MOTS-CLÉS
# ─────────────────────────────────────────────────────────────────
@router.get("/keywords", response_model=List[dict])
def top_keywords(
    period: str = Query("today", regex="^(today|week|all)$"),
    category: str = Query("all"),
):
    where, params = [], []
    if period == "today":
        where.append("post_date = CURRENT_DATE")
    elif period == "week":
        where.append("post_date >= CURRENT_DATE - INTERVAL '7 days'")
    if category != "all":
        where.append("categorie = %s")
        params.append(category)

    where_sql = "WHERE " + " AND ".join(where) if where else ""
    sql = f"""
        WITH t AS (
            SELECT keyword, occurrence
            FROM keywords_results
            {where_sql}
        )
        SELECT keyword,
               SUM(occurrence) AS occ,
               ROW_NUMBER() OVER (ORDER BY SUM(occurrence) DESC) AS rank
        FROM t
        GROUP BY keyword
        ORDER BY occ DESC
        LIMIT 20;
    """

    try:
        with get_connection() as conn, conn.cursor() as cur:
            cur.execute(sql, params)
            rows = cur.fetchall()
            return [{"rank": r[2], "keyword": r[0], "occurrence": r[1] or 0} for r in rows]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ─────────────────────────────────────────────────────────────────
# 🔸 NOMBRE TOTAL DE POSTS
# ─────────────────────────────────────────────────────────────────
@router.get("/post-count")
def get_post_count(
    period: str = Query("today", regex="^(today|week|all)$"),
    category: str = Query("all"),
):
    where, params = [], []
    if period == "today":
        where.append("post_date = CURRENT_DATE")
    elif period == "week":
        where.append("post_date >= CURRENT_DATE - INTERVAL '7 days'")
    if category != "all":
        where.append("categorie = %s")
        params.append(category)

    where_sql = "WHERE " + " AND ".join(where) if where else ""
    sql = f"""
        SELECT COALESCE(SUM(post_occurrence), 0)
        FROM trends_results
        {where_sql};
    """

    try:
        with get_connection() as conn, conn.cursor() as cur:
            cur.execute(sql, params)
            result = cur.fetchone()[0]
            return {"count": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
