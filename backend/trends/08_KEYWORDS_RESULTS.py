#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build_keywords_results.py
─────────────────────────
Top-20 mots par jour × catégorie (+All) – cumulatif.

• Toutes les lignes keyword_status='pending' sont prises (days_back=0 par défaut)
• Les occurrences sont AJOUTÉES lors d’un nouvel import sur la même journée.
"""

import os, re, argparse, time
import pandas as pd
import psycopg2
from psycopg2.extras import execute_batch
from sqlalchemy import create_engine
from dotenv import load_dotenv

# ─── Logging (rich → couleurs, sinon print) ────────────────────────────
try:
    from rich.console import Console
    from rich.table   import Table
    from rich import box
    console = Console()
    def log(m):  console.log(m)
    def rule(m): console.rule(m)
    def table(title, rows, cols):
        t = Table(title=title, box=box.SIMPLE, show_edge=False)
        for c in cols: t.add_column(c, justify="right" if c!="Date" else "left")
        for r in rows: t.add_row(*map(str, r))
        console.print(t)
except ModuleNotFoundError:
    console = None
    def log(m):  print(m)
    def rule(m): print(f"========== {m} ==========")
    def table(title, rows, cols):
        print(f"\n{title}"); print(" | ".join(cols))
        for r in rows: print(" | ".join(map(str, r)))

# ─── tqdm (facultatif) ─────────────────────────────────────────────────
try:
    from tqdm import tqdm
except ModuleNotFoundError:
    tqdm = lambda x, **kw: x

# ─── Arguments CLI ─────────────────────────────────────────────────────
parser = argparse.ArgumentParser()
parser.add_argument("--days_back", type=int, default=0,
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

# ─── Connexion PG + engine ─────────────────────────────────────────────
def get_conn_engine():
    load_dotenv(r"C:\Users\dell\Desktop\DATA\SUP DE VINCI\08 - PROJET THAMALIEN\05_PIGMALION_V05_DEF\.env07")
    cfg = {k: os.getenv(k) for k in ("DB_USER","DB_PASSWORD","DB_HOST","DB_PORT","DB_NAME")}
    conn = psycopg2.connect(dbname=cfg["DB_NAME"], user=cfg["DB_USER"],
                            password=cfg["DB_PASSWORD"], host=cfg["DB_HOST"],
                            port=cfg["DB_PORT"])
    eng  = create_engine(
        f"postgresql+psycopg2://{cfg['DB_USER']}:{cfg['DB_PASSWORD']}"
        f"@{cfg['DB_HOST']}:{cfg['DB_PORT']}/{cfg['DB_NAME']}")
    return conn, eng

conn, eng = get_conn_engine()

# ─── Stop-words & tokenisation ─────────────────────────────────────────
STOPWORDS = set(pd.read_csv(r"data/Liste_Stopwords_V01_24.05.2025.csv",
                            header=None)[0].str.lower())
TOKEN_RE  = re.compile(r"[a-zàâçéèêëîïôûùüÿñæœ']{3,}", re.I)
def tokenize(txt): return TOKEN_RE.findall(txt.lower())

# ─── Posts à traiter ───────────────────────────────────────────────────
date_clause = "" if WINDOW==0 else \
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
log(f"[yellow]Posts chargés : {len(df):,}")
if df.empty:
    log("[green]Aucun post à traiter → fin."); conn.close(); exit()

# ─── Bascule en ok immédiate ───────────────────────────────────────────
with conn, conn.cursor() as cur:
    execute_batch(cur,
        "UPDATE post_clean SET keyword_status='ok' WHERE post_url=%(post_url)s;",
        df[['post_url']].drop_duplicates().to_dict('records'))
conn.commit(); log(f"[green]Posts marqués ok : {cur.rowcount:,}")

# ─── Filtre catégories ─────────────────────────────────────────────────
df = df[df['cat'].isin(ALLOWED_CATEGORIES)]
log(f"[yellow]Après filtre catégories : {len(df):,} posts")
if df.empty:
    log("[red]0 post dans les catégories retenues → fin."); conn.close(); exit()

table("Posts par jour", df.groupby('d').size().reset_index(name='posts').values,
      ["Date","Posts"])

# ─── Comptage tokens ───────────────────────────────────────────────────
records, token_total = [], 0
for d, cat, txt in tqdm(zip(df["d"], df["cat"], df["post_clean_contenu"]),
                        total=len(df), desc="Tokenisation"):
    words = [w for w in tokenize(txt) if w not in STOPWORDS]
    token_total += len(words)
    for w in words:
        records.append((d, cat, w))
        records.append((d, "All", w))
log(f"[cyan]Tokens retenus : {token_total:,}")

kw_df = (pd.DataFrame(records, columns=['d','cat','kw'])
           .groupby(['d','cat','kw']).size().reset_index(name='occ'))
kw_df['rank'] = (kw_df.sort_values(['d','cat','occ'], ascending=[True,True,False])
                       .groupby(['d','cat']).cumcount() + 1)
kw_top = kw_df[kw_df['rank'] <= TOP_N]
table("UPSERT par jour",
      kw_top.groupby('d').size().reset_index(name='UPSERTs').values,
      ["Date","Lignes"])

# ─── UPSERT cumulatif ──────────────────────────────────────────────────
UPSERT = """
INSERT INTO keywords_results (post_date,categorie,keyword,ranking,occurrence)
VALUES (%(d)s,%(cat)s,%(kw)s,%(rank)s,%(occ)s)
ON CONFLICT (post_date,categorie,keyword) DO UPDATE
  SET ranking    = LEAST(keywords_results.ranking, EXCLUDED.ranking),
      occurrence = keywords_results.occurrence + EXCLUDED.occurrence;
"""
with conn, conn.cursor() as cur:
    execute_batch(cur, UPSERT, kw_top.to_dict('records'))
conn.commit();  log(f"[green]UPSERT effectué : {len(kw_top):,} lignes")

# ─── Résumé ────────────────────────────────────────────────────────────
elapsed = time.time() - t0
table("Résumé keywords", [
    ["Posts analysés",         f"{len(df):,}"],
    ["Tokens retenus",         f"{token_total:,}"],
    ["Triplets (d×cat×kw)",    f"{len(kw_df):,}"],
    [f"Lignes TOP-{TOP_N}",    f"{len(kw_top):,}"],
    ["Durée (s)",              f"{elapsed:.1f}"]
], ["Étape","Valeur"])

conn.close()
rule("[bold green]Terminé")
