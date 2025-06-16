import os
import time
import pandas as pd
import psycopg2
from dotenv import load_dotenv
from atproto import Client
from tqdm import tqdm

# Chargement des variables d'environnement
load_dotenv(r"C:\Users\dell\Desktop\DATA\SUP DE VINCI\08 - PROJET THAMALIEN\05_PIGMALION_V05_DEF\.env07")

# Connexion à l'API Bluesky
client = Client()
client.login(
    os.getenv("BLUESKY_HANDLE"),
    os.getenv("BLUESKY_PASSWORD")
)

# Connexion à PostgreSQL
conn = psycopg2.connect(
    dbname=os.getenv("DB_NAME"),
    user=os.getenv("DB_USER"),
    password=os.getenv("DB_PASSWORD"),
    host=os.getenv("DB_HOST"),
    port=os.getenv("DB_PORT")
)
cur = conn.cursor()

# Requête : uniquement les comptes non traités
query = """
SELECT compte_did, compte_brut_handle,
       compte_nombre_publication,
       compte_brut_nombre_followers,
       compte_brut_date_creation
FROM compte_brut
WHERE compte_completion_02 IS NULL;
"""
df = pd.read_sql(query, conn)

# Compteurs
cumul_publications = 0
cumul_followers = 0
cumul_creation = 0
cumul_invalide = 0

# Traitement
for idx, row in tqdm(df.iterrows(), total=len(df), desc="Mise à jour partielle des comptes"):
    did = row["compte_did"]
    try:
        profile = client.app.bsky.actor.get_profile({"actor": did})
        p = profile.__dict__

        posts_count = p.get("posts_count")
        followers_count = p.get("followers_count")
        created_at = p.get("created_at")

        update_fields = {}
        if row["compte_nombre_publication"] is None and posts_count is not None:
            update_fields["compte_nombre_publication"] = posts_count
            cumul_publications += 1
        if row["compte_brut_nombre_followers"] is None and followers_count is not None:
            update_fields["compte_brut_nombre_followers"] = followers_count
            cumul_followers += 1
        if row["compte_brut_date_creation"] is None and created_at is not None:
            update_fields["compte_brut_date_creation"] = created_at
            cumul_creation += 1

        update_fields["compte_completion_02"] = 'OK'

        set_clause = ", ".join([f"{k} = %s" for k in update_fields.keys()])
        sql = f"""
            UPDATE compte_brut
            SET {set_clause}
            WHERE compte_did = %s;
        """
        values = list(update_fields.values()) + [did]
        cur.execute(sql, values)
        conn.commit()

    except Exception as e:
        conn.rollback()
        cumul_invalide += 1
        try:
            cur.execute(
                """
                UPDATE compte_brut
                SET compte_completion_02 = 'COMPTE INVALIDE'
                WHERE compte_did = %s;
                """,
                (did,)
            )
            conn.commit()
        except Exception as inner_e:
            conn.rollback()
            print(f"Erreur interne lors du marquage comme invalide pour {did} : {inner_e}")

    if (idx + 1) % 100 == 0:
        print(f"\nRapport après {idx + 1} comptes traités :")
        print(f" - compte_nombre_publication : {cumul_publications} valeurs ajoutées")
        print(f" - compte_brut_nombre_followers : {cumul_followers} valeurs ajoutées")
        print(f" - compte_brut_date_creation : {cumul_creation} valeurs ajoutées")

# Fin
print(f"\nComptes invalides rencontrés : {cumul_invalide}")
cur.close()
conn.close()
print("Mise à jour terminée.")
