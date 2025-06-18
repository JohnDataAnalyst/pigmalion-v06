from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from db import get_db    # ton utilitaire dépendance

router = APIRouter(prefix="/trends", tags=["trends"])

def _date_min(range_: str):
    from datetime import date, timedelta
    today = date.today()
    if range_ == "today": return today
    if range_ == "week":  return today - timedelta(days=7)
    return None           # 'all'

@router.get("/summary")
def summary(range: str = "all", db = Depends(get_db)):
    dmin = _date_min(range)
    row = db.execute(text("""
        SELECT SUM(post_occurrence) AS nb
        FROM   trends_results
        WHERE  (:dmin IS NULL OR post_date >= :dmin)
          AND  categorie = 'All';
    """), {"dmin": dmin}).one()
    return {"range": range, "post_count": row.nb or 0}

@router.get("/top_keywords")
def top_keywords(range: str = "all", limit: int = 20, db = Depends(get_db)):
    dmin = _date_min(range)
    rows = db.execute(text("""
        SELECT keyword, SUM(occurrence) AS cnt
        FROM   keywords_results
        WHERE  (:dmin IS NULL OR post_date >= :dmin)
          AND  categorie = 'All'
        GROUP  BY keyword
        ORDER  BY cnt DESC
        LIMIT  :limit;
    """), {"dmin": dmin, "limit": limit}).fetchall()
    return [
        {"rank": i+1, "keyword": r.keyword, "count": r.cnt}
        for i, r in enumerate(rows)
    ]
