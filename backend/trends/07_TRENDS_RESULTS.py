#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build_trends_results.py  –  cumulatif
Agrège émotions & toxicité par jour×cat et met à jour trends_results sans
effacer les agrégats existants (moyenne pondérée).
"""

import os, argparse, time
import pandas as pd
import psycopg2
from psycopg2.extras import execute_batch
from sqlalchemy import create_engine
from dotenv import load_dotenv
from rich.console import Console
from rich.table import Table
from rich import box

# ─── Logger ─────────────────────────────────────────────────────────────
console = Console()
log, rule = console.log, console.rule

# ─── Connexion PG ───────────────────────────────────────────────────────
def get_pg_connection(return_engine=False):
    load_dotenv(r"C:\Users\dell\Desktop\DATA\SUP DE VINCI\08 - PROJET THAMALIEN\05_PIGMALION_V05_DEF\.env07")
    cfg = dict(
        user=os.getenv("DB_USER"), password=os.getenv("DB_PASSWORD"),
        host=os.getenv("DB_HOST", "localhost"), port=os.getenv("DB_PORT", "5432"),
        dbname=os.getenv("DB_NAME"),
    )
    conn = psycopg2.connect(**cfg)
    if return_engine:
        url = f"postgresql+psycopg2://{cfg['user']}:{cfg['password']}@{cfg['host']}:{cfg['port']}/{cfg['dbname']}"
        return conn, create_engine(url)
    return conn

# ─── Paramètres CLI ────────────────────────────────────────────────────
parser = argparse.ArgumentParser()
parser.add_argument("--days_back", type=int, default=0,
                    help="Fenêtre glissante en jours (0 = tout l'historique)")
WINDOW = parser.parse_args().days_back
rule(f"[bold cyan]Trends aggregation  |  days_back = {WINDOW}")

ALLOWED_CATEGORIES = {
    'news_social_concern','arts_entertainment','sports_gaming','pop_culture',
    'learning_educational','science_technology','business_entrepreneurship',
    'food_dining','travel_adventure','fashion_style','health_fitness','family'
}

# ─── Requête posts pending ─────────────────────────────────────────────
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

# ─── Pipeline ───────────────────────────────────────────────────────────
t0          = time.time()
conn, eng   = get_pg_connection(return_engine=True)
df          = pd.read_sql(QUERY, eng)
initial_cnt = len(df)
log(f"[yellow]Posts chargés : {initial_cnt:,}")

if df.empty:
    log("[green]Aucun post à traiter → fin."); conn.close(); exit()

# Marque tout de suite en ok
with conn, conn.cursor() as cur:
    execute_batch(cur,
        "UPDATE post_clean SET trend_status='ok' WHERE post_url=%(post_url)s;",
        df[['post_url']].drop_duplicates().to_dict('records'))
conn.commit()
log(f"[green]Posts marqués ok : {cur.rowcount:,}")

# Filtre 12 catégories
df = df[df['cat'].isin(ALLOWED_CATEGORIES)]
log(f"[yellow]Après filtre catégories : {len(df):,} posts")
if df.empty:
    log("[red]0 post dans les 12 catégories → fin."); conn.close(); exit()

# Agrégation
agg_cat = (df.groupby(['d','cat'])
             .agg(post_occ=('post_url','size'),
                  anger=('anger','mean'), disgust=('disgust','mean'),
                  fear=('fear','mean'),   joy=('joy','mean'),
                  surprise=('surprise','mean'),
                  toxic=('toxic','mean'), severe_toxic=('severe_toxic','mean'),
                  obscene=('obscene','mean'), threat=('threat','mean'),
                  insult=('insult','mean'), hate=('hate','mean'))
             .reset_index())

agg_all = (df.groupby('d')
             .agg(post_occ=('post_url','size'),
                  anger=('anger','mean'), disgust=('disgust','mean'),
                  fear=('fear','mean'),   joy=('joy','mean'),
                  surprise=('surprise','mean'),
                  toxic=('toxic','mean'), severe_toxic=('severe_toxic','mean'),
                  obscene=('obscene','mean'), threat=('threat','mean'),
                  insult=('insult','mean'), hate=('hate','mean'))
             .reset_index()
             .assign(cat='All'))

agg = pd.concat([agg_cat, agg_all], ignore_index=True)
log(f"[yellow]Groupes à UPSERT : {len(agg):,}")

# ─── UPSERT cumulatif (moyenne pondérée) ────────────────────────────────
UPSERT = """
INSERT INTO trends_results (
  post_date, categorie, post_occurrence,
  mean_anger, mean_disgust, mean_fear, mean_joy, mean_surprise,
  mean_toxic, mean_severe_toxic, mean_obscene, mean_threat,
  mean_insult, mean_hate)
VALUES (
  %(d)s, %(cat)s, %(post_occ)s,
  %(anger)s, %(disgust)s, %(fear)s, %(joy)s, %(surprise)s,
  %(toxic)s, %(severe_toxic)s, %(obscene)s, %(threat)s,
  %(insult)s, %(hate)s)
ON CONFLICT (post_date, categorie) DO UPDATE
  SET post_occurrence = trends_results.post_occurrence + EXCLUDED.post_occurrence,

      mean_anger = (
        trends_results.mean_anger * trends_results.post_occurrence +
        EXCLUDED.mean_anger       * EXCLUDED.post_occurrence
      ) / (trends_results.post_occurrence + EXCLUDED.post_occurrence),

      mean_disgust = (
        trends_results.mean_disgust * trends_results.post_occurrence +
        EXCLUDED.mean_disgust       * EXCLUDED.post_occurrence
      ) / (trends_results.post_occurrence + EXCLUDED.post_occurrence),

      mean_fear = (
        trends_results.mean_fear * trends_results.post_occurrence +
        EXCLUDED.mean_fear       * EXCLUDED.post_occurrence
      ) / (trends_results.post_occurrence + EXCLUDED.post_occurrence),

      mean_joy = (
        trends_results.mean_joy * trends_results.post_occurrence +
        EXCLUDED.mean_joy       * EXCLUDED.post_occurrence
      ) / (trends_results.post_occurrence + EXCLUDED.post_occurrence),

      mean_surprise = (
        trends_results.mean_surprise * trends_results.post_occurrence +
        EXCLUDED.mean_surprise       * EXCLUDED.post_occurrence
      ) / (trends_results.post_occurrence + EXCLUDED.post_occurrence),

      mean_toxic = (
        trends_results.mean_toxic * trends_results.post_occurrence +
        EXCLUDED.mean_toxic       * EXCLUDED.post_occurrence
      ) / (trends_results.post_occurrence + EXCLUDED.post_occurrence),

      mean_severe_toxic = (
        trends_results.mean_severe_toxic * trends_results.post_occurrence +
        EXCLUDED.mean_severe_toxic       * EXCLUDED.post_occurrence
      ) / (trends_results.post_occurrence + EXCLUDED.post_occurrence),

      mean_obscene = (
        trends_results.mean_obscene * trends_results.post_occurrence +
        EXCLUDED.mean_obscene       * EXCLUDED.post_occurrence
      ) / (trends_results.post_occurrence + EXCLUDED.post_occurrence),

      mean_threat = (
        trends_results.mean_threat * trends_results.post_occurrence +
        EXCLUDED.mean_threat       * EXCLUDED.post_occurrence
      ) / (trends_results.post_occurrence + EXCLUDED.post_occurrence),

      mean_insult = (
        trends_results.mean_insult * trends_results.post_occurrence +
        EXCLUDED.mean_insult       * EXCLUDED.post_occurrence
      ) / (trends_results.post_occurrence + EXCLUDED.post_occurrence),

      mean_hate = (
        trends_results.mean_hate * trends_results.post_occurrence +
        EXCLUDED.mean_hate       * EXCLUDED.post_occurrence
      ) / (trends_results.post_occurrence + EXCLUDED.post_occurrence);
"""

with conn, conn.cursor() as cur:
    execute_batch(cur, UPSERT, agg.to_dict('records'))
conn.commit()
log(f"[green]UPSERT exécuté pour {len(agg):,} groupes")

# ─── Résumé ────────────────────────────────────────────────────────────
elapsed = time.time() - t0
tbl = Table(title="Résumé cumulatif", box=box.SIMPLE, show_edge=False)
tbl.add_column("Étape"); tbl.add_column("Valeur", justify="right")
tbl.add_row("Posts analysés",     f"{len(df):,}")
tbl.add_row("Groupes UPSERT",     f"{len(agg):,}")
tbl.add_row("Durée (s)",          f"{elapsed:.1f}")
console.print(tbl)
conn.close()
rule("[bold green]Terminé")
