#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build_keywords_results.py
─────────────────────────
Calcule le top-20 mots par jour × catégorie (+ All) en excluant les stop-words
et alimente keywords_results.

Usage
-----
python build_keywords_results.py             # 25 jours (défaut)
python build_keywords_results.py --days_back 0   # back-fill complet
"""

import os, re, argparse, time
import pandas as pd
import psycopg2
from psycopg2.extras import execute_batch
from sqlalchemy import create_engine
from dotenv import load_dotenv

# ───────────────────────── Logger (rich si dispo) ───────────────────────
try:
    from rich.console import Console
    from rich.table import Table
    from rich import box
    console = Console()
    def log(msg): console.log(msg)
    def rule(msg): console.rule(msg)
    def summary(rows):
        tbl = Table(title="Résumé keywords", box=box.SIMPLE, show_edge=False)
        tbl.add_column("Étape"); tbl.add_column("Valeur", justify="right")
        for k, v in rows: tbl.add_row(k, v)
        console.print(tbl)
except ModuleNotFoundError:
    console = None
    def log(msg): print(msg)
    def rule(msg): print("="*10, msg, "="*10)
    def summary(rows):
        print("\nRésumé keywords")
        for k, v in rows: print(f" - {k:<25} {v}")

# ───────────────────────── Paramètres CLI ───────────────────────────────
parser = argparse.ArgumentParser(description="Aggregation keywords_results")
parser.add_argument("--days_back", type=int, default=25,
                    help="Fenêtre en jours (0 = tout l'historique)")
args   = parser.parse_args()
WINDOW = args.days_back
rule(f"[bold cyan]Keywords aggregation  |  days_back = {WINDOW}")

TOP_N = 20
ALLOWED_CATEGORIES = {
    'news_social_concern','arts_entertainment','sports_gaming','pop_culture',
    'learning_educational','science_technology','business_entrepreneurship',
    'food_dining','travel_adventure','fashion_style','health_fitness','family'
}

# ───────────────────────── Connexion PG + engine ────────────────────────
def get_conn_and_engine():
    load_dotenv(r"C:\Users\dell\Desktop\DATA\SUP DE VINCI\08 - PROJET THAMALIEN\05_PIGMALION_V05_DEF\.env07")
    cfg = dict(
        user=os.getenv("DB_USER"), password=os.getenv("DB_PASSWORD"),
        host=os.getenv("DB_HOST","localhost"), port=os.getenv("DB_PORT","5432"),
        dbname=os.getenv("DB_NAME"))
    conn = psycopg2.connect(**cfg)
    url  = f"postgresql+psycopg2://{cfg['user']}:{cfg['password']}@{cfg['host']}:{cfg['port']}/{cfg['dbname']}"
    return conn, create_engine(url)

conn, eng = get_conn_and_engine()

# ───────────────────────── Stop-words & tokenisation ────────────────────
STOPWORDS_CSV = r"data/Liste_Stopwords_V01_24.05.2025.csv"
STOPWORDS = set(pd.read_csv(STOPWORDS_CSV, header=None)[0].str.lower())
TOKEN_RE  = re.compile(r"[a-zàâçéèêëîïôûùüÿñæœ']{3,}", re.I)

def tokenize(txt: str):
    return TOKEN_RE.findall(txt.lower())

# ───────────────────────── Lecture des posts pending ────────────────────
date_clause = "" if WINDOW == 0 else \
    f"AND pc.post_clean_date_nettoyage >= CURRENT_DATE - INTERVAL '{WINDOW} day'"

QUERY = f"""
SELECT pc.post_url,
       DATE(pc.post_clean_date_nettoyage) AS d,
       COALESCE(pcmc.post_clean_mesure_categories_label_predominant,'other') AS cat,
       pc.post_clean_contenu
FROM   post_clean pc
LEFT   JOIN post_clean_mesure_categories pcmc ON pcmc.post_url = pc.post_url
WHERE  pc.keyword_status = 'pending'
{date_clause};
"""

t0 = time.time()
df = pd.read_sql(QUERY, eng)
initial_cnt = len(df)
log(f"[yellow]Posts chargés : {initial_cnt:,}")

if df.empty:
    log("[green]Aucun post à traiter → fin."); conn.close(); exit()

# ───────────────────────── Marquer keyword_status=ok ────────────────────
with conn, conn.cursor() as cur:
    execute_batch(cur,
        "UPDATE post_clean SET keyword_status='ok' WHERE post_url=%(post_url)s;",
        df[['post_url']].drop_duplicates().to_dict('records'))
conn.commit()
log(f"[green]Posts marqués ok : {cur.rowcount:,}")

# ───────────────────────── Filtre catégories ────────────────────────────
df = df[df['cat'].isin(ALLOWED_CATEGORIES)]
log(f"[yellow]Après filtre catégories : {len(df):,} posts "
    f"({initial_cnt-len(df):,} exclus)")

if df.empty:
    log("[red]0 post dans les catégories retenues → fin."); conn.close(); exit()

# ───────────────────────── Comptage occurrences ─────────────────────────
records = []
for d, cat, txt in zip(df["d"], df["cat"], df["post_clean_contenu"]):
    tokens = [t for t in tokenize(txt) if t not in STOPWORDS]
    for tok in tokens:
        records.append((d, cat, tok))
        records.append((d, "All", tok))

kw_df = (pd.DataFrame(records, columns=['d','cat','kw'])
           .groupby(['d','cat','kw'])
           .size()
           .reset_index(name='occ'))

kw_df['rank'] = (kw_df.sort_values(['d','cat','occ'], ascending=[True,True,False])
                          .groupby(['d','cat'])
                          .cumcount() + 1)
kw_top = kw_df[kw_df['rank'] <= TOP_N]
log(f"[yellow]Tokens distincts gardés (≤TOP{TOP_N}) : {len(kw_top):,}")

# ───────────────────────── UPSERT keywords_results ──────────────────────
UPSERT = """
INSERT INTO keywords_results (
  post_date, categorie, keyword, ranking, occurrence)
VALUES (
  %(d)s, %(cat)s, %(kw)s, %(rank)s, %(occ)s)
ON CONFLICT (post_date, categorie, keyword) DO UPDATE
  SET ranking = EXCLUDED.ranking,
      occurrence = EXCLUDED.occurrence;
"""
rows = kw_top.to_dict('records')
with conn, conn.cursor() as cur:
    execute_batch(cur, UPSERT, rows)
conn.commit()
log(f"[green]Lignes UPSERT envoyées : {len(rows):,}")

# Compte réel dans la fenêtre
with conn, conn.cursor() as cur:
    cur.execute("""
        SELECT COUNT(*) FROM keywords_results
        WHERE post_date >= CURRENT_DATE - INTERVAL %s
    """, (f"{WINDOW} day",) if WINDOW else ("10000 day",))
    db_rows = cur.fetchone()[0]
log(f"[green]Lignes présentes dans keywords_results (fenêtre) : {db_rows:,}")

# ───────────────────────── Résumé final ────────────────────────────────
elapsed = time.time() - t0
summary([
    ("Posts lus",              f"{initial_cnt:,}"),
    ("Posts conservés",        f"{len(df):,}"),
    ("Triplets jour×cat×kw",   f"{len(kw_df):,}"),
    ("Lignes UPSERT envoyées", f"{len(rows):,}"),
    ("Présentes en DB",        f"{db_rows:,}"),
    ("Durée (s)",              f"{elapsed:.1f}")
])

conn.close()
rule("[bold green]Terminé")
