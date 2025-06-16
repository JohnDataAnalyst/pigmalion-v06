import psycopg2

# Connexion PostgreSQL
conn = psycopg2.connect(
    dbname="pigmalion_v04",
    user="postgres",
    password="Root",
    host="localhost",
    port=5432
)
cur = conn.cursor()

# (Optionnel) Supprimer les anciennes données
cur.execute("DELETE FROM synthese_quotidienne")

# Requête d’agrégation uniquement sur les posts en anglais
query = """
INSERT INTO synthese_quotidienne (
    date_aggregation, categorie_label, nb_posts,
    score_toxic, score_severe_toxic, score_obscene, score_threat,
    score_insult, score_identity_hate,
    score_anger, score_disgust, score_fear, score_joy,
    score_neutral, score_sadness, score_surprise
)
SELECT
    pb.post_brut_date::date AS date_aggregation,
    cat.post_clean_mesure_categories_label_predominant AS categorie_label,
    COUNT(*) AS nb_posts,

    -- Toxicité
    AVG(tox.post_clean_mesure_toxicite_score_toxic),
    AVG(tox.post_clean_mesure_toxicite_score_severe_toxic),
    AVG(tox.post_clean_mesure_toxicite_score_obscene),
    AVG(tox.post_clean_mesure_toxicite_score_threat),
    AVG(tox.post_clean_mesure_toxicite_score_insult),
    AVG(tox.post_clean_mesure_toxicite_score_identity_hate),

    -- Émotions
    AVG(emo.post_clean_mesure_emotion_score_anger),
    AVG(emo.post_clean_mesure_emotion_score_disgust),
    AVG(emo.post_clean_mesure_emotion_score_fear),
    AVG(emo.post_clean_mesure_emotion_score_joy),
    AVG(emo.post_clean_mesure_emotion_score_neutral),
    AVG(emo.post_clean_mesure_emotion_score_sadness),
    AVG(emo.post_clean_mesure_emotion_score_surprise)

FROM post_brut pb
JOIN post_clean pc ON pc.post_url = pb.post_brut_url
JOIN post_clean_mesure_categories cat ON cat.post_url = pc.post_url
JOIN post_clean_mesure_toxicite tox ON tox.post_url = pc.post_url
JOIN post_clean_mesure_emotion emo ON emo.post_url = pc.post_url

WHERE pb.post_brut_date IS NOT NULL
  AND pc.post_clean_langue = 'en'

GROUP BY pb.post_brut_date::date, cat.post_clean_mesure_categories_label_predominant
ORDER BY date_aggregation, categorie_label;
"""

cur.execute(query)
conn.commit()
cur.close()
conn.close()

print("✅ synthese_quotidienne remplie avec succès.")
