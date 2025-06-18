#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build_trends_results.py
Agrège émotions & toxicité par jour + catégorie, puis alimente trends_results.

Usage
-----
python build_trends_results.py            # 25 jours (défaut)
python build_trends_results.py --days_back 0   # back-fill complet
"""

import os, argparse, time
import pandas as pd
import psycopg2
from psycopg2.extras import execute_batch
from sqlalchemy import create_engine, text
from dotenv import load_dotenv
from rich.console import Console
from rich.table import Table
from rich import box

# ───────────────────────── Logger ───────────────────────── #
console = Console()
log, rule = console.log, console.rule

# ───────────────────────── Connexion PG ─────────────────── #
def get_pg_connection(return_engine=False):
    load_dotenv(r"C:\Users\dell\Desktop\DATA\SUP DE VINCI\08 - PROJET THAMALIEN\05_PIGMALION_V05_DEF\.env07")
    cfg = dict(
        user     = os.getenv("DB_USER"),
        password = os.getenv("DB_PASSWORD"),
        host     = os.getenv("DB_HOST", "localhost"),
        port     = os.getenv("DB_PORT", "5432"),
        dbname   = os.getenv("DB_NAME"),
    )
    conn = psycopg2.connect(**cfg)
    if return_engine:
        url = f"postgresql+psycopg2://{cfg['user']}:{cfg['password']}@{cfg['host']}:{cfg['port']}/{cfg['dbname']}"
        return conn, create_engine(url)
    return conn

# ───────────────────────── Params CLI ───────────────────── #
parser = argparse.ArgumentParser()
parser.add_argument("--days_back", type=int, default=25,
                    help="Fenêtre glissante en jours (0 = tout l'historique)")
WINDOW = parser.parse_args().days_back
rule(f"[bold cyan]Trends aggregation  |  days_back = {WINDOW}")

# 12 catégories retenues
ALLOWED_CATEGORIES = {
    'news_social_concern','arts_entertainment','sports_gaming','pop_culture',
    'learning_educational','science_technology','business_entrepreneurship',
    'food_dining','travel_adventure','fashion_style','health_fitness','family'
}

# ───────────────────────── Requête principale ───────────── #
date_clause = "" if WINDOW == 0 else \
    f"AND pc.post_clean_date_nettoyage >= CURRENT_DATE - INTERVAL '{WINDOW} day'"

QUERY = f"""
SELECT pc.post_url,
       DATE(pc.post_clean_date_nettoyage)  AS d,
       COALESCE(pcmc.post_clean_mesure_categories_label_predominant,'other') AS cat,
       peme.post_clean_mesure_emotion_score_anger    AS anger,
       peme.post_clean_mesure_emotion_score_disgust  AS disgust,
       peme.post_clean_mesure_emotion_score_fear     AS fear,
       peme.post_clean_mesure_emotion_score_joy      AS joy,
       peme.post_clean_mesure_emotion_score_surprise AS surprise,
       ptox.post_clean_mesure_toxicite_score_toxic        AS toxic,
       ptox.post_clean_mesure_toxicite_score_severe_toxic AS severe_toxic,
       ptox.post_clean_mesure_toxicite_score_obscene      AS obscene,
       ptox.post_clean_mesure_toxicite_score_threat       AS threat,
       ptox.post_clean_mesure_toxicite_score_insult       AS insult,
       ptox.post_clean_mesure_toxicite_score_identity_hate AS hate
FROM   post_clean pc
LEFT   JOIN post_clean_mesure_categories pcmc ON pcmc.post_url = pc.post_url
LEFT   JOIN post_clean_mesure_emotion    peme ON peme.post_url = pc.post_url
LEFT   JOIN post_clean_mesure_toxicite   ptox ON ptox.post_url = pc.post_url
WHERE  pc.trend_status = 'pending'
{date_clause};
"""

# ───────────────────────── Pipeline ─────────────────────── #
t0          = time.time()
conn, eng   = get_pg_connection(return_engine=True)
df          = pd.read_sql(QUERY, eng)
initial_cnt = len(df)
log(f"[yellow]Posts chargés : {initial_cnt:,}")

if df.empty:
    log("[green]Aucun post à traiter → fin.")
    conn.close(); exit()

# Marquer 'ok' immédiatement
with conn, conn.cursor() as cur:
    execute_batch(cur,
        "UPDATE post_clean SET trend_status='ok' WHERE post_url = %(post_url)s;",
        df[['post_url']].drop_duplicates().to_dict('records'))
conn.commit()
log(f"[green]Posts marqués ok : {cur.rowcount:,}")

# Filtrage catégories
df = df[df['cat'].isin(ALLOWED_CATEGORIES)]
log(f"[yellow]Après filtre catégories : {len(df):,} posts "
    f"({initial_cnt-len(df):,} exclus)")

if df.empty:
    log("[red]0 post dans les 12 catégories → rien à agréger.")
    conn.close(); exit()

# Agrégation jour × catégorie
agg_cat = (
    df.groupby(['d','cat'])
      .agg(post_occurrence=('post_url','size'),
           mean_anger        =('anger','mean'),
           mean_disgust      =('disgust','mean'),
           mean_fear         =('fear','mean'),
           mean_joy          =('joy','mean'),
           mean_surprise     =('surprise','mean'),
           mean_toxic        =('toxic','mean'),
           mean_severe_toxic =('severe_toxic','mean'),
           mean_obscene      =('obscene','mean'),
           mean_threat       =('threat','mean'),
           mean_insult       =('insult','mean'),
           mean_hate         =('hate','mean'))
      .reset_index())

# Ligne globale All
agg_all = (
    df.groupby('d')
      .agg(post_occurrence=('post_url','size'),
           mean_anger        =('anger','mean'),
           mean_disgust      =('disgust','mean'),
           mean_fear         =('fear','mean'),
           mean_joy          =('joy','mean'),
           mean_surprise     =('surprise','mean'),
           mean_toxic        =('toxic','mean'),
           mean_severe_toxic =('severe_toxic','mean'),
           mean_obscene      =('obscene','mean'),
           mean_threat       =('threat','mean'),
           mean_insult       =('insult','mean'),
           mean_hate         =('hate','mean'))
      .reset_index()
      .assign(cat='All'))

agg = pd.concat([agg_cat, agg_all], ignore_index=True)
log(f"[yellow]Lignes agrégées (cat + All) : {len(agg):,}")

# UPSERT
UPSERT = """
INSERT INTO trends_results (
  post_date, categorie, post_occurrence,
  mean_anger, mean_disgust, mean_fear, mean_joy, mean_surprise,
  mean_toxic, mean_severe_toxic, mean_obscene, mean_threat,
  mean_insult, mean_hate)
VALUES (
  %(d)s, %(cat)s, %(post_occurrence)s,
  %(mean_anger)s, %(mean_disgust)s, %(mean_fear)s, %(mean_joy)s, %(mean_surprise)s,
  %(mean_toxic)s, %(mean_severe_toxic)s, %(mean_obscene)s, %(mean_threat)s,
  %(mean_insult)s, %(mean_hate)s)
ON CONFLICT (post_date, categorie) DO UPDATE SET
  post_occurrence   = EXCLUDED.post_occurrence,
  mean_anger        = EXCLUDED.mean_anger,
  mean_disgust      = EXCLUDED.mean_disgust,
  mean_fear         = EXCLUDED.mean_fear,
  mean_joy          = EXCLUDED.mean_joy,
  mean_surprise     = EXCLUDED.mean_surprise,
  mean_toxic        = EXCLUDED.mean_toxic,
  mean_severe_toxic = EXCLUDED.mean_severe_toxic,
  mean_obscene      = EXCLUDED.mean_obscene,
  mean_threat       = EXCLUDED.mean_threat,
  mean_insult       = EXCLUDED.mean_insult,
  mean_hate         = EXCLUDED.mean_hate;
"""
rows = agg.to_dict("records")
with conn, conn.cursor() as cur:
    execute_batch(cur, UPSERT, rows)
conn.commit()
log(f"[green]Lignes envoyées en UPSERT : {len(rows):,}")

# Compte réel dans la fenêtre
with conn, conn.cursor() as cur:
    cur.execute("""
        SELECT COUNT(*) FROM trends_results
        WHERE post_date >= CURRENT_DATE - INTERVAL %s
    """, (f"{WINDOW} day",) if WINDOW else ("10000 day",))
    db_rows = cur.fetchone()[0]
log(f"[green]Lignes réellement présentes dans trends_results (fenêtre) : {db_rows:,}")

# Tableau récap
elapsed = time.time() - t0
tbl = Table(title="Résumé agrégation", box=box.SIMPLE, show_edge=False)
tbl.add_column("Étape"); tbl.add_column("Valeur", justify="right")
tbl.add_row("Posts lus",           f"{initial_cnt:,}")
tbl.add_row("Posts conservés",     f"{len(df):,}")
tbl.add_row("Groupes jour×cat",    f"{len(agg_cat):,}")
tbl.add_row("Lignes agrégées",     f"{len(rows):,}")
tbl.add_row("Présentes en DB",     f"{db_rows:,}")
tbl.add_row("Durée (s)",           f"{elapsed:.1f}")
console.print(tbl)

conn.close()
rule("[bold green]Terminé")
