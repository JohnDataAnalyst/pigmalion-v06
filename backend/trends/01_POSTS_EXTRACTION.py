import os
import time
import pandas as pd
import psycopg2
from atproto import Client
from dotenv import load_dotenv
from datetime import datetime, timedelta

# ──────────────────────────────────────────────────────────────────────
# 1) Calcul dynamique de la racine du projet (05_PIGMALION_V05_DEF)
# ──────────────────────────────────────────────────────────────────────
current_file = os.path.abspath(__file__)
project_root = os.path.abspath(os.path.join(current_file, "..", "..", ".."))
# → “C:/Users/dell/Desktop/DATA/SUP DE VINCI/08 - PROJET THAMALIEN/05_PIGMALION_V05_DEF”

# ──────────────────────────────────────────────────────────────────────
# 2) PARAMÈTRES mis à jour
# ──────────────────────────────────────────────────────────────────────
NB_BOUCLES = 5
NB_POSTS_PAR_MOT_CLE = 10

# a) Chemin vers data/csv/liste_keywords.csv
csv_folder = os.path.join(project_root, "data", "csv")
CSV_KEYWORDS_PATH = os.path.join(csv_folder, "liste_keywords.csv")

# b) Chemin vers le fichier d’environnement renommé .env07
ENV_PATH = os.path.join(project_root, ".env07")

# ──────────────────────────────────────────────────────────────────────
# 3) Fonction de connexion PostgreSQL
# ──────────────────────────────────────────────────────────────────────
def get_connexion():
    load_dotenv(ENV_PATH)
    return psycopg2.connect(
        dbname=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT")
    )

# ──────────────────────────────────────────────────────────────────────
# 4) Connexion Bluesky
# ──────────────────────────────────────────────────────────────────────
load_dotenv(ENV_PATH)
handle   = os.getenv("BLUESKY_HANDLE")
password = os.getenv("BLUESKY_PASSWORD")
client   = Client()
client.login(handle, password)

# ──────────────────────────────────────────────────────────────────────
# 5) Lecture des mots-clés depuis data/csv/liste_keywords.csv
# ──────────────────────────────────────────────────────────────────────
df_keywords = pd.read_csv(CSV_KEYWORDS_PATH)
df_keywords.columns = df_keywords.columns.str.strip().str.lower()
df_keywords = df_keywords.dropna(subset=["categories", "keyword"])
df_keywords.rename(columns={"categories": "categorie"}, inplace=True)

# ──────────────────────────────────────────────────────────────────────
# 6) Connexion à la base PostgreSQL et préchargement des URLs existantes
# ──────────────────────────────────────────────────────────────────────
conn = get_connexion()
cur = conn.cursor()

cur.execute("SELECT post_brut_url FROM post_brut;")
urls_connues = set(row[0] for row in cur.fetchall())

# ──────────────────────────────────────────────────────────────────────
# 7) Requêtes SQL
# ──────────────────────────────────────────────────────────────────────
insert_compte = """
INSERT INTO compte_brut (compte_did, compte_brut_handle)
VALUES (%s, %s)
ON CONFLICT (compte_did) DO NOTHING;
"""

update_date_premiere_analyse = """
UPDATE compte_brut
SET compte_date_premiere_analyse = %s
WHERE compte_did = %s AND compte_date_premiere_analyse IS NULL;
"""

insert_post = """
INSERT INTO post_brut (
    post_brut_url, post_brut_date, post_brut_contenu,
    compte_handle, post_brut_url_affichage,
    post_brut_date_scrapping, categorie, keyword,
    post_brut_poids, compte_did,
    post_brut_presence_media, post_brut_temps_scraping
)
VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
ON CONFLICT (post_brut_url) DO NOTHING;
"""

# ──────────────────────────────────────────────────────────────────────
# 8) Seuil temporel : 24 h en arrière
# ──────────────────────────────────────────────────────────────────────
seuil_date = datetime.utcnow() - timedelta(hours=24)

# ──────────────────────────────────────────────────────────────────────
# 9) Boucle d’extraction et d’insertion
# ──────────────────────────────────────────────────────────────────────
total_posts_insérés = 0

for loop_index in range(1, NB_BOUCLES + 1):
    print(f"\n=== Boucle {loop_index} / {NB_BOUCLES} ===")

    for _, row in df_keywords.iterrows():
        categorie    = row["categorie"]
        keyword      = row["keyword"]
        posts        = []
        cursor_token = None

        try:
            print(f"🔎 Recherche [{keyword}] (catégorie : {categorie})…")
            while len(posts) < NB_POSTS_PAR_MOT_CLE:
                result = client.app.bsky.feed.search_posts(params={"q": keyword, "cursor": cursor_token})
                feed   = result.posts
                if not feed:
                    break
                posts.extend(feed)
                cursor_token = result.cursor
                if not cursor_token:
                    break
        except Exception as e:
            print(f"❌ Erreur récupération : {keyword} → {e}")
            continue

        valeurs_batch = []

        for post in posts[:NB_POSTS_PAR_MOT_CLE]:
            try:
                uri = post.uri
                if uri in urls_connues:
                    continue

                text = getattr(post.record, "text", "").replace("\n", " ").replace("\r", "").strip()
                createdAt_str = getattr(post.record, "created_at", None)
                if createdAt_str is None:
                    continue

                createdAt = datetime.strptime(createdAt_str, "%Y-%m-%dT%H:%M:%S.%fZ")
                if createdAt < seuil_date:
                    continue

                author_handle  = post.author.handle
                url_affichage  = f"https://bsky.app/profile/{author_handle}/post/{uri.split('/')[-1]}"
                date_scrap     = datetime.now(datetime.utcnow().astimezone().tzinfo)
                poids          = len(text.split())
                compte_did     = post.author.did
                has_media      = post.embed is not None
                timestamp      = round(time.time(), 3)

                # Insertion ou mise à jour du compte
                cur.execute(insert_compte, (compte_did, author_handle))
                cur.execute(update_date_premiere_analyse, (date_scrap, compte_did))

                # Préparation de la ligne à insérer
                valeurs_batch.append((
                    uri,
                    createdAt,
                    text,
                    author_handle,
                    url_affichage,
                    date_scrap,
                    categorie,
                    keyword,
                    poids,
                    compte_did,
                    has_media,
                    timestamp
                ))
                urls_connues.add(uri)

            except Exception as e:
                print(f"⚠️ Post ignoré : {e}")

        # Insertion en batch
        try:
            if valeurs_batch:
                cur.executemany(insert_post, valeurs_batch)
                conn.commit()
                nb_inserts = len(valeurs_batch)
                total_posts_insérés += nb_inserts
                print(f"✅ {nb_inserts} posts insérés pour le mot-clé : {keyword}")
                print(f"🔄 Total cumulé : {total_posts_insérés}")
            else:
                print(f"ℹ️ Rien à insérer pour : {keyword}")
        except Exception as e:
            conn.rollback()
            print(f"❌ Échec batch [{keyword}] → rollback : {e}")

# ──────────────────────────────────────────────────────────────────────
# 10) Fermeture des connexions
cur.close()
conn.close()
