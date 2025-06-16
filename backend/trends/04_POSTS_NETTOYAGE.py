import os
import re
import time
import pandas as pd
from tqdm import tqdm
from langdetect import detect
from datetime import datetime
from dotenv import load_dotenv
from sqlalchemy import create_engine
import psycopg2

# === Connexion PostgreSQL ===
def get_connexions():
    load_dotenv(r"C:\Users\dell\Desktop\DATA\SUP DE VINCI\08 - PROJET THAMALIEN\05_PIGMALION_V05_DEF\.env07")
    user = os.getenv("DB_USER")
    password = os.getenv("DB_PASSWORD")
    host = os.getenv("DB_HOST")
    port = os.getenv("DB_PORT")
    db = os.getenv("DB_NAME")

    engine = create_engine(f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{db}")
    conn = psycopg2.connect(dbname=db, user=user, password=password, host=host, port=port)
    return engine, conn

# === Nettoyage texte brut ===
def nettoyer_texte(texte):
    # Passage en minuscules, suppression d'URLs, mentions, hashtags et ponctuation
    texte = texte.lower()
    texte = re.sub(r"http\S+|@\S+|#\S+|[^\w\s]", "", texte)
    # Normalisation des espaces
    return re.sub(r"\s+", " ", texte).strip()

# === Détection de la langue ===
def detecter_langue(texte):
    try:
        return detect(texte)
    except:
        return "und"

# === Connexion
print("📡 Connexion à la base...")
engine, conn = get_connexions()
cur = conn.cursor()

# === Sélection des posts à nettoyer
query = """
SELECT pb.post_brut_url, pb.post_brut_contenu
FROM post_brut pb
LEFT JOIN post_clean pc ON pb.post_brut_url = pc.post_url
WHERE pc.post_url IS NULL
  AND pb.post_brut_contenu IS NOT NULL;
"""

df = pd.read_sql(query, engine)
print(f"🚀 {len(df)} posts à nettoyer.")

# === Traitement et insertion
for _, row in tqdm(df.iterrows(), total=len(df), desc="Nettoyage"):
    url = row["post_brut_url"]
    brut = row["post_brut_contenu"]
    start = time.time()

    # Nettoyage et métriques
    clean = nettoyer_texte(brut)
    langue = detecter_langue(clean)
    poids = len(clean.split())
    duree = round(time.time() - start, 3)
    now = datetime.utcnow()

    # Insertion dans post_clean
    cur.execute(
        """
        INSERT INTO post_clean (
            post_url,
            post_clean_contenu,
            post_clean_langue,
            post_clean_poids,
            post_clean_date_nettoyage,
            post_clean_duree_nettoyage
        ) VALUES (%s, %s, %s, %s, %s, %s)
        ON CONFLICT (post_url) DO NOTHING;
        """,
        (url, clean, langue, poids, now, duree)
    )
    conn.commit()

# === Fermeture
cur.close()
conn.close()
print("✅ Nettoyage terminé.")
