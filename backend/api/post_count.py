# backend/api/post_count.py
from fastapi import APIRouter, Query
import psycopg2, os
from dotenv import load_dotenv

router = APIRouter(prefix="/api")

load_dotenv()                         # DSN dans .env
DSN = os.getenv("PG_DSN")

@router.get("/post-count")
def post_count(
    period: str   = Query("today", pattern="^(today|week|all)$"),
    category: str = Query("All")
):
    sql = """
    SELECT COALESCE(SUM(post_occurrence),0)
    FROM   trends_results
    WHERE  (%s = 'All' OR categorie = %s)
      AND  (
            %s = 'all'
         OR (%s = 'today' AND post_date = CURRENT_DATE)
         OR (%s = 'week'  AND post_date >= DATE_TRUNC('week', CURRENT_DATE))
          );
    """
    with psycopg2.connect(DSN) as c, c.cursor() as cur:
        cur.execute(sql, (category, category, period, period, period))
        n = cur.fetchone()[0]
    return {"count": n}
