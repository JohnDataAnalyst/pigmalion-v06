import os
import pandas as pd
from tqdm import tqdm
from dotenv import load_dotenv
from atproto import Client
import psycopg2

# === Chargement des identifiants depuis le bon .env ===
ENV_PATH = r"C:\Users\dell\Desktop\DATA\SUP DE VINCI\08 - PROJET THAMALIEN\05_PIGMALION_V05_DEF\.env07"
load_dotenv(ENV_PATH)

# === Connexion API Bluesky ===
client = Client()
client.login(
    os.getenv("BLUESKY_HANDLE"),
    os.getenv("BLUESKY_PASSWORD")
)

# === Connexion PostgreSQL ===
conn = psycopg2.connect(
    dbname=os.getenv("DB_NAME"),
    user=os.getenv("DB_USER"),
    password=os.getenv("DB_PASSWORD"),
    host=os.getenv("DB_HOST"),
    port=os.getenv("DB_PORT")
)
cur = conn.cursor()

# === Requête ciblant uniquement les comptes incomplets ET non marqués "OK" ===
query = """
SELECT compte_did, compte_brut_handle,
       compte_brut_avatar_url,
       compte_brut_is_verified,
       compte_brut_bio,
       compte_brut_banner_url
FROM compte_brut
WHERE compte_completion_01 IS DISTINCT FROM 'OK';
"""
df = pd.read_sql(query, conn)

# === Phase d’analyse : lignes incomplètes ===
colonnes_cibles = [
    "compte_brut_avatar_url",
    "compte_brut_is_verified",
    "compte_brut_bio",
    "compte_brut_banner_url"
]
df_incomplets = df[df[colonnes_cibles].isnull().any(axis=1)]
print(f"\n🔍 {len(df_incomplets)} comptes nécessitent un enrichissement.\n")

# === Fonction d'enrichissement si champ vide ===
def enrich_if_null(old, new):
    return new if old is None else old

# === Traitement API & mise à jour PostgreSQL ===
for _, row in tqdm(df_incomplets.iterrows(), total=len(df_incomplets), desc="Enrichissement comptes"):
    did = row["compte_did"]

    try:
        profile = client.app.bsky.actor.get_profile({"actor": did})

        cur.execute("SELECT * FROM compte_brut WHERE compte_did = %s", (did,))
        existing = cur.fetchone()
        columns = [desc[0] for desc in cur.description]
        data_dict = dict(zip(columns, existing))

        new_data = {
            "compte_did": did,
            "compte_brut_handle": row.get("compte_brut_handle"),
            "compte_brut_avatar_url": enrich_if_null(data_dict.get("compte_brut_avatar_url"), getattr(profile, "avatar", None)),
            "compte_brut_is_verified": enrich_if_null(data_dict.get("compte_brut_is_verified"), getattr(profile, "labels", None) is not None),
            "compte_brut_bio": enrich_if_null(data_dict.get("compte_brut_bio"), getattr(profile, "description", None)),
            "compte_brut_banner_url": enrich_if_null(data_dict.get("compte_brut_banner_url"), getattr(profile, "banner", None)),
        }

    except Exception as e:
        msg = str(e)
        if 'Profile not found' in msg or 'Account has been suspended' in msg:
            print(f"Compte introuvable ou suspendu pour {did}. Marqué comme 'OK'.")
            try:
                cur.execute("""
                    UPDATE compte_brut
                    SET compte_completion_01 = 'OK'
                    WHERE compte_did = %s;
                """, (did,))
                conn.commit()
            except Exception as inner_e:
                conn.rollback()
                print(f"Erreur en marquant OK pour {did} : {inner_e}")
            continue
        else:
            conn.rollback()
            print(f"Erreur pour {did} : {e}")
            continue

    try:
        cur.execute("""
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
                compte_brut_handle = EXCLUDED.compte_brut_handle,
                compte_brut_avatar_url = COALESCE(compte_brut.compte_brut_avatar_url, EXCLUDED.compte_brut_avatar_url),
                compte_brut_is_verified = COALESCE(compte_brut.compte_brut_is_verified, EXCLUDED.compte_brut_is_verified),
                compte_brut_bio = COALESCE(compte_brut.compte_brut_bio, EXCLUDED.compte_brut_bio),
                compte_brut_banner_url = COALESCE(compte_brut.compte_brut_banner_url, EXCLUDED.compte_brut_banner_url),
                compte_completion_01 = 'OK';
        """, new_data)
        conn.commit()

    except Exception as e:
        conn.rollback()
        print(f"Erreur lors de l'insertion pour {did} : {e}")

# === Nettoyage ===
cur.close()
conn.close()
print("\n✅ Mise à jour terminée.")
