import os
import time
import pandas as pd
import psycopg2
from sqlalchemy import create_engine
from atproto import Client
from dotenv import load_dotenv
from datetime import datetime, timedelta, timezone
from tqdm import tqdm
import warnings

# Masquer le warning Pandas sur psycopg2
warnings.filterwarnings("ignore", category=UserWarning, module="pandas.io.sql")


# ======================
# === PARAMÈTRES GÉNÉRAUX ===
# ======================
TARGET_NEW_POSTS  = 12000      # Objectif de nouveaux tweets pour ce run
PER_KEYWORD_LIMIT = 10         # Nb max de tweets à récupérer / mot-clé à chaque tour
ENRICH_INTERVAL   = 100        # Tous les 100 posts, on exécute Étape 2+3

# --- CHEMIN VERS LE FICHIER CSV DES MOTS-CLÉS ---
CSV_KEYWORDS_PATH = r"C:\Users\dell\Desktop\DATA\SUP DE VINCI\08 - PROJET THAMALIEN\06_pigmalion_v06\data\liste_keywords.csv"

# --- CHEMIN VERS LE FICHIER CSV DES STOPWORDS ---
CSV_STOPWORDS_PATH = r"C:\Users\dell\Desktop\DATA\SUP DE VINCI\08 - PROJET THAMALIEN\06_pigmalion_v06\data\Liste_Stopwords_V01_24.05.2025.csv"

# --- CHEMIN VERS LE FICHIER .env (".env07") ---
ENV_PATH = r"C:\Users\dell\Desktop\DATA\SUP DE VINCI\08 - PROJET THAMALIEN\06_pigmalion_v06\.env10"

# --- RÉPERTOIRE CONTENANT VOS MODÈLES ---
MODEL_PATH = r"C:\Users\dell\Desktop\DATA\SUP DE VINCI\08 - PROJET THAMALIEN\06_pigmalion_v06\models"


# ==================================
# === FONCTION DE PARSING DE DATE ===
# ==================================
def parse_created_at(createdAt_str: str) -> datetime | None:
    """
    Gère les formats :
      - 'YYYY-MM-DDTHH:MM:SSZ'
      - 'YYYY-MM-DDTHH:MM:SS.%fZ'
      - avec fuseau (ex. '+00:00', '+09:00', '-07:00')
    Retourne un datetime timezone-aware en UTC ou None si échec.
    """
    if not createdAt_str:
        return None
    try:
        if "." in createdAt_str and createdAt_str.endswith("Z"):
            return datetime.strptime(createdAt_str, "%Y-%m-%dT%H:%M:%S.%fZ").replace(tzinfo=timezone.utc)
        elif createdAt_str.endswith("Z"):
            return datetime.strptime(createdAt_str, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
        else:
            return datetime.fromisoformat(createdAt_str).astimezone(timezone.utc)
    except Exception:
        return None


# ===========================
# === CONNEXION POSTGRESQL ===
# ===========================
def get_connexion():
    # Charge les variables d’environnement depuis .env07
    load_dotenv(ENV_PATH)
    return psycopg2.connect(
        dbname   = os.getenv("DB_NAME"),
        user     = os.getenv("DB_USER"),
        password = os.getenv("DB_PASSWORD"),
        host     = os.getenv("DB_HOST"),
        port     = os.getenv("DB_PORT")
    )


# =====================================
# === CRÉATION D’UN MOTEUR SQLALCHEMY ===
# =====================================
load_dotenv(ENV_PATH)
db_user = os.getenv("DB_USER")
db_pass = os.getenv("DB_PASSWORD")
db_host = os.getenv("DB_HOST")
db_port = os.getenv("DB_PORT")
db_name = os.getenv("DB_NAME")
DB_URL = f"postgresql+psycopg2://{db_user}:{db_pass}@{db_host}:{db_port}/{db_name}"
engine = create_engine(DB_URL)


# ========================================
# === CONNEXION BLUESKY (ATPROTO) –––––––
# ========================================
handle   = os.getenv("BLUESKY_HANDLE")
password = os.getenv("BLUESKY_PASSWORD")
client   = Client()
client.login(handle, password)


# ============================
# === LECTURE DES MOTS-CLÉS & STOPWORDS ===
# ============================
df_keywords = pd.read_csv(CSV_KEYWORDS_PATH)
df_keywords.columns = df_keywords.columns.str.strip().str.lower()
df_keywords = df_keywords.dropna(subset=["categories", "keyword"])
df_keywords.rename(columns={"categories": "categorie"}, inplace=True)

# Si vous souhaitez charger la liste de stopwords :
df_stopwords = pd.read_csv(CSV_STOPWORDS_PATH, header=None, names=["stopword"])
stopwords_list = df_stopwords["stopword"].astype(str).str.strip().tolist()


# =====================
# === REQUÊTES SQL ===
# =====================

# 1) Nouveau : on insère dès le départ la date de première analyse
SQL_INSERT_COMPTE = """
INSERT INTO compte_brut (
    compte_did,
    compte_brut_handle,
    compte_date_premiere_analyse
)
VALUES (%s, %s, %s)
ON CONFLICT (compte_did) DO NOTHING;
"""

SQL_INSERT_POST = """
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

# Étape 2 : enrichissement initial des comptes
SQL_SELECT_COMPTES_INCOMPLETS = """
SELECT compte_did, compte_brut_handle,
       compte_brut_avatar_url,
       compte_brut_is_verified,
       compte_brut_bio,
       compte_brut_banner_url
FROM compte_brut
WHERE compte_completion_01 IS DISTINCT FROM 'OK';
"""

SQL_MARK_COMPTE_OK_ETAPE1 = """
UPDATE compte_brut
SET compte_completion_01 = 'OK'
WHERE compte_did = %s;
"""

SQL_INSERT_OR_UPDATE_COMPTE_BRUT = """
INSERT INTO public.compte_brut (
    compte_did,
    compte_brut_handle,
    compte_brut_avatar_url,
    compte_brut_is_verified,
    compte_brut_bio,
    compte_brut_banner_url,
    compte_completion_01
) VALUES (%(compte_did)s, %(compte_brut_handle)s, %(compte_brut_avatar_url)s,
          %(compte_brut_is_verified)s, %(compte_brut_bio)s, %(compte_brut_banner_url)s,
          'OK')
ON CONFLICT (compte_did) DO UPDATE SET
    compte_brut_handle      = EXCLUDED.compte_brut_handle,
    compte_brut_avatar_url  = COALESCE(compte_brut.compte_brut_avatar_url, EXCLUDED.compte_brut_avatar_url),
    compte_brut_is_verified = COALESCE(compte_brut.compte_brut_is_verified, EXCLUDED.compte_brut_is_verified),
    compte_brut_bio         = COALESCE(compte_brut.compte_brut_bio, EXCLUDED.compte_brut_bio),
    compte_brut_banner_url  = COALESCE(compte_brut.compte_brut_banner_url, EXCLUDED.compte_brut_banner_url),
    compte_completion_01    = 'OK';
"""

# Étape 3 : complément métadonnées comptes
SQL_SELECT_COMPTES_INCOMPLETS_02 = """
SELECT compte_did, compte_brut_handle,
       compte_nombre_publication,
       compte_brut_nombre_followers,
       compte_brut_date_creation
FROM compte_brut
WHERE compte_completion_02 IS NULL;
"""

SQL_UPDATE_COMPTE_COMPLETION_02 = """
UPDATE compte_brut
SET {set_clause}
WHERE compte_did = %s;
"""

SQL_MARK_COMPTE_INVALIDE_ETAPE3 = """
UPDATE compte_brut
SET compte_completion_02 = 'COMPTE INVALIDE'
WHERE compte_did = %s;
"""


def enrich_if_null(old, new):
    return new if old is None else old


# ======================================
# === FONCTIONS D’ENRICHISSEMENT 2 & 3 ===
# ======================================
def etape2_enrichissement(conn):
    """
    Charge tous les comptes où compte_completion_01 <> 'OK',
    enrichit avatar, bio, banner, is_verified, puis marque 'OK'.
    """
    print("Chargement des comptes à enrichir (étape 2)…")
    df_comptes_01 = pd.read_sql(SQL_SELECT_COMPTES_INCOMPLETS, engine)
    count = len(df_comptes_01)
    print(f"étape 2 : {count} comptes trouvés pour enrichissement.")
    if count == 0:
        return 0

    cur = conn.cursor()
    for _, row in tqdm(
        df_comptes_01.iterrows(),
        total=count,
        desc="Étape 2 – Enrichissement comptes",
        leave=False
    ):
        did = row["compte_did"]
        try:
            profile = client.app.bsky.actor.get_profile({"actor": did})
            cur.execute("SELECT * FROM compte_brut WHERE compte_did = %s", (did,))
            existing = cur.fetchone()
            cols = [d[0] for d in cur.description]
            data_dict = dict(zip(cols, existing))

            new_data = {
                "compte_did": did,
                "compte_brut_handle": row.get("compte_brut_handle"),
                "compte_brut_avatar_url": enrich_if_null(
                    data_dict.get("compte_brut_avatar_url"),
                    getattr(profile, "avatar", None)
                ),
                "compte_brut_is_verified": enrich_if_null(
                    data_dict.get("compte_brut_is_verified"),
                    getattr(profile, "labels", None) is not None
                ),
                "compte_brut_bio": enrich_if_null(
                    data_dict.get("compte_brut_bio"),
                    getattr(profile, "description", None)
                ),
                "compte_brut_banner_url": enrich_if_null(
                    data_dict.get("compte_brut_banner_url"),
                    getattr(profile, "banner", None)
                ),
            }
        except Exception as e:
            msg = str(e)
            # Si le compte a disparu ou est suspendu, on marque quand même "OK" pour ne pas boucler
            if 'Profile not found' in msg or 'Account has been suspended' in msg:
                try:
                    cur.execute(SQL_MARK_COMPTE_OK_ETAPE1, (did,))
                    conn.commit()
                except Exception:
                    conn.rollback()
                continue
            else:
                conn.rollback()
                continue

        try:
            cur.execute(SQL_INSERT_OR_UPDATE_COMPTE_BRUT, new_data)
            conn.commit()
        except Exception:
            conn.rollback()

    cur.close()
    return count


def etape3_complement(conn):
    """
    Charge tous les comptes où compte_completion_02 IS NULL,
    complète posts_count, followers_count, date_creation, ou marque INVALIDE.
    """
    print("Chargement des comptes à compléter (étape 3)…")
    df_comptes_02 = pd.read_sql(SQL_SELECT_COMPTES_INCOMPLETS_02, engine)
    count = len(df_comptes_02)
    print(f"étape 3 : {count} comptes trouvés pour complément.")
    if count == 0:
        return 0

    cur = conn.cursor()
    for _, row in tqdm(
        df_comptes_02.iterrows(),
        total=count,
        desc="Étape 3 – Complément comptes",
        leave=False
    ):
        did = row["compte_did"]
        try:
            profile = client.app.bsky.actor.get_profile({"actor": did})
            p = profile.__dict__
            posts_count     = p.get("posts_count")
            followers_count = p.get("followers_count")
            created_at      = p.get("created_at")

            upd = {}
            if row["compte_nombre_publication"] is None and posts_count is not None:
                upd["compte_nombre_publication"] = posts_count
            if row["compte_brut_nombre_followers"] is None and followers_count is not None:
                upd["compte_brut_nombre_followers"] = followers_count
            if row["compte_brut_date_creation"] is None and created_at is not None:
                upd["compte_brut_date_creation"] = created_at
            upd["compte_completion_02"] = 'OK'

            set_clause = ", ".join([f"{k} = %s" for k in upd.keys()])
            sql = SQL_UPDATE_COMPTE_COMPLETION_02.format(set_clause=set_clause)
            vals = list(upd.values()) + [did]
            cur.execute(sql, vals)
            conn.commit()

        except Exception:
            conn.rollback()
            try:
                cur.execute(SQL_MARK_COMPTE_INVALIDE_ETAPE3, (did,))
                conn.commit()
            except Exception:
                conn.rollback()

    cur.close()
    return count


# ======================================
# === SCRIPT PRINCIPAL : BOUCLE GLOBALE ===
# ======================================
def main():
    # 1) Connexion unique à la BDD
    conn = get_connexion()
    cur = conn.cursor()

    # 2) Charger la liste des URLs déjà connues pour éviter doublons
    cur.execute("SELECT post_brut_url FROM post_brut")
    urls_connues = set(row[0] for row in cur.fetchall())

    # 3) Compteur principal et compteur intermédiaire
    nouveaux_posts_insérés = 0
    since_last_enrich     = 0

    # 4) Barre de progression globale (0 → TARGET_NEW_POSTS)
    pbar = tqdm(total=TARGET_NEW_POSTS, initial=0, unit="tweet", desc="Extraction en cours")

    # 5) Boucle principale : tant que l’on n’a pas atteint TARGET_NEW_POSTS
    while nouveaux_posts_insérés < TARGET_NEW_POSTS:
        seuil_date = datetime.now(timezone.utc) - timedelta(hours=24)

        # (a) Parcours de tous les mots-clés
        for _, row in df_keywords.iterrows():
            if nouveaux_posts_insérés >= TARGET_NEW_POSTS:
                break  # on a atteint la cible

            categorie    = row["categorie"]
            keyword      = row["keyword"]
            buffer_posts = []
            cursor_token = None

            print(f"Recherche [{keyword}] (catégorie : {categorie})...")

            try:
                # Récupérer jusqu’à PER_KEYWORD_LIMIT posts pour ce mot-clé
                while len(buffer_posts) < PER_KEYWORD_LIMIT:
                    result = client.app.bsky.feed.search_posts(
                        params={"q": keyword, "cursor": cursor_token}
                    )
                    feed = result.posts
                    if not feed:
                        break
                    buffer_posts.extend(feed)
                    cursor_token = result.cursor
                    if cursor_token is None:
                        break

                buffer_posts = buffer_posts[:PER_KEYWORD_LIMIT]
            except Exception as e:
                print(f"Erreur récupération '{keyword}' → {e}")
                continue

            nb_ins_pour_ce_keyword = 0

            # (b) Insertion post par post
            for post in buffer_posts:
                if nouveaux_posts_insérés >= TARGET_NEW_POSTS:
                    break

                uri = post.uri
                if uri in urls_connues:
                    continue

                createdAt_str = getattr(post.record, "created_at", None)
                createdAt     = parse_created_at(createdAt_str)
                if createdAt is None or createdAt < seuil_date:
                    continue

                text           = getattr(post.record, "text", "").replace("\n", " ").replace("\r", "").strip()
                author_handle  = post.author.handle
                url_affichage  = f"https://bsky.app/profile/{author_handle}/post/{uri.split('/')[-1]}"
                date_scrap     = datetime.now(timezone.utc)
                # Si vous voulez exclure les stopwords du calcul de "poids", vous pouvez filtrer ici :
                # words = [w for w in text.split() if w.lower() not in stopwords_list]
                # poids = len(words)
                poids          = len(text.split())
                compte_did     = post.author.did
                has_media      = post.embed is not None
                timestamp      = round(time.time(), 3)

                try:
                    # 1) Insertion du compte avec date première analyse
                    cur.execute(SQL_INSERT_COMPTE, (compte_did, author_handle, date_scrap))
                except Exception:
                    conn.rollback()

                # 2) Insertion du post
                try:
                    cur.execute(SQL_INSERT_POST, (
                        uri, createdAt, text,
                        author_handle, url_affichage,
                        date_scrap, categorie, keyword,
                        poids, compte_did,
                        has_media, timestamp
                    ))
                    conn.commit()
                    urls_connues.add(uri)
                    nb_ins_pour_ce_keyword += 1
                    nouveaux_posts_insérés += 1
                    since_last_enrich += 1
                    pbar.update(1)
                except Exception:
                    conn.rollback()

                # 3) Dès que since_last_enrich ≥ ENRICH_INTERVAL, on déclenche Étape 2+3
                if since_last_enrich >= ENRICH_INTERVAL:
                    print("\n--- Palier atteint : exécution Étape 2 & 3 avant de poursuivre ---")
                    # Étape 2
                    count2 = etape2_enrichissement(conn)
                    print(f"Étape 2 terminée, {count2} comptes enrichis.")
                    # Étape 3
                    count3 = etape3_complement(conn)
                    print(f"Étape 3 terminée, {count3} comptes complétés.")
                    since_last_enrich = 0
                    print("--- Reprise de la récupération des tweets ---\n")

            # (c) Affichage après chaque mot-clé
            print(f"{nb_ins_pour_ce_keyword} posts insérés pour le mot-clé : {keyword}")
            print(f"Total cumulé de posts insérés : {nouveaux_posts_insérés}\n")

        # Fin du for mots-clés. On revient au while s’il reste des tweets à récupérer.
        print(f"Fin d’un tour complet de mots-clés. Total actuel : {nouveaux_posts_insérés}/{TARGET_NEW_POSTS}\n")

    # 6) Fin de la boucle principale : on ferme tout
    pbar.close()
    cur.close()
    conn.close()
    print(f"Extraction terminée : {TARGET_NEW_POSTS} nouveaux tweets insérés.")


if __name__ == "__main__":
    main()
