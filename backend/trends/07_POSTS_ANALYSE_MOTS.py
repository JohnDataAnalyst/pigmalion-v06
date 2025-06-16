# -*- coding: utf-8 -*-
"""
Analyse & scoring des comptes – v2
 • Gestion des dates invalides (0001-01-01, NaT, NaN…)
 • Commentaire humain varié (colonne commentaire_bot)
"""

import os, random
from datetime import datetime, timezone
import psycopg2
import pandas as pd
from tqdm import tqdm
from dotenv import load_dotenv

# ------------------------------------------------------------------ #
# 1. Connexion PostgreSQL (.env07)
# ------------------------------------------------------------------ #
ENV_PATH = r"C:\Users\dell\Desktop\DATA\SUP DE VINCI\08 - PROJET THAMALIEN\05_PIGMALION_V05_DEF\.env07"

def get_conn():
    load_dotenv(ENV_PATH)
    return psycopg2.connect(
        dbname   = os.getenv("DB_NAME"),
        user     = os.getenv("DB_USER"),
        password = os.getenv("DB_PASSWORD"),
        host     = os.getenv("DB_HOST"),
        port     = os.getenv("DB_PORT")
    )

# ------------------------------------------------------------------ #
# 2. Dictionnaires pour le commentaire
# ------------------------------------------------------------------ #
INTRO = {
    "Probable bot": [
        "Tout porte à croire qu’il s’agit d’un bot :",
        "Les indices suggèrent un bot probable :",
        "Ce compte paraît fortement automatisé :"
    ],
    "Suspicion": [
        "Plusieurs signaux suscitent la méfiance :",
        "Ce compte présente certains éléments suspects :",
        "La fiabilité de ce compte est incertaine :"
    ],
    "Probable humain": [
        "Ce compte semble globalement fiable.",
        "Les indicateurs pointent vers un compte authentique.",
        "Aucun signe majeur de fraude : ce compte paraît humain."
    ]
}

MOTIFS_TXT = {
    "bio vide"        : ["la biographie n’est pas renseignée",
                         "aucune description n’est fournie"],
    "aucun site"      : ["aucun site personnel n’est indiqué",
                         "pas de lien externe référencé"],
    "fréq élevée"     : ["la fréquence de publication est très élevée",
                         "le rythme d’activité est inhabituellement soutenu"],
    "peu followers"   : ["le nombre de followers est très faible",
                         "l’audience du compte est presque inexistante"],
    "diff nom/handle" : ["le nom affiché diffère fortement du handle",
                         "l’écart entre nom et handle est inhabituel"],
    "non vérifié"     : ["le compte n’est pas vérifié",
                         "le badge de vérification est absent"]
}

POND = {           # pondérations inchangées
    "bio vide":        0.2,
    "aucun site":      0.1,
    "fréq élevée":     0.2,
    "peu followers":   0.2,
    "diff nom/handle": 0.2,
    "non vérifié":     0.1
}

# ------------------------------------------------------------------ #
# 3. Outils
# ------------------------------------------------------------------ #
def safe_days(d1, d2):
    """Renvoie la différence en jours ou None si impossible"""
    try:
        if pd.isna(d1) or pd.isna(d2):
            return None
        return (pd.to_datetime(d1, errors="coerce") -
                pd.to_datetime(d2, errors="coerce")).days
    except Exception:
        return None

def detecter_motifs(r):
    m = []
    if not r["compte_brut_bio"]:
        m.append("bio vide")
    if not r.get("compte_brut_url_site"):
        m.append("aucun site")

    jours = safe_days(r["compte_date_premiere_analyse"],
                      r["compte_brut_date_creation"])
    if jours and jours > 0 and r["compte_nombre_publication"]/jours > 20:
        m.append("fréq élevée")

    if r["compte_brut_nombre_followers"] is not None \
       and r["compte_brut_nombre_followers"] < 10:
        m.append("peu followers")

    if r.get("compte_brut_display_name") and r.get("compte_brut_handle"):
        if abs(len(r["compte_brut_display_name"])
               - len(r["compte_brut_handle"])) > 5:
            m.append("diff nom/handle")

    if r.get("compte_brut_is_verified") in [False, 'False', 'false', 0, '0', None]:
        m.append("non vérifié")
    return m

def score_from_motifs(motifs):
    """Somme des pondérations"""
    return round(sum(POND[m] for m in motifs), 2)

def commentaire(label, motifs):
    if label == "Probable humain":
        return random.choice(INTRO[label])
    intro = random.choice(INTRO[label])
    frag  = [random.choice(MOTIFS_TXT[m]) for m in motifs]
    corps = frag[0] if len(frag)==1 else ", ".join(frag[:-1])+" et "+frag[-1]
    phrase = f"{intro} {corps}."
    return phrase[0].upper()+phrase[1:]

# ------------------------------------------------------------------ #
# 4. Process principal
# ------------------------------------------------------------------ #
def analyser_et_inserer():
    conn = get_conn()
    cur  = conn.cursor()
    # lecture (pandas avertit car psycopg2 : sans gravité)
    df = pd.read_sql(
        "SELECT * FROM public.compte_brut",
        conn,
        parse_dates=["compte_brut_date_creation", "compte_date_premiere_analyse"]
    )

    print(f"🔍 Analyse de {len(df)} comptes…")
    res = []

    for _, row in tqdm(df.iterrows(), total=len(df), desc="Analyse"):
        motifs = detecter_motifs(row)
        score  = score_from_motifs(motifs)

        if score >= 0.6:
            label = "Probable bot"
        elif score >= 0.4:
            label = "Suspicion"
        else:
            label = "Probable humain"

        res.append((
            row["compte_did"],
            score,
            label,
            commentaire(label, motifs),
            datetime.now(timezone.utc)  # date_analyse_01
        ))

    # S’assurer que la colonne existe
    cur.execute("""
        ALTER TABLE public.compte_mesure_bot
        ADD COLUMN IF NOT EXISTS commentaire_bot text;
    """)

    # Vider tous les anciens résultats
    cur.execute("DELETE FROM public.compte_mesure_bot")

    # Insérer les nouvelles mesures
    cur.executemany("""
        INSERT INTO public.compte_mesure_bot
        (compte_did, score_bot, label_bot, commentaire_bot, date_analyse_01)
        VALUES (%s, %s, %s, %s, %s)
    """, res)

    conn.commit()
    cur.close()
    conn.close()
    print("✅ Table compte_mesure_bot mise à jour.")

# ------------------------------------------------------------------ #
if __name__ == "__main__":
    analyser_et_inserer()
