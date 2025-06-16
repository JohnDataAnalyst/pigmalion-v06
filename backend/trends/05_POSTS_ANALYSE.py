import os
import psycopg2
import time
from dotenv import load_dotenv
from datetime import datetime
from tqdm import tqdm
import torch

from transformers import (
    AutoTokenizer,
    AutoModelForSequenceClassification,
    pipeline
)

# ───────────────────────────────────────────────────────────────────────────────
# === CONFIGURATION =============================================================
# ───────────────────────────────────────────────────────────────────────────────

# Chemin vers votre fichier .env (nouveau nom)
DOTENV_PATH = r"C:\Users\dell\Desktop\DATA\SUP DE VINCI\08 - PROJET THAMALIEN\05_PIGMALION_V05_DEF\.env07"
load_dotenv(DOTENV_PATH)

DB_HOST     = os.getenv("DB_HOST")
DB_PORT     = os.getenv("DB_PORT")
DB_NAME     = os.getenv("DB_NAME")
DB_USER     = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")

if not all([DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD]):
    raise ValueError("❌ Une ou plusieurs variables d’environnement sont manquantes dans .env07")

# Dispositif pour les pipelines (GPU si disponible, sinon CPU)
DEVICE = 0 if torch.cuda.is_available() else -1

# Chemins vers les modèles stockés localement
MODELS = {
    "emotion":    r"C:\Users\dell\Desktop\DATA\SUP DE VINCI\08 - PROJET THAMALIEN\05_PIGMALION_V05_DEF\models\j-hartmann_emotion-english-distilroberta-base",
    "categories": r"C:\Users\dell\Desktop\DATA\SUP DE VINCI\08 - PROJET THAMALIEN\05_PIGMALION_V05_DEF\models\cardiffnlp_tweet-topic-21-multi",
    "veracity":   r"C:\Users\dell\Desktop\DATA\SUP DE VINCI\08 - PROJET THAMALIEN\05_PIGMALION_V05_DEF\models\ghanashyamvtatti_roberta-fake-news",
    "irony":      r"C:\Users\dell\Desktop\DATA\SUP DE VINCI\08 - PROJET THAMALIEN\05_PIGMALION_V05_DEF\models\cardiffnlp_twitter-roberta-base-irony",
    "toxicity":   r"C:\Users\dell\Desktop\DATA\SUP DE VINCI\08 - PROJET THAMALIEN\05_PIGMALION_V05_DEF\models\unitary_toxic-bert",
    "tone":       r"C:\Users\dell\Desktop\DATA\SUP DE VINCI\08 - PROJET THAMALIEN\05_PIGMALION_V05_DEF\models\finiteautomata_bertweet-base-sentiment-analysis"
}

# Correspondance entre clefs et noms de tables PostgreSQL
TABLES = {
    "emotion":    "post_clean_mesure_emotion",
    "categories": "post_clean_mesure_categories",
    "veracity":   "post_clean_mesure_veracitedirecte",
    "irony":      "post_clean_mesure_ironie",
    "toxicity":   "post_clean_mesure_toxicite",
    "tone":       "post_clean_mesure_ton"
}

# Mappage des étiquettes renvoyées par le modèle "categories" vers vos colonnes
LABEL_MAPPING_CATEGORIES = {
    "news_&_social_concern":       "news_social_concern",
    "celebrity_&_pop_culture":     "pop_culture",
    "diaries_&_daily_life":        "other",
    "arts_&_culture":              "arts_entertainment",
    "travel_&_adventure":          "travel_adventure",
    "music":                       "pop_culture",
    "film_tv_&_video":             "arts_entertainment",
    "other_hobbies":               "other",
    "business_&_entrepreneurs":    "business_entrepreneurship",
    "relationships":               "relationships_dating",
    "fashion_&_style":             "fashion_style",
    "family":                      "family",
    "learning_&_educational":      "learning_educational",
    "fitness_&_health":            "health_fitness",
    "youth_&_student_life":        "youth_student_life",
    "science_&_technology":        "science_technology",
    "gaming":                      "sports_gaming",
    "food_&_dining":               "food_dining",
    "sports":                      "sports_gaming",
    "religion_&_spirituality":     "religion_spirituality",
    "pop_&_culture":               "pop_culture",
    "environment":                 "environment",
    "pets_&_animals":              "pets_animals",
    "lgbtq":                       "lgbtq",
    "other":                       "other"
}

# ───────────────────────────────────────────────────────────────────────────────
# === FONCTIONS UTILITAIRES =====================================================
# ───────────────────────────────────────────────────────────────────────────────

def get_conn():
    """
    Ouvre une connexion psycopg2 vers PostgreSQL en se basant sur les variables d’environnement.
    """
    return psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD
    )

def get_remaining_post_urls():
    """
    Récupère la liste de tous les post_url présents dans post_clean où post_clean_langue='en',
    puis retire ceux déjà analysés dans chacune des tables de mesure.
    """
    conn = get_conn()
    cur = conn.cursor()

    # 1) tous les posts en anglais
    cur.execute("""
        SELECT post_url 
        FROM post_clean 
        WHERE post_clean_langue = 'en';
    """)
    all_urls = {row[0] for row in cur.fetchall()}

    remaining = set(all_urls)
    # 2) pour chaque table de mesure, retire les urls déjà insérées
    for table in TABLES.values():
        cur.execute(f"SELECT post_url FROM {table};")
        done = {row[0] for row in cur.fetchall()}
        remaining -= done

    cur.close()
    conn.close()
    return list(remaining)

def fetch_post_content(post_url: str) -> str | None:
    """
    Récupère le contenu nettoyé (post_clean_contenu) d’un post donné.
    """
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT post_clean_contenu 
        FROM post_clean 
        WHERE post_url = %s;
    """, (post_url,))
    res = cur.fetchone()
    cur.close()
    conn.close()
    return res[0] if res else None

def insert_result(post_url: str, table: str, values: list, fields: str):
    """
    Insère les valeurs 'values' dans la table 'table' pour les colonnes
    spécifiées dans 'fields' (une chaîne de colonnes séparées par des virgules).
    ON CONFLICT(post_url) DO NOTHING pour éviter les doublons.
    """
    conn = get_conn()
    cur = conn.cursor()
    placeholders = ", ".join("%s" for _ in values)
    sql = f"""
        INSERT INTO {table} ({fields})
        VALUES ({placeholders})
        ON CONFLICT (post_url) DO NOTHING;
    """
    cur.execute(sql, values)
    conn.commit()
    cur.close()
    conn.close()

def load_pipeline_local(model_path: str, device: int):
    """
    Charge en local un pipeline de classification de texte à partir du dossier 'model_path'.
    Utilise AutoTokenizer et AutoModelForSequenceClassification avec local_files_only=True.
    """
    tokenizer = AutoTokenizer.from_pretrained(model_path, local_files_only=True)
    model     = AutoModelForSequenceClassification.from_pretrained(model_path, local_files_only=True)
    return pipeline(
        "text-classification",
        model= model,
        tokenizer= tokenizer,
        device= device,
        top_k= None
    )

def analyse_post(pipe, texte: str, label_mapping: dict | None = None):
    """
    Applique le pipeline 'pipe' sur le texte donné,
    construit un dictionnaire scores[label] = max(score),
    retourne (label_prédominant, score_prédominant, scores_dict, durée_analysis).
    """
    t0 = time.time()
    result = pipe(texte, top_k=None)
    # result est une liste de dicts [{ 'label': ..., 'score': ... }, ...]
    scores = {}
    for item in result:
        lbl = item["label"].lower()
        if label_mapping:
            lbl = label_mapping.get(lbl, lbl)
        # on garde le score max par label
        scores[lbl] = max(scores.get(lbl, 0.0), float(item["score"]))
    # label prédominant
    pred = max(scores, key=scores.get)
    duree = round(time.time() - t0, 3)
    return pred, scores[pred], scores, duree

# ───────────────────────────────────────────────────────────────────────────────
# === PROGRAMME PRINCIPAL ========================================================
# ───────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("📦 Chargement des modèles locaux...")

    # 1) Charger un pipeline pour chaque modèle
    pipelines: dict[str, pipeline] = {}
    for cle, chemin in MODELS.items():
        print(f"  • {cle} ← {chemin}")
        try:
            pipelines[cle] = load_pipeline_local(chemin, DEVICE)
        except Exception as e:
            print(f"❌ Échec chargement modèle '{cle}' depuis '{chemin}': {e}")
            raise SystemExit(1)

    print("✅ Tous les modèles ont été chargés.\n")

    # 2) Récupérer la liste des posts à analyser
    print("🔎 Récupération des URLs restantes à analyser...")
    urls = get_remaining_post_urls()
    total = len(urls)
    print(f"👉  Nombre de posts à traiter : {total}\n")

    # 3) Pour chaque post : fetch contenu, puis appliquer tous les pipelines
    for post_url in tqdm(urls, desc="Progression globale"):
        texte = fetch_post_content(post_url)
        if not texte:
            continue

        date_analyse = datetime.utcnow()

        for cle, pipe in pipelines.items():
            table = TABLES[cle]

            # Appliquer le modèle
            try:
                label_pred, score_pred, scores_dict, duree = analyse_post(
                    pipe,
                    texte,
                    LABEL_MAPPING_CATEGORIES if cle == "categories" else None
                )
            except Exception as e:
                print(f"❌ Erreur lors de l'analyse '{cle}' pour '{post_url}': {e}")
                continue

            # Préparer le `fields` et la liste `values` en fonction de chaque clé
            if cle == "emotion":
                fields = ", ".join([
                    "post_url",
                    "post_clean_mesure_emotion_date_analyse",
                    "post_clean_mesure_emotion_duree_analyse",
                    "post_clean_mesure_emotion_modele",
                    "post_clean_mesure_emotion_label_predominant",
                    "post_clean_mesure_emotion_score_predominant",
                    "post_clean_mesure_emotion_score_anger",
                    "post_clean_mesure_emotion_score_disgust",
                    "post_clean_mesure_emotion_score_fear",
                    "post_clean_mesure_emotion_score_joy",
                    "post_clean_mesure_emotion_score_neutral",
                    "post_clean_mesure_emotion_score_sadness",
                    "post_clean_mesure_emotion_score_surprise"
                ])
                # s'assurer que les clés existent dans scores_dict
                values = [
                    post_url,
                    date_analyse,
                    duree,
                    os.path.basename(MODELS[cle]),
                    label_pred,
                    score_pred,
                    scores_dict.get("anger", 0.0),
                    scores_dict.get("disgust", 0.0),
                    scores_dict.get("fear", 0.0),
                    scores_dict.get("joy", 0.0),
                    scores_dict.get("neutral", 0.0),
                    scores_dict.get("sadness", 0.0),
                    scores_dict.get("surprise", 0.0)
                ]

            elif cle == "tone":
                fields = ", ".join([
                    "post_url",
                    "post_clean_mesure_ton_date_analyse",
                    "post_clean_mesure_ton_duree_analyse",
                    "post_clean_mesure_ton_modele",
                    "post_clean_mesure_ton_label_predominant",
                    "post_clean_mesure_ton_score_predominant",
                    "post_clean_mesure_ton_score_positive",
                    "post_clean_mesure_ton_score_neutre",
                    "post_clean_mesure_ton_score_negative"
                ])
                values = [
                    post_url,
                    date_analyse,
                    duree,
                    os.path.basename(MODELS[cle]),
                    label_pred,
                    score_pred,
                    scores_dict.get("positive", 0.0),
                    scores_dict.get("neutral", 0.0),
                    scores_dict.get("negative", 0.0)
                ]

            elif cle == "veracity":
                fields = ", ".join([
                    "post_url",
                    "post_clean_mesure_veracitedirecte_date_analyse",
                    "post_clean_mesure_veracitedirecte_duree_analyse",
                    "post_clean_mesure_veracitedirecte_modele",
                    "post_clean_mesure_veracitedirecte_label_predominant",
                    "post_clean_mesure_veracitedirecte_score_predominant",
                    "post_clean_mesure_veracitedirecte_score_real",
                    "post_clean_mesure_veracitedirecte_score_fake"
                ])
                values = [
                    post_url,
                    date_analyse,
                    duree,
                    os.path.basename(MODELS[cle]),
                    label_pred,
                    score_pred,
                    scores_dict.get("real", 0.0),
                    scores_dict.get("fake", 0.0)
                ]

            elif cle == "irony":
                fields = ", ".join([
                    "post_url",
                    "post_clean_mesure_ironie_date_analyse",
                    "post_clean_mesure_ironie_duree_analyse",
                    "post_clean_mesure_ironie_modele",
                    "post_clean_mesure_ironie_label_predominant",
                    "post_clean_mesure_ironie_score_predominant",
                    "post_clean_mesure_ironie_score_non_irony",
                    "post_clean_mesure_ironie_score_irony"
                ])
                values = [
                    post_url,
                    date_analyse,
                    duree,
                    os.path.basename(MODELS[cle]),
                    label_pred,
                    score_pred,
                    scores_dict.get("non_irony", 0.0),
                    scores_dict.get("irony", 0.0)
                ]

            elif cle == "toxicity":
                fields = ", ".join([
                    "post_url",
                    "post_clean_mesure_toxicite_date_analyse",
                    "post_clean_mesure_toxicite_duree_analyse",
                    "post_clean_mesure_toxicite_modele",
                    "post_clean_mesure_toxicite_label_predominant",
                    "post_clean_mesure_toxicite_score_predominant",
                    "post_clean_mesure_toxicite_score_toxic",
                    "post_clean_mesure_toxicite_score_severe_toxic",
                    "post_clean_mesure_toxicite_score_obscene",
                    "post_clean_mesure_toxicite_score_threat",
                    "post_clean_mesure_toxicite_score_insult",
                    "post_clean_mesure_toxicite_score_identity_hate"
                ])
                values = [
                    post_url,
                    date_analyse,
                    duree,
                    os.path.basename(MODELS[cle]),
                    label_pred,
                    score_pred,
                    scores_dict.get("toxic", 0.0),
                    scores_dict.get("severe_toxic", 0.0),
                    scores_dict.get("obscene", 0.0),
                    scores_dict.get("threat", 0.0),
                    scores_dict.get("insult", 0.0),
                    scores_dict.get("identity_hate", 0.0)
                ]

            elif cle == "categories":
                # tri alphabétique des catégories mappées
                mapped_labels = sorted(set(LABEL_MAPPING_CATEGORIES.values()))
                score_cols = ", ".join(f"post_clean_mesure_categories_score_{lbl}" for lbl in mapped_labels)
                fields = ", ".join([
                    "post_url",
                    "post_clean_mesure_categories_date_analyse",
                    "post_clean_mesure_categories_duree_analyse",
                    "post_clean_mesure_categories_modele",
                    "post_clean_mesure_categories_label_predominant",
                    "post_clean_mesure_categories_score_predominant",
                    score_cols
                ])
                values = [
                    post_url,
                    date_analyse,
                    duree,
                    os.path.basename(MODELS[cle]),
                    label_pred,
                    score_pred
                ] + [scores_dict.get(lbl, 0.0) for lbl in mapped_labels]

            else:
                # clé inconnue : passer
                continue

            # 4) Insérer dans la table dédiée
            try:
                insert_result(post_url, table, values, fields)
            except Exception as e:
                print(f"❌ Échec INSERT dans '{table}' pour '{post_url}': {e}")

    print("\n✅ Analyse globale terminée.")
